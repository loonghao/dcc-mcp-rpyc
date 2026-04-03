"""DCC-MCP-IPC package.

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
from dcc_mcp_ipc.action_adapter import ActionAdapter

# Import from adapter module
from dcc_mcp_ipc.adapter import ApplicationAdapter
from dcc_mcp_ipc.adapter import DCCAdapter
from dcc_mcp_ipc.adapter import get_adapter

# Import from client module
from dcc_mcp_ipc.client import BaseApplicationClient
from dcc_mcp_ipc.client import BaseDCCClient
from dcc_mcp_ipc.client import ClientRegistry
from dcc_mcp_ipc.client import ConnectionPool
from dcc_mcp_ipc.client import get_client

# Import from discovery module
from dcc_mcp_ipc.discovery import FileDiscoveryStrategy
from dcc_mcp_ipc.discovery import ServiceDiscoveryFactory
from dcc_mcp_ipc.discovery import ServiceInfo
from dcc_mcp_ipc.discovery import ServiceRegistry
from dcc_mcp_ipc.discovery import ZeroConfDiscoveryStrategy

# Import from server module
from dcc_mcp_ipc.server import ApplicationRPyCService
from dcc_mcp_ipc.server import BaseRPyCService
from dcc_mcp_ipc.server import DCCServer
from dcc_mcp_ipc.server import is_server_running
from dcc_mcp_ipc.server import start_server
from dcc_mcp_ipc.server import stop_server

# Import from snapshot module
from dcc_mcp_ipc.snapshot.base import BaseSnapshot
from dcc_mcp_ipc.snapshot.base import SnapshotConfig
from dcc_mcp_ipc.snapshot.base import SnapshotError
from dcc_mcp_ipc.snapshot.base import SnapshotFormat
from dcc_mcp_ipc.snapshot.base import SnapshotResult
from dcc_mcp_ipc.snapshot.rpyc import RPyCSnapshot
from dcc_mcp_ipc.snapshot import create_snapshot

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
