"""Tests for the background task scheduler."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from tablo_legacy_m3u.scheduler import Scheduler, SchedulerState
from tablo_legacy_m3u.tablo_client import TabloServerBusyError


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
    def test_raises_when_not_warmed(self, scheduler: Scheduler) -> None:
        with pytest.raises(RuntimeError, match="must be warmed before starting"):
            scheduler.start()


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

    def test_uses_server_retry_hint(
        self, scheduler: Scheduler, scheduler_task: MagicMock
    ) -> None:
        """`warm()` uses `TabloServerBusyError.retry_in_s` instead of backoff.

        The end result static values of retry wait time, depending on the server hint,
        rather than escalating backoff delays.
        """
        busy = TabloServerBusyError(MagicMock(), 5000)
        scheduler_task.side_effect = [busy, None]

        waits: list[float] = []
        original_wait = scheduler._stop_event.wait

        def capture_wait(timeout: float) -> bool:
            waits.append(timeout)
            return original_wait(timeout=0)

        with patch.object(scheduler._stop_event, "wait", side_effect=capture_wait):
            scheduler.warm()

        assert waits == [5.0]
        assert scheduler.state == SchedulerState.READY

    def test_server_busy_does_not_escalate_backoff(
        self, scheduler: Scheduler, scheduler_task: MagicMock
    ) -> None:
        """Repeated server_busy uses server hint each time, not exponential backoff."""
        busy = TabloServerBusyError(MagicMock(), 10000)
        scheduler_task.side_effect = [busy, busy, None]

        waits: list[float] = []
        original_wait = scheduler._stop_event.wait

        def capture_wait(timeout: float) -> bool:
            waits.append(timeout)
            return original_wait(timeout=0)

        with patch.object(scheduler._stop_event, "wait", side_effect=capture_wait):
            scheduler.warm()

        assert waits == [10.0, 10.0]


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
        assert scheduler.state == SchedulerState.WARMING


class TestRun:
    """Tests for `_run()` task execution and rescheduling."""

    def test_calls_task_and_reschedules(
        self, scheduler: Scheduler, scheduler_task: MagicMock, mock_timer: MagicMock
    ) -> None:

        scheduler.warm()
        scheduler_task.reset_mock()
        scheduler._run()

        scheduler_task.assert_called_once()
        mock_timer.assert_called_once_with(300, scheduler._run)
        mock_timer.return_value.start.assert_called_once()

    def test_survives_task_exception(
        self, scheduler: Scheduler, scheduler_task: MagicMock, mock_timer: MagicMock
    ) -> None:
        """Ensure `_run()` handles task exceptions gracefully / do not raise."""
        scheduler_task.side_effect = [None, RuntimeError("boom")]

        scheduler.warm()
        scheduler_task.reset_mock()
        scheduler._run()

        scheduler_task.assert_called_once()
        mock_timer.assert_called_once()
        assert scheduler.state == SchedulerState.ERROR

    def test_noop_when_stopped(
        self, scheduler: Scheduler, scheduler_task: MagicMock, mock_timer: MagicMock
    ) -> None:
        scheduler.stop()
        scheduler_task.reset_mock()

        scheduler._run()

        scheduler_task.assert_not_called()
        mock_timer.assert_not_called()

    @pytest.mark.usefixtures("mock_timer")
    def test_skips_task_when_not_ready(
        self, scheduler: Scheduler, scheduler_task: MagicMock
    ) -> None:
        """_run() reschedules without executing when state is not READY."""
        scheduler._run()

        scheduler_task.assert_not_called()

    @pytest.mark.usefixtures("mock_timer")
    def test_recovers_from_error(
        self, scheduler: Scheduler, scheduler_task: MagicMock
    ) -> None:
        """`_run()` transitions ERROR to READY on success."""
        scheduler.warm()
        scheduler_task.reset_mock()

        scheduler._state = SchedulerState.ERROR
        scheduler._run()

        assert scheduler.state == SchedulerState.READY


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


class TestState:
    """Tests for `SchedulerState` transitions."""

    def test_initial_state_is_idle(self, scheduler: Scheduler) -> None:
        assert scheduler.state == SchedulerState.IDLE

    def test_state_ready_after_warm(self, scheduler: Scheduler) -> None:
        scheduler.warm()

        assert scheduler.state == SchedulerState.READY

    def test_state_retrying_after_failure(
        self, scheduler: Scheduler, scheduler_task: MagicMock
    ) -> None:
        scheduler_task.side_effect = RuntimeError("fail")

        with patch.object(scheduler._stop_event, "wait", return_value=True):
            scheduler.warm()

        assert scheduler.state == SchedulerState.RETRYING

    def test_state_stopped_after_stop(self, scheduler: Scheduler) -> None:
        scheduler.stop()

        assert scheduler.state == SchedulerState.STOPPED

    def test_stop_overrides_any_state(self, scheduler: Scheduler) -> None:
        scheduler.warm()

        assert scheduler.state == SchedulerState.READY

        scheduler.stop()

        assert scheduler.state == SchedulerState.STOPPED  # type: ignore[comparison-overlap]

    @pytest.mark.usefixtures("mock_timer")
    def test_state_error_after_run_failure(
        self, scheduler: Scheduler, scheduler_task: MagicMock
    ) -> None:
        scheduler_task.side_effect = [None, RuntimeError("boom")]

        scheduler.warm()
        scheduler._run()

        assert scheduler.state == SchedulerState.ERROR


class TestStatus:
    """Tests for scheduler status properties."""

    def test_initial_status(self, scheduler: Scheduler) -> None:
        assert scheduler.last_success is None
        assert scheduler.next_run is None
        assert scheduler.last_error is None

    @pytest.mark.usefixtures("mock_timer")
    def test_warm_success_sets_last_success(self, scheduler: Scheduler) -> None:
        scheduler.warm()

        assert scheduler.last_success is not None
        assert scheduler.last_error is None

    def test_warm_failure_sets_last_error(
        self, scheduler: Scheduler, scheduler_task: MagicMock
    ) -> None:
        scheduler_task.side_effect = RuntimeError("fail")

        with patch.object(scheduler._stop_event, "wait", return_value=True):
            scheduler.warm()

        assert scheduler.last_success is None
        assert scheduler.last_error == "fail"

    @pytest.mark.usefixtures("mock_timer")
    def test_run_success_sets_last_success(self, scheduler: Scheduler) -> None:
        scheduler.warm()
        scheduler._run()

        assert scheduler.last_success is not None
        assert scheduler.last_error is None
        assert scheduler.state == SchedulerState.READY

    @pytest.mark.usefixtures("mock_timer")
    def test_run_failure_sets_last_error(
        self, scheduler: Scheduler, scheduler_task: MagicMock
    ) -> None:
        scheduler_task.side_effect = [None, RuntimeError("boom")]

        scheduler.warm()
        scheduler_task.reset_mock()
        scheduler._run()

        assert scheduler.last_success is not None
        assert scheduler.last_error == "boom"
        assert scheduler.state == SchedulerState.ERROR

    @pytest.mark.usefixtures("mock_timer")
    def test_schedule_sets_next_run(self, scheduler: Scheduler) -> None:
        scheduler._schedule()

        assert scheduler.next_run is not None

    @pytest.mark.usefixtures("mock_timer")
    def test_stop_clears_next_run(self, scheduler: Scheduler) -> None:
        scheduler._schedule()
        assert scheduler.next_run is not None

        scheduler.stop()
        assert scheduler.next_run is None
