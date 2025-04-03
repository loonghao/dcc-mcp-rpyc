"""Client registry for DCC-MCP-RPYC.

This module provides a registry for client classes that can be used to connect to
DCC applications. It allows registering client classes for specific DCC applications
and retrieving them by name.
"""

# Import built-in modules
import logging
from typing import Dict
from typing import Optional
from typing import Type

# Import local modules
from dcc_mcp_rpyc.client.dcc import BaseDCCClient

# Configure logging
logger = logging.getLogger(__name__)


class ClientRegistry:
    """Registry for client classes.
    
    This class provides a registry for client classes that can be used to connect to
    DCC applications. It allows registering client classes for specific DCC applications
    and retrieving them by name.
    """
    
    # Registry of client classes
    _registry: Dict[str, Type[BaseDCCClient]] = {}
    
    @classmethod
    def register_client_class(cls, dcc_name: str, client_class: Type[BaseDCCClient]) -> None:
        """Register a client class for a specific DCC application.
        
        Args:
            dcc_name: Name of the DCC application
            client_class: Client class to register
        """
        cls._registry[dcc_name.lower()] = client_class
        logger.info(f"Registered client class {client_class.__name__} for {dcc_name}")
    
    @classmethod
    def get_client_class(cls, dcc_name: str) -> Type[BaseDCCClient]:
        """Get the client class for a specific DCC application.
        
        Args:
            dcc_name: Name of the DCC application
        
        Returns:
            The client class for the specified application
        
        Raises:
            ValueError: If the application is not supported
        """
        dcc_name = dcc_name.lower()
        if dcc_name not in cls._registry:
            raise ValueError(f"No client class registered for {dcc_name}")
        return cls._registry[dcc_name]
    
    @classmethod
    def list_supported_dccs(cls) -> list:
        """List all supported DCC applications.
        
        Returns:
            A list of supported DCC application names
        """
        return list(cls._registry.keys())
