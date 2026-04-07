"""Tests for application/client.py (ApplicationClient).

Covers execute_remote_call, get_application_info, get_environment_info,
execute_python, import_module, call_function, get_actions,
and connect_to_application factory.
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.application.client import ApplicationClient
from dcc_mcp_ipc.application.client import connect_to_application


def make_client(connected=False, **kwargs):
    """Create an ApplicationClient with auto_connect disabled."""
    defaults = {"app_name": "python", "host": "localhost", "port": 18812, "auto_connect": False}
    defaults.update(kwargs)
    return ApplicationClient(**defaults)


class TestApplicationClientInit:
    """Tests for ApplicationClient initialisation."""

    def test_default_app_name(self):
        """Test default app name is 'python'."""
        client = make_client()
        assert client.app_name == "python"


class TestExecuteRemoteCall:
    """Tests for ApplicationClient.execute_remote_call."""

    def test_callable_receives_connection(self):
        """Test that a callable func receives the connection object."""
        client = make_client()
        mock_conn = MagicMock()
        client.connection = mock_conn
        mock_conn.root.ping.return_value = "pong"

        with patch.object(client, "is_connected", return_value=True):
            result = client.execute_remote_call(lambda c: c.root.ping())

        assert result == "pong"

    def test_string_name_uses_execute_remote_command(self):
        """Test that a string name falls back to execute_remote_command."""
        client = make_client()
        client.connection = MagicMock()

        with (
            patch.object(client, "is_connected", return_value=True),
            patch.object(client, "execute_remote_command", return_value="cmd_result") as mock_cmd,
        ):
            result = client.execute_remote_call("my_command", "arg1", kw="val")

        assert result == "cmd_result"
        mock_cmd.assert_called_once_with("my_command", "arg1", kw="val")

    def test_connects_when_not_connected(self):
        """Test that execute_remote_call connects first if not connected."""
        client = make_client()
        mock_conn = MagicMock()
        client.connection = mock_conn
        mock_conn.root.test.return_value = 1

        with (
            patch.object(client, "is_connected", return_value=False),
            patch.object(client, "connect", return_value=True),
        ):
            result = client.execute_remote_call(lambda c: c.root.test())

        assert result == 1

    def test_raises_if_connect_fails(self):
        """Test that ConnectionError is raised when connect fails."""
        client = make_client()

        with (
            patch.object(client, "is_connected", return_value=False),
            patch.object(client, "connect", return_value=False),
        ):
            with pytest.raises(ConnectionError):
                client.execute_remote_call(lambda c: None)

    def test_propagates_remote_exception(self):
        """Test that exceptions from the remote call propagate."""
        client = make_client()
        client.connection = MagicMock()

        with patch.object(client, "is_connected", return_value=True):
            with pytest.raises(RuntimeError, match="remote failure"):
                client.execute_remote_call(lambda c: (_ for _ in ()).throw(RuntimeError("remote failure")))


class TestApplicationClientRemoteMethods:
    """Tests for remote-delegating methods of ApplicationClient."""

    def _connected_client(self):
        """Return a client with execute_remote_call patched for predictable testing."""
        client = make_client()
        client.connection = MagicMock()

        def mock_exec(func, *args, **kwargs):
            return func(client.connection)

        client.execute_remote_call = mock_exec
        return client

    def test_get_application_info(self):
        """Test get_application_info delegates to root.get_application_info."""
        client = self._connected_client()
        client.connection.root.get_application_info.return_value = {"name": "python"}

        result = client.get_application_info()

        assert result["name"] == "python"

    def test_get_environment_info(self):
        """Test get_environment_info delegates to root.get_environment_info."""
        client = self._connected_client()
        client.connection.root.get_environment_info.return_value = {"python_version": "3.11"}

        result = client.get_environment_info()

        assert result["python_version"] == "3.11"

    def test_execute_python(self):
        """Test execute_python delegates to root.execute_python."""
        client = self._connected_client()
        client.connection.root.execute_python.return_value = {"result": 42}

        result = client.execute_python("1+1")

        client.connection.root.execute_python.assert_called_once_with("1+1", None)
        assert result == {"result": 42}

    def test_execute_python_with_context(self):
        """Test execute_python passes context."""
        client = self._connected_client()
        client.connection.root.execute_python.return_value = {"result": 10}
        ctx = {"x": 5}

        client.execute_python("result = x * 2", ctx)

        client.connection.root.execute_python.assert_called_once_with("result = x * 2", ctx)

    def test_import_module(self):
        """Test import_module delegates to root.get_module."""
        client = self._connected_client()
        mock_os = MagicMock()
        client.connection.root.get_module.return_value = mock_os

        result = client.import_module("os")

        client.connection.root.get_module.assert_called_once_with("os")
        assert result is mock_os

    def test_call_function(self):
        """Test call_function delegates to root.call_function."""
        client = self._connected_client()
        client.connection.root.call_function.return_value = "/tmp/test.txt"

        result = client.call_function("os.path", "join", "/tmp", "test.txt")

        client.connection.root.call_function.assert_called_once_with("os.path", "join", "/tmp", "test.txt")
        assert result == "/tmp/test.txt"

    def test_get_actions(self):
        """Test get_actions delegates to root.get_actions."""
        client = self._connected_client()
        client.connection.root.get_actions.return_value = {"action1": {}}

        result = client.get_actions()

        assert result == {"action1": {}}


class TestConnectToApplication:
    """Tests for connect_to_application factory function."""

    def test_returns_application_client(self):
        """Test that connect_to_application returns an ApplicationClient."""
        client = connect_to_application(host="127.0.0.1", port=18812, auto_connect=False)
        assert isinstance(client, ApplicationClient)

    def test_custom_params(self):
        """Test that custom params are forwarded correctly."""
        client = connect_to_application(
            host="192.168.1.1",
            port=9999,
            connection_timeout=10.0,
            auto_connect=False,
            app_name="houdini",
        )
        assert client.host == "192.168.1.1"
        assert client.port == 9999
        assert client.app_name == "houdini"
