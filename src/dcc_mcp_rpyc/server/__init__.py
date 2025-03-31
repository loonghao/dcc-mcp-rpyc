"""Server module for DCC-MCP-RPYC.

This package provides server classes for exposing DCC functionality via RPYC,
including base services, DCC-specific services, and server lifecycle management.
"""

# Import local modules
from dcc_mcp_rpyc.server.base import ApplicationRPyCService
from dcc_mcp_rpyc.server.base import BaseRPyCService
from dcc_mcp_rpyc.server.dcc import DCCRPyCService
from dcc_mcp_rpyc.server.dcc import DCCServer
from dcc_mcp_rpyc.server.factory import cleanup_server
from dcc_mcp_rpyc.server.factory import create_dcc_server
from dcc_mcp_rpyc.server.factory import create_raw_threaded_server
from dcc_mcp_rpyc.server.factory import create_service_factory
from dcc_mcp_rpyc.server.factory import create_shared_service_instance
from dcc_mcp_rpyc.server.factory import get_rpyc_config
from dcc_mcp_rpyc.server.factory import register_dcc_service
from dcc_mcp_rpyc.server.factory import unregister_dcc_service
from dcc_mcp_rpyc.server.lifecycle import create_server
from dcc_mcp_rpyc.server.lifecycle import is_server_running
from dcc_mcp_rpyc.server.lifecycle import start_server
from dcc_mcp_rpyc.server.lifecycle import stop_server

__all__ = [
    # Alphabetically sorted
    "ApplicationRPyCService",
    "BaseRPyCService",
    "DCCRPyCService",
    "DCCServer",
    "cleanup_server",
    "create_dcc_server",
    "create_raw_threaded_server",
    "create_server",
    "create_service_factory",
    "create_shared_service_instance",
    "get_rpyc_config",
    "is_server_running",
    "register_dcc_service",
    "start_server",
    "stop_server",
    "unregister_dcc_service",
]
