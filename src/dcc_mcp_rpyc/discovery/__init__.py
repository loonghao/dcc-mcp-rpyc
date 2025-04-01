"""Service discovery module for DCC-MCP-RPYC.

This module provides functionality for discovering and connecting to DCC-MCP services.
"""

# Import local modules
from dcc_mcp_rpyc.discovery.base import ServiceDiscoveryStrategy
from dcc_mcp_rpyc.discovery.base import ServiceInfo
from dcc_mcp_rpyc.discovery.factory import ServiceDiscoveryFactory
from dcc_mcp_rpyc.discovery.file_strategy import FileDiscoveryStrategy
from dcc_mcp_rpyc.discovery.registry import ServiceRegistry
from dcc_mcp_rpyc.discovery.zeroconf_strategy import ZEROCONF_AVAILABLE
from dcc_mcp_rpyc.discovery.zeroconf_strategy import ZeroConfDiscoveryStrategy

__all__ = [
    "ZEROCONF_AVAILABLE",
    "FileDiscoveryStrategy",
    "ServiceDiscoveryFactory",
    "ServiceDiscoveryStrategy",
    "ServiceInfo",
    "ServiceRegistry",
    "ZeroConfDiscoveryStrategy",
]
