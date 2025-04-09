"""Service discovery functions for DCC-MCP-RPYC servers.

This module provides functions for registering and discovering DCC services.
"""

# Import built-in modules
import logging
import os
import platform
import socket
import time
import uuid
from typing import Dict, Any, Optional

# Import local modules
from dcc_mcp_rpyc.discovery import ServiceInfo
from dcc_mcp_rpyc.discovery import ServiceRegistry

# Configure logging
logger = logging.getLogger(__name__)


def get_system_info() -> Dict[str, Any]:
    """Get system information for service metadata.

    Returns:
        Dictionary with system information
    """
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "username": os.environ.get("USERNAME", os.environ.get("USER", "unknown")),
        "start_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def register_dcc_service(
    dcc_name: str, 
    host: str, 
    port: int, 
    version: Optional[str] = None,
    scene_name: Optional[str] = None,
    instance_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Register a DCC service for discovery.

    Args:
        dcc_name: Name of the DCC application
        host: Host of the DCC service
        port: Port of the DCC service
        version: Version of the DCC application (optional)
        scene_name: Name of the current scene (optional)
        instance_id: Unique identifier for this instance (optional)
        metadata: Additional metadata to include (optional)

    Returns:
        Path to the registry file
    """
    # Generate a unique instance ID if not provided
    if instance_id is None:
        instance_id = str(uuid.uuid4())
    
    # Create base metadata
    service_metadata = {
        "version": version or "unknown",
        "scene": scene_name or "untitled",
        "instance_id": instance_id,
    }
    
    # Add system information
    service_metadata.update(get_system_info())
    
    # Add additional metadata if provided
    if metadata:
        service_metadata.update(metadata)
    
    # Create service registry
    registry = ServiceRegistry()
    
    # Create service info
    service_info = ServiceInfo(
        name=f"{dcc_name}-{service_metadata['version']}",
        host=host,
        port=port,
        dcc_type=dcc_name,
        metadata=service_metadata
    )

    # Register with file strategy
    registry.register_service_with_strategy("file", service_info)
    
    # Register with ZeroConf if available
    try:
        from dcc_mcp_rpyc.discovery import ZEROCONF_AVAILABLE
        if ZEROCONF_AVAILABLE:
            registry.register_service_with_strategy("zeroconf", service_info)
    except Exception as e:
        logger.warning(f"Failed to register service with ZeroConf: {e}")

    # Return registry path
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
