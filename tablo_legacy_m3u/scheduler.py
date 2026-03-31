"""Background task scheduler using threading.Timer."""

import logging
import threading

from collections.abc import Callable

logger = logging.getLogger(__name__)


class Scheduler:
    """Repeating background task on a fixed interval."""

    def __init__(
        self,
        name: str,
        interval: int,
        task: Callable[[], object],
    ) -> None:
        """Create a scheduler that can run a task every 'interval' seconds."""
        self._name = name
        self._interval = interval
        self._task = task
        self._stop_event = threading.Event()
        self._timer: threading.Timer | None = None

    def start(self) -> None:
        """Start the scheduler. First run happens after one interval."""
        logger.info("Scheduler %r started (every %ds)", self._name, self._interval)

        self._schedule()

    def stop(self) -> None:
        """Stop the scheduler and cancel the pending timer (if applicable)."""
        self._stop_event.set()

        if self._timer is not None:
            self._timer.cancel()

        logger.info("Scheduler %r stopped", self._name)

    def _schedule(self) -> None:
        """Schedule the next run of the task.

        In the edge case that the stop event is set while the task is running,
        it will prevent a new scheduled thread from being created.
        """
        if self._stop_event.is_set():
            return

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

        logger.info("Running scheduled task %r", self._name)

        try:
            self._task()
        except Exception:
            logger.exception("Scheduled task %r failed", self._name)

        self._schedule()
