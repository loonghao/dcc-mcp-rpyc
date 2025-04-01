"""Utility functions and classes for DCC-MCP-RPYC."""

# Import from rpyc_utils module
# Import local modules
# Import from discovery module (now in dcc_mcp_rpyc.discovery)
from dcc_mcp_rpyc.discovery import FileDiscoveryStrategy
from dcc_mcp_rpyc.discovery import ServiceDiscoveryFactory
from dcc_mcp_rpyc.discovery import ServiceInfo
from dcc_mcp_rpyc.discovery import ServiceRegistry
from dcc_mcp_rpyc.discovery import ZeroConfDiscoveryStrategy

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
    "FileDiscoveryStrategy",
    "ServiceDiscoveryFactory",
    "ServiceInfo",
    "ServiceRegistry",
    "ZeroConfDiscoveryStrategy",
    "deliver_parameters",
    "execute_remote_command",
    "get_container",
    "handle_error",
    "register_factory",
    "register_instance",
    "register_singleton",
    "resolve",
    "with_action_result",
    "with_error_handling",
]
