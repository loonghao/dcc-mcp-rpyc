"""Tests for the dcc_adapter module.

This module contains tests for the DCCAdapter class.
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
class TestDCCAdapter(DCCAdapter):
    """Test implementation of DCCAdapter for testing."""

    def __init__(self):
        """Initialize the TestDCCAdapter with default values."""
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
            self.client.root = self.client.connection.root
            self.client.connected = True
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
        try:
            if command == "test_command":
                return ActionResultModel(
                    success=True,
                    message="Command executed successfully",
                    context={"command": command, "args": args, "kwargs": kwargs},
                )
            elif command == "error_command":
                raise ValueError("Test error")
            elif command == "echo":
                return args[0]
            else:
                return ActionResultModel(success=False, message=f"Unknown command: {command}", context={})
        except Exception as e:
            return ActionResultModel(success=False, message=str(e), context={})

    def create_primitive(self, primitive_type: str, params=None) -> Dict[str, Any]:
        """Create a primitive object in the DCC application.

        Args:
        ----
            primitive_type: Type of primitive to create
            params: Parameters for the primitive

        Returns:
        -------
            Dictionary with information about the created primitive

        """
        if params is None:
            params = {}

        try:
            # Simulate creating a primitive
            return ActionResultModel(
                success=True,
                message=f"Created {primitive_type} successfully",
                context={"primitive": primitive_type, "params": params},
            ).model_dump()
        except Exception as e:
            return ActionResultModel(
                success=False, message=f"Failed to create {primitive_type}", error=str(e), context={}
            ).model_dump()

    def call_plugin(self, plugin_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Call a plugin function.

        Args:
        ----
            plugin_name: Name of the plugin to call
            context: Context for the plugin call

        Returns:
        -------
            Result of the plugin call

        """
        try:
            # Simulate calling a plugin
            if plugin_name == "test_plugin":
                return ActionResultModel(
                    success=True,
                    message=f"Successfully called plugin {plugin_name}",
                    context={"plugin": plugin_name, "context": context, "status": "success"},
                ).model_dump()
            else:
                return ActionResultModel(
                    success=False, message=f"Unknown plugin: {plugin_name}", error="Plugin not found", context={}
                ).model_dump()
        except Exception as e:
            return ActionResultModel(
                success=False, message=f"Error calling plugin {plugin_name}", error=str(e), context={}
            ).model_dump()

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

        self._initialize_client()
        return self.client is not None

    def is_connected(self) -> bool:
        """Check if the adapter is connected to the DCC application.

        Returns
        -------
            bool: True if connected, False otherwise

        """
        if not self.client:
            return False

        try:
            # Try to ping the server
            return self.client.is_connected()
        except Exception as e:
            logging.error(f"Error checking connection: {e}")
            return False


class TestDCCAdapterClass:
    """Tests for the DCCAdapter class."""

    def test_adapter_initialization(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test adapter initialization.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        server, port = dcc_rpyc_server  # Unpack both server and port
        adapter = None

        try:
            # Create an adapter with the correct port
            adapter = TestDCCAdapter()
            adapter.port = port  # Set the port to the server port

            # Connect to the server
            adapter.connect()

            # Verify the adapter was created correctly
            assert adapter.host == "127.0.0.1", "Adapter should have the correct host"
            assert adapter.port == port, "Adapter should have the correct port"
            assert adapter.timeout == 5, "Adapter should have the correct timeout"
            assert adapter.dcc_name == "test_dcc", "Adapter should have the correct DCC name"

            # Verify the adapter is connected
            assert adapter.is_connected(), "Adapter should be connected"
            assert adapter.client is not None, "Adapter should have a client"
            assert adapter.client.is_connected(), "Adapter client should be connected"
        finally:
            # Clean up
            if adapter and adapter.client:
                adapter.client.disconnect()

    def test_execute_command(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test executing a command.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        server, port = dcc_rpyc_server  # Unpack both server and port
        adapter = None

        try:
            # Create an adapter with the correct port
            adapter = TestDCCAdapter()
            adapter.port = port  # Set the port to the server port

            # Connect to the server
            adapter.connect()

            # Execute a command
            result = adapter.execute_command("test_command", {"arg1": "value1"})

            # Verify the result is an ActionResultModel
            assert isinstance(result, ActionResultModel), "Result should be an ActionResultModel"
            assert result.success, "Result should indicate success"
            assert result.message, "Result should have a message"
            assert "command" in result.context, "Result context should contain command info"
            assert result.context["command"] == "test_command", "Command name should be correct"
            assert "args" in result.context, "Result context should contain args"
            assert result.context["args"] == ({"arg1": "value1"},), "Args should be correct"
            assert "kwargs" in result.context, "Result context should contain kwargs"
            assert result.context["kwargs"] == {}, "Kwargs should be empty"
        finally:
            # Clean up
            if adapter and adapter.client:
                adapter.client.disconnect()

    def test_create_primitive(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test creating a primitive.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        server, port = dcc_rpyc_server  # Unpack both server and port
        adapter = None

        try:
            # Create an adapter with the correct port
            adapter = TestDCCAdapter()
            adapter.port = port  # Set the port to the server port

            # Connect to the server
            adapter.connect()

            # Create a primitive
            result = adapter.create_primitive("sphere", {"radius": 1.0})

            # Verify the result
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "success" in result, "Result should contain success"
            assert result["success"], "Result should indicate success"
            assert "message" in result, "Result should have a message"
            assert "context" in result, "Result should have context"
            assert "primitive" in result["context"], "Result context should contain primitive info"
            assert result["context"]["primitive"] == "sphere", "Primitive type should be correct"
            assert "params" in result["context"], "Result context should contain params"
            assert result["context"]["params"] == {"radius": 1.0}, "Params should be correct"
        finally:
            # Clean up
            if adapter and adapter.client:
                adapter.client.disconnect()

    def test_get_scene_info(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test getting scene info.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        server, port = dcc_rpyc_server  # Unpack both server and port
        adapter = None

        try:
            # Create an adapter with the correct port
            adapter = TestDCCAdapter()
            adapter.port = port  # Set the port to the server port

            # Connect to the server
            adapter.connect()

            # Get scene info
            result = adapter.get_scene_info()

            # Verify the result is an ActionResultModel
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "success" in result, "Result should contain success"
            assert result["success"], "Result should indicate success"
            assert "message" in result, "Result should have a message"
            assert "context" in result, "Result should have context"
            # Check scene information in context
            assert "name" in result["context"], "Result context should contain scene name"
            assert result["context"]["name"] == "test_scene", "Scene name should be correct"
            assert "path" in result["context"], "Result context should contain scene path"
            assert "modified" in result["context"], "Result context should contain modified flag"
            assert "objects" in result["context"], "Result context should contain objects count"
        finally:
            # Clean up
            if adapter and adapter.client:
                adapter.client.disconnect()

    def test_call_plugin(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test calling a plugin.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        server, port = dcc_rpyc_server  # Unpack both server and port
        adapter = None

        try:
            # Create an adapter with the correct port
            adapter = TestDCCAdapter()
            adapter.port = port  # Set the port to the server port

            # Connect to the server
            adapter.connect()

            # Call a plugin
            result = adapter.call_plugin("test_plugin", {"param1": "value1"})

            # Verify the result is an ActionResultModel
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "success" in result, "Result should contain success"
            assert result["success"], "Result should indicate success"
            assert "message" in result, "Result should have a message"
            assert "context" in result, "Result should have context"
            assert "plugin" in result["context"], "Result context should contain plugin info"
            assert result["context"]["plugin"] == "test_plugin", "Plugin name should be correct"
            assert "context" in result["context"], "Result context should contain the plugin context"
            assert result["context"]["context"] == {"param1": "value1"}, "Plugin context should be correct"
            assert "status" in result["context"], "Result context should contain status"
            assert result["context"]["status"] == "success", "Status should be success"
        finally:
            # Clean up
            if adapter and adapter.client:
                adapter.client.disconnect()

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
            adapter = TestDCCAdapter()
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
            # Check session information in context
            assert "application" in result["context"], "Result context should contain application info"
            assert result["context"]["application"] == "test_dcc", "Application name should be correct"
            assert "version" in result["context"], "Result context should contain version info"
            assert "user" in result["context"], "Result context should contain user info"
            assert "workspace" in result["context"], "Result context should contain workspace info"
            assert "scene" in result["context"], "Result context should contain scene info"
            assert isinstance(result["context"]["scene"], dict), "Scene should be a dictionary"
        finally:
            # Clean up
            if adapter and adapter.client:
                adapter.client.disconnect()

    def test_is_connected(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test checking if the adapter is connected.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        server, port = dcc_rpyc_server  # Unpack both server and port
        adapter = None

        try:
            # Create an adapter with the correct port
            adapter = TestDCCAdapter()
            adapter.port = port  # Set the port to the server port

            # Check before connecting
            assert not adapter.is_connected(), "Adapter should not be connected before connecting"

            # Connect to the server
            adapter.connect()

            # Check after connecting
            assert adapter.is_connected(), "Adapter should be connected after connecting"

            # Disconnect
            adapter.client.disconnect()

            # Check after disconnecting
            assert not adapter.is_connected(), "Adapter should not be connected after disconnecting"
        finally:
            # Clean up
            if adapter and adapter.client and adapter.client.is_connected():
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
            adapter = TestDCCAdapter()
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
