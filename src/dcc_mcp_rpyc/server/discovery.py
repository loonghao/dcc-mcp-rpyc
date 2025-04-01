"""Service discovery functions for DCC-MCP-RPYC servers.

This module provides functions for registering and discovering DCC services.
"""

# Import built-in modules
import logging

# Import local modules
from dcc_mcp_rpyc.discovery import ServiceInfo
from dcc_mcp_rpyc.discovery import ServiceRegistry

# Configure logging
logger = logging.getLogger(__name__)


def register_dcc_service(dcc_name: str, host: str, port: int) -> str:
    """Register a DCC service for discovery.

    Args:
        dcc_name: Name of the DCC application
        host: Host of the DCC service
        port: Port of the DCC service

    Returns:
        Path to the registry file

    """
    registry = ServiceRegistry()
    service_info = ServiceInfo(name=dcc_name, host=host, port=port, dcc_type=dcc_name, metadata={"version": "1.0.0"})

    registry.register_service_with_strategy("file", service_info)

    strategy = registry.get_strategy("file")
    return strategy.registry_path


def unregister_dcc_service(registry_path: str) -> bool:
    """Unregister a DCC service.

    Args:
        registry_path: Path to the registry file

    Returns:
        True if successful, False otherwise

    """
    registry = ServiceRegistry()

    try:
        registry.ensure_strategy("file", registry_path=registry_path)
    except ValueError:
        return False

    services = registry.discover_services("file")
    if not services:
        return False

    success = True
    for service in services:
        if not registry.unregister_service("file", service):
            success = False

    return success
