"""Pytest configuration for DCC-MCP-RPYC tests.

This module provides fixtures and configuration for pytest tests.
"""

# Import built-in modules
import os
import tempfile
import time
from typing import Any
from typing import Dict
from typing import Generator
from typing import Tuple

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel
import pytest
import rpyc

# Import local modules
import dcc_mcp_rpyc.discovery as discovery
from dcc_mcp_rpyc.server import BaseRPyCService
from dcc_mcp_rpyc.server import DCCServer


@pytest.fixture
def temp_registry_path():
    """Provide a temporary registry file path."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name

    # Reset the global registry cache
    discovery._registry_loaded = False
    discovery._service_registry = {}

    # Return the path
    yield temp_path

    # Clean up
    if os.path.exists(temp_path):
        os.remove(temp_path)

    # Reset the global registry cache again
    discovery._registry_loaded = False
    discovery._service_registry = {}


class TestRPyCService(BaseRPyCService):
    """Test RPYC service for testing."""

    def exposed_echo(self, arg):
        """Echo the argument back."""
        return arg

    def exposed_add(self, a, b):
        """Add two numbers."""
        return a + b


@pytest.fixture
def rpyc_server() -> Generator[Tuple[DCCServer, int], None, None]:
    """Create a RPYC server for testing.

    Yields
    ------
        Tuple of (server, port)

    """
    # Create a server
    server = DCCServer(
        dcc_name="test_rpyc",
        service_class=TestRPyCService,
        host="127.0.0.1",  # Use explicit IPv4 address instead of localhost
        port=0,  # Let OS choose a port
    )

    # Start the server in a thread
    server._start_in_thread()

    # Get the port
    port = server.port

    # Wait for the server to start
    time.sleep(0.5)  # Shorter wait time

    # Verify server is accessible
    max_retries = 5
    retry_delay = 0.5  # Shorter delay between retries
    for i in range(max_retries):
        try:
            conn = rpyc.connect("127.0.0.1", port)  # Use explicit IPv4 address
            conn.ping()  # Ensure connection is working
            conn.close()
            break
        except (ConnectionRefusedError, EOFError):
            if i == max_retries - 1:
                raise
            print(f"Retrying connection to server at 127.0.0.1:{port}, attempt {i+1}/{max_retries}")
            time.sleep(retry_delay)

    try:
        yield server, port
    finally:
        # Clean up
        server.stop()


class TestDCCService(BaseRPyCService):
    """Test DCC RPYC service for testing."""

    def exposed_get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        return ActionResultModel(
            success=True,
            message="Successfully retrieved scene information",
            context={"name": "test_scene", "path": "/path/to/test_scene", "modified": False, "objects": 0},
        ).model_dump()

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
        return ActionResultModel(
            success=True,
            message="Successfully retrieved session information",
            context={
                "application": "test_dcc",
                "version": "1.0.0",
                "user": "test_user",
                "workspace": "/path/to/workspace",
                "scene": {"name": "test_scene", "path": "/path/to/test_scene", "modified": False, "objects": 0},
            },
        ).model_dump()

    def exposed_get_actions(self) -> Dict[str, Any]:
        """Get all available actions for the DCC application.

        Returns
        -------
            Dict with action information

        """
        return ActionResultModel(
            success=True,
            message="Successfully retrieved actions",
            context={
                "actions": [
                    {"name": "create_sphere", "category": "Create", "description": "Create a sphere"},
                    {"name": "create_cube", "category": "Create", "description": "Create a cube"},
                ]
            },
        ).model_dump()

    def exposed_echo(self, arg):
        """Echo the argument back.

        Args:
        ----
            arg: The argument to echo back

        Returns:
        -------
            The same argument

        """
        return arg

    def exposed_add(self, a, b):
        """Add two numbers.

        Args:
        ----
            a: First number
            b: Second number

        Returns:
        -------
            Sum of a and b

        """
        return a + b

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


@pytest.fixture
def dcc_rpyc_server() -> Generator[Tuple[DCCServer, int], None, None]:
    """Create a DCC RPYC server for testing.

    Yields
    ------
        Tuple of (server, port)

    """
    # Create a server
    server = DCCServer(
        dcc_name="test_dcc",
        service_class=TestDCCService,
        host="127.0.0.1",  # Use explicit IPv4 address
        port=0,  # Let OS choose a port
    )

    # Start the server in a thread
    server._start_in_thread()

    # Get the port
    port = server.port

    # Wait for the server to start
    time.sleep(0.5)  # Shorter wait time

    # Verify server is accessible
    max_retries = 5
    retry_delay = 0.5  # Shorter delay between retries
    for i in range(max_retries):
        try:
            conn = rpyc.connect("127.0.0.1", port)  # Use explicit IPv4 address
            conn.ping()  # Ensure connection is working
            conn.close()
            break
        except (ConnectionRefusedError, EOFError):
            if i == max_retries - 1:
                raise
            print(f"Retrying connection to server at 127.0.0.1:{port}, attempt {i+1}/{max_retries}")
            time.sleep(retry_delay)

    try:
        yield server, port
    finally:
        # Clean up
        server.stop()


@pytest.fixture
def dcc_server(temp_registry_path: str) -> Generator[Tuple[DCCServer, int], None, None]:
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
        dcc_name="test_dcc",
        service_class=TestDCCService,
        host="127.0.0.1",  # Use explicit IPv4 address
        port=0,  # Let OS choose a port
    )

    # Start the server in a thread
    server._start_in_thread()

    # Get the port
    port = server.port

    # Register the service
    # Import local modules
    from dcc_mcp_rpyc.discovery import register_service

    register_service("test_dcc", "127.0.0.1", port, registry_path=temp_registry_path)  # Use explicit IPv4 address

    # Wait for the server to start
    time.sleep(0.5)  # Shorter wait time

    # Verify server is accessible
    max_retries = 5
    retry_delay = 0.5  # Shorter delay between retries
    for i in range(max_retries):
        try:
            conn = rpyc.connect("127.0.0.1", port)  # Use explicit IPv4 address
            conn.ping()  # Ensure connection is working
            conn.close()
            break
        except (ConnectionRefusedError, EOFError):
            if i == max_retries - 1:
                raise
            print(f"Retrying connection to server at 127.0.0.1:{port}, attempt {i+1}/{max_retries}")
            time.sleep(retry_delay)

    try:
        yield server, port
    finally:
        # Clean up
        # Import local modules
        from dcc_mcp_rpyc.discovery import unregister_service

        unregister_service("test_dcc", registry_path=temp_registry_path)
        server.stop()
