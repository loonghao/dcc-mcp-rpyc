"""Factory functions for DCC-MCP-RPYC servers.

This module provides factory functions for creating and managing RPYC servers
for DCC applications.
"""

# Import built-in modules
import logging
import threading
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Type

# Import third-party modules
import rpyc
from rpyc.utils.server import ThreadedServer

# Import local modules
from dcc_mcp_rpyc.server.base import BaseRPyCService
from dcc_mcp_rpyc.server.dcc import DCCServer
from dcc_mcp_rpyc.server.discovery import unregister_dcc_service
from dcc_mcp_rpyc.server.server_utils import create_raw_threaded_server

# Configure logging
logger = logging.getLogger(__name__)


def create_dcc_server(
    dcc_name: str,
    service_class: Type[BaseRPyCService],
    host: str = "localhost",
    port: Optional[int] = None,
    protocol_config: Optional[Dict[str, Any]] = None,
    registry_path: Optional[str] = None,
    use_zeroconf: bool = False,
) -> DCCServer:
    """Create a DCC server.

    Args:
        dcc_name: Name of the DCC application
        service_class: Service class to use
        host: Host to bind to
        port: Port to bind to
        protocol_config: Protocol configuration
        registry_path: Path to the registry file
        use_zeroconf: Whether to use ZeroConf for service discovery (default: False)

    Returns:
        A DCC server instance

    """
    server = create_raw_threaded_server(
        service_class=service_class,
        hostname=host,
        port=port,
        protocol_config=protocol_config,
    )

    return DCCServer(
        dcc_name=dcc_name,
        service_class=service_class,
        host=host,
        port=port,
        server=server,
        protocol_config=protocol_config,
        registry_path=registry_path,
        use_zeroconf=use_zeroconf,
    )


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
