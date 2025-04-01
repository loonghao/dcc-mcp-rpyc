"""Server lifecycle management for DCC-MCP-RPYC.

This module provides functions for managing the lifecycle of RPYC servers,
including creation, starting, stopping, and checking the status of servers.
"""

# Import built-in modules
import logging
import threading
from typing import Any
from typing import Dict
from typing import Optional
from typing import Type
from typing import Union

# Import third-party modules
from rpyc.core import service
from rpyc.utils.server import ThreadedServer

# Import local modules
from dcc_mcp_rpyc.server.base import BaseRPyCService
from dcc_mcp_rpyc.server.dcc import DCCServer
from dcc_mcp_rpyc.server.factory import cleanup_server
from dcc_mcp_rpyc.server.factory import create_dcc_server as _create_dcc_server
from dcc_mcp_rpyc.server.factory import create_raw_threaded_server
from dcc_mcp_rpyc.server.server_utils import get_rpyc_config

# Configure logging
logger = logging.getLogger(__name__)

# Global registry of running servers
_servers = {}


def create_server(
    service_class: Type[service.Service] = BaseRPyCService,
    host: str = "localhost",
    port: int = 0,
    protocol_config: Optional[Dict[str, Any]] = None,
    server_type: str = "threaded",
    name: Optional[Optional[str]] = None,
    use_zeroconf: bool = False,
) -> Union[ThreadedServer, DCCServer]:
    """Create a new RPYC server instance.

    This function creates a new RPYC server instance with the specified configuration.
    The server is not started automatically, use start_server to start it.

    Args:
    ----
        service_class: The RPyC service class to use (default: BaseRPyCService)
        host: The hostname to bind to (default: 'localhost')
        port: The port to bind to (default: 0, auto-select)
        protocol_config: Custom protocol configuration (default: None)
        server_type: Type of server to create, one of 'threaded' or 'dcc' (default: 'threaded')
        name: Optional name for the server, required for 'dcc' server type
        use_zeroconf: Whether to use ZeroConf for service discovery (default: False)

    Returns:
    -------
        A server instance (ThreadedServer or DCCServer)

    Raises:
    ------
        ValueError: If server_type is 'dcc' but name is not provided

    """
    if server_type == "dcc":
        if not name:
            raise ValueError("Name is required for DCC server type")
        server = _create_dcc_server(name, service_class, host, port, use_zeroconf)
    else:  # Default to threaded server
        if protocol_config is None:
            protocol_config = get_rpyc_config()
        server = create_raw_threaded_server(service_class, host, port, protocol_config)

    # Generate a unique ID for the server
    server_id = f"{server_type}_{host}_{port}_{id(server)}"

    # Store the server in the registry
    _servers[server_id] = {
        "server": server,
        "thread": None,
        "running": False,
        "type": server_type,
        "name": name,
        "use_zeroconf": use_zeroconf,
    }

    logger.info(f"Created {server_type} server on {host}:{port}")
    return server


def start_server(
    server: Union[ThreadedServer, DCCServer],
    daemon: bool = True,
    auto_register: bool = True,
) -> threading.Thread:
    """Start a server in a new thread.

    This function starts a server in a new thread and optionally registers it
    for discovery.

    Args:
    ----
        server: The server instance to start
        daemon: Whether the server thread should be a daemon thread (default: True)
        auto_register: Whether to automatically register the server for discovery (default: True)

    Returns:
    -------
        The thread in which the server is running

    Raises:
    ------
        ValueError: If the server is already running

    """
    # Find the server in the registry
    server_info = None
    for sid, info in _servers.items():
        if info["server"] is server:
            server_info = info
            break

    if server_info is None:
        # Server not in registry, add it
        server_id = f"unknown_{server.host}_{server.port}_{id(server)}"
        server_info = {
            "server": server,
            "thread": None,
            "running": False,
            "type": "unknown",
            "name": None,
        }
        _servers[server_id] = server_info

    # Check if the server is already running
    if server_info["running"]:
        raise ValueError("Server is already running")

    # Define the thread target function
    def _server_thread():
        try:
            logger.info(f"Starting server on {server.host}:{server.port}")
            server.start()
        except Exception as e:
            logger.error(f"Error in server thread: {e}")
            server_info["running"] = False

    # Create and start the thread
    thread = threading.Thread(target=_server_thread, daemon=daemon)
    thread.start()

    # Update the server info
    server_info["thread"] = thread
    server_info["running"] = True

    logger.info(f"Server started on {server.host}:{server.port}")
    return thread


def stop_server(
    server: Union[ThreadedServer, DCCServer],
    timeout: float = 5.0,
    unregister: bool = True,
) -> bool:
    """Stop a running server.

    This function stops a running server and optionally unregisters it from discovery.

    Args:
    ----
        server: The server instance to stop
        timeout: Timeout for stopping the server in seconds (default: 5.0)
        unregister: Whether to unregister the server from discovery (default: True)

    Returns:
    -------
        True if the server was stopped successfully, False otherwise

    """
    # Find the server in the registry
    server_info = None
    for sid, info in _servers.items():
        if info["server"] is server:
            server_info = info
            break

    if server_info is None:
        logger.warning("Server not found in registry")
        return False

    # Check if the server is running
    if not server_info["running"]:
        logger.warning("Server is not running")
        return True

    # Stop the server and clean up
    try:
        cleanup_server(server, None, timeout)
        server_info["running"] = False
        logger.info(f"Server stopped on {server.host}:{server.port}")
        return True
    except Exception as e:
        logger.error(f"Error stopping server: {e}")
        return False


def is_server_running(server: Union[ThreadedServer, DCCServer]) -> bool:
    """Check if a server is running.

    This function checks if a server is currently running.

    Args:
    ----
        server: The server instance to check

    Returns:
    -------
        True if the server is running, False otherwise

    """
    # Find the server in the registry
    for info in _servers.values():
        if info["server"] is server:
            return info["running"]

    # Server not in registry
    return False
