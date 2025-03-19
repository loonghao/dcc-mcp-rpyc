"""Tests for the server module.

This module contains tests for the DCCServer and DCCRPyCService classes.
"""

# Import built-in modules
from typing import Tuple

# Import third-party modules
import pytest
import rpyc

# Import local modules
from dcc_mcp_rpyc.server import BaseRPyCService
from dcc_mcp_rpyc.server import DCCServer


class TestDCCRPyCService:
    """Tests for the DCCRPyCService class."""

    def test_with_scene_info_decorator(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test the with_scene_info decorator.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        _, port = dcc_rpyc_server

        # Connect to the server
        conn = rpyc.connect("localhost", port)

        # Test the echo method (which doesn't use the decorator)
        result = conn.root.echo("test")
        assert result == "test"

        # Test a method with the decorator
        # We need to create a method with the decorator for testing
        # This is done in the TestDCCService class in conftest.py

        # Get the add method result
        result = conn.root.add(1, 2)
        assert result == 3

        # Close the connection
        conn.close()


class TestDCCServer:
    """Tests for the DCCServer class."""

    def test_server_start_stop(self, temp_registry_path: str):
        """Test starting and stopping the server.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        # Create a server
        server = DCCServer(dcc_name="test_dcc", service_class=BaseRPyCService, host="127.0.0.1", port=0)

        # Start the server
        port = server.start(threaded=True)
        assert port, "Server should start and return a port"
        assert server.is_running(), "Server should be running"

        # Try to connect to the server
        conn = rpyc.connect("127.0.0.1", port)
        # RPyC ping() returns None, but the connection should be established
        conn.root.get_service_name()  # This will raise an exception if not connected
        conn.close()

        # Stop the server
        assert server.stop(), "Server should stop successfully"
        assert not server.is_running(), "Server should not be running"

        # Try to connect to the server (should fail)
        with pytest.raises(ConnectionRefusedError):
            rpyc.connect("127.0.0.1", port)

    def test_server_cleanup(self, dcc_server: Tuple[DCCServer, int]):
        """Test server cleanup.

        Args:
        ----
            dcc_server: Fixture providing a DCCServer instance

        """
        server, port = dcc_server

        # Verify the server is running
        assert server.is_running(), "Server should be running"

        # Try to connect to the server
        conn = rpyc.connect("127.0.0.1", port)
        conn.root.get_service_name()  # This will raise an exception if not connected
        conn.close()

        # Clean up the server
        assert server.cleanup(), "Server cleanup should succeed"
        assert not server.is_running(), "Server should not be running"

        # Try to connect to the server (should fail)
        with pytest.raises(ConnectionRefusedError):
            rpyc.connect("127.0.0.1", port)

    def test_create_server_function(self, temp_registry_path: str):
        """Test the create_dcc_server function.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        # Import local modules
        from dcc_mcp_rpyc.server import create_dcc_server

        # Create a server
        server = create_dcc_server(
            dcc_name="test_dcc",
            service_class=BaseRPyCService,
            host="localhost",
            port=0,  # Let OS choose a port
        )

        # Verify the server was created
        assert isinstance(server, DCCServer), "create_dcc_server should return a DCCServer instance"
        assert server.dcc_name == "test_dcc", "Server should have the correct DCC name"
        assert server.service_class == BaseRPyCService, "Server should have the correct service class"

        # Start the server
        port = server.start(threaded=True)
        assert port > 0, "Server should start with a valid port"

        # Clean up
        server.cleanup()
