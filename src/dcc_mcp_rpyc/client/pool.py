"""Connection pool module for DCC-MCP-RPYC.

This module provides utilities for managing connections to DCC RPYC servers,
including connection pooling and client registry.
"""

# Import built-in modules
import logging
from typing import Callable
from typing import ClassVar
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Type

# Import local modules
from dcc_mcp_rpyc.client.dcc import BaseDCCClient

# Configure logging
logger = logging.getLogger(__name__)


class ClientRegistry:
    """Registry for DCC client classes.

    This class provides a registry for custom DCC client classes that can be used
    with the connection pool. It allows registering custom client classes for
    specific DCC applications and retrieving them later.

    Attributes
    ----------
        _registry: Dictionary mapping DCC names to client classes

    """

    _registry: ClassVar[Dict[str, Type[BaseDCCClient]]] = {}

    @classmethod
    def register(cls, dcc_name: str, client_class: Type[BaseDCCClient]):
        """Register a client class for a DCC.

        Args:
        ----
            dcc_name: Name of the DCC to register the client class for
            client_class: The client class to register

        """
        cls._registry[dcc_name.lower()] = client_class
        logger.info(f"Registered client class {client_class.__name__} for {dcc_name}")

    @classmethod
    def get_client_class(cls, dcc_name: str) -> Type[BaseDCCClient]:
        """Get the client class for a DCC.

        Args:
        ----
            dcc_name: Name of the DCC to get the client class for

        Returns:
        -------
            The client class for the specified DCC, or BaseDCCClient if no custom
            client class is registered

        """
        return cls._registry.get(dcc_name.lower(), BaseDCCClient)


class ConnectionPool:
    """Pool of RPYC connections to DCC servers.

    This class provides a pool of connections to DCC RPYC servers that can be
    reused to avoid the overhead of creating new connections.

    Attributes
    ----------
        pool: Dictionary mapping (dcc_name, host, port) to client instances

    """

    def __init__(self):
        """Initialize the connection pool."""
        self.pool: Dict[Tuple[str, str, int], BaseDCCClient] = {}

    def get_client(
        self,
        dcc_name: str,
        host: Optional[Optional[str]] = None,
        port: Optional[Optional[int]] = None,
        auto_connect: bool = True,
        connection_timeout: float = 5.0,
        registry_path: Optional[Optional[str]] = None,
        client_class: Optional[Optional[Type[BaseDCCClient]]] = None,
        client_factory: Optional[Callable[..., BaseDCCClient]] = None,
    ) -> BaseDCCClient:
        """Get a client from the pool or create a new one.

        Args:
        ----
            dcc_name: Name of the DCC to connect to
            host: Host of the DCC RPYC server (default: None, auto-discover)
            port: Port of the DCC RPYC server (default: None, auto-discover)
            auto_connect: Whether to automatically connect (default: True)
            connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
            registry_path: Optional path to the registry file (default: None)
            client_class: Optional client class to use (default: None, use registry)
            client_factory: Optional factory function to create clients (default: None, use create_client)

        Returns:
        -------
            A client instance for the specified DCC

        """
        # Normalize DCC name
        dcc_name = dcc_name.lower()

        # Try to get an existing client from the pool
        client = self._get_existing_client(dcc_name, host, port)
        if client is not None:
            return client

        # Create a new client
        return self._create_new_client(
            dcc_name,
            host,
            port,
            auto_connect,
            connection_timeout,
            registry_path,
            client_class,
            client_factory,
        )

    def _get_existing_client(self, dcc_name: str, host: Optional[str], port: Optional[int]) -> Optional[BaseDCCClient]:
        """Get an existing client from the pool if available.

        Args:
        ----
            dcc_name: Name of the DCC to connect to
            host: Host of the DCC RPYC server
            port: Port of the DCC RPYC server

        Returns:
        -------
            An existing client instance or None if not found

        """
        # Normalize DCC name
        dcc_name = dcc_name.lower()

        # Check if we have a client for the specified DCC, host, and port
        for (pool_dcc, pool_host, pool_port), client in self.pool.items():
            if pool_dcc == dcc_name and (host is None or pool_host == host) and (port is None or pool_port == port):
                # Check if the client is still connected
                if client.is_connected():
                    logger.info(f"Using existing client for {dcc_name} at {pool_host}:{pool_port}")
                    return client
                else:
                    # Remove the disconnected client from the pool
                    logger.info(f"Removing disconnected client for {dcc_name} at {pool_host}:{pool_port}")
                    del self.pool[(pool_dcc, pool_host, pool_port)]
                    break

        return None

    def _create_new_client(
        self,
        dcc_name: str,
        host: Optional[str],
        port: Optional[int],
        auto_connect: bool,
        connection_timeout: float,
        registry_path: Optional[str],
        client_class: Optional[Type[BaseDCCClient]],
        client_factory: Optional[Callable[..., BaseDCCClient]],
    ) -> BaseDCCClient:
        """Create a new client instance.

        Args:
        ----
            dcc_name: Name of the DCC to connect to
            host: Host of the DCC RPYC server
            port: Port of the DCC RPYC server
            auto_connect: Whether to automatically connect
            connection_timeout: Timeout for connection attempts in seconds
            registry_path: Optional path to the registry file
            client_class: Optional client class to use
            client_factory: Optional factory function to create clients

        Returns:
        -------
            A new client instance

        """
        # Normalize DCC name
        dcc_name = dcc_name.lower()

        # Use provided client class or get from registry
        if client_class is None:
            client_class = ClientRegistry.get_client_class(dcc_name)

        # Use provided factory or create client directly
        if client_factory is not None:
            client = client_factory(
                dcc_name,
                host=host,
                port=port,
                auto_connect=auto_connect,
                connection_timeout=connection_timeout,
                registry_path=registry_path,
            )
        else:
            client = client_class(
                dcc_name,
                host=host,
                port=port,
                auto_connect=auto_connect,
                connection_timeout=connection_timeout,
                registry_path=registry_path,
            )

        # Add the client to the pool if it's connected
        if client.is_connected():
            self.pool[(dcc_name, client.host, client.port)] = client
            logger.info(f"Added new client for {dcc_name} at {client.host}:{client.port} to the pool")

        return client

    def release_client(self, client: BaseDCCClient):
        """Release a client back to the pool.

        Args:
        ----
            client: The client to release

        """
        # Check if the client is still connected
        if client.is_connected():
            # Add the client to the pool
            self.pool[(client.app_name, client.host, client.port)] = client
            logger.info(f"Released client for {client.app_name} at {client.host}:{client.port} back to the pool")
        else:
            # Close the client if it's disconnected
            client.disconnect()
            logger.info(f"Closed disconnected client for {client.app_name}")

    def close_all(self):
        """Close all connections in the pool."""
        for (dcc_name, host, port), client in list(self.pool.items()):
            try:
                client.disconnect()
                logger.info(f"Closed client for {dcc_name} at {host}:{port}")
            except Exception as e:
                logger.error(f"Error closing client for {dcc_name} at {host}:{port}: {e}")

        # Clear the pool
        self.pool.clear()
        logger.info("Cleared connection pool")


# Global connection pool
_connection_pool = ConnectionPool()


def get_client(
    dcc_name: str,
    host: Optional[Optional[str]] = None,
    port: Optional[Optional[int]] = None,
    auto_connect: bool = True,
    connection_timeout: float = 5.0,
    registry_path: Optional[Optional[str]] = None,
    client_class: Optional[Optional[Type[BaseDCCClient]]] = None,
    client_factory: Optional[Callable[..., BaseDCCClient]] = None,
) -> BaseDCCClient:
    """Get a client from the global connection pool.

    Args:
    ----
        dcc_name: Name of the DCC to connect to
        host: Host of the DCC RPYC server (default: None, auto-discover)
        port: Port of the DCC RPYC server (default: None, auto-discover)
        auto_connect: Whether to automatically connect (default: True)
        connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
        registry_path: Optional path to the registry file (default: None)
        client_class: Optional client class to use (default: None, use registry)
        client_factory: Optional factory function to create clients (default: None, use create_client)

    Returns:
    -------
        A client instance for the specified DCC

    """
    return _connection_pool.get_client(
        dcc_name,
        host=host,
        port=port,
        auto_connect=auto_connect,
        connection_timeout=connection_timeout,
        registry_path=registry_path,
        client_class=client_class,
        client_factory=client_factory,
    )


def close_all_connections():
    """Close all connections in the global connection pool."""
    _connection_pool.close_all()
