"""Integration tests for DCC-MCP-RPYC with DCC applications.

This module contains integration tests for the DCC-MCP-RPYC package with DCC applications.
These tests require a running DCC application with the DCC-MCP-RPYC server installed.
"""

# Import built-in modules
import sys
import threading
import time

# Import third-party modules
import pytest
import rpyc
from rpyc.utils.server import ThreadedServer

# Import local modules
from dcc_mcp_rpyc.client import BaseDCCClient
from dcc_mcp_rpyc.discovery import FileDiscoveryStrategy
from dcc_mcp_rpyc.discovery import ServiceInfo
from dcc_mcp_rpyc.discovery import ServiceRegistry


# Mock DCC service class
class MockDCCService(rpyc.Service):
    """Mock DCC service class, used for testing.

    This class mocks the basic functionality of a DCC application, such as getting DCC info, scene info, etc.
    """

    def __init__(self, dcc_name="mock_dcc"):
        super().__init__()
        self.dcc_name = dcc_name

    def exposed_get_dcc_info(self, conn=None):
        """Get DCC info."""
        return {
            "name": self.dcc_name,
            "version": "1.0.0",
            "platform": sys.platform,
            "python_version": sys.version,
        }

    def exposed_get_scene_info(self, conn=None):
        """Get scene info."""
        return {
            "file_path": "/path/to/mock/scene.ext",
            "scene_name": "mock_scene",
            "objects": ["object1", "object2", "object3"],
        }

    def exposed_execute_command(self, command, args=None, conn=None):
        """Execute a command."""
        return {
            "success": True,
            "result": f"Executed command: {command} with args: {args}",
        }

    def exposed_get_selection(self, conn=None):
        """Get selection."""
        return ["object1", "object2"]

    def exposed_set_selection(self, objects, conn=None):
        """Set selection."""
        return {
            "success": True,
            "result": f"Set selection to: {objects}",
        }

    def exposed_get_object_attributes(self, object_name, conn=None):
        """Get object attributes."""
        return {
            "name": object_name,
            "type": "mesh",
            "position": [0, 0, 0],
            "rotation": [0, 0, 0],
            "scale": [1, 1, 1],
        }


_mock_servers = {}


def start_mock_dcc_service(dcc_name, host="localhost", port=0):
    """Start a mock DCC service.

    Args:
        dcc_name: DCC name
        host: Host name
        port: Port number, 0 means auto-allocate

    Returns:
        (host, port) tuple

    """
    global _mock_servers

    # Check if the service is already running
    if dcc_name in _mock_servers:
        server, host, port = _mock_servers[dcc_name]
        return host, port

    # Create a service instance with the specified DCC name
    service = MockDCCService(dcc_name=dcc_name)

    # Create a server
    server = ThreadedServer(
        service,
        hostname=host,
        port=port,
        protocol_config={"allow_all_attrs": True},
    )

    # Start the server in a separate thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    # Wait for the server to start
    time.sleep(0.1)

    # Get the port that was assigned
    port = server.port

    # Store the server instance
    _mock_servers[dcc_name] = (server, host, port)

    # Register the service
    registry = ServiceRegistry()
    strategy = registry.get_strategy("file")
    if not strategy:
        strategy = FileDiscoveryStrategy()
        registry.register_strategy("file", strategy)

    service_info = ServiceInfo(name=dcc_name, host=host, port=port, dcc_type=dcc_name, metadata={"version": "1.0.0"})
    registry.register_service("file", service_info)

    return host, port


def stop_mock_dcc_service(dcc_name):
    """Close mock DCC service.

    Args:
        dcc_name: DCC name

    """
    global _mock_servers

    if dcc_name in _mock_servers:
        server, host, port = _mock_servers[dcc_name]
        server.close()

        # Unregister the service
        registry = ServiceRegistry()
        strategy = registry.get_strategy("file")
        if strategy:
            service_info = ServiceInfo(
                name=dcc_name, host=host, port=port, dcc_type=dcc_name, metadata={"version": "1.0.0"}
            )
            registry.unregister_service("file", service_info)

        del _mock_servers[dcc_name]


@pytest.fixture
def mock_dcc_services():
    """Start mock DCC services."""
    # Start mock services for common DCCs
    start_mock_dcc_service("maya")
    start_mock_dcc_service("houdini")
    start_mock_dcc_service("nuke")

    yield

    # Stop all mock services
    for dcc_name in list(_mock_servers.keys()):
        stop_mock_dcc_service(dcc_name)


# Skip tests if no DCC services are available
pytestmark = pytest.mark.skipif(
    not ServiceRegistry().list_services(),  # Check if any DCC services are available
    reason="No DCC services available for testing",
)


def get_test_dcc_client(dcc_name: str):
    """Get a DCC client for testing if available.

    Args:
    ----
        dcc_name: Name of the DCC application to connect to

    Returns:
    -------
        DCC client if available, None otherwise

    """
    # Try to find the service
    registry = ServiceRegistry()
    service = registry.get_service(dcc_name)

    if not service:
        # Try to discover services
        strategy = registry.get_strategy("file")
        if strategy:
            registry.discover_services("file", dcc_name)
            service = registry.get_service(dcc_name)

    if not service:
        # Start a mock service
        host, port = start_mock_dcc_service(dcc_name)

        # Create a client
        client = BaseDCCClient(host=host, port=port)
        return client

    # Create a client
    client = BaseDCCClient(host=service.host, port=service.port)
    return client


def test_maya_integration():
    """Test integration with Maya."""
    # Get a Maya client
    client = get_test_dcc_client("maya")
    assert client is not None

    # Test connection
    assert client.is_connected()

    # Test get_dcc_info
    dcc_info = client.get_dcc_info()
    assert dcc_info is not None
    assert dcc_info["name"] == "maya"

    # Test get_scene_info
    scene_info = client.get_scene_info()
    assert scene_info is not None
    assert "file_path" in scene_info
    assert "scene_name" in scene_info
    assert "objects" in scene_info

    # Test execute_command
    result = client.execute_command("polyCube", {"width": 2.0})
    assert result is not None
    assert result["success"] is True


def test_houdini_integration():
    """Test integration with Houdini."""
    # Get a Houdini client
    client = get_test_dcc_client("houdini")
    assert client is not None

    # Test connection
    assert client.is_connected()

    # Test get_dcc_info
    dcc_info = client.get_dcc_info()
    assert dcc_info is not None
    assert dcc_info["name"] == "houdini"

    # Test get_scene_info
    scene_info = client.get_scene_info()
    assert scene_info is not None
    assert "file_path" in scene_info
    assert "scene_name" in scene_info
    assert "objects" in scene_info


def test_nuke_integration():
    """Test integration with Nuke."""
    # Get a Nuke client
    client = get_test_dcc_client("nuke")
    assert client is not None

    # Test connection
    assert client.is_connected()

    # Test get_dcc_info
    dcc_info = client.get_dcc_info()
    assert dcc_info is not None
    assert dcc_info["name"] == "nuke"

    # Test get_scene_info
    scene_info = client.get_scene_info()
    assert scene_info is not None
    assert "file_path" in scene_info
    assert "scene_name" in scene_info
    assert "objects" in scene_info
