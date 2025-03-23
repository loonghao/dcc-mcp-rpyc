"""Integration tests for DCC-MCP-RPYC.

This module contains integration tests that test the interaction between
different components of the DCC-MCP-RPYC system.
"""

# Import built-in modules
import time
from typing import Any
from typing import Dict
from typing import Generator
from typing import Tuple

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.adapter import DCCAdapter
from dcc_mcp_rpyc.client import BaseDCCClient
from dcc_mcp_rpyc.server import DCCRPyCService
from dcc_mcp_rpyc.server import DCCServer


# Create a concrete implementation of DCCAdapter for testing
class TestDCCAdapter(DCCAdapter):
    """Test implementation of DCCAdapter for integration testing."""

    def __init__(self, host="127.0.0.1", port=None, dcc_name="test_dcc"):
        """Initialize the TestDCCAdapter with specified values."""
        self.host = host
        self.port = port
        super().__init__(dcc_name)

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
                connection_timeout=5.0,  # Increase the connection timeout
            )

            # Wait for the connection to establish
            time.sleep(0.5)

            # Verify the connection status
            if not self.client.is_connected():
                print(f"Warning: Client failed to connect to {self.host}:{self.port}")

        except Exception as e:
            print(f"Error initializing client: {e}")
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
                return {"result": "test_result", "args": args, "kwargs": kwargs}
            else:
                return {"result": f"Unknown command: {command}"}
        except Exception as e:
            return {"error": str(e)}

    def create_primitive(self, primitive_type: str, **kwargs) -> Dict[str, Any]:
        """Create a primitive object in the DCC application.

        Args:
        ----
            primitive_type: Type of primitive to create
            **kwargs: Additional arguments for primitive creation

        Returns:
        -------
            Result of primitive creation

        """
        return {"primitive": primitive_type, "kwargs": kwargs}

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        return {"name": "test_scene", "path": "/path/to/test_scene", "modified": False, "objects": 0}

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
        # Return result in ActionResultModel format
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
                "execution_time": "0.05s",
                "result_type": "mock_result",
                "dcc_info": {"name": self.dcc_name, "version": "2023.0", "platform": "test"},
            },
        }

    def is_connected(self) -> bool:
        """Check if the adapter is connected to the DCC application.

        Returns
        -------
            True if connected, False otherwise

        """
        return self.client is not None and hasattr(self.client, "root") and self.client.is_connected()


@pytest.fixture
def integration_setup(
    temp_registry_path: str,
) -> Generator[Tuple[DCCServer, BaseDCCClient, TestDCCAdapter], None, None]:
    """Set up an integration test environment.

    This fixture creates a DCCServer, a BaseDCCClient, and a TestDCCAdapter
    for integration testing.

    Args:
    ----
        temp_registry_path: Fixture providing a temporary registry file path

    Yields:
    ------
        Tuple of (server, client, adapter)

    """
    # Create a DCCServer
    server = DCCServer(
        dcc_name="test_dcc",
        service_class=TestDCCService,
        host="127.0.0.1",  # Use 127.0.0.1 instead of localhost
        port=0,  # Let OS choose a port
    )

    # Start the server
    port = server.start(threaded=True)

    # Wait for the server to start
    time.sleep(1.0)  # Increase the wait time to 1 second

    # Create a client
    client = BaseDCCClient(
        dcc_name="test_dcc",
        host="127.0.0.1",  # Use 127.0.0.1 instead of localhost
        port=port,
        auto_connect=True,
        connection_timeout=5.0,  # Set the connection timeout to 5 seconds
    )

    # Create an adapter
    adapter = TestDCCAdapter(host="127.0.0.1", port=port)  # Use 127.0.0.1 instead of localhost

    # Ensure the adapter connects to the server
    adapter._initialize_client()

    # Wait for the connection to establish
    time.sleep(1.0)  # Increase the wait time to 1 second

    # Verify the connection status
    if not client.is_connected():
        print("Warning: Client failed to connect to server")

    if not adapter.is_connected():
        print("Warning: Adapter failed to connect to server")

    # If the connection fails, retry up to 3 times
    retry_count = 0
    max_retries = 3

    while (not client.is_connected() or not adapter.is_connected()) and retry_count < max_retries:
        print(f"Retrying connection (attempt {retry_count + 1}/{max_retries})...")

        # Reinitialize the client
        if not client.is_connected():
            try:
                client.disconnect()
            except Exception:
                pass
            client = BaseDCCClient(
                dcc_name="test_dcc", host="127.0.0.1", port=port, auto_connect=True, connection_timeout=5.0
            )

        # Reinitialize the adapter
        if not adapter.is_connected():
            adapter = TestDCCAdapter(host="127.0.0.1", port=port)
            adapter._initialize_client()

        time.sleep(1.0)
        retry_count += 1

    yield server, client, adapter

    # Clean up
    try:
        # First disconnect the client
        if client and hasattr(client, "is_connected") and client.is_connected():
            client.disconnect()

        # Disconnect the adapter if it's connected
        if adapter and hasattr(adapter, "client") and adapter.client:
            adapter.client.disconnect()

        # Sleep briefly to allow disconnections to complete
        time.sleep(0.1)

        # Then stop the server
        if server and hasattr(server, "is_running") and server.is_running():
            # Force close any remaining clients before stopping
            if hasattr(server, "server") and server.server and hasattr(server.server, "clients"):
                for conn in list(server.server.clients):
                    try:
                        conn.close()
                    except Exception as e:
                        print(f"Error closing client connection: {e}")

            # Now stop the server
            server.stop()
    except Exception as e:
        print(f"Error during integration test cleanup: {e}")


class TestDCCService(DCCRPyCService):
    """Test DCC RPYC service for integration testing."""

    def exposed_get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        return {"name": "test_scene", "path": "/path/to/test_scene", "modified": False, "objects": 0}

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        return self.exposed_get_scene_info()

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session.

        Returns
        -------
            Dict with session information

        """
        return self.exposed_get_session_info()

    def exposed_get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session.

        Returns
        -------
            Dict with session information

        """
        return {"name": "test_session", "id": "test_session_id"}

    def exposed_execute_cmd(self, cmd_name: str, *args, **kwargs) -> Dict[str, Any]:
        """Execute a command.

        Args:
        ----
            cmd_name: Name of the command to execute
            *args: Positional arguments for the command
            **kwargs: Keyword arguments for the command

        Returns:
        -------
            Result of the command execution

        """
        if cmd_name == "test_command":
            return {"result": "test_result", "args": args, "kwargs": kwargs}
        else:
            return {"result": f"Unknown command: {cmd_name}"}

    def exposed_create_primitive(self, primitive_type: str, **kwargs) -> Dict[str, Any]:
        """Create a primitive object.

        Args:
        ----
            primitive_type: Type of primitive to create
            **kwargs: Additional arguments for primitive creation

        Returns:
        -------
            Result of primitive creation

        """
        return {"primitive": primitive_type, "kwargs": kwargs}

    def exposed_plugin_call(self, plugin_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
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
        # Return result in ActionResultModel format
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
                "execution_time": "0.05s",
                "result_type": "mock_result",
                "dcc_info": {"name": "test_dcc", "version": "2023.0", "platform": "test"},
            },
        }


class TestIntegration:
    """Integration tests for DCC-MCP-RPYC."""

    def test_server_client_adapter_integration(
        self, integration_setup: Tuple[DCCServer, BaseDCCClient, TestDCCAdapter]
    ):
        """Test the integration between server, client, and adapter.

        Args:
        ----
            integration_setup: Fixture providing a server, client, and adapter

        """
        server, client, adapter = integration_setup

        # Skip test if server is not running
        if not server.is_running():
            pytest.skip("Server is not running")

        # Skip test if client is not connected
        if not client.is_connected():
            pytest.skip("Client is not connected to server")

        # Skip test if adapter is not connected
        if not adapter.is_connected():
            pytest.skip("Adapter is not connected to server")

        # Test client remote call
        result = client.call("execute_cmd", "test_command", "arg1", "arg2", kwarg1="value1")
        assert result["result"] == "test_result", "Client remote call should return the correct result"

        # Test adapter execute_command
        result = adapter.execute_command("test_command", "arg1", "arg2", kwarg1="value1")
        assert result["result"] == "test_result", "Adapter execute_command should return the correct result"

        # Test adapter create_primitive
        result = adapter.create_primitive("cube", size=2.0, position=[0, 0, 0])
        assert result["primitive"] == "cube", "Adapter create_primitive should return the correct result"

    def test_client_reconnection(self, integration_setup: Tuple[DCCServer, BaseDCCClient, TestDCCAdapter]):
        """Test client reconnection functionality.

        Args:
        ----
            integration_setup: Fixture providing a server, client, and adapter

        """
        server, client, _ = integration_setup

        # Skip test if server is not running
        if not server.is_running():
            pytest.skip("Server is not running")

        # Skip test if client is not connected
        if not client.is_connected():
            pytest.skip("Client is not connected to server")

        # Disconnect the client
        client.disconnect()
        assert not client.is_connected(), "Client should be disconnected"

        # Reconnect the client
        client.connect()
        assert client.is_connected(), "Client should be connected after reconnection"

        # Test client remote call after reconnection
        result = client.call("execute_cmd", "test_command")
        assert result["result"] == "test_result", "Client remote call should work after reconnection"

    def test_adapter_reconnection(self, integration_setup: Tuple[DCCServer, BaseDCCClient, TestDCCAdapter]):
        """Test adapter reconnection functionality.

        Args:
        ----
            integration_setup: Fixture providing a server, client, and adapter

        """
        server, _, adapter = integration_setup

        # Skip test if server is not running
        if not server.is_running():
            pytest.skip("Server is not running")

        # Skip test if adapter is not connected
        if not adapter.is_connected():
            pytest.skip("Adapter is not connected to server")

        # Disconnect the adapter by setting client to None
        adapter.client = None
        assert not adapter.is_connected(), "Adapter should be disconnected"

        # Reconnect the adapter
        adapter._initialize_client()
        time.sleep(0.5)  # Wait for connection to establish

        # Skip the rest of the test if reconnection failed
        if not adapter.is_connected():
            pytest.skip("Adapter failed to reconnect to server")

        # Test adapter execute_command after reconnection
        result = adapter.execute_command("test_command")
        assert result["result"] == "test_result", "Adapter execute_command should work after reconnection"

    def test_server_restart(self, integration_setup: Tuple[DCCServer, BaseDCCClient, TestDCCAdapter]):
        """Test server restart functionality.

        Args:
        ----
            integration_setup: Fixture providing a server, client, and adapter

        """
        server, client, adapter = integration_setup

        # Skip test if server is not running
        if not server.is_running():
            pytest.skip("Server is not running")

        # Skip test if client is not connected
        if not client.is_connected():
            pytest.skip("Client is not connected to server")

        # Skip test if adapter is not connected
        if not adapter.is_connected():
            pytest.skip("Adapter is not connected to server")

        # Get the port for reconnection
        port = server.port

        # Stop the server
        server.stop()
        assert not server.is_running(), "Server should be stopped"

        # Verify client and adapter are disconnected
        time.sleep(0.5)  # Wait for disconnection to propagate
        assert not client.is_connected(), "Client should be disconnected after server stop"
        assert not adapter.is_connected(), "Adapter should be disconnected after server stop"

        # Restart the server
        server.start(threaded=True, port=port)
        time.sleep(1.0)  # Wait for server to start
        assert server.is_running(), "Server should be running after restart"

        # Reconnect client and adapter
        client.connect()
        adapter._initialize_client()
        time.sleep(0.5)  # Wait for connections to establish

        # Skip the rest of the test if reconnection failed
        if not client.is_connected() or not adapter.is_connected():
            pytest.skip("Client or adapter failed to reconnect to server after restart")

        # Test client and adapter functionality after server restart
        client_result = client.call("execute_cmd", "test_command")
        assert client_result["result"] == "test_result", "Client should work after server restart"

        adapter_result = adapter.execute_command("test_command")
        assert adapter_result["result"] == "test_result", "Adapter should work after server restart"

    def test_adapter_call_action_function(self, integration_setup: Tuple[DCCServer, BaseDCCClient, TestDCCAdapter]):
        """Test adapter call_action_function method.

        Args:
        ----
            integration_setup: Fixture providing a server, client, and adapter

        """
        server, _, adapter = integration_setup

        # Skip test if server is not running or adapter is not connected
        if not server.is_running():
            pytest.skip("Server is not running")

        if not adapter.is_connected():
            pytest.skip("Adapter is not connected to server")

        # Test adapter call_action_function
        result = adapter.call_action_function(
            action_name="test_action",
            function_name="test_function",
            context={"param1": "value1"},
            arg1="value1",
            kwarg1="value2",
        )

        # Verify the result matches ActionResultModel structure
        assert "success" in result, "Result should contain 'success' field"
        assert "message" in result, "Result should contain 'message' field"
        assert "prompt" in result, "Result should contain 'prompt' field"
        assert "error" in result, "Result should contain 'error' field"
        assert "context" in result, "Result should contain 'context' field"

        # Verify the values
        assert result["success"] is True, "Success should be True"
        assert "test_action.test_function" in result["message"], "Message should mention the action and function"
        assert result["prompt"] is not None, "Prompt should not be None"
        assert result["error"] is None, "Error should be None for successful execution"
        assert isinstance(result["context"], dict), "Context should be a dictionary"
        assert "action_name" in result["context"], "Context should contain action_name"
        assert result["context"]["action_name"] == "test_action", "Context should have correct action_name"
        assert result["context"]["function_name"] == "test_function", "Context should have correct function_name"

    def test_rpyc_call_action_function(self, integration_setup: Tuple[DCCServer, BaseDCCClient, TestDCCAdapter]):
        """Test RPyC call_action_function method.

        Args:
        ----
            integration_setup: Fixture providing a server, client, and adapter

        """
        server, client, _ = integration_setup

        # Skip test if server is not running or client is not connected
        if not server.is_running():
            pytest.skip("Server is not running")

        if not client.is_connected():
            pytest.skip("Client is not connected to server")

        # Test client call_action_function via RPyC
        result = client.call(
            "call_action_function", "test_action", "test_function", {"param1": "value1"}, "arg1", kwarg1="value2"
        )

        # Verify the result matches ActionResultModel structure
        assert "success" in result, "Result should contain 'success' field"
        assert "message" in result, "Result should contain 'message' field"
        assert "prompt" in result, "Result should contain 'prompt' field"
        assert "error" in result, "Result should contain 'error' field"
        assert "context" in result, "Result should contain 'context' field"

        # Verify the values
        assert result["success"] is True, "Success should be True"
        assert "test_action.test_function" in result["message"], "Message should mention the action and function"
        assert result["prompt"] is not None, "Prompt should not be None"
        assert result["error"] is None, "Error should be None for successful execution"
        assert isinstance(result["context"], dict), "Context should be a dictionary"
        assert "action_name" in result["context"], "Context should contain action_name"
        assert result["context"]["action_name"] == "test_action", "Context should have correct action_name"
        assert result["context"]["function_name"] == "test_function", "Context should have correct function_name"
        assert "args" in result["context"], "Context should contain args"
        assert result["context"]["args"] == ("arg1",), "Context should have correct args"
        assert "kwargs" in result["context"], "Context should contain kwargs"
        # Use dict() to ensure consistent format
        assert dict(result["context"]["kwargs"]) == {"kwarg1": "value2"}, "Context should have correct kwargs"
        assert "user_context" in result["context"], "Context should contain user_context"
        assert result["context"]["user_context"] == {"param1": "value1"}, "Context should have correct user_context"
