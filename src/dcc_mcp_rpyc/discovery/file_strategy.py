"""File-based service discovery strategy for DCC-MCP-RPYC.

This module provides a service discovery strategy that uses files to register and discover services.
"""

# Import built-in modules
import json
import logging
import os
import time
from typing import List
from typing import Optional

# Import third-party modules
from dcc_mcp_core.utils.filesystem import get_config_dir

# Import local modules
from dcc_mcp_rpyc.discovery.base import ServiceDiscoveryStrategy
from dcc_mcp_rpyc.discovery.base import ServiceInfo

# Configure logging
logger = logging.getLogger(__name__)

# Default registry path using dcc-mcp-core
config_dir = get_config_dir(ensure_exists=True)
DEFAULT_REGISTRY_PATH = os.path.join(config_dir, "service_registry.json")


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
        """Load the registry from file with enhanced error handling and version compatibility."""
        try:
            if os.path.exists(self.registry_path):
                with open(self.registry_path) as f:
                    try:
                        data = json.load(f)
                        # Check data format version
                        version = data.pop("_version", 1) if isinstance(data, dict) else 1
                        
                        # Process based on version
                        if version == 1:
                            # Handle v1 format
                            if isinstance(data, dict):
                                self._services = data
                                logger.debug(f"Loaded registry from {self.registry_path} (version {version})")
                            else:
                                logger.error(f"Invalid registry data format in {self.registry_path}")
                                self._backup_invalid_registry()
                                self._services = {}
                        else:
                            # Handle unknown version
                            logger.warning(f"Unknown registry version {version}, attempting compatibility handling")
                            if isinstance(data, dict):
                                self._services = data
                            else:
                                self._services = {}
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid registry file format in {self.registry_path}: {e}")
                        # Backup and create new file
                        self._backup_invalid_registry()
                        self._services = {}
            else:
                logger.debug(f"Registry file {self.registry_path} does not exist")
                self._services = {}
        except Exception as e:
            logger.error(f"Error loading registry: {e}")
            self._services = {}
            
    def _backup_invalid_registry(self) -> None:
        """Backup an invalid registry file."""
        try:
            if os.path.exists(self.registry_path):
                backup_path = f"{self.registry_path}.bak.{int(time.time())}"
                import shutil
                shutil.copy2(self.registry_path, backup_path)
                logger.info(f"Backed up invalid registry file to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to backup invalid registry file: {e}")

    def _save_registry(self) -> None:
        """Save the registry to file with version information."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)

            # Add version information
            data = self._services.copy()
            data["_version"] = 1  # Current version
            
            with open(self.registry_path, "w") as f:
                json.dump(data, f, indent=2)
                logger.debug(f"Saved registry to {self.registry_path} (version 1)")
        except Exception as e:
            logger.error(f"Error saving registry: {e}")

    def discover_services(self, service_type: Optional[str] = None) -> List[ServiceInfo]:
        """Discover available services.

        Args:
            service_type: Optional type of service to discover (e.g., 'maya', 'houdini')

        Returns:
            List of discovered ServiceInfo objects

        """
        # Reload the registry to get the latest services
        self._load_registry()

        services = []
        for dcc_name, service_data in self._services.items():
            if service_type and dcc_name != service_type:
                continue

            # Check if service data is valid
            if not isinstance(service_data, dict):
                logger.warning(f"Invalid service data for {dcc_name}: {service_data}")
                continue

            # Check if service is stale (older than 1 hour)
            timestamp = service_data.get("timestamp", 0)
            if time.time() - timestamp > 3600:  # 1 hour
                logger.debug(f"Service {dcc_name} is stale, skipping")
                continue

            try:
                service_info = ServiceInfo(
                    name=service_data.get("name", dcc_name),
                    host=service_data.get("host", ""),
                    port=service_data.get("port", 0),
                    dcc_type=dcc_name,
                    metadata=service_data.get("metadata", {}),
                )
                services.append(service_info)
            except Exception as e:
                logger.warning(f"Error creating ServiceInfo for {dcc_name}: {e}")

        return services

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
                "timestamp": time.time(),
                "metadata": service_info.metadata,
            }

            # Register the service
            self._services[service_info.dcc_type] = service_data

            # Save the registry
            self._save_registry()

            logger.info(f"Registered service {service_info.name} for DCC {service_info.dcc_type}")
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

            # Check if service exists
            if service_info.dcc_type not in self._services:
                logger.warning(f"Service {service_info.name} for DCC {service_info.dcc_type} not found")
                return False

            # Unregister the service
            del self._services[service_info.dcc_type]

            # Save the registry
            self._save_registry()

            logger.info(f"Unregistered service {service_info.name} for DCC {service_info.dcc_type}")
            return True
        except Exception as e:
            logger.error(f"Error unregistering service: {e}")
            return False
