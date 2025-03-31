"""Utility functions and classes for DCC-MCP-RPYC."""

# Import from rpyc_utils module
# Import local modules
# Import from decorators module
from dcc_mcp_rpyc.utils.decorators import with_action_result
from dcc_mcp_rpyc.utils.decorators import with_error_handling

# Import from di module
from dcc_mcp_rpyc.utils.di import Container
from dcc_mcp_rpyc.utils.di import get_container
from dcc_mcp_rpyc.utils.di import register_factory
from dcc_mcp_rpyc.utils.di import register_instance
from dcc_mcp_rpyc.utils.di import register_singleton
from dcc_mcp_rpyc.utils.di import resolve

# Import from discovery module
from dcc_mcp_rpyc.utils.discovery import cleanup_stale_services
from dcc_mcp_rpyc.utils.discovery import discover_services
from dcc_mcp_rpyc.utils.discovery import find_service_registry_files
from dcc_mcp_rpyc.utils.discovery import get_latest_service
from dcc_mcp_rpyc.utils.discovery import register_service
from dcc_mcp_rpyc.utils.discovery import unregister_service

# Import from errors module
from dcc_mcp_rpyc.utils.errors import ActionError
from dcc_mcp_rpyc.utils.errors import ConnectionError
from dcc_mcp_rpyc.utils.errors import DCCMCPError
from dcc_mcp_rpyc.utils.errors import ExecutionError
from dcc_mcp_rpyc.utils.errors import handle_error
from dcc_mcp_rpyc.utils.rpyc_utils import deliver_parameters
from dcc_mcp_rpyc.utils.rpyc_utils import execute_remote_command

__all__ = [
    # Alphabetically sorted
    "ActionError",
    "ConnectionError",
    "Container",
    "DCCMCPError",
    "ExecutionError",
    "cleanup_stale_services",
    "deliver_parameters",
    "discover_services",
    "execute_remote_command",
    "find_service_registry_files",
    "get_container",
    "get_latest_service",
    "handle_error",
    "register_factory",
    "register_instance",
    "register_service",
    "register_singleton",
    "resolve",
    "unregister_service",
    "with_action_result",
    "with_error_handling",
]
