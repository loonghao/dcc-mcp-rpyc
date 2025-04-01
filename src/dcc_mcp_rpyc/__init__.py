"""DCC-MCP-RPYC package.

This package provides utilities for connecting to DCC applications via RPYC.
It includes client and server classes, as well as utilities for service discovery and registration.
"""

# Import built-in modules
import os
import sys
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import Union

# Import third-party modules
# Import dcc_mcp_core modules
from dcc_mcp_core.actions import Action
from dcc_mcp_core.actions import ActionRegistry
from dcc_mcp_core.models import ActionResultModel
from dcc_mcp_core.utils.filesystem import get_config_dir
import rpyc

# Import local modules
# Import from action_adapter module
from dcc_mcp_rpyc.action_adapter import ActionAdapter

# Import from adapter module
from dcc_mcp_rpyc.adapter import ApplicationAdapter
from dcc_mcp_rpyc.adapter import DCCAdapter
from dcc_mcp_rpyc.adapter import get_adapter

# Import from client module
from dcc_mcp_rpyc.client import BaseApplicationClient
from dcc_mcp_rpyc.client import BaseDCCClient
from dcc_mcp_rpyc.client import ClientRegistry
from dcc_mcp_rpyc.client import ConnectionPool
from dcc_mcp_rpyc.client import get_client

# Import from discovery module
from dcc_mcp_rpyc.discovery import FileDiscoveryStrategy
from dcc_mcp_rpyc.discovery import ServiceDiscoveryFactory
from dcc_mcp_rpyc.discovery import ServiceInfo
from dcc_mcp_rpyc.discovery import ServiceRegistry
from dcc_mcp_rpyc.discovery import ZeroConfDiscoveryStrategy

# Import from server module
from dcc_mcp_rpyc.server import ApplicationRPyCService
from dcc_mcp_rpyc.server import BaseRPyCService
from dcc_mcp_rpyc.server import DCCServer
from dcc_mcp_rpyc.server import is_server_running
from dcc_mcp_rpyc.server import start_server
from dcc_mcp_rpyc.server import stop_server

# Get default registry path
config_dir = get_config_dir(ensure_exists=True)
DEFAULT_REGISTRY_PATH = os.path.join(config_dir, "service_registry.json")

__all__ = [
    # Discovery functions
    "DEFAULT_REGISTRY_PATH",
    # Action adapter
    "ActionAdapter",
    # Adapter classes and functions
    "ApplicationAdapter",
    # Server classes and functions
    "ApplicationRPyCService",
    # Client classes and functions
    "BaseApplicationClient",
    "BaseDCCClient",
    "BaseRPyCService",
    "ClientRegistry",
    "ConnectionPool",
    "DCCAdapter",
    "DCCServer",
    "FileDiscoveryStrategy",
    "ServiceDiscoveryFactory",
    "ServiceInfo",
    "ServiceRegistry",
    "ZeroConfDiscoveryStrategy",
    "get_adapter",
    "get_client",
    "is_server_running",
    "start_server",
    "stop_server",
]
