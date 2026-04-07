"""Tests for client/dcc.py (BaseDCCClient).

Covers ensure_connection context manager, execute_with_connection,
and all DCC-specific remote methods.
"""

# Import built-in modules
from contextlib import contextmanager
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.client.dcc import BaseDCCClient


def make_client(connected=True):
    """Create a BaseDCCClient with mocked connection."""
    client = BaseDCCClient("maya", host="localhost", port=7001, auto_connect=False)
    if connected:
        client.connection = MagicMock()
    return client


class TestBaseDCCClientInit:
    """Tests for BaseDCCClient initialisation."""

    def test_dcc_name_lowercased(self):
        """Test that dcc_name is stored in lowercase."""
        client = BaseDCCClient("Maya", host="localhost", port=7001, auto_connect=False)
        assert client.dcc_name == "maya"


class TestEnsureConnection:
    """Tests for BaseDCCClient.ensure_connection context manager."""

    def test_yields_connection_when_connected(self):
        """Test that context manager yields the active connection."""
        client = make_client(connected=True)
        with patch.object(client, "is_connected", return_value=True):
            with client.ensure_connection() as conn:
                assert conn is client.connection

    def test_connects_when_not_connected(self):
        """Test that ensure_connection tries to connect if not already connected."""
        client = make_client(connected=False)
        with patch.object(client, "is_connected", return_value=False), patch.object(
            client, "connect", return_value=True
        ):
            client.connection = MagicMock()
            with client.ensure_connection() as conn:
                assert conn is client.connection

    def test_raises_if_connect_fails(self):
        """Test that ensure_connection raises ConnectionError if connect returns False."""
        client = make_client(connected=False)
        with patch.object(client, "is_connected", return_value=False), patch.object(
            client, "connect", return_value=False
        ):
            with pytest.raises(ConnectionError):
                with client.ensure_connection():
                    pass

    def test_propagates_inner_exception(self):
        """Test that exceptions inside the context manager propagate."""
        client = make_client(connected=True)
        with patch.object(client, "is_connected", return_value=True):
            with pytest.raises(ValueError, match="test error"):
                with client.ensure_connection():
                    raise ValueError("test error")


class TestExecuteWithConnection:
    """Tests for BaseDCCClient.execute_with_connection."""

    def test_calls_func_with_connection(self):
        """Test that func receives the connection."""
        client = make_client(connected=True)
        mock_conn = MagicMock()
        client.connection = mock_conn

        with patch.object(client, "is_connected", return_value=True):
            result = client.execute_with_connection(lambda c: c.root.ping())

        mock_conn.root.ping.assert_called_once()

    def test_propagates_exception_from_func(self):
        """Test that exceptions from the function propagate."""
        client = make_client(connected=True)
        with patch.object(client, "is_connected", return_value=True):
            with pytest.raises(RuntimeError, match="remote error"):
                client.execute_with_connection(
                    lambda c: (_ for _ in ()).throw(RuntimeError("remote error"))
                )


class TestDCCMethods:
    """Tests for BaseDCCClient DCC-specific remote methods."""

    def _connected_client(self):
        """Return a client whose execute_with_connection is patched."""
        client = make_client(connected=False)

        def mock_exec(func):
            return func(client.connection)

        client.connection = MagicMock()
        client.execute_with_connection = mock_exec
        return client

    def test_get_dcc_info(self):
        """Test get_dcc_info delegates to conn.root.get_dcc_info."""
        client = self._connected_client()
        client.connection.root.get_dcc_info.return_value = {"name": "maya", "version": "2025"}

        result = client.get_dcc_info()

        assert result["name"] == "maya"
        client.connection.root.get_dcc_info.assert_called_once()

    def test_get_scene_info(self):
        """Test get_scene_info delegates to conn.root.get_scene_info."""
        client = self._connected_client()
        client.connection.root.get_scene_info.return_value = {"objects": []}

        result = client.get_scene_info()

        assert result["objects"] == []

    def test_get_session_info(self):
        """Test get_session_info delegates to conn.root.get_session_info."""
        client = self._connected_client()
        client.connection.root.get_session_info.return_value = {"session_id": "s1"}

        result = client.get_session_info()

        assert result["session_id"] == "s1"

    def test_create_primitive_success(self):
        """Test create_primitive success path."""
        client = self._connected_client()
        client.connection.root.create_primitive.return_value = {"name": "pCube1"}

        result = client.create_primitive("cube", size=2.0)

        client.connection.root.create_primitive.assert_called_once_with("cube", size=2.0)
        assert result["name"] == "pCube1"

    def test_create_primitive_exception_returns_error_dict(self):
        """Test create_primitive returns ActionResultModel on exception."""
        client = make_client(connected=False)
        with patch.object(client, "is_connected", return_value=False), patch.object(
            client, "connect", return_value=False
        ):
            result = client.create_primitive("cube")

        assert result["success"] is False
        assert "Failed to create cube" in result["message"]

    def test_execute_command_success(self):
        """Test execute_command success path."""
        client = self._connected_client()
        client.connection.root.execute_command.return_value = {"result": "ok"}

        result = client.execute_command("polyCube", name="myCube")

        assert result["result"] == "ok"

    def test_execute_command_exception_returns_error_dict(self):
        """Test execute_command returns ActionResultModel on exception."""
        client = make_client(connected=False)
        with patch.object(client, "is_connected", return_value=False), patch.object(
            client, "connect", return_value=False
        ):
            result = client.execute_command("badCmd")

        assert result["success"] is False

    def test_execute_script_success(self):
        """Test execute_script success path."""
        client = self._connected_client()
        client.connection.root.execute_script.return_value = {"output": "hello"}

        result = client.execute_script("print('hello')", script_type="python")

        assert result["output"] == "hello"

    def test_execute_script_exception_returns_error_dict(self):
        """Test execute_script returns ActionResultModel on exception."""
        client = make_client(connected=False)
        with patch.object(client, "is_connected", return_value=False), patch.object(
            client, "connect", return_value=False
        ):
            result = client.execute_script("bad_script")

        assert result["success"] is False

    def test_execute_python_success(self):
        """Test execute_python success path."""
        client = make_client(connected=True)
        client.connection.root.execute_python.return_value = 42
        with patch.object(client, "is_connected", return_value=True):
            result = client.execute_python("1 + 1")

        assert result == 42

    def test_execute_python_not_connected_raises(self):
        """Test execute_python raises ConnectionError when not connected."""
        client = make_client(connected=False)
        with patch.object(client, "is_connected", return_value=False):
            with pytest.raises(ConnectionError):
                client.execute_python("print('hi')")

    def test_execute_python_exception_propagates(self):
        """Test execute_python propagates remote exceptions."""
        client = make_client(connected=True)
        client.connection.root.execute_python.side_effect = RuntimeError("syntax error")
        with patch.object(client, "is_connected", return_value=True):
            with pytest.raises(RuntimeError, match="syntax error"):
                client.execute_python("bad syntax!!!")

    def test_execute_dcc_command_success(self):
        """Test execute_dcc_command delegates to conn.root.execute_dcc_command."""
        client = make_client(connected=True)
        client.connection.root.execute_dcc_command.return_value = "mel_result"
        with patch.object(client, "is_connected", return_value=True):
            result = client.execute_dcc_command("polyCube")

        assert result == "mel_result"

    def test_execute_dcc_command_not_connected_raises(self):
        """Test execute_dcc_command raises ConnectionError when not connected."""
        client = make_client(connected=False)
        with patch.object(client, "is_connected", return_value=False):
            with pytest.raises(ConnectionError):
                client.execute_dcc_command("polyCube")

    def test_execute_dcc_command_exception_propagates(self):
        """Test execute_dcc_command propagates remote exceptions."""
        client = make_client(connected=True)
        client.connection.root.execute_dcc_command.side_effect = RuntimeError("cmd failed")
        with patch.object(client, "is_connected", return_value=True):
            with pytest.raises(RuntimeError, match="cmd failed"):
                client.execute_dcc_command("badCmd")


class TestClose:
    """Tests for BaseDCCClient.close."""

    def test_close_when_connected(self):
        """Test close disconnects when connected."""
        client = make_client(connected=True)
        with patch.object(client, "is_connected", return_value=True), patch.object(
            client, "disconnect"
        ) as mock_disconnect:
            client.close()

        mock_disconnect.assert_called_once()

    def test_close_when_not_connected(self):
        """Test close is a no-op when not connected."""
        client = make_client(connected=False)
        with patch.object(client, "is_connected", return_value=False), patch.object(
            client, "disconnect"
        ) as mock_disconnect:
            client.close()

        mock_disconnect.assert_not_called()
