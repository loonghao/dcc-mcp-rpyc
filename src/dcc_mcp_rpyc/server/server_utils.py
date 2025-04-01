"""Utility functions for DCC-MCP-RPYC servers.

This module provides utility functions for creating and managing RPYC servers
for DCC applications.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Type

# Import third-party modules
from rpyc.core import service
from rpyc.utils.server import ThreadedServer

# Configure logging
logger = logging.getLogger(__name__)


def get_rpyc_config(allow_all_attrs=False, allow_public_attrs=True, allow_pickle=False) -> Dict[str, Any]:
    """Get a configuration dictionary for RPyC connections.

    This function creates a configuration dictionary with common settings
    for RPyC connections in the DCC-MCP ecosystem.

    Args:
        allow_all_attrs: Whether to allow access to all attributes
        allow_public_attrs: Whether to allow access to public attributes
        allow_pickle: Whether to allow pickle serialization

    Returns:
        A configuration dictionary for RPyC connections

    """
    config = {
        "allow_all_attrs": allow_all_attrs,
        "allow_public_attrs": allow_public_attrs,
        "allow_pickle": allow_pickle,
        "sync_request_timeout": 60.0,  # 60 seconds timeout for sync requests
        "allow_getattr": True,  # Allow getattr access
        "allow_setattr": True,  # Allow setattr access
        "allow_delattr": True,  # Allow delattr access
        "allow_methods": True,  # Allow method calls
    }

    return config


def create_raw_threaded_server(
    service_class: Type[service.Service],
    hostname: str = "localhost",
    port: Optional[int] = None,
    protocol_config: Optional[Dict[str, Any]] = None,
    socket_path: Optional[str] = None,
    ipv6: bool = False,
    authenticator: Optional[Callable] = None,
    auto_register: bool = False,
) -> ThreadedServer:
    """Create a raw threaded server.

    Args:
        service_class: Service class to use
        hostname: Host to bind to
        port: Port to bind to
        protocol_config: Protocol configuration
        socket_path: Path to the socket file
        ipv6: Whether to use IPv6
        authenticator: Authentication function
        auto_register: Whether to automatically register the service

    Returns:
        A ThreadedServer instance

    """
    # Use get_rpyc_config to get default protocol configuration
    if protocol_config is None:
        protocol_config = get_rpyc_config(allow_all_attrs=True, allow_public_attrs=True, allow_pickle=True)

    # Create server
    server = ThreadedServer(
        service_class,
        hostname=hostname,
        port=port,
        protocol_config=protocol_config,
        socket_path=socket_path,
        ipv6=ipv6,
        authenticator=authenticator,
        auto_register=auto_register,
    )

    return server
