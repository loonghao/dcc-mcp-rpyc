"""Pytest configuration for DCC-MCP-RPYC tests.

This module provides fixtures and configuration for pytest tests.
"""

# Import built-in modules
import os
import tempfile
import threading
import time

# Import third-party modules
# Import dcc_mcp_core modules
import pytest
from rpyc.utils.server import ThreadedServer

# Import local modules
from dcc_mcp_rpyc.discovery import FileDiscoveryStrategy
from dcc_mcp_rpyc.discovery import ServiceInfo
from dcc_mcp_rpyc.discovery import ServiceRegistry

# Import dcc_mcp_rpyc modules
from dcc_mcp_rpyc.server.base import BaseRPyCService
from dcc_mcp_rpyc.server.dcc import DCCServer
from dcc_mcp_rpyc.testing.mock_services import MockDCCService


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
def service_registry(temp_registry_path):
    """Provide a service registry with file discovery strategy."""
    registry = ServiceRegistry()
    strategy = FileDiscoveryStrategy(registry_path=temp_registry_path)
    registry.register_strategy("file", strategy)
    yield registry
    # Reset the registry singleton for the next test
    ServiceRegistry._reset_instance()


@pytest.fixture
def rpyc_server():
    """Create a RPYC server for testing.

    Yields
    ------
        Tuple of (server, port)

    """
    # Create a server with a random port
    service = BaseRPyCService
    server = ThreadedServer(service, port=0, protocol_config={"allow_all_attrs": True})

    # Start the server in a separate thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    # Wait for the server to start
    time.sleep(0.1)

    # Get the port that was assigned
    port = server.port

    yield server, port

    # Stop the server
    server.close()
    server_thread.join(timeout=1.0)


@pytest.fixture
def dcc_rpyc_server():
    """Create a DCC RPYC server for testing.

    Yields
    ------
        Tuple of (server, port)

    """
    # Create a server with a random port
    service = MockDCCService
    server = ThreadedServer(service, port=0, protocol_config={"allow_all_attrs": True})

    # Start the server in a separate thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    # Wait for the server to start
    time.sleep(0.1)

    # Get the port that was assigned
    port = server.port

    yield server, port

    # Stop the server
    server.close()
    server_thread.join(timeout=1.0)


@pytest.fixture
def dcc_server(temp_registry_path, service_registry):
    """Create a DCC server for testing.

    Args:
    ----
        temp_registry_path: Fixture providing a temporary registry file path
        service_registry: Fixture providing a service registry

    Yields:
    ------
        Tuple of (server, port)

    """
    # Create a server with a random port
    service = DCCServer
    server = ThreadedServer(service, port=0, protocol_config={"allow_all_attrs": True})

    # Start the server in a separate thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    # Wait for the server to start
    time.sleep(0.1)

    # Get the port that was assigned
    port = server.port

    # Register the service
    service_info = ServiceInfo(
        name="test_dcc_server", host="localhost", port=port, dcc_type="test_dcc", metadata={"version": "1.0.0"}
    )
    service_registry.register_service("file", service_info)

    yield server, port

    # Unregister the service
    service_registry.unregister_service("file", service_info)

    # Stop the server
    server.close()
    server_thread.join(timeout=1.0)


@pytest.fixture
def dcc_service():
    """Create a DCC service for testing.

    Returns
    -------
        MockDCCService instance

    """
    return MockDCCService()
