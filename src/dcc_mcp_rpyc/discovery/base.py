"""Base classes for service discovery strategies.

This module defines the base interfaces and classes for service discovery strategies.
"""

# Import built-in modules
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

# Import third-party modules
from pydantic import BaseModel
from pydantic import Field


class ServiceInfo(BaseModel):
    """Information about a discovered service.

    Attributes:
        name: Name of the service
        host: Hostname or IP address of the service
        port: Port number of the service
        dcc_type: Type of DCC software (e.g., 'maya', 'houdini')
        metadata: Additional metadata about the service

    """

    name: str
    host: str
    port: int
    dcc_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ServiceDiscoveryStrategy(ABC):
    """Base class for service discovery strategies.

    This abstract class defines the interface for service discovery strategies.
    Concrete implementations should provide methods for discovering and registering services.
    """

    @abstractmethod
    def discover_services(self, service_type: Optional[str] = None) -> List[ServiceInfo]:
        """Discover available services.

        Args:
            service_type: Optional type of service to discover (e.g., 'maya', 'houdini')

        Returns:
            List of discovered ServiceInfo objects

        """

    @abstractmethod
    def register_service(self, service_info: ServiceInfo) -> bool:
        """Register a service with the discovery mechanism.

        Args:
            service_info: Information about the service to register

        Returns:
            True if registration was successful, False otherwise

        """

    @abstractmethod
    def unregister_service(self, service_info: ServiceInfo) -> bool:
        """Unregister a service from the discovery mechanism.

        Args:
            service_info: Information about the service to unregister

        Returns:
            True if unregistration was successful, False otherwise

        """
