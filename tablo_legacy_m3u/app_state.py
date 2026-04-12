"""Application initialization state and Tablo device status."""

import contextlib
import queue
import threading

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from tablo_legacy_m3u.tablo_types import (
    GuideStatus,
    HarddriveInfo,
    ServerInfo,
    TunerStatus,
)
from tablo_legacy_m3u.version_check import VersionChecker

if TYPE_CHECKING:
    from tablo_legacy_m3u.scheduler import Scheduler
    from tablo_legacy_m3u.tablo_client import TabloClient


class InitPhase(StrEnum):
    """Initialization lifecycle phases."""

    DISCOVERING = "discovering"
    CONNECTING = "connecting"
    WARMING = "warming"
    READY = "ready"
    ERROR = "error"


@dataclass
class DeviceStatus:
    """Snapshot of Tablo device health, updated by the device probe."""

    server_info: ServerInfo | None = None
    tuners: list[TunerStatus] = field(default_factory=list)
    harddrives: list[HarddriveInfo] = field(default_factory=list)
    guide_status: GuideStatus | None = None
    last_guide_update: datetime | None = None
    last_probe: datetime | None = None
    error: str | None = None


class AppState:
    """Container for application initialization state.

    Concurrency:
    - `phase` transitions are strictly thread-safe.
    - `tablo_client`, `enable_epg`, and `schedulers` are sequentially populated by the
      background init thread. They are safe to read at any time (relying on initial
      defaults and Python's GIL for atomic reference updates), but will only reflect
      their fully populated state once `ready.is_set()` is True.
    - `device_status` is updated by the background probe and safely read by web
      threads via atomic reference assignments.
    """

    def __init__(self, check_for_updates: bool = True) -> None:
        """Initialize AppState with default values."""
        self._lock = threading.Lock()
        self._phase = InitPhase.DISCOVERING
        self.tablo_client: TabloClient | None = None
        self.device_status: DeviceStatus = DeviceStatus()
        self.enable_epg: bool = False
        self.schedulers: list[Scheduler] = []
        self.ready = threading.Event()
        self.error: str | None = None
        self._tuner_executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1)
        self._tuner_future: Future[None] | None = None
        self._tuner_lock = threading.Lock()
        self._sse_subscribers: set[queue.Queue[str]] = set()
        self._sse_lock = threading.Lock()
        self.version_checker = VersionChecker(enabled=check_for_updates)

    def sse_subscribe(self) -> queue.Queue[str]:
        """Subscribe to SSE events.

        Returns a bounded queue that will receive published events.
        Events are dropped if the queue is full (stalled client).
        """
        q: queue.Queue[str] = queue.Queue(maxsize=16)
        with self._sse_lock:
            self._sse_subscribers.add(q)
        return q

    def sse_unsubscribe(self, q: queue.Queue[str]) -> None:
        """Unsubscribe from SSE events."""
        with self._sse_lock:
            self._sse_subscribers.discard(q)

    def sse_publish(self, event: str) -> None:
        """Publish an SSE event to all subscribers."""
        with self._sse_lock:
            subscribers = list(self._sse_subscribers)
        for q in subscribers:
            with contextlib.suppress(queue.Full):
                q.put_nowait(event)

    def submit_tuner_refresh(self, task: Callable[[], None]) -> None:
        """Submit a tuner refresh, skipping if one is already pending."""
        with self._tuner_lock:
            if self._tuner_future is None or self._tuner_future.done():
                self._tuner_future = self._tuner_executor.submit(task)

    def drain_tuner_refresh(self, timeout: float = 5) -> None:
        """Block until any pending tuner refresh completes. For testing."""
        self._tuner_executor.submit(lambda: None).result(timeout=timeout)

    def shutdown_executor(self) -> None:
        """Shut down the tuner refresh executor."""
        self._tuner_executor.shutdown(wait=False, cancel_futures=True)
        self.version_checker.shutdown()

    @property
    def phase(self) -> InitPhase:
        """Convenience property to get the current app phase."""
        return self._phase

    def set_phase(self, phase: InitPhase) -> None:
        """Transition to a new phase. Thread-safe."""
        with self._lock:
            self._phase = phase
            if phase == InitPhase.READY:
                self.ready.set()
            elif phase == InitPhase.ERROR:
                self.ready.clear()
