"""Tests for application initialization state."""

from tablo_legacy_m3u.app_state import AppState, DeviceStatus, InitPhase


class TestInitPhase:
    """Tests for InitPhase enum values."""

    def test_all_phases(self) -> None:
        assert set(InitPhase) == {
            InitPhase.DISCOVERING,
            InitPhase.CONNECTING,
            InitPhase.WARMING,
            InitPhase.READY,
            InitPhase.ERROR,
        }

    def test_values_are_lowercase(self) -> None:
        for phase in InitPhase:
            assert phase.value == phase.name.lower()


class TestDeviceStatus:
    """Tests for DeviceStatus defaults."""

    def test_defaults(self) -> None:
        status = DeviceStatus()

        assert status.server_info is None
        assert status.tuners == []
        assert status.harddrives == []
        assert status.guide_status is None
        assert status.last_probe is None
        assert status.error is None


class TestAppState:
    """Tests for AppState initialization and phase transitions."""

    def test_initial_state(self) -> None:
        state = AppState()

        assert state.phase == InitPhase.DISCOVERING
        assert not state.ready.is_set()
        assert state.tablo_client is None
        assert state.enable_epg is False
        assert state.schedulers == []
        assert state.error is None

    def test_set_phase_ready(self) -> None:
        state = AppState()

        state.set_phase(InitPhase.READY)

        assert state.phase == InitPhase.READY
        assert state.ready.is_set()

    def test_set_phase_error_clears_ready(self) -> None:
        state = AppState()
        state.set_phase(InitPhase.READY)
        assert state.ready.is_set()

        state.set_phase(InitPhase.ERROR)

        assert state.phase == InitPhase.ERROR
        assert not state.ready.is_set()

    def test_phase_transition_sequence(self) -> None:
        state = AppState()

        for phase in (
            InitPhase.DISCOVERING,
            InitPhase.CONNECTING,
            InitPhase.WARMING,
            InitPhase.READY,
        ):
            state.set_phase(phase)
            assert state.phase == phase

        assert state.ready.is_set()

    def test_device_status_is_independent_instance(self) -> None:
        state1 = AppState()
        state2 = AppState()

        assert state1.device_status is not state2.device_status
