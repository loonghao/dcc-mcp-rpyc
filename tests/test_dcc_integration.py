"""Integration tests for DCC-MCP-RPYC with DCC applications.

This module contains integration tests for the DCC-MCP-RPYC package with DCC applications.
These tests require a running DCC application with the DCC-MCP-RPYC server installed.
"""

# Import built-in modules
import sys
import threading
import time
from typing import Optional

# Import third-party modules
import pytest
import rpyc
from rpyc.utils.server import ThreadedServer

# Import local modules
from dcc_mcp_rpyc.client import BaseDCCClient
from dcc_mcp_rpyc.utils.discovery import discover_services
from dcc_mcp_rpyc.utils.discovery import get_latest_service
from dcc_mcp_rpyc.utils.discovery import register_service


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

    def exposed_execute_python(self, code, conn=None):
        """Execute Python code."""
        try:
            # Create a safe local namespace
            local_vars = {}
            # Execute code and return result
            exec(code, {}, local_vars)
            # If code has a return value variable, return it
            if "_result" in local_vars:
                return local_vars["_result"]
            # Otherwise return the last variable's value
            elif local_vars:
                return list(local_vars.values())[-1]
            return None
        except Exception as e:
            return str(e)

    def exposed_execute_dcc_command(self, command, conn=None):
        """Execute DCC command."""
        if self.dcc_name == "maya" and "sphere" in command:
            return "test_sphere2"
        elif self.dcc_name == "houdini":
            return "houdini_result"
        elif self.dcc_name == "nuke":
            return "nuke_result"
        return f"Executed command: {command}"


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
    # Create service instance
    service = MockDCCService(dcc_name)
    # Create server
    server = ThreadedServer(
        service=service,
        hostname=host,
        port=port,
        protocol_config={"allow_public_attrs": True},
        logger=None,
    )

    # Get actual port
    if port == 0:
        port = server.port

    # Register service
    register_service(dcc_name, host, port)

    # Start server in new thread
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()

    # Store server instance for later closing
    _mock_servers[dcc_name] = (server, thread)

    # Wait for server to start
    time.sleep(0.5)

    return host, port


# Close mock DCC service
def stop_mock_dcc_service(dcc_name):
    """Close mock DCC service.

    Args:
        dcc_name: DCC name

    """
    if dcc_name in _mock_servers:
        server, thread = _mock_servers[dcc_name]
        server.close()
        del _mock_servers[dcc_name]


# Start mock DCC services
@pytest.fixture(scope="module")
def mock_dcc_services():
    """Start mock DCC services."""
    # Start mock services
    start_mock_dcc_service("maya")
    start_mock_dcc_service("houdini")
    start_mock_dcc_service("nuke")

    # Run tests
    yield

    # Cleanup: close all mock services
    for dcc_name in list(_mock_servers.keys()):
        stop_mock_dcc_service(dcc_name)


# Skip tests if no DCC services are available
pytestmark = pytest.mark.skipif(
    not any(discover_services().values()),  # Check if any DCC services are available
    reason="No DCC services available for integration testing",
)


def get_test_dcc_client(dcc_name: str) -> Optional[BaseDCCClient]:
    """Get a DCC client for testing if available.

    Args:
    ----
        dcc_name: Name of the DCC application to connect to

    Returns:
    -------
        DCC client if available, None otherwise

    """
    # Discover services
    services_by_dcc = discover_services()

    # Get list of services for specified DCC
    dcc_services = services_by_dcc.get(dcc_name.lower(), [])
    if not dcc_services:
        return None

    # Get latest service
    service = get_latest_service(dcc_services)
    if not service:
        return None

    # Create client
    client = BaseDCCClient(dcc_name=dcc_name, host=service.get("host"), port=service.get("port"))

    # Try to connect
    try:
        client.connect()
        return client
    except Exception:
        return None


@pytest.mark.maya
@pytest.mark.usefixtures("mock_dcc_services")
def test_maya_integration():
    """Test integration with Maya."""
    # Get Maya client
    client = get_test_dcc_client("maya")
    if not client:
        pytest.skip("Maya service not available")

    try:
        # Get DCC info
        dcc_info = client.get_dcc_info()
        assert dcc_info["name"] == "maya"
        assert "version" in dcc_info

        # Execute Python code
        result = client.execute_python("_result = ['test_sphere']")
        assert isinstance(result, list)
        assert "test_sphere" in result[0]

        # Execute DCC command
        result = client.execute_dcc_command("sphere -name test_sphere2;")
        assert isinstance(result, str)
        assert "test_sphere2" in result

        # Get scene info
        scene_info = client.get_scene_info()
        assert isinstance(scene_info, dict)
        assert "file_path" in scene_info
    finally:
        # Close client
        client.close()


@pytest.mark.houdini
@pytest.mark.usefixtures("mock_dcc_services")
def test_houdini_integration():
    """Test integration with Houdini."""
    # Get Houdini client
    client = get_test_dcc_client("houdini")
    if not client:
        pytest.skip("Houdini service not available")

    try:
        # Get DCC info
        dcc_info = client.get_dcc_info()
        assert dcc_info["name"] == "houdini"
        assert "version" in dcc_info

        # Execute Python code
        result = client.execute_python("_result = 'test_geo'")
        assert isinstance(result, str)
        assert "test_geo" in result

        # Get scene info
        scene_info = client.get_scene_info()
        assert isinstance(scene_info, dict)
        assert "file_path" in scene_info
    finally:
        # Close client
        client.close()


@pytest.mark.nuke
@pytest.mark.usefixtures("mock_dcc_services")
def test_nuke_integration():
    """Test integration with Nuke."""
    # Get Nuke client
    client = get_test_dcc_client("nuke")
    if not client:
        pytest.skip("Nuke service not available")

    try:
        # Get DCC info
        dcc_info = client.get_dcc_info()
        assert dcc_info["name"] == "nuke"
        assert "version" in dcc_info

        # Execute Python code
        result = client.execute_python("_result = 'Blur'")
        assert isinstance(result, str)
        assert "Blur" in result

        # Get scene info
        scene_info = client.get_scene_info()
        assert isinstance(scene_info, dict)
        assert "file_path" in scene_info
    finally:
        # Close client
        client.close()
