"""Background task scheduler using threading.Timer."""

import logging
import threading

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from tablo_legacy_m3u.tablo_client import TabloServerBusyError

logger = logging.getLogger(__name__)


class SchedulerState(StrEnum):
    """Possible states for a Scheduler."""

    IDLE = "idle"
    WARMING = "warming"
    RETRYING = "retrying"
    READY = "ready"
    ERROR = "error"
    STOPPED = "stopped"


class Scheduler:
    """Repeating background task on a fixed interval."""

    INITIAL_RETRY_DELAY: int = 60  # 1 minute
    MAX_RETRY_DELAY: int = 900  # 15 minutes

    def __init__(
        self,
        name: str,
        interval: int,
        task: Callable[[], object],
        on_state_change: Callable[[], None] | None = None,
    ) -> None:
        """Create a scheduler that can run a task every 'interval' seconds."""
        self._name = name
        self._interval = interval
        self._task = task
        self._stop_event = threading.Event()
        self._timer: threading.Timer | None = None
        self._state = SchedulerState.IDLE
        self._last_success: datetime | None = None
        self._next_run: datetime | None = None
        self._last_error: str | None = None
        self._on_state_change = on_state_change

    @property
    def name(self) -> str:
        """Convenience property to get the scheduler name."""
        return self._name

    @property
    def state(self) -> SchedulerState:
        """Convenience property to get the scheduler state."""
        return self._state

    @property
    def last_success(self) -> datetime | None:
        """Convenience property to get the last successful run time."""
        return self._last_success

    @property
    def next_run(self) -> datetime | None:
        """Convenience property to get the next scheduled run time."""
        return self._next_run

    @property
    def last_error(self) -> str | None:
        """Convenience property to get the last error message."""
        return self._last_error

    def _set_state(self, state: SchedulerState) -> bool:
        """Update state unless stopped. Returns False if stopped.

        Used to prevent state changes after stopping, even in edge cases where the stop
        event is set while a task is running or during the warm retry loop.
        Effectively a TOCTOU guard.
        """
        if self._stop_event.is_set():
            return False
        self._state = state

        if self._on_state_change:
            try:
                self._on_state_change()
            except Exception:
                logger.exception("`on_state_change` callback failed for %r", self._name)

        return True

    def warm(self) -> None:  # noqa: PLR0911
        """Attempt initial cache warm. Retries with backoff on failure."""
        delay = self.INITIAL_RETRY_DELAY

        while not self._stop_event.is_set():
            if not self._set_state(SchedulerState.WARMING):
                return

            try:
                self._task()

                self._last_success = datetime.now(UTC)
                self._last_error = None

                if not self._set_state(SchedulerState.READY):
                    return

                return
            except TabloServerBusyError as e:
                self._last_error = str(e)

                if not self._set_state(SchedulerState.RETRYING):
                    return

                logger.warning(
                    "Initial %r fetch: server busy, retrying in %ds",
                    self._name,
                    int(e.retry_in_s),
                )

                if self._stop_event.wait(timeout=e.retry_in_s):
                    return
            except Exception as e:  # noqa: BLE001, Scheduler must survive task failures
                self._last_error = str(e)

                if not self._set_state(SchedulerState.RETRYING):
                    return

                logger.warning(
                    "Initial %r fetch failed, retrying in %ds",
                    self._name,
                    delay,
                )

                if self._stop_event.wait(timeout=delay):
                    return  # stopped during wait

                delay = min(delay * 2, self.MAX_RETRY_DELAY)

    def warm_async(self) -> None:
        """Start cache warming in a background thread."""
        self._set_state(SchedulerState.WARMING)
        thread = threading.Thread(
            target=self.warm,
            name=f"warm-{self._name}",
            daemon=True,
        )
        thread.start()

    def start(self) -> None:
        """Start the scheduler. First run happens after one interval."""
        if self._state not in {
            SchedulerState.READY,
            SchedulerState.WARMING,
            SchedulerState.RETRYING,
        }:
            msg = (
                f"Scheduler {self._name!r} must be warmed"
                f" before starting (state: {self._state})"
            )
            raise RuntimeError(msg)

        logger.info("Scheduler %r started (every %ds)", self._name, self._interval)

        self._schedule()

    def stop(self) -> None:
        """Stop the scheduler and cancel the pending timer (if applicable)."""
        self._stop_event.set()
        if self._timer is not None:
            self._timer.cancel()

        self._state = SchedulerState.STOPPED
        self._next_run = None

        logger.info("Scheduler %r stopped", self._name)

    def _schedule(self) -> None:
        """Schedule the next run of the task.

        In the edge case that the stop event is set while the task is running,
        it will prevent a new scheduled thread from being created.
        """
        if self._stop_event.is_set():
            return

        self._next_run = datetime.now(UTC) + timedelta(seconds=self._interval)
        self._timer = threading.Timer(self._interval, self._run)
        self._timer.daemon = True
        self._timer.name = f"scheduler-{self._name}"
        self._timer.start()

    def _run(self) -> None:
        """Run the scheduled task and reschedule the next run.

        Catches and logs any exceptions from the task to prevent the scheduler from
        stopping. In the edge case that the stop event is set while the task is running,
        it will prevent the next run from being scheduled.
        """
        if self._stop_event.is_set():
            return

        if self._state not in {SchedulerState.READY, SchedulerState.ERROR}:
            self._schedule()
            return

        logger.info("Running scheduled task %r", self._name)

        try:
            self._task()
            self._last_success = datetime.now(UTC)
            self._last_error = None

            if not self._set_state(SchedulerState.READY):
                return

        except Exception as e:
            self._last_error = str(e)
            logger.exception("Scheduled task %r failed", self._name)

            if not self._set_state(SchedulerState.ERROR):
                return

        self._schedule()
