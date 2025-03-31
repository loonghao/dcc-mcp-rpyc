"""Pytest configuration for DCC-MCP-RPYC tests.

This module provides fixtures and configuration for pytest tests.
"""

# Import built-in modules
import os
import sys
import tempfile
import time

# Import third-party modules
# Import dcc_mcp_core modules
import pytest
from rpyc.utils.server import ThreadedServer

# Import local modules
# Import dcc_mcp_rpyc modules
from dcc_mcp_rpyc.server.base import BaseRPyCService
from dcc_mcp_rpyc.server.dcc import DCCServer
from dcc_mcp_rpyc.testing.mock_services import MockDCCService
from dcc_mcp_rpyc.testing.mock_services import start_mock_dcc_service
from dcc_mcp_rpyc.testing.mock_services import stop_mock_dcc_service
from dcc_mcp_rpyc.utils.discovery import cleanup_stale_services
from dcc_mcp_rpyc.utils.discovery import register_service
from dcc_mcp_rpyc.utils.discovery import unregister_service


@pytest.fixture
def temp_registry_path():
    """Provide a temporary registry file path."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name

    yield temp_path

    # Clean up the temporary file
    try:
        os.unlink(temp_path)
    except OSError:
        pass


@pytest.fixture
def rpyc_server():
    """Create a RPYC server for testing.

    Yields
    ------
        Tuple of (server, port)

    """
    # Create a server
    server = ThreadedServer(
        BaseRPyCService,
        port=0,  # Use a random port
        protocol_config={
            "allow_public_attrs": True,
            "allow_pickle": True,
            "sync_request_timeout": 30,
        },
    )

    # Start the server in a separate thread
    server_thread = server.start()

    # Wait for the server to start
    time.sleep(0.1)

    # Get the port
    port = server.port

    # Yield the server and port
    yield server, port

    # Close the server
    server.close()

    # Wait for the server thread to finish
    server_thread.join(timeout=1)


@pytest.fixture
def dcc_rpyc_server():
    """Create a DCC RPYC server for testing.

    Yields
    ------
        Tuple of (server, port)

    """
    server, port = start_mock_dcc_service()
    yield server, port
    stop_mock_dcc_service(server)


@pytest.fixture
def dcc_server(temp_registry_path: str):
    """Create a DCC server for testing.

    Args:
    ----
        temp_registry_path: Fixture providing a temporary registry file path

    Yields:
    ------
        Tuple of (server, port)

    """
    # Create a server
    server = DCCServer(
        service=MockDCCService,
        host="localhost",
        port=0,  # Use a random port
        registry_path=temp_registry_path,
        service_name="MockDCC",
        service_info={
            "name": "MockDCC",
            "version": "1.0.0",
            "platform": sys.platform,
        },
    )

    # Start the server
    server.start()

    # Wait for the server to start
    time.sleep(0.1)

    # Get the port
    port = server.port

    # Register the service
    register_service(
        name="MockDCC",
        host="localhost",
        port=port,
        registry_path=temp_registry_path,
        service_info={
            "name": "MockDCC",
            "version": "1.0.0",
            "platform": sys.platform,
        },
    )

    # Yield the server and port
    try:
        yield server, port
    finally:
        server.stop()
        unregister_service("MockDCC", "localhost", port)
        cleanup_stale_services()
        try:
            os.remove(temp_registry_path)
        except (FileNotFoundError, PermissionError):
            pass
        time.sleep(0.1)


@pytest.fixture
def dcc_service():
    """Create a DCC service for testing.

    Returns
    -------
        MockDCCService instance

    """
    return MockDCCService()
