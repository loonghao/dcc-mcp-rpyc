"""Tests for the session and action related methods in the DCCAdapter class.

This module contains tests for the get_session_info and get_actions methods of the DCCAdapter class.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Dict
from typing import Tuple

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel
import rpyc

# Import local modules
from dcc_mcp_rpyc.adapter import DCCAdapter
from dcc_mcp_rpyc.client import BaseDCCClient
from dcc_mcp_rpyc.server import DCCServer


# Create a concrete implementation of DCCAdapter for testing
class TestSessionAdapter(DCCAdapter):
    """Test implementation of DCCAdapter for testing session related methods."""

    def __init__(self):
        """Initialize the TestSessionAdapter with default values."""
        self.host = "127.0.0.1"  # Use explicit IPv4 address instead of localhost
        self.port = None
        self.timeout = 5
        # Call the parent constructor with the DCC name
        super().__init__("test_dcc")

    def _initialize_client(self) -> None:
        """Initialize the client for communicating with the DCC application.

        This method initializes the client for the test DCC adapter.
        """
        if self.port is None:
            self.client = None
            return

        try:
            # Create a client
            self.client = BaseDCCClient(self.dcc_name)

            # Connect to the server
            self.client.connection = rpyc.connect(self.host, self.port)
        except Exception as e:
            logging.error(f"Error initializing client: {e}")
            self.client = None

    def _initialize_action_paths(self) -> None:
        """Initialize the paths to search for actions.

        This method initializes the paths to search for actions for the test DCC adapter.
        """
        # No action paths for testing

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        try:
            # Call the remote method
            if self.client and self.client.connection:
                return self.client.connection.root.exposed_get_scene_info()
            return ActionResultModel(
                success=False, message="Not connected to DCC", error="Not connected", context={}
            ).model_dump()
        except Exception as e:
            return ActionResultModel(
                success=False, message="Failed to retrieve scene information", error=str(e), context={}
            ).model_dump()

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session.

        Returns
        -------
            Dict with session information

        """
        try:
            # Call the remote method
            if self.client and self.client.connection:
                return self.client.connection.root.exposed_get_session_info()
            return ActionResultModel(
                success=False, message="Not connected to DCC", error="Not connected", context={}
            ).model_dump()
        except Exception as e:
            return ActionResultModel(
                success=False, message="Failed to retrieve session information", error=str(e), context={}
            ).model_dump()

    def get_actions(self) -> Dict[str, Any]:
        """Get all available actions for the DCC application.

        Returns
        -------
            Dict with action information

        """
        try:
            # Call the remote method
            if self.client and self.client.connection:
                return self.client.connection.root.exposed_get_actions()
            return ActionResultModel(
                success=False, message="Not connected to DCC", error="Not connected", context={}
            ).model_dump()
        except Exception as e:
            return ActionResultModel(
                success=False, message="Failed to retrieve actions", error=str(e), context={}
            ).model_dump()

    def connect(self):
        """Connect to the DCC application."""
        if not self.port:
            raise ValueError("Port is not set")

        # In tests, we need to actually connect instead of raising an exception
        self._initialize_client()
        return self.client is not None


class TestAdapterSessionClass:
    """Test class for the DCCAdapter session related methods."""

    def test_get_session_info(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test getting session info.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        server, port = dcc_rpyc_server  # Unpack both server and port
        adapter = None

        try:
            # Create an adapter with the correct port
            adapter = TestSessionAdapter()
            adapter.port = port  # Set the port to the server port

            # Connect to the server
            adapter.connect()

            # Get session info
            result = adapter.get_session_info()

            # Verify the result is an ActionResultModel
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "success" in result, "Result should contain success"
            assert result["success"], "Result should indicate success"
            assert "message" in result, "Result should have a message"
            assert "context" in result, "Result should have context"
            assert "application" in result["context"], "Result context should contain application info"
            assert result["context"]["application"] == "test_dcc", "Application name should be correct"
            assert "version" in result["context"], "Result context should contain version info"
            assert "user" in result["context"], "Result context should contain user info"
        finally:
            # Clean up
            if adapter and adapter.client:
                adapter.client.disconnect()

    def test_get_actions(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test getting actions.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        server, port = dcc_rpyc_server  # Unpack both server and port
        adapter = None

        try:
            # Create an adapter with the correct port
            adapter = TestSessionAdapter()
            adapter.port = port  # Set the port to the server port

            # Connect to the server
            adapter.connect()

            # Get actions
            result = adapter.get_actions()

            # Verify the result is an ActionResultModel
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "success" in result, "Result should contain success"
            assert result["success"], "Result should indicate success"
            assert "message" in result, "Result should have a message"
            assert "context" in result, "Result should have context"
            assert "actions" in result["context"], "Result context should contain actions"
            assert isinstance(result["context"]["actions"], list), "Actions should be a list"
            assert len(result["context"]["actions"]) > 0, "Actions list should not be empty"
            assert "name" in result["context"]["actions"][0], "Action should have a name"
            assert "category" in result["context"]["actions"][0], "Action should have a category"
            assert "description" in result["context"]["actions"][0], "Action should have a description"
        finally:
            # Clean up
            if adapter and adapter.client:
                adapter.client.disconnect()

    def test_connection_error(self):
        """Test handling of connection errors."""
        adapter = TestSessionAdapter()
        adapter.port = 12345  # Use an invalid port

        # Try to connect (should fail but not raise exception)
        result = adapter.connect()
        assert not result, "Connection should fail with invalid port"

        # Try to get session info (should return error result)
        result = adapter.get_session_info()
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "success" in result, "Result should contain success"
        assert not result["success"], "Result should indicate failure"
        assert "error" in result, "Result should have an error message"

    def test_error_handling(self, monkeypatch):
        """Test error handling in get_session_info and get_actions.

        Args:
        ----
            monkeypatch: Pytest fixture for monkeypatching

        """
        adapter = TestSessionAdapter()
        adapter.port = 8765  # Set a port to avoid "Not connected" error

        # Create a mock client and connection object
        class MockConnection:
            def __init__(self):
                self.root = self

            def exposed_get_session_info(self):
                raise Exception("Test exception")

        class MockClient:
            def __init__(self):
                self.connection = MockConnection()
                self.is_connected_result = True

            def is_connected(self):
                return self.is_connected_result

            def disconnect(self):
                self.is_connected_result = False

        # Set adapter's client to mock object
        adapter.client = MockClient()

        # Try to get session info (should return error result)
        result = adapter.get_session_info()
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "success" in result, "Result should contain success"
        assert not result["success"], "Result should indicate failure"
        assert "error" in result, "Result should have an error message"
        assert "Test exception" in result["error"], "Error should contain the exception message"
