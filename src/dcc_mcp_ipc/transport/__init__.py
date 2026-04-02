"""Transport layer for DCC-MCP-IPC.

This package provides protocol-agnostic transport abstractions for communicating
with DCC applications. The transport layer decouples the upper-level client/adapter
code from the specific IPC protocol used (RPyC, HTTP, WebSocket, etc.).
"""

# Import local modules
from dcc_mcp_ipc.transport.base import BaseTransport
from dcc_mcp_ipc.transport.base import TransportConfig
from dcc_mcp_ipc.transport.base import TransportError
from dcc_mcp_ipc.transport.base import TransportState
from dcc_mcp_ipc.transport.factory import create_transport
from dcc_mcp_ipc.transport.factory import get_transport
from dcc_mcp_ipc.transport.factory import register_transport

__all__ = [
    "BaseTransport",
    "TransportConfig",
    "TransportError",
    "TransportState",
    "create_transport",
    "get_transport",
    "register_transport",
]
