"""Tests for dcc_mcp_ipc.server.dcc module (DCCServer and DCCRPyCService)."""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.server.dcc import DCCServer


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
