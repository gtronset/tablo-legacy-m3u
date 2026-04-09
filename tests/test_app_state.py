"""Tests for application initialization state."""

import threading

import pytest

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

    def test_submit_tuner_refresh_executes_task(self) -> None:
        state = AppState()
        called = threading.Event()

        state.submit_tuner_refresh(called.set)
        state.drain_tuner_refresh()

        assert called.is_set()

    def test_submit_tuner_refresh_skips_if_pending(self) -> None:
        state = AppState()
        started = threading.Event()
        proceed = threading.Event()
        call_count = 0

        def slow_task() -> None:
            nonlocal call_count
            call_count += 1
            started.set()
            proceed.wait(timeout=5)

        state.submit_tuner_refresh(slow_task)
        assert started.wait(timeout=5)

        # Second submit should be skipped (first is still running)
        state.submit_tuner_refresh(slow_task)
        proceed.set()
        state.drain_tuner_refresh()

        assert call_count == 1

    def test_shutdown_executor(self) -> None:
        state = AppState()
        state.shutdown_executor()

        with pytest.raises(RuntimeError):
            state.submit_tuner_refresh(lambda: None)


class TestSseEventBus:
    """Tests for SSE subscribe/publish/unsubscribe."""

    def test_subscribe_returns_queue(self) -> None:
        state = AppState()
        q = state.sse_subscribe()

        assert q is not None
        assert q.empty()

    def test_publish_delivers_to_subscriber(self) -> None:
        state = AppState()
        q = state.sse_subscribe()

        state.sse_publish("tuners")

        assert q.get_nowait() == "tuners"

    def test_publish_delivers_to_multiple_subscribers(self) -> None:
        state = AppState()
        q1 = state.sse_subscribe()
        q2 = state.sse_subscribe()

        state.sse_publish("probe")

        assert q1.get_nowait() == "probe"
        assert q2.get_nowait() == "probe"

    def test_unsubscribe_stops_delivery(self) -> None:
        state = AppState()
        q = state.sse_subscribe()
        state.sse_unsubscribe(q)

        state.sse_publish("status")

        assert q.empty()

    def test_publish_with_no_subscribers(self) -> None:
        state = AppState()

        state.sse_publish("probe")  # should not raise

    def test_unsubscribe_idempotent(self) -> None:
        state = AppState()
        q = state.sse_subscribe()

        state.sse_unsubscribe(q)
        state.sse_unsubscribe(q)  # should not raise
