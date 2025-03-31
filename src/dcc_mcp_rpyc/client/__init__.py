"""Client classes for DCC-MCP-RPYC.

This package provides client classes for connecting to DCC RPyC services.
"""

# Import local modules
# Import from async_base module
from dcc_mcp_rpyc.client.async_base import AsyncBaseApplicationClient
from dcc_mcp_rpyc.client.async_base import close_all_async_connections
from dcc_mcp_rpyc.client.async_base import get_async_client

# Import from async_dcc module
from dcc_mcp_rpyc.client.async_dcc import AsyncBaseDCCClient

# Import from base module
from dcc_mcp_rpyc.client.base import BaseApplicationClient
from dcc_mcp_rpyc.client.base import close_all_connections
from dcc_mcp_rpyc.client.base import get_client

# Import from dcc module
from dcc_mcp_rpyc.client.dcc import BaseDCCClient

# Import from pool module
from dcc_mcp_rpyc.client.pool import ClientRegistry
from dcc_mcp_rpyc.client.pool import ConnectionPool

__all__ = [
    # Alphabetically sorted
    "AsyncBaseApplicationClient",
    "AsyncBaseDCCClient",
    "BaseApplicationClient",
    "BaseDCCClient",
    "ClientRegistry",
    "ConnectionPool",
    "close_all_async_connections",
    "close_all_connections",
    "get_async_client",
    "get_client",
]
