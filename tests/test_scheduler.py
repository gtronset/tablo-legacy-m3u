"""Tests for the background task scheduler."""

import logging

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from tablo_legacy_m3u.scheduler import Scheduler, SchedulerState


@pytest.fixture
def mock_timer() -> Generator[MagicMock]:
    """Patch threading.Timer to prevent real threads in tests."""
    with patch("tablo_legacy_m3u.scheduler.threading.Timer") as mock:
        yield mock


class TestStart:
    """Tests for `start()` scheduling the first timer."""

    def test_schedules_timer(
        self,
        scheduler: Scheduler,
        mock_timer: MagicMock,
    ) -> None:
        scheduler.warm()
        scheduler.start()

        mock_timer.assert_called_once_with(300, scheduler._run)
        timer_instance = mock_timer.return_value

        assert timer_instance.daemon is True
        assert timer_instance.name == "scheduler-test"
        timer_instance.start.assert_called_once()

    @pytest.mark.usefixtures("mock_timer")
    def test_logs_warning_when_not_warmed(
        self,
        scheduler: Scheduler,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        with caplog.at_level(logging.WARNING):
            scheduler.start()

        assert "starting in idle state" in caplog.text


class TestStop:
    """Tests for `stop()` cancellation and cleanup."""

    def test_sets_stop_event(self, scheduler: Scheduler) -> None:
        scheduler.stop()

        assert scheduler._stop_event.is_set()
        assert scheduler.state == SchedulerState.STOPPED

    def test_cancels_pending_timer(
        self, scheduler: Scheduler, mock_timer: MagicMock
    ) -> None:
        scheduler.warm()

        scheduler.start()

        scheduler.stop()

        mock_timer.return_value.cancel.assert_called_once()
        assert scheduler.state == SchedulerState.STOPPED

    def test_stop_without_timer(self, scheduler: Scheduler) -> None:
        """Stopping before start should not raise."""
        scheduler.stop()
        assert scheduler.state == SchedulerState.STOPPED


class TestWarm:
    """Tests for `warm()` initial cache warming with retry logic."""

    def test_calls_task_and_marks_warmed(
        self, scheduler: Scheduler, scheduler_task: MagicMock
    ) -> None:
        scheduler.warm()

        scheduler_task.assert_called_once()
        assert scheduler.state == SchedulerState.READY

    def test_retries_on_failure(
        self, scheduler: Scheduler, scheduler_task: MagicMock
    ) -> None:
        scheduler_task.side_effect = [RuntimeError("fail"), None]

        with patch.object(scheduler._stop_event, "wait", return_value=False):
            scheduler.warm()

        assert scheduler_task.call_count == 2  # noqa: PLR2004, 1 initial call + 1 retry
        assert scheduler.state == SchedulerState.READY

    def test_backoff_caps_at_max_delay(
        self, scheduler: Scheduler, scheduler_task: MagicMock
    ) -> None:
        scheduler_task.side_effect = [RuntimeError] * 5 + [None]
        waits: list[float] = []

        original_wait = scheduler._stop_event.wait

        def capture_wait(timeout: float) -> bool:
            waits.append(timeout)

            return original_wait(timeout=0)  # return immediately

        with patch.object(scheduler._stop_event, "wait", side_effect=capture_wait):
            scheduler.warm()

        # 60 → 120 → 240 → 480 → 900 (capped)
        assert waits == [60, 120, 240, 480, 900]

    def test_exits_when_stopped_during_wait(
        self, scheduler: Scheduler, scheduler_task: MagicMock
    ) -> None:
        scheduler_task.side_effect = RuntimeError("fail")

        with patch.object(scheduler._stop_event, "wait", return_value=True):
            scheduler.warm()

        scheduler_task.assert_called_once()

        assert scheduler.state == SchedulerState.RETRYING


class TestWarmAsync:
    """Tests for `warm_async()` background warming."""

    def test_starts_daemon_thread(self, scheduler: Scheduler) -> None:
        with patch("tablo_legacy_m3u.scheduler.threading.Thread") as mock_thread:
            scheduler.warm_async()

        mock_thread.assert_called_once_with(
            target=scheduler.warm,
            name="warm-test",
            daemon=True,
        )
        mock_thread.return_value.start.assert_called_once()


class TestRun:
    """Tests for `_run()` task execution and rescheduling."""

    def test_calls_task_and_reschedules(
        self, scheduler: Scheduler, scheduler_task: MagicMock, mock_timer: MagicMock
    ) -> None:
        scheduler_task.reset_mock()

        scheduler._run()

        scheduler_task.assert_called_once()
        mock_timer.assert_called_once_with(300, scheduler._run)
        mock_timer.return_value.start.assert_called_once()

    def test_survives_task_exception(
        self, scheduler: Scheduler, scheduler_task: MagicMock, mock_timer: MagicMock
    ) -> None:
        """Ensure `_run()` handles task exceptions gracefully / do not raise."""
        scheduler_task.side_effect = RuntimeError("boom")

        scheduler._run()

        scheduler_task.assert_called_once()
        mock_timer.assert_called_once()

    def test_noop_when_stopped(
        self, scheduler: Scheduler, scheduler_task: MagicMock, mock_timer: MagicMock
    ) -> None:
        scheduler.stop()
        scheduler_task.reset_mock()

        scheduler._run()

        scheduler_task.assert_not_called()
        mock_timer.assert_not_called()


class TestSchedule:
    """Tests for `_schedule()` timer creation."""

    def test_creates_daemon_timer(
        self, scheduler: Scheduler, mock_timer: MagicMock
    ) -> None:
        scheduler._schedule()

        mock_timer.assert_called_once_with(300, scheduler._run)
        timer_instance = mock_timer.return_value

        assert timer_instance.daemon is True
        assert timer_instance.name == "scheduler-test"
        timer_instance.start.assert_called_once()

    def test_noop_when_stopped(
        self, scheduler: Scheduler, mock_timer: MagicMock
    ) -> None:
        scheduler.stop()

        scheduler._schedule()

        mock_timer.assert_not_called()
