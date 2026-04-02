"""Application module for DCC-MCP-IPC.

This package provides application-specific classes for connecting to and interacting with
general Python applications.
"""

# Import local modules
from dcc_mcp_ipc.application.adapter import GenericApplicationAdapter
from dcc_mcp_ipc.application.client import ApplicationClient
from dcc_mcp_ipc.application.client import connect_to_application

# Import from submodules
from dcc_mcp_ipc.application.service import ApplicationService
from dcc_mcp_ipc.application.service import create_application_server
from dcc_mcp_ipc.application.service import start_application_server

__all__ = [
    "ApplicationClient",
    "ApplicationService",
    "GenericApplicationAdapter",
    "connect_to_application",
    "create_application_server",
    "start_application_server",
]
