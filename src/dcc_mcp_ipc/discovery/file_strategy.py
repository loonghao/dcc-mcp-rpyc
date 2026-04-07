"""File-based service discovery strategy for DCC-MCP-IPC.

This module provides a service discovery strategy that uses files to register and discover services.
"""

# Import built-in modules
import json
import logging
import os
import time
from typing import Optional

# Import third-party modules
from dcc_mcp_core import get_config_dir

# Import local modules
from dcc_mcp_ipc.discovery.base import ServiceDiscoveryStrategy
from dcc_mcp_ipc.discovery.base import ServiceInfo

# Configure logging
logger = logging.getLogger(__name__)


def _get_default_config_dir() -> str:
    """Return the default per-user config directory for registry files."""
    try:
        config_dir = get_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        return config_dir
    except Exception:
        # Fallback to OS-standard path if dcc_mcp_core is unavailable
        if os.name == "nt":
            base_dir = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        else:
            base_dir = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
        config_dir = os.path.join(base_dir, "dcc_mcp_ipc")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir


DEFAULT_REGISTRY_PATH = os.path.join(_get_default_config_dir(), "service_registry.json")


class FileDiscoveryStrategy(ServiceDiscoveryStrategy):
    """File-based service discovery strategy.

    This strategy uses files to register and discover services.
    """

    def __init__(self, registry_path: Optional[str] = None):
        """Initialize the file discovery strategy.

        Args:
            registry_path: Path to the registry file (default: None, uses default path)

        """
        self.registry_path = registry_path or DEFAULT_REGISTRY_PATH
        self._services = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load the registry from file."""
        try:
            if os.path.exists(self.registry_path):
                with open(self.registry_path) as f:
                    data = json.load(f)
                    self._services = data
                    logger.debug(f"Loaded registry from {self.registry_path}")
            else:
                logger.debug(f"Registry file {self.registry_path} does not exist")
        except Exception as e:
            logger.error(f"Error loading registry: {e}")

    def _save_registry(self) -> None:
        """Save the registry to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)

            with open(self.registry_path, "w") as f:
                json.dump(self._services, f, indent=2)
                logger.debug(f"Saved registry to {self.registry_path}")
        except Exception as e:
            logger.error(f"Error saving registry: {e}")

    def discover_services(self, service_type: Optional[str] = None) -> list[ServiceInfo]:
        """Discover available services.

        Args:
            service_type: Optional type of service to discover (e.g., 'maya', 'houdini')

        Returns:
            List of discovered ServiceInfo objects

        """
        # Reload the registry to get the latest services
        self._load_registry()

        services = []
        for key, service_data in self._services.items():
            # Check if service data is valid
            if not isinstance(service_data, dict):
                logger.warning(f"Invalid service data for {key}: {service_data}")
                continue

            # Extract dcc_type from service data or key
            # New format: stored in service_data["dcc_type"]
            # Legacy format: key is the dcc_type directly (no ":" separator)
            dcc_type = service_data.get("dcc_type", key.split(":")[0] if ":" in key else key)

            if service_type and dcc_type != service_type:
                continue

            # Check if service is stale (older than 1 hour)
            timestamp = service_data.get("timestamp", 0)
            if time.time() - timestamp > 3600:  # 1 hour
                logger.debug(f"Service {key} is stale, skipping")
                continue

            try:
                service_info = ServiceInfo(
                    name=service_data.get("name", key),
                    host=service_data.get("host", ""),
                    port=service_data.get("port", 0),
                    dcc_type=dcc_type,
                    metadata=service_data.get("metadata", {}),
                )
                services.append(service_info)
            except Exception as e:
                logger.warning(f"Error creating ServiceInfo for {key}: {e}")

        return services

    @staticmethod
    def _make_service_key(service_info: ServiceInfo) -> str:
        """Create a unique key for a service instance.

        Uses dcc_type:host:port to uniquely identify each instance,
        allowing multiple instances of the same DCC type.

        Args:
            service_info: Information about the service

        Returns:
            A unique string key for the service instance

        """
        return f"{service_info.dcc_type}:{service_info.host}:{service_info.port}"

    def register_service(self, service_info: ServiceInfo) -> bool:
        """Register a service with the discovery mechanism.

        Args:
            service_info: Information about the service to register

        Returns:
            True if registration was successful, False otherwise

        """
        try:
            # Reload the registry to get the latest services
            self._load_registry()

            # Create service data
            service_data = {
                "name": service_info.name,
                "host": service_info.host,
                "port": service_info.port,
                "dcc_type": service_info.dcc_type,
                "timestamp": time.time(),
                "metadata": service_info.metadata,
            }

            # Register the service using composite key (dcc_type:host:port)
            # This allows multiple instances of the same DCC type
            key = self._make_service_key(service_info)
            self._services[key] = service_data

            # Save the registry
            self._save_registry()

            logger.info(
                f"Registered service {service_info.name} for DCC "
                f"{service_info.dcc_type} at {service_info.host}:{service_info.port}"
            )
            return True
        except Exception as e:
            logger.error(f"Error registering service: {e}")
            return False

    def unregister_service(self, service_info: ServiceInfo) -> bool:
        """Unregister a service from the discovery mechanism.

        Args:
            service_info: Information about the service to unregister

        Returns:
            True if unregistration was successful, False otherwise

        """
        try:
            # Reload the registry to get the latest services
            self._load_registry()

            key = self._make_service_key(service_info)

            # Try new composite key first
            if key in self._services:
                del self._services[key]
            # Fallback: try legacy dcc_type key for backward compatibility
            elif service_info.dcc_type in self._services:
                del self._services[service_info.dcc_type]
            else:
                logger.warning(
                    f"Service {service_info.name} for DCC "
                    f"{service_info.dcc_type} at {service_info.host}:{service_info.port} not found"
                )
                return False

            # Save the registry
            self._save_registry()

            logger.info(
                f"Unregistered service {service_info.name} for DCC "
                f"{service_info.dcc_type} at {service_info.host}:{service_info.port}"
            )
            return True
        except Exception as e:
            logger.error(f"Error unregistering service: {e}")
            return False
