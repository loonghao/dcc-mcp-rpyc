"""DCC-MCP-IPC package.

This package provides utilities for connecting to DCC applications through a
protocol-agnostic IPC layer while preserving the existing RPyC-based client and
server workflows.
"""

# Import built-in modules
from importlib import import_module
import os
from typing import Any

# Import third-party modules
from dcc_mcp_core import ActionResultModel
from dcc_mcp_core import get_config_dir

__all__ = [
    "DEFAULT_REGISTRY_PATH",
    "ActionAdapter",
    "ApplicationAdapter",
    "ApplicationRPyCService",
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

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "DEFAULT_REGISTRY_PATH": ("dcc_mcp_ipc.discovery.file_strategy", "DEFAULT_REGISTRY_PATH"),
    "ActionAdapter": ("dcc_mcp_ipc.action_adapter", "ActionAdapter"),
    "ApplicationAdapter": ("dcc_mcp_ipc.adapter", "ApplicationAdapter"),
    "ApplicationRPyCService": ("dcc_mcp_ipc.server", "ApplicationRPyCService"),
    "BaseApplicationClient": ("dcc_mcp_ipc.client", "BaseApplicationClient"),
    "BaseDCCClient": ("dcc_mcp_ipc.client", "BaseDCCClient"),
    "BaseRPyCService": ("dcc_mcp_ipc.server", "BaseRPyCService"),
    "ClientRegistry": ("dcc_mcp_ipc.client", "ClientRegistry"),
    "ConnectionPool": ("dcc_mcp_ipc.client", "ConnectionPool"),
    "DCCAdapter": ("dcc_mcp_ipc.adapter", "DCCAdapter"),
    "DCCServer": ("dcc_mcp_ipc.server", "DCCServer"),
    "FileDiscoveryStrategy": ("dcc_mcp_ipc.discovery", "FileDiscoveryStrategy"),
    "ServiceDiscoveryFactory": ("dcc_mcp_ipc.discovery", "ServiceDiscoveryFactory"),
    "ServiceInfo": ("dcc_mcp_ipc.discovery", "ServiceInfo"),
    "ServiceRegistry": ("dcc_mcp_ipc.discovery", "ServiceRegistry"),
    "ZeroConfDiscoveryStrategy": ("dcc_mcp_ipc.discovery", "ZeroConfDiscoveryStrategy"),
    "get_adapter": ("dcc_mcp_ipc.adapter", "get_adapter"),
    "get_client": ("dcc_mcp_ipc.client", "get_client"),
    "is_server_running": ("dcc_mcp_ipc.server", "is_server_running"),
    "start_server": ("dcc_mcp_ipc.server", "start_server"),
    "stop_server": ("dcc_mcp_ipc.server", "stop_server"),
}


def __getattr__(name: str) -> Any:
    """Lazily import public package attributes on demand."""
    try:
        module_name, attribute_name = _LAZY_IMPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return module attributes for interactive discovery."""
    return sorted(set(globals()) | set(__all__))
