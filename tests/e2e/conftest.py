"""Shared fixtures for E2E tests.

Provides lightweight server/client fixtures that simulate Blender, Maya, and
Houdini IPC endpoints using MockDCCService — no real DCC install required.
"""

# Import built-in modules
import threading
import time

# Import third-party modules
import pytest
from rpyc.utils.server import ThreadedServer

# Import local modules
from dcc_mcp_ipc.testing.mock_services import MockDCCService


def _start_mock_server(dcc_name: str) -> tuple:
    """Start a MockDCCService on a random port and return (server, port)."""
    # Pass the service CLASS (not an instance) so RPyC creates one per connection
    # and properly maps exposed_* methods via the default RPyC protocol.
    server = ThreadedServer(
        MockDCCService,
        port=0,
        protocol_config={"allow_public_attrs": True},
        logger=None,
    )
    thread = threading.Thread(target=server.start, daemon=True, name=f"e2e-{dcc_name}")
    thread.start()
    # Give the server a moment to bind
    time.sleep(0.15)
    return server, server.port


@pytest.fixture(scope="module")
def blender_server():
    """Module-scoped mock Blender IPC server on a random port."""
    server, port = _start_mock_server("blender")
    yield server, port
    server.close()


@pytest.fixture(scope="module")
def maya_server():
    """Module-scoped mock Maya IPC server on a random port."""
    server, port = _start_mock_server("maya")
    yield server, port
    server.close()


@pytest.fixture(scope="module")
def houdini_server():
    """Module-scoped mock Houdini IPC server on a random port."""
    server, port = _start_mock_server("houdini")
    yield server, port
    server.close()
