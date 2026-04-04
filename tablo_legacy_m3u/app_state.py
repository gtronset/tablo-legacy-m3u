"""Application initialization state and Tablo device status."""

import threading

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
    last_probe: datetime | None = None
    error: str | None = None


class AppState:
    """Thread-safe container for application initialization state."""

    def __init__(self) -> None:
        """Initialize AppState with default values."""
        self._lock = threading.Lock()
        self._phase = InitPhase.DISCOVERING
        self.tablo_client: TabloClient | None = None
        self.device_status: DeviceStatus = DeviceStatus()
        self.enable_epg: bool = False
        self.schedulers: list[Scheduler] = []
        self.ready = threading.Event()
        self.error: str | None = None

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
