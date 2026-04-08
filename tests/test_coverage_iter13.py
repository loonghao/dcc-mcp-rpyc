"""Iteration 13 coverage tests — push 99% to 100%.

Covers the 30 remaining missing statements across:
  - scene/base.py        (gimbal-lock rotation branch, model_dump)
  - scene/rpyc.py        (non-list fallback in get_objects, get_selection generic path)
  - transport/http.py    (disconnect exception path)
  - transport/websocket.py (reader thread join, exception-while-not-connected branch)
  - server/factory.py    (unregister thread exception path)
  - skills/scanner.py    (stop_watching no-watcher, reload no-watcher, register failure)
  - discovery/registry.py (ensure_strategy invalid type)
  - client/base.py       (file-based discovery success path)
  - application/adapter.py (adapter line 76 - initialize_action_paths)
  - client/async_base.py  (close when connection already None)
"""

# Import built-in modules
import math
import threading
import time
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest


# =============================================================================
# scene/base.py — TransformMatrix gimbal-lock branch (lines 71-73)
# =============================================================================


class TestTransformMatrixGimbalLock:
    """Cover the gimbal-lock branch (sy <= 1e-6) in TransformMatrix.rotation."""

    def test_gimbal_lock_branch(self) -> None:
        """When sy is near zero the else branch computes rx/ry differently."""
        from dcc_mcp_ipc.scene.base import TransformMatrix

        # Construct a matrix where sqrt(m[0]**2 + m[1]**2) is effectively 0.
        # For this we need m[0]=0 and m[1]=0.
        # Use a near-gimbal-lock rotation matrix where first two elements are ~0.
        m = [0.0] * 16
        # m[0]=0, m[1]=0 → sy = 0 → else branch
        # m[8] and m[9], m[4], m[5] drive the result
        m[0] = 0.0
        m[1] = 0.0
        m[4] = 1.0
        m[5] = 0.0
        m[8] = 0.0
        m[9] = 1.0
        m[10] = 0.0
        # translation/homogeneous don't matter for rotation
        m[15] = 1.0
        tm = TransformMatrix(matrix=m)
        rx, ry, rz = tm.rotation
        # rz should be 0 in the gimbal-lock branch
        assert rz == pytest.approx(0.0)
        # Just verify it runs without exception and returns three values
        assert isinstance(rx, float)
        assert isinstance(ry, float)

    def test_transform_matrix_model_dump_returns_dict(self) -> None:
        """TransformMatrix.model_dump() should return an asdict-compatible dict."""
        from dcc_mcp_ipc.scene.base import TransformMatrix

        tm = TransformMatrix()
        data = tm.model_dump()
        assert isinstance(data, dict)
        assert "matrix" in data
        assert len(data["matrix"]) == 16


# =============================================================================
# scene/rpyc.py — non-list return falls through to generic (line 450→456)
# and get_selection generic fallback (lines 529-533)
# =============================================================================


class TestRpycSceneFallbacks:
    """Cover fallback paths that were previously untested."""

    def test_get_objects_non_list_falls_to_generic(self) -> None:
        """When DCC script returns a non-list the method falls to _generic_get_objects."""
        from dcc_mcp_ipc.scene.rpyc import RPyCSceneInfo

        # Script returns a dict instead of a list → isinstance check fails → generic
        execute = MagicMock(return_value={"unexpected": "dict"})
        si = RPyCSceneInfo(dcc_name="maya", execute_func=execute)
        # _generic_get_objects will call execute again; make second call return []
        execute.side_effect = [{"unexpected": "dict"}, []]
        result = si.get_objects()
        assert isinstance(result, list)

    def test_get_selection_generic_fallback_returns_list(self) -> None:
        """get_selection falls to generic path when DCC script returns non-list."""
        from dcc_mcp_ipc.scene.rpyc import RPyCSceneInfo

        # First call (DCC-specific) returns a non-iterable value → generic path
        call_count = [0]

        def _exec(code):
            call_count[0] += 1
            if call_count[0] == 1:
                return "not_a_list"   # triggers non-list branch in get_selection
            raise Exception("generic also fails")  # generic path also fails → []

        si = RPyCSceneInfo(dcc_name="maya", execute_func=_exec)
        result = si.get_selection()
        assert result == []

    def test_get_hierarchy_returns_dict_instead_of_SceneHierarchy(self) -> None:
        """When DCC script returns a non-dict the code falls to build from objects."""
        from dcc_mcp_ipc.scene.rpyc import RPyCSceneInfo

        execute = MagicMock(return_value="not_a_dict")
        si = RPyCSceneInfo(dcc_name="maya", execute_func=execute)
        result = si.get_hierarchy()
        # Fallback: build from get_objects → which also fails → empty hierarchy
        from dcc_mcp_ipc.scene.base import SceneHierarchy

        assert isinstance(result, SceneHierarchy)

    def test_get_materials_non_list_returns_empty(self) -> None:
        """When DCC script returns a non-list for materials, result is []."""
        from dcc_mcp_ipc.scene.rpyc import RPyCSceneInfo

        execute = MagicMock(return_value=42)  # not a list
        si = RPyCSceneInfo(dcc_name="maya", execute_func=execute)
        result = si.get_materials()
        assert result == []

    def test_get_cameras_non_list_returns_empty(self) -> None:
        """When DCC script returns a non-list for cameras, result is []."""
        from dcc_mcp_ipc.scene.rpyc import RPyCSceneInfo

        execute = MagicMock(return_value="camera_string")  # not a list
        si = RPyCSceneInfo(dcc_name="maya", execute_func=execute)
        result = si.get_cameras()
        assert result == []

    def test_get_lights_non_list_returns_empty(self) -> None:
        """When DCC script returns a non-list for lights, result is []."""
        from dcc_mcp_ipc.scene.rpyc import RPyCSceneInfo

        execute = MagicMock(return_value=None)  # not a list
        si = RPyCSceneInfo(dcc_name="maya", execute_func=execute)
        result = si.get_lights()
        assert result == []

    def test_get_scene_name_private_blender_path(self) -> None:
        """Cover blender branch in _get_scene_name."""
        from dcc_mcp_ipc.scene.rpyc import RPyCSceneInfo

        execute = MagicMock(return_value="my_scene.blend")
        si = RPyCSceneInfo(dcc_name="blender", execute_func=execute)
        result = si._get_scene_name()
        assert result == "my_scene.blend"

    def test_get_scene_name_private_scene_error_returns_empty(self) -> None:
        """When _exec raises SceneError in _get_scene_name, return ''."""
        from dcc_mcp_ipc.scene.base import SceneError
        from dcc_mcp_ipc.scene.rpyc import RPyCSceneInfo

        execute = MagicMock(side_effect=SceneError("fail", dcc_type="maya"))
        si = RPyCSceneInfo(dcc_name="maya", execute_func=execute)
        result = si._get_scene_name()
        assert result == ""


# =============================================================================
# transport/http.py — disconnect raises exception (lines 121-122)
# =============================================================================


class TestHTTPTransportDisconnectException:
    """Cover the exception-swallowing branch in HTTPTransport.disconnect."""

    @patch("dcc_mcp_ipc.transport.http.http.client.HTTPConnection")
    def test_disconnect_close_raises_is_swallowed(self, MockHTTPConn):
        from dcc_mcp_ipc.transport.http import HTTPTransport
        from dcc_mcp_ipc.transport.http import HTTPTransportConfig
        from dcc_mcp_ipc.transport.base import TransportState

        mock_conn = MagicMock()
        mock_conn.close.side_effect = OSError("connection already closed")
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig())
        transport.connect()
        # Should not raise even though close() throws
        transport.disconnect()
        assert transport.state == TransportState.DISCONNECTED


# =============================================================================
# transport/websocket.py — reader thread join (line 212) and
# exception-while-not-connected (376→378)
# =============================================================================


class TestWebSocketTransportMissingBranches:
    """Cover reader-thread join and non-CONNECTED exception branch."""

    def test_disconnect_joins_alive_reader_thread(self) -> None:
        """disconnect() calls reader_thread.join when it is alive (line 212)."""
        from dcc_mcp_ipc.transport.websocket import WebSocketTransport
        from dcc_mcp_ipc.transport.websocket import WebSocketTransportConfig
        from dcc_mcp_ipc.transport.base import TransportState

        config = WebSocketTransportConfig(host="localhost", port=8765)
        t = WebSocketTransport(config)

        # Inject a fake reader thread that stays "alive" for 0.1 s
        barrier = threading.Event()

        def _long_running():
            barrier.wait(timeout=5.0)

        reader = threading.Thread(target=_long_running, daemon=True)
        reader.start()
        t._reader_thread = reader

        # Also inject a stopped writer thread (not alive)
        writer = threading.Thread(target=lambda: None, daemon=True)
        writer.start()
        writer.join()  # wait for it to finish
        t._writer_thread = writer

        # Signal reader to stop so join(timeout=2) completes
        barrier.set()

        mock_ws = MagicMock()
        t._ws = mock_ws
        t._state = TransportState.CONNECTED

        t.disconnect()

        assert t._reader_thread is None
        assert t._writer_thread is None

    def test_reader_exception_while_disconnecting(self) -> None:
        """When exception is raised in reader loop while state!=CONNECTED, skip log."""
        from dcc_mcp_ipc.transport.websocket import WebSocketTransport
        from dcc_mcp_ipc.transport.websocket import WebSocketTransportConfig
        from dcc_mcp_ipc.transport.base import TransportState
        import queue

        config = WebSocketTransportConfig(host="localhost", port=8765)
        t = WebSocketTransport(config)

        # Simulate reader loop where state has already changed to DISCONNECTED
        # when the exception fires — the `if self._state == TransportState.CONNECTED`
        # branch evaluates to False → goes straight to break (376→378)

        def fake_recv_message(ws):
            # First call: change state then raise
            t._state = TransportState.DISCONNECTED
            raise OSError("simulated error")

        t._state = TransportState.CONNECTED
        fake_ws = MagicMock()
        t._ws = fake_ws

        with patch.object(t, "_recv_message", side_effect=fake_recv_message):
            with patch.object(t, "_dispatch_message"):
                # Run reader loop directly in a thread to observe the branch
                loop_thread = threading.Thread(target=t._reader_loop, daemon=True)
                loop_thread.start()
                loop_thread.join(timeout=2.0)
        # If we get here without hanging the branch was reached without logging error
        assert not loop_thread.is_alive()


# =============================================================================
# server/factory.py — unregister thread exception (lines 123-125)
# =============================================================================


class TestServerFactoryUnregisterException:
    """Cover the except branch when unregister raises (lines 123-125)."""

    def test_cleanup_server_unregister_exception_returns_false(self) -> None:
        from dcc_mcp_ipc.server.factory import cleanup_server

        mock_server = MagicMock()
        mock_server.close = MagicMock()

        # Patch unregister_dcc_service to raise so the Thread.start succeeds but
        # the except block at line 123 catches it via the Thread constructor raising.
        # Simplest: patch threading.Thread to raise RuntimeError directly.
        with patch("dcc_mcp_ipc.server.factory.threading.Thread", side_effect=RuntimeError("fail")):
            result = cleanup_server(mock_server, registry_file="/tmp/fake_registry.json")

        assert result is False


# =============================================================================
# skills/scanner.py — stop_watching no-watcher (183→exit), reload no-watcher (197),
# register failure (306-307)
# =============================================================================


class TestSkillManagerMissingPaths:
    """Cover missing branches in SkillManager."""

    def test_stop_watching_noop_when_no_watcher(self) -> None:
        """stop_watching() when _watcher is None is a no-op (line 183→exit)."""
        from dcc_mcp_ipc.skills.scanner import SkillManager

        with patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mgr = SkillManager()
        assert mgr._watcher is None
        mgr.stop_watching()  # should not raise, does nothing
        assert mgr._watcher is None

    def test_reload_without_watcher_calls_load_paths(self) -> None:
        """reload() when _watcher is None falls back to load_paths (line 197)."""
        from dcc_mcp_ipc.skills.scanner import SkillManager

        with patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mgr = SkillManager()

        assert mgr._watcher is None
        with patch.object(mgr, "load_paths", return_value=["skill_a"]) as mock_lp:
            result = mgr.reload()
        mock_lp.assert_called_once_with(mgr._skill_paths, force_refresh=True)
        assert result == ["skill_a"]

    def test_register_skill_exception_is_logged_not_raised(self) -> None:
        """When adapter.register_action raises, _register_skill logs and continues (306-307)."""
        from dcc_mcp_ipc.skills.scanner import SkillManager
        from dcc_mcp_ipc.action_adapter import ActionAdapter

        adapter = ActionAdapter("fail_register_test")
        with patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mgr = SkillManager(adapter=adapter)

        meta = MagicMock()
        meta.name = "bad_skill"
        meta.description = "desc"
        meta.dcc = "python"
        meta.tags = []
        meta.version = "0.1"
        meta.skill_path = "/tmp/bad"
        meta.scripts = ["run.py"]
        meta.depends = []

        with patch.object(adapter, "register_action", side_effect=ValueError("bad action")):
            # Should not raise
            mgr._register_skill(meta)

        # Skill should NOT be in the registered dict since registration failed
        assert "bad_skill" not in mgr._registered_skills


# =============================================================================
# discovery/registry.py — ensure_strategy invalid type (line 215)
# and get_service branch 172→171 (list returns None for unmatched dcc_type)
# =============================================================================


class TestDiscoveryRegistryMissingPaths:
    """Cover ensure_strategy invalid type and get_service no-match."""

    def test_ensure_strategy_invalid_type_raises_value_error(self) -> None:
        """ensure_strategy raises ValueError for unknown strategy types (line 215)."""
        from dcc_mcp_ipc.discovery.registry import ServiceRegistry

        registry = ServiceRegistry()
        with pytest.raises(ValueError, match="not supported"):
            registry.ensure_strategy("completely_unknown_strategy_xyz")

    def test_get_service_no_match_returns_none(self) -> None:
        """get_service returns None when no matching service exists (172→171 branch)."""
        from dcc_mcp_ipc.discovery.registry import ServiceRegistry
        from dcc_mcp_ipc.discovery.base import ServiceInfo

        registry = ServiceRegistry()
        # Register a service with dcc_type="maya"
        svc = ServiceInfo(name="maya_instance", dcc_type="maya", host="localhost", port=7001)
        registry._services["maya_instance"] = svc

        # Query for a non-existent dcc_type
        result = registry.get_service("blender")
        assert result is None


# =============================================================================
# client/base.py — file discovery success (lines 114-118)
# =============================================================================


class TestClientBaseDiscoveryFilePath:
    """Cover file-based discovery success path in BaseApplicationClient.discover_service."""

    def test_file_discovery_returns_host_port(self) -> None:
        """When file strategy finds services, host/port are updated and returned."""
        from dcc_mcp_ipc.client.base import BaseApplicationClient
        from dcc_mcp_ipc.discovery.base import ServiceInfo

        client = BaseApplicationClient.__new__(BaseApplicationClient)
        client.app_name = "maya"
        client.host = "localhost"
        client.port = 7001
        client.registry_path = "/tmp"
        client.use_zeroconf = False

        fake_service = ServiceInfo(name="maya", dcc_type="maya", host="10.0.0.1", port=7777)

        with patch("dcc_mcp_ipc.client.base.ServiceRegistry") as MockReg:
            mock_registry = MagicMock()
            MockReg.return_value = mock_registry
            mock_registry.get_strategy.return_value = None
            mock_registry.discover_services.return_value = [fake_service]

            host, port = client._discover_service()

        assert host == "10.0.0.1"
        assert port == 7777


# =============================================================================
# application/adapter.py — _initialize_action_paths sets action_paths = []
# =============================================================================


class TestApplicationAdapterInitPaths:
    """Cover _initialize_action_paths in GenericApplicationAdapter (line 76)."""

    def test_initialize_action_paths_sets_empty_list(self) -> None:
        from dcc_mcp_ipc.application.adapter import GenericApplicationAdapter

        # GenericApplicationAdapter is a concrete subclass; can be instantiated
        adapter = GenericApplicationAdapter.__new__(GenericApplicationAdapter)
        adapter._initialize_action_paths()
        assert adapter.action_paths == []


# =============================================================================
# client/async_base.py — close() when connection is already None (line 144)
# =============================================================================


class TestAsyncBaseClientCloseBranch:
    """Cover close() when self.connection is None (line 148 branch False)."""

    def test_close_when_connection_is_none_is_noop(self) -> None:
        """close() with connection=None should not raise."""
        from dcc_mcp_ipc.client.async_base import AsyncBaseApplicationClient

        client = AsyncBaseApplicationClient.__new__(AsyncBaseApplicationClient)
        client.connection = None
        client.host = "localhost"
        client.port = 7001
        # Should not raise
        client.close()

    def test_close_when_connection_closed_is_noop(self) -> None:
        """close() with closed connection should not call close() again."""
        from dcc_mcp_ipc.client.async_base import AsyncBaseApplicationClient

        client = AsyncBaseApplicationClient.__new__(AsyncBaseApplicationClient)
        mock_conn = MagicMock()
        mock_conn.closed = True
        client.connection = mock_conn
        client.host = "localhost"
        client.port = 7001
        client.close()
        mock_conn.close.assert_not_called()


# =============================================================================
# async_base.py — connect() returns False when connection_attempts=0 (line 144)
# =============================================================================


class TestAsyncConnectReturnFalse:
    """Cover async connect() return False when connection_attempts=0."""

    def test_connect_zero_attempts_returns_false(self) -> None:
        """connect() with connection_attempts=0 should return False immediately."""
        import asyncio
        from dcc_mcp_ipc.client.async_base import AsyncBaseApplicationClient

        client = AsyncBaseApplicationClient.__new__(AsyncBaseApplicationClient)
        client.host = "localhost"
        client.port = 7001
        client.service_name = "test"
        client.config = {}
        client.connection = None
        client.connection_attempts = 0  # zero attempts → loop never runs → return False
        client.connection_timeout = 5.0
        client.connection_retry_delay = 0.0

        result = asyncio.run(client.connect())
        assert result is False


# =============================================================================
# discovery/registry.py — ensure_strategy via factory returns None (line 215)
# =============================================================================


class TestEnsureStrategyFactoryReturnsNone:
    """Cover line 215: factory.get_strategy returns None → ValueError."""

    def test_ensure_strategy_factory_returns_none_raises(self) -> None:
        from dcc_mcp_ipc.discovery.registry import ServiceRegistry

        registry = ServiceRegistry()
        # Patch the factory inside discovery.factory so that get_strategy returns None
        with patch("dcc_mcp_ipc.discovery.factory.ServiceDiscoveryFactory") as MockFactoryCls:
            mock_factory = MagicMock()
            mock_factory.get_strategy.return_value = None
            MockFactoryCls.return_value = mock_factory

            # Need to also patch the local import inside ensure_strategy
            import dcc_mcp_ipc.discovery.factory as factory_mod
            with patch.object(factory_mod, "ServiceDiscoveryFactory", MockFactoryCls):
                with pytest.raises(ValueError):
                    registry.ensure_strategy("fake_type_for_coverage")


# =============================================================================
# transport/websocket.py — reader thread join while alive (line 212)
# =============================================================================


class TestWebSocketReaderThreadJoin:
    """Cover disconnect() joining an alive reader thread (line 212)."""

    def test_disconnect_joins_both_threads(self) -> None:
        """disconnect() joins reader thread when alive."""
        from dcc_mcp_ipc.transport.websocket import WebSocketTransport
        from dcc_mcp_ipc.transport.websocket import WebSocketTransportConfig
        from dcc_mcp_ipc.transport.base import TransportState

        config = WebSocketTransportConfig(host="localhost", port=8765)
        t = WebSocketTransport(config)

        gate = threading.Event()

        def _hold():
            gate.wait(timeout=5.0)

        reader = threading.Thread(target=_hold, daemon=True)
        reader.start()

        writer = threading.Thread(target=_hold, daemon=True)
        writer.start()

        t._reader_thread = reader
        t._writer_thread = writer
        t._ws = MagicMock()
        t._state = TransportState.CONNECTED

        # Release threads before disconnect so join completes quickly
        gate.set()
        time.sleep(0.05)

        t.disconnect()
        assert t._reader_thread is None
        assert t._writer_thread is None
