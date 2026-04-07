"""Tests for server/server_utils.py.

Covers get_rpyc_config and create_raw_threaded_server.
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.server.server_utils import create_raw_threaded_server
from dcc_mcp_ipc.server.server_utils import get_rpyc_config


class TestGetRpycConfig:
    """Tests for get_rpyc_config."""

    def test_default_config_keys(self):
        """Test that default config contains expected keys."""
        config = get_rpyc_config()
        assert "allow_all_attrs" in config
        assert "allow_public_attrs" in config
        assert "allow_pickle" in config
        assert "sync_request_timeout" in config
        assert "allow_getattr" in config
        assert "allow_methods" in config

    def test_default_values(self):
        """Test that default values are correct."""
        config = get_rpyc_config()
        assert config["allow_all_attrs"] is False
        assert config["allow_public_attrs"] is True
        assert config["allow_pickle"] is False
        assert config["sync_request_timeout"] == 60.0

    def test_custom_values(self):
        """Test that custom values override defaults."""
        config = get_rpyc_config(allow_all_attrs=True, allow_pickle=True)
        assert config["allow_all_attrs"] is True
        assert config["allow_pickle"] is True

    def test_returns_dict(self):
        """Test that get_rpyc_config returns a dict."""
        config = get_rpyc_config()
        assert isinstance(config, dict)


class TestCreateRawThreadedServer:
    """Tests for create_raw_threaded_server."""

    def test_returns_threaded_server(self):
        """Test that create_raw_threaded_server returns a ThreadedServer."""
        with patch("dcc_mcp_ipc.server.server_utils.ThreadedServer") as mock_cls:
            mock_server = MagicMock()
            mock_cls.return_value = mock_server
            mock_service = MagicMock()

            server = create_raw_threaded_server(mock_service, hostname="localhost", port=8000)

            assert server is mock_server
            mock_cls.assert_called_once()

    def test_uses_custom_protocol_config(self):
        """Test that custom protocol_config is passed to ThreadedServer."""
        with patch("dcc_mcp_ipc.server.server_utils.ThreadedServer") as mock_cls:
            mock_cls.return_value = MagicMock()
            mock_service = MagicMock()
            custom_config = {"allow_all_attrs": True}

            create_raw_threaded_server(mock_service, port=8001, protocol_config=custom_config)

            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs["protocol_config"] == custom_config

    def test_default_protocol_config_applied(self):
        """Test that default protocol config (allow_all_attrs=True) is applied when None."""
        with patch("dcc_mcp_ipc.server.server_utils.ThreadedServer") as mock_cls:
            mock_cls.return_value = MagicMock()
            mock_service = MagicMock()

            create_raw_threaded_server(mock_service, port=8002)

            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs["protocol_config"]["allow_all_attrs"] is True

    def test_passes_hostname_and_port(self):
        """Test that hostname and port are forwarded."""
        with patch("dcc_mcp_ipc.server.server_utils.ThreadedServer") as mock_cls:
            mock_cls.return_value = MagicMock()
            mock_service = MagicMock()

            create_raw_threaded_server(mock_service, hostname="0.0.0.0", port=7777)

            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs["hostname"] == "0.0.0.0"
            assert call_kwargs["port"] == 7777

    def test_passes_optional_socket_path(self):
        """Test that socket_path is forwarded."""
        with patch("dcc_mcp_ipc.server.server_utils.ThreadedServer") as mock_cls:
            mock_cls.return_value = MagicMock()
            mock_service = MagicMock()

            create_raw_threaded_server(mock_service, socket_path="/tmp/test.sock")

            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs["socket_path"] == "/tmp/test.sock"

    def test_passes_auto_register(self):
        """Test that auto_register is forwarded."""
        with patch("dcc_mcp_ipc.server.server_utils.ThreadedServer") as mock_cls:
            mock_cls.return_value = MagicMock()
            mock_service = MagicMock()

            create_raw_threaded_server(mock_service, auto_register=True)

            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs["auto_register"] is True
