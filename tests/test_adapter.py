"""Tests for the dcc_adapter module.

This module contains tests for the DCCAdapter class.
"""

# Import built-in modules
import logging
import time
from typing import Any
from typing import Dict
from typing import Tuple

# Import third-party modules
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
        # Initialize with default values
        self.host = "127.0.0.1"  # Use explicit IPv4 address instead of localhost
        self.port = None
        self.timeout = 5
        self.dcc_name = "test_dcc"  # Set default DCC name
        self.dcc_client = None

    def is_connected(self) -> bool:
        """Check if the adapter is connected to the DCC application.

        Returns
        -------
            bool: True if connected, False otherwise

        """
        if not self.dcc_client:
            return False

        try:
            # Try to ping the server
            return self.dcc_client.is_connected()
        except Exception as e:
            logging.error(f"Error checking connection: {e}")
            return False

    def _create_client(self) -> BaseDCCClient:
        """Create a client for the DCC application.

        Returns
        -------
            BaseDCCClient instance

        """
        # Create a client with retry logic
        max_retries = 3
        retry_delay = 0.5
        last_error = None

        for attempt in range(max_retries):
            try:
                client = BaseDCCClient(
                    dcc_name=self.dcc_name,
                    host="127.0.0.1" if self.host == "localhost" else self.host,  # Use explicit IPv4 address
                    port=self.port,
                    auto_connect=True,
                    connection_timeout=self.timeout,  # Use the timeout from the adapter
                )

                # Verify connection is working
                if client.is_connected():
                    return client

                # If we got here, connection didn't work
                logging.warning(f"Connection attempt {attempt+1}/{max_retries} failed, retrying...")
                time.sleep(retry_delay)
            except Exception as e:
                last_error = e
                logging.error(f"Error connecting to DCC server: {e}, attempt {attempt+1}/{max_retries}")
                time.sleep(retry_delay)

        # If we get here, all retries failed
        if last_error:
            raise ConnectionError(f"Failed to connect to DCC server after {max_retries} attempts: {last_error}")
        else:
            raise ConnectionError(f"Failed to connect to DCC server after {max_retries} attempts")

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
                return {"command": command, "args": args, "kwargs": kwargs}
            elif command == "error_command":
                raise ValueError("Test error")
            elif command == "echo":
                return args[0]
            else:
                return {"result": f"Unknown command: {command}"}
        except Exception as e:
            return {"error": str(e)}

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

        if primitive_type == "sphere":
            return {"primitive": primitive_type, "params": params}
        else:
            return {"primitive_type": primitive_type, "params": params}

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        return {"scene": "test_scene", "objects": []}

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

    def connect(self):
        """Connect to the DCC application."""
        if not self.port:
            raise ValueError("Port is not set")

        # Create a client
        # Import local modules
        from dcc_mcp_rpyc.client import BaseDCCClient

        self.dcc_client = BaseDCCClient(self.dcc_name)

        # Connect to the server
        try:
            self.dcc_client.connection = rpyc.connect(self.host, self.port)
            self.dcc_client.root = self.dcc_client.connection.root
            self.dcc_client.connected = True
            return True
        except Exception as e:
            logging.error(f"Error connecting to DCC service: {e}")
            self.dcc_client = None
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
            assert adapter.dcc_client is not None, "Adapter should have a client"
            assert adapter.dcc_client.is_connected(), "Adapter client should be connected"
        finally:
            # Clean up
            if adapter and adapter.dcc_client:
                adapter.dcc_client.disconnect()

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

            # Verify the result
            assert result == {
                "command": "test_command",
                "args": ({"arg1": "value1"},),
                "kwargs": {},
            }, "Command should be executed correctly"
        finally:
            # Clean up
            if adapter and adapter.dcc_client:
                adapter.dcc_client.disconnect()

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
            assert result == {"primitive": "sphere", "params": {"radius": 1.0}}, "Primitive should be created correctly"
        finally:
            # Clean up
            if adapter and adapter.dcc_client:
                adapter.dcc_client.disconnect()

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

            # Verify the result
            assert result == {"scene": "test_scene", "objects": []}, "Scene info should be returned correctly"
        finally:
            # Clean up
            if adapter and adapter.dcc_client:
                adapter.dcc_client.disconnect()

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

            # Verify the result
            assert result == {
                "plugin": "test_plugin",
                "context": {"param1": "value1"},
                "status": "success",
            }, "Plugin should be called correctly"
        finally:
            # Clean up
            if adapter and adapter.dcc_client:
                adapter.dcc_client.disconnect()

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
            adapter.dcc_client.disconnect()

            # Check after disconnecting
            assert not adapter.is_connected(), "Adapter should not be connected after disconnecting"
        finally:
            # Clean up
            if adapter and adapter.dcc_client and adapter.dcc_client.is_connected():
                adapter.dcc_client.disconnect()
