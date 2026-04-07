"""Tests for dcc_mcp_ipc.server.lifecycle module."""

# Import built-in modules
import threading
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.server import lifecycle as lifecycle_module
from dcc_mcp_ipc.server.lifecycle import create_server
from dcc_mcp_ipc.server.lifecycle import is_server_running
from dcc_mcp_ipc.server.lifecycle import start_server
from dcc_mcp_ipc.server.lifecycle import stop_server


@pytest.fixture(autouse=True)
def clear_server_registry():
    """Clear the global _servers registry before each test."""
    original = lifecycle_module._servers.copy()
    lifecycle_module._servers.clear()
    yield
    lifecycle_module._servers.clear()
    lifecycle_module._servers.update(original)


class TestCreateServer:
    """Tests for the create_server function."""

    @patch("dcc_mcp_ipc.server.lifecycle.create_raw_threaded_server")
    @patch("dcc_mcp_ipc.server.lifecycle.get_rpyc_config")
    def test_create_threaded_server(self, mock_config, mock_create):
        mock_server = MagicMock()
        mock_create.return_value = mock_server
        mock_config.return_value = {}

        server = create_server(server_type="threaded")

        assert server is mock_server
        mock_create.assert_called_once()

    @patch("dcc_mcp_ipc.server.lifecycle._create_dcc_server")
    def test_create_dcc_server(self, mock_create_dcc):
        # Import local modules
        from dcc_mcp_ipc.server.base import BaseRPyCService

        mock_server = MagicMock()
        mock_create_dcc.return_value = mock_server

        server = create_server(server_type="dcc", name="maya")

        assert server is mock_server
        mock_create_dcc.assert_called_once_with("maya", BaseRPyCService, "localhost", 0, False)

    @patch("dcc_mcp_ipc.server.lifecycle._create_dcc_server")
    def test_create_dcc_server_requires_name(self, mock_create_dcc):
        with pytest.raises(ValueError, match="Name is required"):
            create_server(server_type="dcc")

    @patch("dcc_mcp_ipc.server.lifecycle.create_raw_threaded_server")
    @patch("dcc_mcp_ipc.server.lifecycle.get_rpyc_config")
    def test_server_added_to_registry(self, mock_config, mock_create):
        mock_server = MagicMock()
        mock_create.return_value = mock_server
        mock_config.return_value = {}

        create_server(server_type="threaded")
        assert len(lifecycle_module._servers) == 1

    @patch("dcc_mcp_ipc.server.lifecycle.create_raw_threaded_server")
    @patch("dcc_mcp_ipc.server.lifecycle.get_rpyc_config")
    def test_create_with_custom_protocol_config(self, mock_config, mock_create):
        mock_server = MagicMock()
        mock_create.return_value = mock_server

        server = create_server(
            server_type="threaded",
            protocol_config={"allow_all_attrs": True},
        )
        assert server is mock_server
        # When protocol_config provided, get_rpyc_config should NOT be called
        mock_config.assert_not_called()


class TestStartServer:
    """Tests for the start_server function."""

    def _make_mock_server(self):
        mock_server = MagicMock()
        mock_server.host = "localhost"
        mock_server.port = 18812
        return mock_server

    def test_start_server_not_in_registry(self):
        mock_server = self._make_mock_server()
        mock_server.start = MagicMock()

        thread = start_server(mock_server)
        assert isinstance(thread, threading.Thread)

    def test_start_server_in_registry(self):
        mock_server = self._make_mock_server()
        server_id = "test_server_id"
        lifecycle_module._servers[server_id] = {
            "server": mock_server,
            "thread": None,
            "running": False,
            "type": "threaded",
            "name": None,
        }

        mock_server.start = MagicMock()
        start_server(mock_server)
        assert lifecycle_module._servers[server_id]["running"] is True

    def test_start_already_running_raises(self):
        mock_server = self._make_mock_server()
        server_id = "already_running"
        lifecycle_module._servers[server_id] = {
            "server": mock_server,
            "thread": MagicMock(),
            "running": True,
            "type": "threaded",
            "name": None,
        }

        with pytest.raises(ValueError, match="already running"):
            start_server(mock_server)

    def test_start_returns_thread(self):
        mock_server = self._make_mock_server()
        mock_server.start = MagicMock()

        thread = start_server(mock_server)
        assert isinstance(thread, threading.Thread)
        assert thread.daemon is True  # default daemon=True


class TestStopServer:
    """Tests for the stop_server function."""

    def _register_server(self, mock_server, running=True):
        server_id = f"test_{id(mock_server)}"
        lifecycle_module._servers[server_id] = {
            "server": mock_server,
            "thread": None,
            "running": running,
            "type": "threaded",
            "name": "test",
        }
        return server_id

    @patch("dcc_mcp_ipc.server.lifecycle.cleanup_server")
    def test_stop_running_server(self, mock_cleanup):
        mock_cleanup.return_value = True
        mock_server = MagicMock()
        mock_server.host = "localhost"
        mock_server.port = 0

        self._register_server(mock_server, running=True)
        result = stop_server(mock_server)

        assert result is True
        mock_cleanup.assert_called_once()

    def test_stop_server_not_in_registry(self):
        mock_server = MagicMock()
        result = stop_server(mock_server)
        assert result is False

    def test_stop_server_not_running(self):
        mock_server = MagicMock()
        self._register_server(mock_server, running=False)

        result = stop_server(mock_server)
        assert result is True

    @patch("dcc_mcp_ipc.server.lifecycle.cleanup_server")
    def test_stop_server_cleanup_fails(self, mock_cleanup):
        mock_cleanup.side_effect = RuntimeError("cleanup error")
        mock_server = MagicMock()
        mock_server.host = "localhost"
        mock_server.port = 0

        self._register_server(mock_server, running=True)
        result = stop_server(mock_server)

        assert result is False


class TestIsServerRunning:
    """Tests for the is_server_running function."""

    def test_running_server(self):
        mock_server = MagicMock()
        lifecycle_module._servers["run_test"] = {
            "server": mock_server,
            "running": True,
        }
        assert is_server_running(mock_server) is True

    def test_stopped_server(self):
        mock_server = MagicMock()
        lifecycle_module._servers["stop_test"] = {
            "server": mock_server,
            "running": False,
        }
        assert is_server_running(mock_server) is False

    def test_unregistered_server(self):
        mock_server = MagicMock()
        assert is_server_running(mock_server) is False


class TestServerThreadErrorPath:
    """Tests for the _server_thread error path inside start_server."""

    def test_server_thread_exception_sets_running_false(self):
        """When server.start() raises, _server_thread should set running=False."""
        import time

        mock_server = MagicMock()
        mock_server.host = "localhost"
        mock_server.port = 0
        mock_server.start.side_effect = RuntimeError("server crashed")

        thread = start_server(mock_server)
        # Wait briefly for the thread to finish processing the exception
        thread.join(timeout=2.0)

        # Find the registry entry for this server
        server_info = None
        for info in lifecycle_module._servers.values():
            if info["server"] is mock_server:
                server_info = info
                break

        assert server_info is not None
        # running should be set to False by the exception handler
        assert server_info["running"] is False

