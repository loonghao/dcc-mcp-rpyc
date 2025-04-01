"""Tests for the DCCAdapter class.

This module contains unit tests for the DCCAdapter class, testing its connection, information retrieval, and execution functionality.
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.adapter.dcc import DCCAdapter
from dcc_mcp_rpyc.client import BaseDCCClient


# Create a factory function to create test adapter instances
def create_test_adapter(dcc_name="test_dcc", host="localhost", port=8000):
    """Create a test adapter instance."""

    # Create a concrete DCCAdapter subclass
    class ConcreteDCCAdapter(DCCAdapter):
        def _initialize_action_paths(self):
            self._action_paths = ["test/path"]

    # Return subclass instance
    return ConcreteDCCAdapter(dcc_name, host, port)


@pytest.fixture
def mock_action_adapter():
    """Create a mock ActionAdapter."""
    mock_adapter = MagicMock()
    return mock_adapter


@pytest.fixture
def mock_dcc_client():
    """Create a mock DCC client."""
    client = MagicMock(spec=BaseDCCClient)
    client.get_dcc_info.return_value = {
        "name": "test_dcc",
        "version": "1.0.0",
    }
    return client


def test_dcc_adapter_basic():
    """Test basic functionality of DCCAdapter."""
    # Mock all dependencies
    with patch("dcc_mcp_rpyc.adapter.base.get_action_adapter") as mock_get_adapter, patch(
        "dcc_mcp_rpyc.adapter.dcc.get_client"
    ) as mock_get_client:
        # Set mock objects
        mock_action_adapter = MagicMock()
        mock_get_adapter.return_value = mock_action_adapter

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create test adapter instance using factory function
        adapter = create_test_adapter("test_dcc", "localhost", 8000)

        # Basic assertions
        assert adapter.dcc_name == "test_dcc"
        assert adapter.app_name == "test_dcc"
        assert adapter.host == "localhost"
        assert adapter.port == 8000
        assert adapter.action_adapter == mock_action_adapter
        assert adapter._action_paths == ["test/path"]


def test_get_application_info():
    """Test getting application information."""
    # Mock dependencies
    with patch("dcc_mcp_rpyc.adapter.base.get_action_adapter"), patch(
        "dcc_mcp_rpyc.adapter.dcc.get_client"
    ) as mock_get_client:
        # Set mock client
        mock_client = MagicMock()
        mock_client.get_dcc_info.return_value = {"name": "test_dcc", "version": "1.0.0", "platform": "test"}
        mock_get_client.return_value = mock_client

        # Create adapter instance using factory function
        adapter = create_test_adapter("test_dcc", "localhost", 8000)

        # Execute test
        result = adapter.get_application_info()

        # Validate result
        assert result["success"] is True
        assert "test_dcc" in result["message"]
        assert result["context"]["name"] == "test_dcc"
        assert result["context"]["version"] == "1.0.0"


def test_get_application_info_not_connected():
    """Test getting application information when not connected."""
    # Mock dependencies
    with patch("dcc_mcp_rpyc.adapter.base.get_action_adapter"), patch("dcc_mcp_rpyc.adapter.dcc.get_client"):
        # Create adapter instance using factory function
        adapter = create_test_adapter("test_dcc", "localhost", 8000)

        # Set mock client to None
        adapter.client = None

        # Execute test
        result = adapter.get_application_info()

        # Validate result
        assert result["success"] is False
        assert "Not connected" in result["message"]


def test_execute_command():
    """Test executing a command."""
    # Mock dependencies
    with patch("dcc_mcp_rpyc.adapter.base.get_action_adapter"), patch(
        "dcc_mcp_rpyc.adapter.dcc.get_client"
    ) as mock_get_client:
        # Set mock client
        mock_client = MagicMock()
        mock_client.execute_command.return_value = {"result": "test_result"}
        mock_get_client.return_value = mock_client

        # Create adapter instance using factory function
        adapter = create_test_adapter("test_dcc", "localhost", 8000)

        # Execute test
        result = adapter.execute_command("test_command", arg1="value1")

        # Validate result
        assert result["success"] is True
        assert "executed command" in result["message"]
        assert result["context"]["result"] == "test_result"
        mock_client.execute_command.assert_called_once_with("test_command", arg1="value1")
