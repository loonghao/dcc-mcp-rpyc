"""DCC-MCP-RPYC package.

This package provides utilities for connecting to DCC applications via RPYC.
It includes client and server classes, as well as utilities for service discovery and registration.
"""

# Import built-in modules
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union

# Import local modules
# Import from action_adapter module
from dcc_mcp_rpyc.action_adapter import ActionAdapter
from dcc_mcp_rpyc.action_adapter import get_action_adapter

# Import from adapter package
from dcc_mcp_rpyc.adapter import ApplicationAdapter
from dcc_mcp_rpyc.adapter import DCCAdapter
from dcc_mcp_rpyc.adapter import SessionAdapter
from dcc_mcp_rpyc.adapter import get_adapter

# Import from client package
from dcc_mcp_rpyc.client import (
    AsyncBaseApplicationClient,  # Synchronous clients; Client registry and connection pool; Asynchronous clients
)
from dcc_mcp_rpyc.client import AsyncBaseDCCClient
from dcc_mcp_rpyc.client import BaseApplicationClient
from dcc_mcp_rpyc.client import BaseDCCClient
from dcc_mcp_rpyc.client import ClientRegistry
from dcc_mcp_rpyc.client import ConnectionPool
from dcc_mcp_rpyc.client import close_all_async_connections
from dcc_mcp_rpyc.client import close_all_connections
from dcc_mcp_rpyc.client import get_async_client
from dcc_mcp_rpyc.client import get_client

# Import from server package
from dcc_mcp_rpyc.server import BaseRPyCService
from dcc_mcp_rpyc.server import DCCServer
from dcc_mcp_rpyc.server import create_server
from dcc_mcp_rpyc.server import is_server_running
from dcc_mcp_rpyc.server import start_server
from dcc_mcp_rpyc.server import stop_server

# Import from utils.discovery module
from dcc_mcp_rpyc.utils.discovery import DEFAULT_REGISTRY_PATH
from dcc_mcp_rpyc.utils.discovery import cleanup_stale_services
from dcc_mcp_rpyc.utils.discovery import discover_services
from dcc_mcp_rpyc.utils.discovery import find_service_registry_files
from dcc_mcp_rpyc.utils.discovery import get_latest_service
from dcc_mcp_rpyc.utils.discovery import register_service
from dcc_mcp_rpyc.utils.discovery import unregister_service

__all__ = [
    # Discovery functions
    "DEFAULT_REGISTRY_PATH",
    # Action adapter
    "ActionAdapter",
    # Adapter classes and functions
    "ApplicationAdapter",
    # Asynchronous clients
    "AsyncBaseApplicationClient",
    "AsyncBaseDCCClient",
    # Client classes and functions
    "BaseApplicationClient",
    "BaseDCCClient",
    # Server classes and functions
    "BaseRPyCService",
    # Client registry and connection pool
    "ClientRegistry",
    "ConnectionPool",
    "DCCAdapter",
    "DCCServer",
    "SessionAdapter",
    "cleanup_stale_services",
    "close_all_async_connections",
    "close_all_connections",
    "create_server",
    "discover_services",
    "find_service_registry_files",
    "get_action_adapter",
    "get_adapter",
    "get_async_client",
    "get_client",
    "get_latest_service",
    "is_server_running",
    "register_service",
    "start_server",
    "stop_server",
    "unregister_service",
]
