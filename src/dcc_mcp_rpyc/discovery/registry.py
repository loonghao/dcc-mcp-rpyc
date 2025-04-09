"""Service registry for DCC-MCP-RPYC.

This module provides a registry for managing service discovery strategies and discovered services.
"""

# Import built-in modules
import logging
from typing import List
from typing import Optional
from typing import Dict
from typing import Any

# Import local modules
from dcc_mcp_rpyc.discovery.base import ServiceDiscoveryStrategy
from dcc_mcp_rpyc.discovery.base import ServiceInfo

# Configure logging
logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Registry for managing service discovery strategies and discovered services.

    This class follows the singleton pattern to ensure a single registry instance
    is used throughout the application.
    """

    _instance = None
    _logger = logging.getLogger(__name__)

    def __new__(cls):
        """Ensure only one instance of ServiceRegistry exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._strategies = {}
            cls._instance._services = {}
            cls._logger.debug("Created new ServiceRegistry instance")
        return cls._instance

    @classmethod
    def _reset_instance(cls):
        """Reset the singleton instance.

        This method is primarily used for testing purposes.
        """
        cls._instance = None
        cls._logger.debug("Reset ServiceRegistry singleton instance")

    def register_strategy(self, name: str, strategy: ServiceDiscoveryStrategy) -> None:
        """Register a service discovery strategy.

        Args:
            name: Name of the strategy
            strategy: The strategy instance to register

        """
        self._strategies[name] = strategy
        self._logger.debug(f"Registered strategy '{name}'")

    def get_strategy(self, name: str) -> Optional[ServiceDiscoveryStrategy]:
        """Get a registered strategy by name.

        Args:
            name: Name of the strategy to retrieve

        Returns:
            The strategy instance or None if not found

        """
        return self._strategies.get(name)

    def list_strategies(self) -> List[str]:
        """List all registered strategy names.

        Returns:
            List of strategy names

        """
        return list(self._strategies.keys())

    def discover_services(self, strategy_name: str, dcc_type: Optional[str] = None) -> List[ServiceInfo]:
        """Discover services using a specific strategy.

        Args:
            strategy_name: Name of the strategy to use
            dcc_type: Optional type of service to discover

        Returns:
            List of discovered services

        Raises:
            ValueError: If the strategy is not found

        """
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            raise ValueError(f"Strategy '{strategy_name}' not found")

        services = strategy.discover_services(dcc_type)

        # Update the services cache
        for service in services:
            key = f"{service.dcc_type}:{service.name}:{service.host}:{service.port}"
            self._services[key] = service

        return services

    def register_service(self, strategy_name: str, service_info: ServiceInfo) -> bool:
        """Register a service using a specific strategy.

        Args:
            strategy_name: Name of the strategy to use
            service_info: Information about the service to register

        Returns:
            True if registration was successful, False otherwise

        Raises:
            ValueError: If the strategy is not found

        """
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            raise ValueError(f"Strategy '{strategy_name}' not found")

        success = strategy.register_service(service_info)

        if success:
            # Update the services cache
            key = f"{service_info.dcc_type}:{service_info.name}:{service_info.host}:{service_info.port}"
            self._services[key] = service_info

        return success

    def unregister_service(self, strategy_name: str, service_info: ServiceInfo) -> bool:
        """Unregister a service using a specific strategy.

        Args:
            strategy_name: Name of the strategy to use
            service_info: Information about the service to unregister

        Returns:
            True if unregistration was successful, False otherwise

        Raises:
            ValueError: If the strategy is not found

        """
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            raise ValueError(f"Strategy '{strategy_name}' not found")

        success = strategy.unregister_service(service_info)

        if success:
            # Update the services cache
            key = f"{service_info.dcc_type}:{service_info.name}:{service_info.host}:{service_info.port}"
            if key in self._services:
                del self._services[key]

        return success

    def get_service(self, dcc_type: str, name: Optional[str] = None) -> Optional[ServiceInfo]:
        """Get a service by DCC type and optionally by name.

        Args:
            dcc_type: Type of DCC software
            name: Optional name of the service

        Returns:
            The service info or None if not found

        """
        for key, service in self._services.items():
            if service.dcc_type == dcc_type and (name is None or service.name == name):
                return service
        return None

    def list_services(self, dcc_type: Optional[str] = None) -> List[ServiceInfo]:
        """List all discovered services, optionally filtered by DCC type.

        Args:
            dcc_type: Optional type of DCC software to filter by

        Returns:
            List of service info objects

        """
        if dcc_type:
            return [s for s in self._services.values() if s.dcc_type == dcc_type]
        return list(self._services.values())

    def get_available_dcc_instances(self, refresh: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """Get all available DCC instances grouped by DCC type.

        This method performs a service discovery using all registered strategies
        and returns a dictionary of DCC instances grouped by DCC type.

        Args:
            refresh: Whether to refresh the service cache (default: True)

        Returns:
            Dictionary with DCC types as keys and lists of instance info as values
            Example: {
                "maya": [
                    {
                        "name": "maya-2022",
                        "host": "127.0.0.1",
                        "port": 18812,
                        "version": "2022",
                        "scene": "untitled.ma",
                        "instance_id": "12345",
                        "start_time": "2025-04-02T10:30:00",
                        "user": "username"
                    }
                ]
            }
        """
        # Use cached results if available and refresh is not requested
        if hasattr(self, '_cached_instances') and not refresh:
            self._logger.debug("Using cached DCC instances")
            return self._cached_instances
            
        # Initialize result dictionary
        result = {}
        
        # Discover services using all registered strategies
        for strategy_name in self.list_strategies():
            try:
                services = self.discover_services(strategy_name)
                
                # Group services by DCC type
                for service in services:
                    dcc_type = service.dcc_type.lower()
                    
                    # Initialize list for DCC type if not exists
                    if dcc_type not in result:
                        result[dcc_type] = []
                        
                    # Create instance info
                    instance_info = {
                        "name": service.name,
                        "host": service.host,
                        "port": service.port,
                        "dcc_type": service.dcc_type,
                    }
                    
                    # Add metadata
                    if service.metadata:
                        for key, value in service.metadata.items():
                            if key not in instance_info:
                                instance_info[key] = value
                                
                    # Check if instance already exists
                    exists = False
                    for existing in result[dcc_type]:
                        if (existing["host"] == instance_info["host"] and
                                existing["port"] == instance_info["port"]):
                            exists = True
                            break
                            
                    # Add instance if not exists
                    if not exists:
                        result[dcc_type].append(instance_info)
            except Exception as e:
                self._logger.error(f"Error discovering services using {strategy_name}: {e}")
                
        # Cache results
        self._cached_instances = result
        
        return result

    def ensure_strategy(self, strategy_type: str, **kwargs) -> ServiceDiscoveryStrategy:
        """Ensure a strategy of the specified type exists in the registry.

        If the strategy doesn't exist, it will be created and registered.

        Args:
            strategy_type: Type of strategy to ensure ('file' or 'zeroconf')
            **kwargs: Additional arguments to pass to the strategy constructor

        Returns:
            The strategy instance

        Raises:
            ValueError: If the strategy type is not supported

        """
        strategy = self.get_strategy(strategy_type)
        if not strategy:
            # Import here to avoid circular imports
            # Import local modules
            from dcc_mcp_rpyc.discovery.factory import ServiceDiscoveryFactory

            factory = ServiceDiscoveryFactory()
            strategy = factory.get_strategy(strategy_type, **kwargs)
            if not strategy:
                raise ValueError(f"Strategy type '{strategy_type}' is not available")
            self.register_strategy(strategy_type, strategy)
        return strategy

    def register_service_with_strategy(
        self, strategy_type: str, service_info: ServiceInfo, unregister: bool = False, **kwargs
    ) -> bool:
        """Register or unregister a service using a specific strategy type.

        This is a convenience method that ensures the strategy exists and registers or unregisters the service.

        Args:
            strategy_type: Type of strategy to use ('file' or 'zeroconf')
            service_info: Information about the service to register or unregister
            unregister: If True, unregister the service instead of registering it
            **kwargs: Additional arguments to pass to the strategy constructor

        Returns:
            True if operation was successful, False otherwise

        """
        self.ensure_strategy(strategy_type, **kwargs)
        if unregister:
            return self.unregister_service(strategy_type, service_info)
        else:
            return self.register_service(strategy_type, service_info)
