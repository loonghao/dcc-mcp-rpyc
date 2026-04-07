"""Tests for dcc_mcp_ipc.server.dcc module (DCCServer and DCCRPyCService)."""

# Import built-in modules
from typing import Any
from typing import Dict
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.server.dcc import DCCRPyCService
from dcc_mcp_ipc.server.dcc import DCCServer


# ---------------------------------------------------------------------------
# Concrete subclass to test DCCRPyCService.exposed_create_primitive
# ---------------------------------------------------------------------------


class _ConcreteDCCService(DCCRPyCService):
    """Minimal concrete subclass for testing the abstract base."""

    def get_scene_info(self) -> Dict[str, Any]:
        return {"objects": []}

    def get_session_info(self) -> Dict[str, Any]:
        return {"session": "test"}

    def create_primitive(self, primitive_type: str, **kwargs) -> Any:
        if primitive_type == "fail":
            raise ValueError("unsupported primitive")
        return {"created": primitive_type}

    def get_application_info(self) -> Dict[str, Any]:
        return {"name": "test_dcc"}

    def get_environment_info(self) -> Dict[str, Any]:
        return {"python_version": "3.12"}

    def execute_python(self, code: str, context=None) -> Any:
        return eval(code)  # test-only, safe in controlled test environment

    def import_module(self, module_name: str) -> Any:
        import importlib
        return importlib.import_module(module_name)

    def call_function(self, module_name: str, function_name: str, *args, **kwargs) -> Any:
        import importlib
        mod = importlib.import_module(module_name)
        return getattr(mod, function_name)(*args, **kwargs)


class TestDCCRPyCServiceSafeCreatePrimitive:
    """Tests for exposed_create_primitive (safe_create_primitive wrapper)."""

    def _make_service(self) -> _ConcreteDCCService:
        # Bypass RPyC service __init__ which may require server context
        svc = object.__new__(_ConcreteDCCService)
        return svc

    def test_success_returns_result_with_scene_info(self):
        # exposed_create_primitive is decorated with @with_scene_info.
        # The decorator merges scene_info into the original dict result:
        # {"created": "sphere", "scene_info": {...}}
        svc = self._make_service()
        result = svc.exposed_create_primitive("sphere")
        assert "scene_info" in result
        assert result.get("created") == "sphere"

    def test_exception_is_re_raised(self):
        svc = self._make_service()
        with pytest.raises(ValueError, match="unsupported primitive"):
            svc.exposed_create_primitive("fail")

    def test_kwargs_forwarded(self):
        svc = self._make_service()
        result = svc.exposed_create_primitive("cube", size=2.0, name="myCube")
        assert result.get("created") == "cube"
        assert "scene_info" in result


class TestDCCServerInit:
    """Tests for DCCServer initialization."""

    def test_default_init(self):
        server = DCCServer(dcc_name="maya")
        assert server.dcc_name == "maya"
        assert server.running is False
        assert server.server is None
        assert server.port == 0

    def test_dcc_name_lowercased(self):
        server = DCCServer(dcc_name="MAYA")
        assert server.dcc_name == "maya"

    def test_custom_host_port(self):
        server = DCCServer(dcc_name="blender", host="localhost", port=18812)
        assert server.host == "localhost"
        assert server.port == 18812

    def test_with_existing_server(self):
        mock_server = MagicMock()
        server = DCCServer(dcc_name="houdini", server=mock_server)
        assert server.server is mock_server

    def test_registry_path(self):
        server = DCCServer(dcc_name="maya", registry_path="/tmp/registry.json")
        assert server.registry_file == "/tmp/registry.json"

    def test_use_zeroconf_defaults(self):
        # Without ZEROCONF_AVAILABLE, use_zeroconf should evaluate to False
        from dcc_mcp_ipc.discovery import ZEROCONF_AVAILABLE
        server = DCCServer(dcc_name="maya", use_zeroconf=True)
        # use_zeroconf is True only if both param and ZEROCONF_AVAILABLE are True
        assert server.use_zeroconf == ZEROCONF_AVAILABLE


class TestDCCServerIsRunning:
    """Tests for the is_running method."""

    def test_not_running_initially(self):
        server = DCCServer(dcc_name="maya")
        assert server.is_running() is False

    def test_running_when_set(self):
        mock_srv = MagicMock()
        server = DCCServer(dcc_name="maya", server=mock_srv)
        server.running = True
        assert server.is_running() is True

    def test_not_running_without_server(self):
        server = DCCServer(dcc_name="maya")
        server.running = True
        server.server = None
        assert server.is_running() is False


class TestDCCServerClose:
    """Tests for the close method."""

    def test_close_with_server(self):
        mock_srv = MagicMock()
        server = DCCServer(dcc_name="maya", server=mock_srv)
        server.close()
        mock_srv.close.assert_called_once()
        assert server.server is None

    def test_close_without_server(self):
        server = DCCServer(dcc_name="maya")
        server.close()  # should not raise

    def test_close_error_sets_server_none(self):
        mock_srv = MagicMock()
        mock_srv.close.side_effect = RuntimeError("close failed")
        server = DCCServer(dcc_name="maya", server=mock_srv)
        server.close()  # should not raise
        assert server.server is None


class TestDCCServerStop:
    """Tests for the stop method."""

    def test_stop_when_not_running(self):
        server = DCCServer(dcc_name="maya")
        result = server.stop()
        assert result is True  # not running = already stopped

    @patch("dcc_mcp_ipc.server.dcc.unregister_dcc_service")
    def test_stop_running_server(self, mock_unreg):
        mock_srv = MagicMock()
        server = DCCServer(dcc_name="maya", server=mock_srv)
        server.running = True
        server.registry_file = "/tmp/maya.json"
        server.use_zeroconf = False

        result = server.stop()
        assert result is True
        assert server.running is False
        mock_unreg.assert_called_once_with("/tmp/maya.json")
        mock_srv.close.assert_called_once()

    @patch("dcc_mcp_ipc.server.dcc.unregister_dcc_service")
    def test_stop_exception_returns_false(self, mock_unreg):
        mock_unreg.side_effect = RuntimeError("unregister failed")
        mock_srv = MagicMock()
        server = DCCServer(dcc_name="maya", server=mock_srv)
        server.running = True

        result = server.stop()
        assert result is False

    @patch("dcc_mcp_ipc.server.dcc.unregister_dcc_service")
    @patch("dcc_mcp_ipc.server.dcc.ServiceRegistry")
    def test_stop_with_zeroconf(self, MockRegistry, mock_unreg):
        from dcc_mcp_ipc.discovery import ZEROCONF_AVAILABLE
        if not ZEROCONF_AVAILABLE:
            pytest.skip("zeroconf not available")

        mock_srv = MagicMock()
        mock_registry = MagicMock()
        MockRegistry.return_value = mock_registry

        server = DCCServer(dcc_name="maya", server=mock_srv)
        server.running = True
        server.use_zeroconf = True
        server.zeroconf_info = MagicMock()

        result = server.stop()
        assert result is True
        mock_registry.register_service_with_strategy.assert_called_once()


class TestDCCServerStart:
    """Tests for the start method."""

    @patch("dcc_mcp_ipc.server.dcc.register_dcc_service")
    def test_start_already_running(self, mock_reg):
        mock_srv = MagicMock()
        mock_srv.port = 18812
        server = DCCServer(dcc_name="maya", server=mock_srv)
        server.running = True
        server.port = 18812

        result = server.start()
        assert result == 18812
        mock_reg.assert_not_called()

    @patch("dcc_mcp_ipc.server.dcc.register_dcc_service")
    def test_start_in_thread(self, mock_reg):
        mock_srv = MagicMock()
        mock_srv.port = 9999
        mock_reg.return_value = "/tmp/reg.json"
        server = DCCServer(dcc_name="maya", server=mock_srv)
        server.use_zeroconf = False

        result = server.start(threaded=True)
        assert result == 9999
        assert server.running is True
        assert server.registry_file == "/tmp/reg.json"

    def test_start_exception_returns_false(self):
        server = DCCServer(dcc_name="maya")
        server.service_class = None  # This will cause _create_server to fail

        with patch.object(server, "_create_server", side_effect=RuntimeError("no service")):
            result = server.start()
            assert result is False

    @patch("dcc_mcp_ipc.server.dcc.register_dcc_service")
    def test_start_in_thread_exception_returns_false_and_clears_server(self, mock_reg):
        """If register_dcc_service raises, _start_in_thread returns False and clears server."""
        mock_srv = MagicMock()
        mock_srv.port = 9999
        # register_dcc_service is called in the background thread after server.start()
        # Making it raise causes the except branch (lines 241-245) to execute
        mock_reg.side_effect = RuntimeError("registration failed")

        server = DCCServer(dcc_name="maya", server=mock_srv)
        server.use_zeroconf = False

        result = server.start(threaded=True)
        assert result is False
        assert server.server is None

    @patch("dcc_mcp_ipc.server.dcc.register_dcc_service")
    @patch("dcc_mcp_ipc.server.dcc.ServiceRegistry")
    def test_start_in_thread_with_zeroconf_registers(self, MockRegistry, mock_reg):
        """When use_zeroconf=True, _start_in_thread registers via ZeroConf."""
        from dcc_mcp_ipc.discovery import ZEROCONF_AVAILABLE
        if not ZEROCONF_AVAILABLE:
            pytest.skip("zeroconf not available")

        mock_srv = MagicMock()
        mock_srv.port = 7777
        mock_reg.return_value = "/tmp/reg.json"

        mock_registry_instance = MagicMock()
        mock_registry_instance.register_service_with_strategy.return_value = True
        MockRegistry.return_value = mock_registry_instance

        server = DCCServer(dcc_name="houdini", server=mock_srv)
        server.use_zeroconf = True

        result = server.start(threaded=True)
        assert result == 7777
        mock_registry_instance.register_service_with_strategy.assert_called_once()
        assert server.zeroconf_info is not None

    @patch("dcc_mcp_ipc.server.dcc.register_dcc_service")
    @patch("dcc_mcp_ipc.server.dcc.ServiceRegistry")
    def test_start_in_thread_zeroconf_failure_logs_warning(self, MockRegistry, mock_reg):
        """When ZeroConf registration fails, a warning is logged but start succeeds."""
        from dcc_mcp_ipc.discovery import ZEROCONF_AVAILABLE
        if not ZEROCONF_AVAILABLE:
            pytest.skip("zeroconf not available")

        mock_srv = MagicMock()
        mock_srv.port = 6666
        mock_reg.return_value = "/tmp/reg.json"

        mock_registry_instance = MagicMock()
        mock_registry_instance.register_service_with_strategy.return_value = False
        MockRegistry.return_value = mock_registry_instance

        server = DCCServer(dcc_name="blender", server=mock_srv)
        server.use_zeroconf = True

        result = server.start(threaded=True)
        # Even if ZeroConf fails, the server should still start
        assert result == 6666
        assert server.running is True


class TestDCCServerCleanup:
    """Tests for the cleanup method."""

    @patch("dcc_mcp_ipc.server.dcc.unregister_dcc_service")
    def test_cleanup_calls_stop(self, mock_unreg):
        mock_srv = MagicMock()
        server = DCCServer(dcc_name="maya", server=mock_srv)
        server.running = True
        server.use_zeroconf = False

        result = server.cleanup()
        assert result is True
