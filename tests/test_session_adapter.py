"""Tests for the SessionAdapter class.

This module contains tests for the SessionAdapter class in the adapter.session module.
"""

# Import built-in modules
from unittest import mock

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.adapter.session import SessionAdapter
from dcc_mcp_rpyc.client import BaseApplicationClient
from dcc_mcp_rpyc.utils.errors import ConnectionError


@pytest.mark.usefixtures()  # Mark as fixture, not test class
class MockSessionAdapter(SessionAdapter):
    """Concrete implementation of SessionAdapter for testing."""

    def _initialize_client(self) -> None:
        """Initialize the client for communicating with the application."""
        self.client = None

    def _initialize_action_paths(self) -> None:
        """Initialize the paths to search for actions."""
        # Only set paths, do not call set_action_search_paths method
        self._action_paths = []

    def get_application_info(self):
        """Get information about the application.

        Returns:
            ActionResultModel with application information

        """
        # Import third-party modules
        from dcc_mcp_core.models import ActionResultModel

        return ActionResultModel(
            success=True,
            message="Successfully retrieved application information",
            context={
                "name": self.app_name,
                "version": "1.0.0",
                "platform": "test",
                "executable": "/path/to/test",
                "pid": 12345,
            },
        )


class TestSessionAdapter:
    """Tests for the SessionAdapter class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock client for testing."""
        client = mock.MagicMock(spec=BaseApplicationClient)
        client.host = "localhost"
        client.port = 12345
        client.is_connected.return_value = True
        # Ensure mock_client has call method
        client.call = mock.MagicMock()
        return client

    @pytest.fixture
    def session_adapter(self):
        """Create a SessionAdapter instance for testing."""
        with mock.patch("dcc_mcp_rpyc.adapter.session.get_client") as mock_get_client:
            mock_client = mock.MagicMock(spec=BaseApplicationClient)
            # Ensure mock_client has call method
            mock_client.call = mock.MagicMock()
            mock_get_client.return_value = mock_client

            with mock.patch("dcc_mcp_rpyc.adapter.session.get_action_adapter") as mock_get_action_adapter:
                mock_action_adapter = mock.MagicMock()
                mock_get_action_adapter.return_value = mock_action_adapter
                adapter = MockSessionAdapter("test_app", session_id="test_session")
                yield adapter

    @pytest.fixture
    def connected_adapter(self, session_adapter, mock_client):
        """Create a connected SessionAdapter instance for testing."""
        session_adapter.client = mock_client
        return session_adapter

    def test_init(self):
        """Test initialization of SessionAdapter."""
        # Mock action_adapter
        with mock.patch("dcc_mcp_rpyc.adapter.session.get_action_adapter") as mock_get_action_adapter:
            mock_action_adapter = mock.MagicMock()
            mock_get_action_adapter.return_value = mock_action_adapter

            # Test with explicit session_id
            adapter = MockSessionAdapter("test_app", session_id="test_session")
            assert adapter.app_name == "test_app"
            assert adapter.session_id == "test_session"
            assert adapter.session_data == {}
            assert adapter.action_adapter is not None

            # Test with auto-generated session_id
            adapter = MockSessionAdapter("test_app")
            assert adapter.app_name == "test_app"
            assert "test_app_session_" in adapter.session_id
            assert adapter.session_data == {}
            assert adapter.action_adapter is not None

    def test_connect_success(self, session_adapter, mock_client):
        """Test successful connection."""
        with mock.patch("dcc_mcp_rpyc.adapter.session.get_client", return_value=mock_client):
            result = session_adapter.connect()
            assert result is True
            assert session_adapter.client == mock_client
            mock_client.connect.assert_called_once()

    def test_connect_failure(self, session_adapter):
        """Test connection failure."""
        with mock.patch("dcc_mcp_rpyc.adapter.session.get_client") as mock_get_client:
            mock_client = mock_get_client.return_value
            mock_client.connect.side_effect = ConnectionError("Connection failed")
            result = session_adapter.connect()
            assert result is False
            mock_client.connect.assert_called_once()

    def test_disconnect_success(self, connected_adapter, mock_client):
        """Test successful disconnection."""
        result = connected_adapter.disconnect()
        assert result is True
        mock_client.disconnect.assert_called_once()

    def test_disconnect_failure(self, connected_adapter, mock_client):
        """Test disconnection failure."""
        mock_client.disconnect.side_effect = Exception("Disconnection failed")
        result = connected_adapter.disconnect()
        assert result is False
        mock_client.disconnect.assert_called_once()

    def test_disconnect_not_connected(self, session_adapter):
        """Test disconnection when not connected."""
        session_adapter.client = None
        result = session_adapter.disconnect()
        assert result is True  # Already disconnected

    def test_ensure_connected_already_connected(self, connected_adapter):
        """Test ensure_connected when already connected."""
        result = connected_adapter.ensure_connected()
        assert result is True
        connected_adapter.client.connect.assert_not_called()

    def test_ensure_connected_reconnect(self, connected_adapter, mock_client):
        """Test ensure_connected when reconnection is needed."""
        mock_client.is_connected.return_value = False
        result = connected_adapter.ensure_connected()
        assert result is True
        mock_client.connect.assert_called_once()

    def test_ensure_connected_reconnect_failure(self, connected_adapter, mock_client):
        """Test ensure_connected when reconnection fails."""
        mock_client.is_connected.return_value = False
        mock_client.connect.side_effect = Exception("Reconnection failed")
        result = connected_adapter.ensure_connected()
        assert result is False
        mock_client.connect.assert_called_once()

    def test_ensure_connected_no_client(self, session_adapter):
        """Test ensure_connected when no client exists."""
        session_adapter.client = None
        with mock.patch.object(session_adapter, "connect", return_value=True) as mock_connect:
            result = session_adapter.ensure_connected()
            assert result is True
            mock_connect.assert_called_once()

    def test_is_connected_with_client(self, connected_adapter, mock_client):
        """Test is_connected with a client."""
        mock_client.is_connected.return_value = True
        assert connected_adapter.is_connected() is True
        mock_client.is_connected.return_value = False
        assert connected_adapter.is_connected() is False

    def test_is_connected_no_client(self, session_adapter):
        """Test is_connected with no client."""
        session_adapter.client = None
        assert session_adapter.is_connected() is False

    def test_get_session_info_connected(self, connected_adapter, mock_client):
        """Test get_session_info when connected."""
        connected_adapter.set_session_data("test_key", "test_value")
        info = connected_adapter.get_session_info()
        assert info["session_id"] == "test_session"
        assert info["app_name"] == "test_app"
        assert info["connected"] is True
        assert info["connection"]["host"] == "localhost"
        assert info["connection"]["port"] == 12345
        assert info["session_data"]["test_key"] == "test_value"

    def test_get_session_info_not_connected(self, session_adapter):
        """Test get_session_info when not connected."""
        session_adapter.client = None
        info = session_adapter.get_session_info()
        assert info["session_id"] == "test_session"
        assert info["app_name"] == "test_app"
        assert info["connected"] is False
        assert "connection" not in info
        assert info["session_data"] == {}

    def test_session_data_operations(self, session_adapter):
        """Test session data operations."""
        # Test set_session_data and get_session_data
        session_adapter.set_session_data("key1", "value1")
        assert session_adapter.get_session_data("key1") == "value1"
        assert session_adapter.get_session_data("key2") is None
        assert session_adapter.get_session_data("key2", "default") == "default"

        # Test clear_session_data
        session_adapter.clear_session_data()
        assert session_adapter.session_data == {}
        assert session_adapter.get_session_data("key1") is None

    def test_execute_python_success(self, connected_adapter, mock_client):
        """Test successful Python code execution."""
        mock_client.call.return_value = 42
        result = connected_adapter.execute_python("2 + 2")
        assert result["success"] is True
        assert result["result"] == 42
        mock_client.call.assert_called_once_with("execute_python", "2 + 2", {})

    def test_execute_python_with_context(self, connected_adapter, mock_client):
        """Test Python code execution with context."""
        mock_client.call.return_value = 15
        context = {"x": 10, "y": 5}
        result = connected_adapter.execute_python("x + y", context)
        assert result["success"] is True
        assert result["result"] == 15
        mock_client.call.assert_called_once_with("execute_python", "x + y", context)

    def test_execute_python_not_connected(self, session_adapter):
        """Test Python code execution when not connected."""
        with mock.patch.object(session_adapter, "ensure_connected", return_value=False):
            session_adapter.client = None
            result = session_adapter.execute_python("2 + 2")
            assert result["success"] is False
            assert "Not connected" in result["error"]

    def test_execute_python_exception(self, connected_adapter, mock_client):
        """Test Python code execution with exception."""
        mock_client.call.side_effect = Exception("Execution failed")
        result = connected_adapter.execute_python("2 + 2")
        assert result["success"] is False
        assert "Execution failed" in result["error"]
        assert "Failed to execute Python code" in result["message"]

    def test_call_action_function_success(self, connected_adapter, mock_client):
        """Test successful action function call."""
        expected_result = {"success": True, "message": "Action executed successfully", "context": {"result": 42}}
        mock_client.call.return_value = expected_result
        result = connected_adapter.call_action_function("test_action", "test_function", {"param": "value"})
        assert result == expected_result
        mock_client.call.assert_called_once_with(
            "call_action_function", "test_action", "test_function", {"param": "value"}
        )

    def test_call_action_function_not_connected(self, session_adapter):
        """Test action function call when not connected."""
        with mock.patch.object(session_adapter, "ensure_connected", return_value=False):
            session_adapter.client = None
            result = session_adapter.call_action_function("test_action", "test_function")
            assert result["success"] is False
            assert "Not connected" in result["error"]
            assert "Failed to call action function" in result["message"]

    def test_call_action_function_exception(self, connected_adapter, mock_client):
        """Test action function call with exception."""
        mock_client.call.side_effect = Exception("Action execution failed")
        result = connected_adapter.call_action_function("test_action", "test_function")
        assert result["success"] is False
        assert "Action execution failed" in result["error"]
        assert "Failed to call action function" in result["message"]
