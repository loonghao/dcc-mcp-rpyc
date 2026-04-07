"""Additional coverage tests for dcc_mcp_ipc.client.base module.

Covers error paths, remote call methods, ZeroConf discovery,
auto-connect logic, and module-level helper functions.
"""

# Import built-in modules
import logging
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.client.base import BaseApplicationClient
from dcc_mcp_ipc.client.base import close_all_connections
from dcc_mcp_ipc.client.base import get_client
from dcc_mcp_ipc.discovery import ServiceInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_connected_client(app_name="test_app"):
    """Return a client instance with a mock connection."""
    client = BaseApplicationClient(app_name, host="localhost", port=9999, auto_connect=False)
    mock_conn = MagicMock()
    mock_conn.ping.return_value = None  # ping() succeeds
    client.connection = mock_conn
    return client, mock_conn


# ---------------------------------------------------------------------------
# __init__ - auto-connect paths (lines 68-73)
# ---------------------------------------------------------------------------

class TestBaseClientInit:
    """Tests for __init__ auto-connect behavior."""

    def test_auto_connect_skipped_without_host_port(self):
        """When no host/port and no discovered service, connect is not called."""
        with patch("dcc_mcp_ipc.client.base.ServiceRegistry") as mock_reg:
            mock_reg.return_value.discover_services.return_value = []
            mock_reg.return_value.get_strategy.return_value = None
            client = BaseApplicationClient("no_service_app", auto_connect=True)
        # Should not crash; host/port remain None
        assert client.host is None or client.port is None

    def test_auto_connect_calls_connect_when_host_and_port_known(self):
        """When host and port are provided and auto_connect=True, connect is called."""
        with patch.object(BaseApplicationClient, "connect", return_value=True) as mock_connect:
            BaseApplicationClient("app", host="localhost", port=9000, auto_connect=True)
        mock_connect.assert_called_once()


# ---------------------------------------------------------------------------
# _discover_service - ZeroConf path (lines 87-104)
# ---------------------------------------------------------------------------

class TestDiscoverServiceZeroConf:
    """Tests for the ZeroConf discovery branch."""

    def test_zeroconf_success(self):
        mock_service = ServiceInfo(name="maya", host="zc_host", port=7777, dcc_type="maya")
        with patch("dcc_mcp_ipc.client.base.ZEROCONF_AVAILABLE", True):
            with patch("dcc_mcp_ipc.client.base.ServiceRegistry") as mock_reg:
                mock_reg_inst = MagicMock()
                mock_reg.return_value = mock_reg_inst
                mock_reg_inst.get_strategy.return_value = MagicMock()
                mock_reg_inst.discover_services.return_value = [mock_service]

                client = BaseApplicationClient("maya", auto_connect=False, use_zeroconf=True)
                host, port = client._discover_service()

        # ZeroConf discovery is the first method tried
        assert host == "zc_host"
        assert port == 7777

    def test_zeroconf_no_services_falls_through_to_file(self):
        with patch("dcc_mcp_ipc.client.base.ZEROCONF_AVAILABLE", True):
            with patch("dcc_mcp_ipc.client.base.ServiceRegistry") as mock_reg:
                mock_reg_inst = MagicMock()
                mock_reg.return_value = mock_reg_inst
                mock_reg_inst.get_strategy.return_value = None
                # ZeroConf returns empty, file also returns empty
                mock_reg_inst.discover_services.return_value = []

                client = BaseApplicationClient("maya", auto_connect=False, use_zeroconf=True)
                host, port = client._discover_service()

        assert host is None
        assert port is None


# ---------------------------------------------------------------------------
# connect - is_connected False branch (lines 162-165)
# ---------------------------------------------------------------------------

class TestConnect:
    """Tests for the connect method edge cases."""

    def test_connect_fails_when_ping_fails_after_connect(self):
        """If connection established but ping fails immediately, connect returns False."""
        client = BaseApplicationClient("app", host="localhost", port=9999, auto_connect=False)
        mock_conn = MagicMock()

        def failing_ping():
            raise Exception("ping failed")

        mock_conn.ping.side_effect = failing_ping

        def mock_connect_func(host, port, config=None):
            return mock_conn

        result = client.connect(rpyc_connect_func=mock_connect_func)
        assert result is False
        assert client.connection is None

    def test_connect_exception_returns_false(self):
        """If connect_func raises, connect returns False."""
        client = BaseApplicationClient("app", host="localhost", port=9999, auto_connect=False)

        def broken_connect(*args, **kwargs):
            raise ConnectionRefusedError("refused")

        result = client.connect(rpyc_connect_func=broken_connect)
        assert result is False
        assert client.connection is None

    def test_connect_already_connected_returns_true(self):
        client, _ = _make_connected_client()
        result = client.connect()
        assert result is True

    def test_connect_without_host_returns_false(self):
        client = BaseApplicationClient("app", auto_connect=False)
        client.host = None
        client.port = None
        result = client.connect()
        assert result is False


# ---------------------------------------------------------------------------
# disconnect
# ---------------------------------------------------------------------------

class TestDisconnect:
    """Tests for the disconnect method."""

    def test_disconnect_no_connection(self):
        client = BaseApplicationClient("app", auto_connect=False)
        assert client.disconnect() is True

    def test_disconnect_success(self):
        client, mock_conn = _make_connected_client()
        result = client.disconnect()
        assert result is True
        mock_conn.close.assert_called_once()
        assert client.connection is None

    def test_disconnect_exception_returns_false(self):
        client, mock_conn = _make_connected_client()
        mock_conn.close.side_effect = Exception("close failed")
        result = client.disconnect()
        assert result is False
        assert client.connection is None


# ---------------------------------------------------------------------------
# reconnect
# ---------------------------------------------------------------------------

class TestReconnect:
    """Tests for the reconnect method."""

    def test_reconnect_calls_disconnect_then_connect(self):
        client = BaseApplicationClient("app", host="localhost", port=9999, auto_connect=False)
        with patch.object(client, "disconnect") as mock_dis:
            with patch.object(client, "connect", return_value=True) as mock_con:
                result = client.reconnect()
        mock_dis.assert_called_once()
        mock_con.assert_called_once()
        assert result is True


# ---------------------------------------------------------------------------
# is_connected
# ---------------------------------------------------------------------------

class TestIsConnected:
    """Tests for is_connected."""

    def test_not_connected_no_connection(self):
        client = BaseApplicationClient("app", auto_connect=False)
        assert client.is_connected() is False

    def test_connected_ping_succeeds(self):
        client, _ = _make_connected_client()
        assert client.is_connected() is True

    def test_not_connected_ping_fails(self):
        client = BaseApplicationClient("app", auto_connect=False)
        mock_conn = MagicMock()
        mock_conn.ping.side_effect = Exception("no ping")
        client.connection = mock_conn
        result = client.is_connected()
        assert result is False
        assert client.connection is None


# ---------------------------------------------------------------------------
# execute_remote_command
# ---------------------------------------------------------------------------

class TestExecuteRemoteCommand:
    """Tests for execute_remote_command."""

    def test_not_connected_raises(self):
        client = BaseApplicationClient("app", auto_connect=False)
        with pytest.raises(ConnectionError):
            client.execute_remote_command("some_cmd")

    def test_success(self):
        client, mock_conn = _make_connected_client()
        mock_conn.my_cmd.return_value = "result"
        result = client.execute_remote_command("my_cmd")
        assert result == "result"

    def test_exception_logs_and_reraises(self, caplog):
        client, mock_conn = _make_connected_client()
        mock_conn.bad_cmd.side_effect = RuntimeError("remote crash")
        with caplog.at_level(logging.ERROR, logger="dcc_mcp_ipc.client.base"):
            with pytest.raises(RuntimeError, match="remote crash"):
                client.execute_remote_command("bad_cmd")


# ---------------------------------------------------------------------------
# execute_python
# ---------------------------------------------------------------------------

class TestExecutePython:
    """Tests for execute_python."""

    def test_not_connected_raises(self):
        client = BaseApplicationClient("app", auto_connect=False)
        with pytest.raises(ConnectionError):
            client.execute_python("1 + 1")

    def test_success(self):
        client, mock_conn = _make_connected_client()
        mock_conn.root.exposed_execute_python.return_value = 2
        result = client.execute_python("1 + 1")
        assert result == 2

    def test_exception_reraises(self):
        client, mock_conn = _make_connected_client()
        mock_conn.root.exposed_execute_python.side_effect = RuntimeError("exec error")
        with pytest.raises(RuntimeError):
            client.execute_python("bad code")


# ---------------------------------------------------------------------------
# import_module
# ---------------------------------------------------------------------------

class TestImportModule:
    """Tests for import_module."""

    def test_not_connected_raises(self):
        client = BaseApplicationClient("app", auto_connect=False)
        with pytest.raises(ConnectionError):
            client.import_module("os")

    def test_success(self):
        import sys
        client, mock_conn = _make_connected_client()
        mock_conn.root.exposed_get_module.return_value = sys
        result = client.import_module("sys")
        assert result is sys

    def test_exception_reraises(self):
        client, mock_conn = _make_connected_client()
        mock_conn.root.exposed_get_module.side_effect = ImportError("no module")
        with pytest.raises(ImportError):
            client.import_module("bad_module")


# ---------------------------------------------------------------------------
# call_function
# ---------------------------------------------------------------------------

class TestCallFunction:
    """Tests for call_function."""

    def test_not_connected_raises(self):
        client = BaseApplicationClient("app", auto_connect=False)
        with pytest.raises(ConnectionError):
            client.call_function("os", "getcwd")

    def test_success(self):
        client, mock_conn = _make_connected_client()
        mock_conn.root.exposed_call_function.return_value = "/tmp"
        result = client.call_function("os", "getcwd")
        assert result == "/tmp"

    def test_exception_reraises(self):
        client, mock_conn = _make_connected_client()
        mock_conn.root.exposed_call_function.side_effect = RuntimeError("func error")
        with pytest.raises(RuntimeError):
            client.call_function("mod", "func")


# ---------------------------------------------------------------------------
# get_application_info
# ---------------------------------------------------------------------------

class TestGetApplicationInfo:
    """Tests for get_application_info."""

    def test_not_connected_raises(self):
        client = BaseApplicationClient("app", auto_connect=False)
        with pytest.raises(ConnectionError):
            client.get_application_info()

    def test_success(self):
        client, mock_conn = _make_connected_client()
        mock_conn.root.get_application_info.return_value = {"name": "maya"}
        result = client.get_application_info()
        assert result["name"] == "maya"

    def test_exception_reraises(self):
        client, mock_conn = _make_connected_client()
        mock_conn.root.get_application_info.side_effect = RuntimeError("info error")
        with pytest.raises(RuntimeError):
            client.get_application_info()


# ---------------------------------------------------------------------------
# get_environment_info
# ---------------------------------------------------------------------------

class TestGetEnvironmentInfo:
    """Tests for get_environment_info."""

    def test_not_connected_raises(self):
        client = BaseApplicationClient("app", auto_connect=False)
        with pytest.raises(ConnectionError):
            client.get_environment_info()

    def test_success(self):
        client, mock_conn = _make_connected_client()
        mock_conn.root.get_environment_info.return_value = {"python_version": "3.12"}
        result = client.get_environment_info()
        assert "python_version" in result

    def test_exception_reraises(self):
        client, mock_conn = _make_connected_client()
        mock_conn.root.get_environment_info.side_effect = RuntimeError("env error")
        with pytest.raises(RuntimeError):
            client.get_environment_info()


# ---------------------------------------------------------------------------
# list_actions
# ---------------------------------------------------------------------------

class TestListActions:
    """Tests for list_actions."""

    def test_not_connected_raises(self):
        client = BaseApplicationClient("app", auto_connect=False)
        with pytest.raises(ConnectionError):
            client.list_actions()

    def test_success(self):
        client, mock_conn = _make_connected_client()
        mock_conn.root.exposed_list_actions.return_value = {"actions": {}}
        result = client.list_actions()
        assert "actions" in result

    def test_exception_reraises(self):
        client, mock_conn = _make_connected_client()
        mock_conn.root.exposed_list_actions.side_effect = RuntimeError("list error")
        with pytest.raises(RuntimeError):
            client.list_actions()


# ---------------------------------------------------------------------------
# call_action
# ---------------------------------------------------------------------------

class TestCallAction:
    """Tests for call_action."""

    def test_not_connected_raises(self):
        client = BaseApplicationClient("app", auto_connect=False)
        with pytest.raises(ConnectionError):
            client.call_action("do_something")

    def test_success(self):
        client, mock_conn = _make_connected_client()
        mock_conn.root.exposed_call_action.return_value = {"success": True}
        result = client.call_action("create_sphere", radius=1.0)
        mock_conn.root.exposed_call_action.assert_called_once_with("create_sphere", radius=1.0)
        assert result["success"] is True

    def test_exception_reraises(self):
        client, mock_conn = _make_connected_client()
        mock_conn.root.exposed_call_action.side_effect = RuntimeError("action error")
        with pytest.raises(RuntimeError):
            client.call_action("failing_action")


# ---------------------------------------------------------------------------
# root property
# ---------------------------------------------------------------------------

class TestRootProperty:
    """Tests for the root property."""

    def test_not_connected_raises(self):
        client = BaseApplicationClient("app", auto_connect=False)
        with pytest.raises(ConnectionError):
            _ = client.root

    def test_returns_connection_root(self):
        client, mock_conn = _make_connected_client()
        mock_root = MagicMock()
        mock_conn.root = mock_root
        assert client.root is mock_root


# ---------------------------------------------------------------------------
# get_client and close_all_connections
# ---------------------------------------------------------------------------

class TestGetClientAndCloseAll:
    """Tests for get_client factory and close_all_connections."""

    def setup_method(self):
        """Clear the client registry before each test."""
        import dcc_mcp_ipc.client.base as base_mod
        base_mod._clients.clear()

    def test_get_client_creates_new(self):
        with patch.object(BaseApplicationClient, "connect", return_value=False):
            client = get_client("new_app", host="localhost", port=9999, auto_connect=False)
        assert isinstance(client, BaseApplicationClient)
        assert client.app_name == "new_app"

    def test_get_client_returns_cached(self):
        with patch.object(BaseApplicationClient, "connect", return_value=False):
            c1 = get_client("cached_app", host="localhost", port=8888, auto_connect=False)
            c2 = get_client("cached_app", host="localhost", port=8888, auto_connect=False)
        assert c1 is c2

    def test_get_client_reconnects_if_disconnected(self):
        with patch.object(BaseApplicationClient, "connect", return_value=False):
            client = get_client("reconnect_app", host="localhost", port=7777, auto_connect=False)

        # Simulate disconnection
        client.connection = None
        with patch.object(client, "connect", return_value=True) as mock_con:
            get_client("reconnect_app", host="localhost", port=7777, auto_connect=False)
        mock_con.assert_called_once()

    def test_close_all_connections(self):
        import dcc_mcp_ipc.client.base as base_mod
        mock_client_1 = MagicMock()
        mock_client_2 = MagicMock()
        base_mod._clients[("app1", "h", 1)] = mock_client_1
        base_mod._clients[("app2", "h", 2)] = mock_client_2

        close_all_connections()

        mock_client_1.disconnect.assert_called_once()
        mock_client_2.disconnect.assert_called_once()
        assert len(base_mod._clients) == 0

    def test_close_all_handles_disconnect_error(self):
        import dcc_mcp_ipc.client.base as base_mod
        mock_client = MagicMock()
        mock_client.disconnect.side_effect = RuntimeError("cannot disconnect")
        base_mod._clients[("app_x", "h", 1)] = mock_client

        # Should not raise
        close_all_connections()
        assert len(base_mod._clients) == 0
