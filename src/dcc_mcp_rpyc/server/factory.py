"""Factory functions for DCC-MCP-RPYC servers.

This module provides factory functions for creating and managing RPYC servers
for DCC applications.
"""

# Import built-in modules
import logging
import os
import threading
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Type

# Import third-party modules
import rpyc
from rpyc.core import service
from rpyc.utils.server import ThreadedServer

# Import local modules
from dcc_mcp_rpyc.server.base import BaseRPyCService
from dcc_mcp_rpyc.server.dcc import DCCServer
from dcc_mcp_rpyc.utils import register_service
from dcc_mcp_rpyc.utils import unregister_service

# Configure logging
logger = logging.getLogger(__name__)


def register_dcc_service(dcc_name: str, host: str, port: int) -> str:
    """Register a DCC service for discovery.

    This function registers a DCC service with the discovery service,
    making it discoverable by clients.

    Args:
    ----
        dcc_name: The name of the DCC
        host: The hostname of the server
        port: The port the server is running on

    Returns:
    -------
        The path to the registry file

    """
    return register_service(dcc_name, host, port)


def unregister_dcc_service(
    registry_file: Optional[Optional[str]] = None, registry_path: Optional[Optional[str]] = None
) -> bool:
    """Unregister a DCC service.

    This function unregisters a DCC service from the discovery service.

    Args:
    ----
        registry_file: The path to the registry file or DCC name (deprecated, kept for compatibility)
        registry_path: Optional alternative registry path

    Returns:
    -------
        True if successful, False otherwise

    """
    try:
        # Handle registry_file parameter
        if registry_file is not None:
            # Check if registry_file is a path
            if os.path.exists(registry_file):
                try:
                    # Try to extract DCC name from registry file
                    # Import local modules
                    from dcc_mcp_rpyc.utils import _load_registry_file

                    registry_data = _load_registry_file(registry_file)
                    dcc_names = list(registry_data.keys())
                    if dcc_names:
                        dcc_name = dcc_names[0]
                    else:
                        dcc_name = "unknown_dcc"
                        logger.warning(f"Could not extract DCC name from registry file, using {dcc_name}")

                    return unregister_service(dcc_name, registry_path=registry_path)
                except Exception as e:
                    logger.error(f"Error loading registry file: {e}")
                    return False
            # Check if registry_file is a DCC name
            elif not any(sep in registry_file for sep in ["/", "\\"]):
                dcc_name = registry_file
                return unregister_service(dcc_name, registry_path=registry_path)

        # If we cannot determine the DCC name, use the default value
        dcc_name = "unknown_dcc"
        return unregister_service(dcc_name, registry_path=registry_path)
    except Exception as e:
        logger.error(f"Error unregistering service: {e}")
        return False


def cleanup_server(
    server_instance: Optional[ThreadedServer],
    registry_file: Optional[str],
    timeout: float = 5.0,
    server_closer: Optional[Callable[[Any], None]] = None,
) -> bool:
    """Clean up a server instance and unregister its service.

    This function stops a server and unregisters its service from the discovery service.

    Args:
    ----
        server_instance: The server instance to stop
        registry_file: The path to the registry file
        timeout: Timeout for cleanup operations in seconds (default: 5.0)
        server_closer: Optional custom function to close the server (default: None)

    Returns:
    -------
        True if successful, False otherwise

    """
    success = True

    # Stop the server if it exists
    if server_instance is not None:
        try:
            # Use provided closer function or default to close()
            if server_closer is not None:
                server_closer(server_instance)
            else:
                server_instance.close()

            logger.info("Server stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            success = False

    # Unregister the service if a registry file is provided
    if registry_file is not None:
        try:
            # Unregister with a timeout
            unregister_thread = threading.Thread(target=unregister_dcc_service, args=(registry_file,))
            unregister_thread.daemon = True
            unregister_thread.start()
            unregister_thread.join(timeout)

            if unregister_thread.is_alive():
                logger.warning("Timeout while unregistering service")
                success = False
            else:
                logger.info("Service unregistered successfully")
        except Exception as e:
            logger.error(f"Error unregistering service: {e}")
            success = False

    return success


def create_raw_threaded_server(
    service_class: Type[service.Service],
    hostname: str = "localhost",
    port: Optional[Optional[int]] = None,
    protocol_config: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
) -> ThreadedServer:
    """Create a ThreadedServer with standard configuration.

    This function creates a ThreadedServer with a standard configuration,
    reducing code duplication across the codebase.

    Args:
    ----
        service_class: The service class to use
        hostname: The hostname to bind to (default: 'localhost')
        port: The port to bind to (default: None, let OS choose)
        protocol_config: Custom protocol configuration (default: None)
        timeout: Timeout for sync requests in seconds (default: 60.0)

    Returns:
    -------
        A configured ThreadedServer instance

    """
    # Use default protocol config if not provided
    if protocol_config is None:
        protocol_config = get_rpyc_config()

    # Set sync request timeout
    protocol_config["sync_request_timeout"] = timeout

    # Create the server
    server = ThreadedServer(
        service_class,
        hostname=hostname,
        port=port,
        protocol_config=protocol_config,
        logger=logger,
    )

    return server


def create_dcc_server(
    dcc_name: str,
    service_class: Type[service.Service] = BaseRPyCService,
    host: str = "localhost",
    port: int = 0,
) -> DCCServer:
    """Create a high-level DCC RPYC server with discovery and management features.

    This function creates a DCCServer instance which provides additional
    functionality on top of the basic RPyC server, including service discovery,
    registration, and lifecycle management.

    Args:
    ----
        dcc_name: Name of the DCC to create a server for
        service_class: Service class to use (default: BaseRPyCService)
        host: Host to bind the server to (default: 'localhost')
        port: Port to bind the server to (default: 0, auto-select)

    Returns:
    -------
        A DCCServer instance

    """
    return DCCServer(dcc_name, service_class, host, port)


def create_service_factory(service_class: Type[rpyc.Service], *args, **kwargs) -> Callable[[Any], rpyc.Service]:
    """Create a factory function for a service class with bound arguments.

    This is similar to rpyc.utils.helpers.classpartial but with more flexibility
    for DCC-MCP specific needs. It allows creating a service factory that will
    instantiate the service with the provided arguments for each new connection.

    Args:
    ----
        service_class: The RPyC service class to create a factory for
        *args: Positional arguments to pass to the service constructor
        **kwargs: Keyword arguments to pass to the service constructor

    Returns:
    -------
        A factory function that creates service instances

    """

    def service_factory(conn=None):
        """Create a new instance of the service class with the bound arguments.

        Args:
        ----
            conn: Optional connection object (ignored, for compatibility with RPyC)

        Returns:
        -------
            A new service instance

        """
        try:
            return service_class(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error creating service instance: {e}")
            logger.exception("Detailed exception information:")
            raise

    # Set the factory name for better debugging
    service_factory.__name__ = f"{service_class.__name__}Factory"
    service_factory.__qualname__ = f"{service_class.__name__}Factory"
    service_factory.__doc__ = f"Factory for {service_class.__name__} instances"

    return service_factory


def create_shared_service_instance(service_class: Type[rpyc.Service], *args, **kwargs) -> Callable[[Any], rpyc.Service]:
    """Create a shared service instance that will be used for all connections.

    This function creates a single instance of the service that will be
    shared among all connections. This is useful when you want to share
    state between different connections.

    Args:
    ----
        service_class: The RPyC service class to instantiate
        *args: Positional arguments to pass to the service constructor
        **kwargs: Keyword arguments to pass to the service constructor

    Returns:
    -------
        A service instance that will be shared among all connections

    """
    # Create a single instance of the service
    try:
        service_instance = service_class(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error creating shared service instance: {e}")
        logger.exception("Detailed exception information:")
        raise

    # Create a factory function that returns the shared instance
    def service_factory(conn=None):
        """Return the shared service instance.

        Args:
        ----
            conn: Optional connection object (ignored, for compatibility with RPyC)

        Returns:
        -------
            The shared service instance

        """
        return service_instance

    # Set the factory name for better debugging
    service_factory.__name__ = f"Shared{service_class.__name__}Factory"
    service_factory.__qualname__ = f"Shared{service_class.__name__}Factory"
    service_factory.__doc__ = f"Factory for shared {service_class.__name__} instance"

    return service_factory


def get_rpyc_config(allow_all_attrs=False, allow_public_attrs=True, allow_pickle=False) -> Dict[str, Any]:
    """Get a configuration dictionary for RPyC connections.

    This function creates a configuration dictionary with common settings
    for RPyC connections in the DCC-MCP ecosystem.

    Args:
    ----
        allow_all_attrs: Whether to allow access to all attributes
        allow_public_attrs: Whether to allow access to public attributes
        allow_pickle: Whether to allow pickle serialization

    Returns:
    -------
        A configuration dictionary for RPyC connections

    """
    config = {
        "allow_all_attrs": allow_all_attrs,
        "allow_public_attrs": allow_public_attrs,
        "allow_pickle": allow_pickle,
        "sync_request_timeout": 60.0,  # 60 seconds timeout for sync requests
        "allow_getattr": True,  # Allow getattr access
        "allow_setattr": True,  # Allow setattr access
        "allow_delattr": True,  # Allow delattr access
        "allow_methods": True,  # Allow method calls
    }

    return config
