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

    def _create_client(self) -> BaseDCCClient:
        """Create a client for the DCC application.

        Returns
        -------
            BaseDCCClient instance

        """
        return BaseDCCClient(dcc_name=self.dcc_name, host=self.host, port=self.port, auto_connect=True)

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

    def is_connected(self) -> bool:
        """Check if the client is connected to the DCC application.

        Returns
        -------
            True if connected, False otherwise

        """
        if hasattr(self, "dcc_client") and self.dcc_client is not None:
            return self.dcc_client.is_connected()
        return False


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
        host="localhost",
        port=0,  # Let OS choose a port
    )

    # Start the server
    port = server.start(threaded=True)

    # Wait for the server to start
    time.sleep(0.5)

    # Create a client
    client = BaseDCCClient(dcc_name="test_dcc", host="localhost", port=port, auto_connect=True)

    # Create an adapter
    adapter = TestDCCAdapter(host="localhost", port=port)

    yield server, client, adapter

    # Clean up
    try:
        # First disconnect the client
        if client.is_connected():
            client.disconnect()

        # Then stop the server
        if server:
            server.stop()
    except Exception as e:
        print(f"Error during integration test cleanup: {e}")


class TestDCCService(DCCRPyCService):
    """Test DCC RPYC service for integration testing."""

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        return {"name": "test_scene", "path": "/path/to/test_scene", "modified": False, "objects": 0}

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

        # Verify the server is running
        assert server.is_running(), "Server should be running"

        # Verify the client is connected
        assert client.is_connected(), "Client should be connected"

        # Verify the adapter is connected
        assert adapter.is_connected(), "Adapter should be connected"

        # Test client remote call
        result = client.call("execute_cmd", "test_command", "arg1", "arg2", kwarg1="value1")
        assert result["result"] == "test_result", "Client remote call should return the correct result"

        # Test adapter execute_command
        result = adapter.execute_command("test_command", "arg1", "arg2", kwarg1="value1")
        assert result["result"] == "test_result", "Adapter execute_command should return the correct result"

        # Test adapter create_primitive
        result = adapter.create_primitive("cube", size=2.0, position=[0, 0, 0])
        assert result["primitive"] == "cube", "Adapter create_primitive should return the correct result"

        # Test adapter get_scene_info
        result = adapter.get_scene_info()
        assert result["name"] == "test_scene", "Adapter get_scene_info should return the correct result"

        # Test adapter call_plugin
        result = adapter.call_plugin("test_plugin", {"param1": "value1"})
        assert result["plugin"] == "test_plugin", "Adapter call_plugin should return the correct result"

    def test_client_reconnection(self, integration_setup: Tuple[DCCServer, BaseDCCClient, TestDCCAdapter]):
        """Test client reconnection.

        Args:
        ----
            integration_setup: Fixture providing a server, client, and adapter

        """
        server, client, _ = integration_setup

        # Verify the client is connected
        assert client.is_connected(), "Client should be connected"

        # Disconnect the client
        client.disconnect()
        assert not client.is_connected(), "Client should be disconnected"

        # Reconnect the client
        client.connect()
        assert client.is_connected(), "Client should be reconnected"

        # Test remote call after reconnection
        result = client.call("execute_cmd", "test_command")
        assert (
            result["result"] == "test_result"
        ), "Client remote call should return the correct result after reconnection"

    def test_adapter_reconnection(self, integration_setup: Tuple[DCCServer, BaseDCCClient, TestDCCAdapter]):
        """Test adapter reconnection.

        Args:
        ----
            integration_setup: Fixture providing a server, client, and adapter

        """
        server, _, adapter = integration_setup

        # Verify the adapter is connected
        assert adapter.is_connected(), "Adapter should be connected"

        # Disconnect the adapter's client
        adapter.dcc_client.disconnect()
        assert not adapter.is_connected(), "Adapter should be disconnected"

        # Reconnect the adapter's client
        adapter.dcc_client.connect()
        assert adapter.is_connected(), "Adapter should be reconnected"

        # Test execute_command after reconnection
        result = adapter.execute_command("test_command")
        assert (
            result["result"] == "test_result"
        ), "Adapter execute_command should return the correct result after reconnection"

    def test_server_restart(self, temp_registry_path: str):
        """Test server restart.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        # Create a server
        server = DCCServer(
            dcc_name="test_dcc",
            service_class=TestDCCService,
            host="127.0.0.1",  # Use 127.0.0.1 instead of localhost
            port=0,  # Let OS choose a port
        )

        # Start the server
        port = server.start(threaded=True)
        assert server.is_running(), "Server should be running"

        # Create a client
        client = BaseDCCClient(
            dcc_name="test_dcc",
            host="127.0.0.1",  # Use 127.0.0.1 instead of localhost
            port=port,
            auto_connect=True,
        )
        assert client.is_connected(), "Client should be connected"

        # Stop the server
        server.stop()
        assert not server.is_running(), "Server should not be running"

        # Verify the client is disconnected
        time.sleep(0.5)  # Give the client time to detect the disconnection
        assert not client.is_connected(), "Client should be disconnected"

        # Restart the server
        port = server.start(threaded=True)
        assert server.is_running(), "Server should be running again"

        # Reconnect the client
        client.port = port  # Update the port in case it changed
        client.connect()
        assert client.is_connected(), "Client should be reconnected"

        # Test remote call after server restart
        result = client.call("execute_cmd", "test_command")
        assert (
            result["result"] == "test_result"
        ), "Client remote call should return the correct result after server restart"

        # Clean up
        client.disconnect()
        server.cleanup()
