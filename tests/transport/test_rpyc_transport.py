"""Tests for the RPyC transport implementation."""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.transport.base import ConnectionError
from dcc_mcp_rpyc.transport.base import ProtocolError
from dcc_mcp_rpyc.transport.base import TransportState
from dcc_mcp_rpyc.transport.rpyc_transport import RPyCTransport
from dcc_mcp_rpyc.transport.rpyc_transport import RPyCTransportConfig


class TestRPyCTransportConfig:
    """Tests for RPyCTransportConfig."""

    def test_default_config(self):
        config = RPyCTransportConfig()
        assert config.sync_request_timeout == 30.0
        assert config.allow_all_attrs is True
        assert config.allow_public_attrs is True
        assert config.host == "localhost"

    def test_custom_config(self):
        config = RPyCTransportConfig(
            host="maya-host",
            port=18812,
            sync_request_timeout=60.0,
            allow_all_attrs=False,
        )
        assert config.host == "maya-host"
        assert config.port == 18812
        assert config.sync_request_timeout == 60.0
        assert config.allow_all_attrs is False


class TestRPyCTransport:
    """Tests for RPyCTransport."""

    def _make_transport(self, **config_kwargs):
        """Create a transport with a mocked rpyc.connect."""
        config = RPyCTransportConfig(**config_kwargs)
        transport = RPyCTransport(config)
        return transport

    def test_init(self):
        transport = RPyCTransport()
        assert transport.state == TransportState.DISCONNECTED
        assert transport.connection is None

    def test_rpyc_config_property(self):
        config = RPyCTransportConfig(host="test", port=1234)
        transport = RPyCTransport(config)
        assert transport.rpyc_config.host == "test"
        assert transport.rpyc_config.port == 1234

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_connect_success(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport(host="localhost", port=18812)
        transport._connect_func = mock_rpyc.connect
        transport.connect()

        assert transport.state == TransportState.CONNECTED
        assert transport.is_connected
        assert transport.connection is mock_conn
        mock_rpyc.connect.assert_called_once()

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_connect_failure(self, mock_rpyc):
        mock_rpyc.connect.side_effect = OSError("Connection refused")

        transport = self._make_transport(host="bad-host", port=9999)
        transport._connect_func = mock_rpyc.connect

        with pytest.raises(ConnectionError, match="Failed to connect"):
            transport.connect()

        assert transport.state == TransportState.ERROR
        assert transport.connection is None

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_connect_already_connected(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()
        # Second connect should be a no-op
        transport.connect()
        assert mock_rpyc.connect.call_count == 1

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_disconnect(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()
        transport.disconnect()

        assert transport.state == TransportState.DISCONNECTED
        assert transport.connection is None
        mock_conn.close.assert_called_once()

    def test_disconnect_when_not_connected(self):
        transport = RPyCTransport()
        transport.disconnect()  # should not raise
        assert transport.state == TransportState.DISCONNECTED

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_disconnect_with_close_error(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_conn.close.side_effect = RuntimeError("close failed")
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()
        transport.disconnect()  # should not raise
        assert transport.state == TransportState.DISCONNECTED
        assert transport.connection is None

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_health_check_connected(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()

        assert transport.health_check() is True
        mock_conn.ping.assert_called_once()

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_health_check_ping_fails(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_conn.ping.side_effect = RuntimeError("ping failed")
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()

        assert transport.health_check() is False
        assert transport.state == TransportState.ERROR

    def test_health_check_not_connected(self):
        transport = RPyCTransport()
        assert transport.health_check() is False

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_execute_exposed_method(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_conn.root.exposed_list_actions.return_value = {"actions": {"create_sphere": {}}}
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()

        result = transport.execute("list_actions")
        assert result == {"actions": {"create_sphere": {}}}

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_execute_method_not_found(self, mock_rpyc):
        """Test that ProtocolError is raised when method doesn't exist on a spec'd mock."""
        # Use a bare object as root spec so getattr returns None
        mock_conn = MagicMock()
        root_obj = object()  # no attributes at all
        mock_conn.root = root_obj
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()

        with pytest.raises(ProtocolError, match="has no method"):
            transport.execute("nonexistent_method")

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_execute_non_dict_result(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_conn.root.exposed_get_version.return_value = "2024.1"
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()

        result = transport.execute("get_version")
        assert result == {"success": True, "result": "2024.1"}

    def test_execute_not_connected(self):
        transport = RPyCTransport()
        with pytest.raises(ConnectionError, match="Not connected"):
            transport.execute("test")

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_execute_remote_error(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_conn.root.exposed_bad_action.side_effect = RuntimeError("DCC crash")
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()

        with pytest.raises(ProtocolError, match="Error executing"):
            transport.execute("bad_action")

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_execute_python(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_conn.root.exposed_execute_python.return_value = 42
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()

        result = transport.execute_python("1 + 1")
        assert result == 42

    def test_execute_python_not_connected(self):
        transport = RPyCTransport()
        with pytest.raises(ConnectionError):
            transport.execute_python("x = 1")

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_call_function(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_conn.root.exposed_call_function.return_value = "/tmp/test"
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()

        result = transport.call_function("os.path", "join", "/tmp", "test")
        assert result == "/tmp/test"
        mock_conn.root.exposed_call_function.assert_called_once_with(
            "os.path", "join", "/tmp", "test"
        )

    def test_call_function_not_connected(self):
        transport = RPyCTransport()
        with pytest.raises(ConnectionError):
            transport.call_function("os", "getcwd")

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_import_module(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_module = MagicMock()
        mock_conn.root.exposed_get_module.return_value = mock_module
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()

        result = transport.import_module("maya.cmds")
        assert result is mock_module

    def test_import_module_not_connected(self):
        transport = RPyCTransport()
        with pytest.raises(ConnectionError):
            transport.import_module("os")

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_root_property(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_rpyc.connect.return_value = mock_conn

        transport = self._make_transport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()

        assert transport.root is mock_conn.root

    def test_root_property_not_connected(self):
        transport = RPyCTransport()
        with pytest.raises(ConnectionError):
            _ = transport.root

    @patch("dcc_mcp_rpyc.transport.rpyc_transport.rpyc")
    def test_context_manager(self, mock_rpyc):
        mock_conn = MagicMock()
        mock_rpyc.connect.return_value = mock_conn

        config = RPyCTransportConfig(host="localhost", port=18812)
        transport = RPyCTransport(config)
        transport._connect_func = mock_rpyc.connect

        with transport as t:
            assert t.is_connected
        assert not t.is_connected
