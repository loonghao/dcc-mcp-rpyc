"""Test utilities for DCC-MCP-RPYC tests.

This module provides common utilities and fixtures for testing the DCC-MCP-RPYC package.
"""

# Import built-in modules
from unittest import mock

# Import local modules
from dcc_mcp_rpyc.server import BaseRPyCService
from dcc_mcp_rpyc.server import DCCServer


def create_service_class():
    """Create a service class that can be used for testing.

    This function returns the BaseRPyCService class which is a valid service class
    for DCCServer initialization.

    Returns
    -------
        A valid service class

    """
    # Return the actual BaseRPyCService class, not an instance
    return BaseRPyCService


def create_dcc_server(dcc_name="test_dcc", host="localhost", port=0):
    """Create a DCCServer instance for testing.

    Args:
    ----
        dcc_name: Name of the DCC (default: "test_dcc")
        host: Host to bind the server to (default: "localhost")
        port: Port to bind the server to (default: 0)

    Returns:
    -------
        A DCCServer instance with a valid service_class

    """
    server = DCCServer(
        dcc_name=dcc_name,
        service_class=BaseRPyCService,  # Use the actual class, not an instance
        host=host,
        port=port,
    )
    return server


def setup_server_for_start(server, port=12345):
    """Set up a server for testing the start method.

    This function sets up the necessary mocks for testing the start method of DCCServer.

    Args:
    ----
        server: DCCServer instance to set up
        port: Port that the server should use (default: 12345)

    Returns:
    -------
        Tuple of (server, mock_server) where mock_server is the mocked ThreadedServer

    """
    # Create a mock ThreadedServer
    mock_server = mock.MagicMock()
    mock_server.port = port

    # Mock the _create_server method to return our mock server
    server._create_server = mock.MagicMock(return_value=mock_server)

    # Mock register_dcc_service to return a mock registry file
    with mock.patch("dcc_mcp_rpyc.server.register_dcc_service", return_value="/tmp/test_registry.json"):
        pass

    return server, mock_server
