"""Tests for the session_info functionality.

This module contains tests for the get_session_info and get_scene_info methods.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Dict
from typing import Tuple

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel
import pytest

# Import local modules
from dcc_mcp_rpyc.adapter import DCCAdapter
from dcc_mcp_rpyc.client import BaseDCCClient
from dcc_mcp_rpyc.server import BaseRPyCService
from dcc_mcp_rpyc.server import DCCServer


class TestSessionInfoService(BaseRPyCService):
    """Test service that implements both get_scene_info and get_session_info."""

    def exposed_get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        return ActionResultModel(
            success=True,
            message="Successfully retrieved scene information",
            context={"name": "test_scene", "path": "/path/to/test_scene", "modified": False, "objects": 0},
        ).model_dump()

    def exposed_get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session.

        Returns
        -------
            Dict with session information

        """
        return ActionResultModel(
            success=True,
            message="Successfully retrieved session information",
            context={
                "application": "test_dcc",
                "version": "1.0.0",
                "user": "test_user",
                "workspace": "/path/to/workspace",
                "scene": {"name": "test_scene", "path": "/path/to/test_scene", "modified": False, "objects": 0},
            },
        ).model_dump()

    def exposed_call_action_function(
        self, action_name: str, function_name: str, context: Dict[str, Any], *args, **kwargs
    ) -> Dict[str, Any]:
        """Call an action function.

        Args:
        ----
            action_name: Name of the action
            function_name: Name of the function to call
            context: Context dictionary with additional parameters
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
        -------
            Result of the action function call in ActionResultModel format

        """
        # Return a result in ActionResultModel format
        return {
            "success": True,
            "message": f"Successfully called {action_name}.{function_name}",
            "prompt": f"You can now use the result of {action_name}.{function_name}",
            "error": None,
            "context": {
                "action_name": action_name,
                "function_name": function_name,
                "args": args,
                "kwargs": kwargs,
                "user_context": context,
            },
        }


# Create a concrete implementation of DCCAdapter for testing
class TestSessionAdapter(DCCAdapter):
    """Test implementation of DCCAdapter with session info support."""

    def __init__(self):
        """Initialize the TestSessionAdapter with default values."""
        # Initialize with default values
        self.host = "127.0.0.1"  # Use explicit IPv4 address instead of localhost
        self.port = None
        self.timeout = 5
        # Call the parent constructor with the DCC name
        super().__init__("test_dcc")
        self.last_connection_check = 0
        self.connection_check_interval = 20

    def _initialize_client(self) -> None:
        """Initialize the client for communicating with the DCC application.

        This method initializes the client for the test DCC adapter.
        """
        if self.port is None:
            self.client = None
            return

        try:
            # Create a client
            self.client = BaseDCCClient(
                dcc_name=self.dcc_name,
                host=self.host,
                port=self.port,
                auto_connect=True,
                connection_timeout=self.timeout,
            )
        except Exception as e:
            logging.error(f"Error connecting to DCC service: {e}")
            self.client = None

    def _initialize_action_paths(self) -> None:
        """Initialize the paths to search for actions.

        This method initializes the action paths for the test DCC adapter.
        """
        self.action_paths = ["test/actions/path"]

    def execute_command(self, command: str, *args, **kwargs) -> Dict[str, Any]:
        """Execute a command in the DCC application.

        Args:
        ----
            command: Command to execute
            *args: Positional arguments for the command
            **kwargs: Keyword arguments for the command

        Returns:
        -------
            Result of the command execution

        """
        return {"command": command, "args": args, "kwargs": kwargs}

    def create_primitive(self, primitive_type: str, params=None) -> Dict[str, Any]:
        """Create a primitive object in the DCC application.

        Args:
        ----
            primitive_type: Type of primitive to create
            params: Parameters for primitive creation

        Returns:
        -------
            Result of primitive creation

        """
        if params is None:
            params = {}

        return {"primitive_type": primitive_type, "params": params}

    def call_plugin(self, plugin_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Call a plugin function.

        Args:
        ----
            plugin_name: Name of the plugin
            context: Context dictionary with additional parameters

        Returns:
        -------
            Result of the plugin function call

        """
        return {"plugin": plugin_name, "context": context, "status": "success"}

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        self.ensure_connected()
        try:
            # Call the get_scene_info function on the DCC client
            if self.client and self.client.connection:
                result = self.client.connection.root.exposed_get_scene_info()

                # If result is already an ActionResultModel dict, return it
                if isinstance(result, dict) and all(k in result for k in ["success", "message", "context"]):
                    return result

                # Otherwise, wrap the result in an ActionResultModel
                return ActionResultModel(
                    success=True, message="Successfully retrieved scene information", context=result
                ).model_dump()
            return ActionResultModel(
                success=False, message="Not connected to DCC", error="Not connected", context={}
            ).model_dump()
        except Exception as e:
            logging.error(f"Error getting scene info: {e}")
            return ActionResultModel(
                success=False, message="Failed to retrieve scene information", error=str(e), context={}
            ).model_dump()

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session.

        Returns
        -------
            Dict with session information

        """
        self.ensure_connected()
        try:
            # Call the get_session_info function on the DCC client
            if self.client and self.client.connection:
                result = self.client.connection.root.exposed_get_session_info()

                # If result is already an ActionResultModel dict, return it
                if isinstance(result, dict) and all(k in result for k in ["success", "message", "context"]):
                    return result

                # Otherwise, wrap the result in an ActionResultModel
                return ActionResultModel(
                    success=True, message="Successfully retrieved session information", context=result
                ).model_dump()
            return ActionResultModel(
                success=False, message="Not connected to DCC", error="Not connected", context={}
            ).model_dump()
        except Exception as e:
            logging.error(f"Error getting session info: {e}")
            return ActionResultModel(
                success=False, message="Failed to retrieve session information", error=str(e), context={}
            ).model_dump()

    def ensure_connected(self):
        """Ensure the adapter is connected to the DCC application."""
        if not self.is_connected():
            self._initialize_client()

    def call_action_function(
        self, action_name: str, function_name: str, context: Dict[str, Any], *args, **kwargs
    ) -> Dict[str, Any]:
        """Call an action function in the DCC application.

        Args:
        ----
            action_name: Name of the action
            function_name: Name of the function to call
            context: Context dictionary with additional parameters
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
        -------
            Result of the action function call in ActionResultModel format

        """
        self.ensure_connected()
        try:
            # Call the call_action_function method of the DCC client
            if self.is_connected():
                return self.client.call("call_action_function", action_name, function_name, context, *args, **kwargs)
            else:
                # Return error information if not connected
                return {
                    "success": False,
                    "message": "Failed to call action function: Not connected to DCC",
                    "prompt": "Please check the connection to the DCC application",
                    "error": "Not connected to DCC",
                    "context": {"action_name": action_name, "function_name": function_name},
                }
        except Exception as e:
            logging.error(f"Error calling action function: {e}")
            # Return error information in ActionResultModel format
            return {
                "success": False,
                "message": f"Failed to call action function: {e}",
                "prompt": "Please check the error message and try again",
                "error": str(e),
                "context": {"action_name": action_name, "function_name": function_name},
            }

    def is_connected(self) -> bool:
        """Check if the adapter is connected to the DCC application.

        Returns
        -------
            True if connected, False otherwise

        """
        return self.client is not None and hasattr(self.client, "root")


@pytest.fixture
def session_info_server() -> Tuple[DCCServer, int]:
    """Create a DCC RPYC server with session info support for testing.

    Returns
    -------
        Tuple of (server, port)

    """
    # Create a server
    server = DCCServer(
        dcc_name="test_dcc",
        service_class=TestSessionInfoService,
        host="127.0.0.1",
        port=0,  # Let OS choose a port
    )

    # Start the server in a thread
    server._start_in_thread()

    # Get the port
    port = server.port

    try:
        yield server, port
    finally:
        # Clean up
        server.stop()


class TestSessionInfo:
    """Tests for the session info functionality."""

    def test_get_scene_info(self, session_info_server: Tuple[DCCServer, int]):
        """Test getting scene info.

        Args:
        ----
            session_info_server: Fixture providing a DCC RPYC server

        """
        server, port = session_info_server
        adapter = None

        try:
            # Create an adapter with the correct port
            adapter = TestSessionAdapter()
            adapter.port = port  # Set the port to the server port

            # Initialize the client
            adapter._initialize_client()

            # Get scene info
            result = adapter.get_scene_info()

            # Verify the result
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "success" in result, "Result should contain success field"
            assert result["success"] is True, "Scene info retrieval should be successful"
            assert "message" in result, "Result should contain a message"
            assert "context" in result, "Result should contain context"
            assert isinstance(result["context"], dict), "Context should be a dictionary"
            assert "name" in result["context"], "Scene info should contain a name"
            assert result["context"]["name"] == "test_scene", "Scene name should be correct"
            assert "path" in result["context"], "Scene info should contain a path"
            assert "modified" in result["context"], "Scene info should contain a modified flag"
            assert "objects" in result["context"], "Scene info should contain an objects count"
        finally:
            # Clean up
            if adapter and adapter.client and adapter.client.is_connected():
                adapter.client.disconnect()

    def test_get_session_info(self, session_info_server: Tuple[DCCServer, int]):
        """Test getting session info.

        Args:
        ----
            session_info_server: Fixture providing a DCC RPYC server

        """
        server, port = session_info_server
        adapter = None

        try:
            # Create an adapter with the correct port
            adapter = TestSessionAdapter()
            adapter.port = port  # Set the port to the server port

            # Initialize the client
            adapter._initialize_client()

            # Get session info
            result = adapter.get_session_info()

            # Verify the result
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "success" in result, "Result should contain success field"
            assert result["success"] is True, "Session info retrieval should be successful"
            assert "message" in result, "Result should contain a message"
            assert "context" in result, "Result should contain context"
            assert isinstance(result["context"], dict), "Context should be a dictionary"
            assert "application" in result["context"], "Session info should contain an application"
            assert result["context"]["application"] == "test_dcc", "Application name should be correct"
            assert "version" in result["context"], "Session info should contain a version"
            assert "user" in result["context"], "Session info should contain a user"
            assert "workspace" in result["context"], "Session info should contain a workspace"
            assert "scene" in result["context"], "Session info should contain scene info"
            assert isinstance(result["context"]["scene"], dict), "Scene info should be a dictionary"
        finally:
            # Clean up
            if adapter and adapter.client and adapter.client.is_connected():
                adapter.client.disconnect()

    def test_backward_compatibility(self, session_info_server: Tuple[DCCServer, int]):
        """Test backward compatibility with older DCC clients.

        Args:
        ----
            session_info_server: Fixture providing a DCC RPYC server

        """
        server, port = session_info_server
        adapter = None

        try:
            # Create an adapter with the correct port
            adapter = TestSessionAdapter()
            adapter.port = port  # Set the port to the server port

            # Initialize the client
            adapter._initialize_client()

            # Get scene info
            scene_info = adapter.get_scene_info()
            assert scene_info["success"] is True, "Scene info retrieval should be successful"
            assert "context" in scene_info, "Result should contain context"
            assert "name" in scene_info["context"], "Scene info should contain a name"

            # Get session info
            session_info = adapter.get_session_info()
            assert session_info["success"] is True, "Session info retrieval should be successful"
            assert "context" in session_info, "Result should contain context"
            assert "application" in session_info["context"], "Session info should contain an application"
            assert "scene" in session_info["context"], "Session info should contain scene info"

            # Verify the scene info is the same in both calls
            assert (
                session_info["context"]["scene"]["name"] == scene_info["context"]["name"]
            ), "Scene name should be the same in both calls"
        finally:
            # Clean up
            if adapter and adapter.client and adapter.client.is_connected():
                adapter.client.disconnect()
