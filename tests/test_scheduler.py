"""Tests for the background task scheduler."""

import logging

from unittest.mock import MagicMock, patch

import pytest

from tablo_legacy_m3u.scheduler import Scheduler


@pytest.fixture
def task() -> MagicMock:
    """Mock callable used as the scheduler task."""
    return MagicMock()


@pytest.fixture
def scheduler(task: MagicMock) -> Scheduler:
    """Scheduler with a 300s interval and mock task."""
    return Scheduler("test", 300, task)


class TestStart:
    """Tests for `start()` scheduling the first timer."""

    def test_schedules_timer(
        self,
        scheduler: Scheduler,
    ) -> None:
        scheduler.warm()

        with patch("tablo_legacy_m3u.scheduler.threading.Timer") as mock_timer:
            scheduler.start()

        mock_timer.assert_called_once_with(300, scheduler._run)
        timer_instance = mock_timer.return_value

        assert timer_instance.daemon is True
        assert timer_instance.name == "scheduler-test"
        timer_instance.start.assert_called_once()

    def test_logs_warning_when_not_warmed(
        self, scheduler: Scheduler, caplog: pytest.LogCaptureFixture
    ) -> None:
        with (
            patch("tablo_legacy_m3u.scheduler.threading.Timer"),
            caplog.at_level(logging.WARNING),
        ):
            scheduler.start()

        assert "starting without warm cache" in caplog.text
