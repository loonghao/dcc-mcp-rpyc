"""Connection pool module for DCC-MCP-RPYC.

This module provides utilities for managing connections to DCC RPYC servers,
including connection pooling and client registry.
"""

# Import built-in modules
import logging
import time
from typing import Callable
from typing import ClassVar
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Type

# Import local modules
from dcc_mcp_rpyc.client.dcc import BaseDCCClient
from dcc_mcp_rpyc.discovery import FileDiscoveryStrategy
from dcc_mcp_rpyc.discovery import ServiceRegistry
from dcc_mcp_rpyc.discovery.zeroconf_strategy import ZeroConfDiscoveryStrategy

# Configure logging
logger = logging.getLogger(__name__)


class ClientRegistry:
    """Registry for DCC client classes.

    This class provides a registry for custom DCC client classes that can be used
    with the connection pool. It allows registering custom client classes for
    specific DCC applications and retrieving them later.

    Attributes:
        _registry: Dictionary mapping DCC names to client classes

    """

    _registry: ClassVar[Dict[str, Type[BaseDCCClient]]] = {}

    @classmethod
    def register(cls, dcc_name: str, client_class: Type[BaseDCCClient]):
        """Register a client class for a DCC.

        Args:
            dcc_name: Name of the DCC to register the client class for
            client_class: The client class to register

        """
        cls._registry[dcc_name.lower()] = client_class
        # Use getattr to safely get the class name, fallback to str(client_class) if not found
        class_name = getattr(client_class, "__name__", str(client_class))
        logger.info(f"Registered client class {class_name} for {dcc_name}")

    @classmethod
    def get_client_class(cls, dcc_name: str) -> Type[BaseDCCClient]:
        """Get the client class for a DCC.

        Args:
            dcc_name: Name of the DCC to get the client class for

        Returns:
            The client class for the specified DCC, or BaseDCCClient if no custom
            client class is registered

        """
        return cls._registry.get(dcc_name.lower(), BaseDCCClient)


class ConnectionPool:
    """Pool of RPYC connections to DCC servers.

    This class provides a pool of connections to DCC RPYC servers that can be
    reused to avoid the overhead of creating new connections. It also manages
    connection lifecycle, including cleanup of idle connections.

    Attributes:
        pool: Dictionary mapping (dcc_name, host, port) to (client, last_used_time)
        max_idle_time: Maximum time in seconds a connection can be idle
        cleanup_interval: Interval in seconds to clean up idle connections
        last_cleanup: Timestamp of the last cleanup operation

    """

    def __init__(self, max_idle_time: float = 300.0, cleanup_interval: float = 60.0):
        """Initialize the connection pool.

        Args:
            max_idle_time: Maximum time in seconds a connection can be idle
            cleanup_interval: Interval in seconds to clean up idle connections

        """
        self.pool: Dict[Tuple[str, str, int], Tuple[BaseDCCClient, float]] = {}
        self.max_idle_time = max_idle_time
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()

    def get_client(
        self,
        dcc_name: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        auto_connect: bool = True,
        connection_timeout: float = 5.0,
        registry_path: Optional[str] = None,
        client_class: Optional[Type[BaseDCCClient]] = None,
        client_factory: Optional[Callable[..., BaseDCCClient]] = None,
        use_zeroconf: bool = False,
    ) -> BaseDCCClient:
        """Get a client from the pool or create a new one.

        Args:
            dcc_name: Name of the DCC to connect to
            host: Host of the DCC RPYC server (default: None, auto-discover)
            port: Port of the DCC RPYC server (default: None, auto-discover)
            auto_connect: Whether to automatically connect (default: True)
            connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
            registry_path: Optional path to the registry file (default: None)
            client_class: Optional client class to use (default: None, use registry)
            client_factory: Optional factory function to create clients (default: None, use create_client)
            use_zeroconf: Whether to use ZeroConf for service discovery (default: False)

        Returns:
            A client instance for the specified DCC

        """
        # Clean up idle connections if needed
        self._cleanup_idle_connections()

        # If host and port are not specified, try to discover them
        goto_create_client = False
        if host is None or port is None:
            # First try to use ZeroConf to discover the service (if enabled)
            if use_zeroconf:
                try:
                    strategy = ZeroConfDiscoveryStrategy()
                    services = strategy.discover_services(dcc_name)
                    if services:
                        # Use the first matching service
                        service = services[0]
                        host = service.host
                        port = service.port
                        logger.info(f"Attempted to use ZeroConf to discover {dcc_name} service, address: {host}:{port}")
                        # If ZeroConf discovery is successful, skip file discovery
                        goto_create_client = True
                except Exception as e:
                    logger.warning(f"Error using ZeroConf discovery: {e}")

            # If ZeroConf discovery fails or is not enabled, fallback to file-based discovery
            if not goto_create_client and (host is None or port is None):
                # Use service registry to find service
                registry = ServiceRegistry()
                strategy = registry.get_strategy("file")
                if not strategy:
                    # If no file strategy found, create a new one
                    strategy = FileDiscoveryStrategy(registry_path=registry_path)
                    registry.register_strategy("file", strategy)

                # Discover service
                registry.discover_services("file", dcc_name)
                service_info = registry.get_service(dcc_name)

                if service_info:
                    host = service_info.host
                    port = service_info.port
                    logger.info(f"Discovered {dcc_name} service at {host}:{port} using file-based discovery")

        # Create a key for the connection pool
        key = (dcc_name.lower(), host, port)

        # Check if we already have a client for this key
        if key in self.pool:
            client, _ = self.pool[key]
            # Update last used time
            self.pool[key] = (client, time.time())

            # If the client is not connected and auto_connect is True, try to reconnect
            if auto_connect and not client.is_connected():
                try:
                    client.connect()
                except Exception as e:
                    logger.warning(f"Failed to reconnect to {dcc_name}: {e}")

            return client

        # Determine the client class to use
        if client_class is None:
            client_class = ClientRegistry.get_client_class(dcc_name)

        # Create a new client
        if client_factory is not None:
            client = client_factory(
                dcc_name=dcc_name,  # Use dcc_name instead of app_name
                host=host,
                port=port,
                auto_connect=auto_connect,
                connection_timeout=connection_timeout,
                registry_path=registry_path,
                use_zeroconf=use_zeroconf,
            )
        else:
            # Check if client_class accepts use_zeroconf parameter
            try:
                client = client_class(
                    dcc_name=dcc_name,  # Use dcc_name instead of app_name
                    host=host,
                    port=port,
                    auto_connect=auto_connect,
                    connection_timeout=connection_timeout,
                    registry_path=registry_path,
                    use_zeroconf=use_zeroconf,
                )
            except TypeError:
                # If client_class does not accept use_zeroconf parameter, do not pass it
                logger.warning(f"{client_class.__name__} does not accept use_zeroconf parameter")
                client = client_class(
                    dcc_name=dcc_name,  # Use dcc_name instead of app_name
                    host=host,
                    port=port,
                    auto_connect=auto_connect,
                    connection_timeout=connection_timeout,
                    registry_path=registry_path,
                )

        # Add the client to the pool with the current timestamp
        self.pool[key] = (client, time.time())

        return client

    def close_client(self, dcc_name: str, host: Optional[str] = None, port: Optional[int] = None) -> bool:
        """Close a client connection.

        Args:
            dcc_name: Name of the DCC
            host: Host of the DCC RPYC server (default: None)
            port: Port of the DCC RPYC server (default: None)

        Returns:
            True if the client was closed, False otherwise

        """
        key = (dcc_name.lower(), host, port)

        if key in self.pool:
            client, _ = self.pool[key]
            try:
                client.disconnect()
                del self.pool[key]
                return True
            except Exception as e:
                logger.warning(f"Error closing connection to {dcc_name}: {e}")

        return False

    def close_all_connections(self):
        """Close all connections in the pool."""
        for key, (client, _) in list(self.pool.items()):
            try:
                client.disconnect()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")

        self.pool.clear()

    def _cleanup_idle_connections(self) -> None:
        """Clean up idle connections.

        This method closes connections that have been idle for too long.
        """
        current_time = time.time()

        # Only clean up at the specified interval
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        self.last_cleanup = current_time

        # Find idle connections
        idle_keys = []
        for key, (_, last_used) in self.pool.items():
            if current_time - last_used > self.max_idle_time:
                idle_keys.append(key)

        # Close idle connections
        for key in idle_keys:
            dcc_name, host, port = key
            if self.close_client(dcc_name, host, port):
                logger.debug(f"Closed idle connection to {dcc_name}")


# Global connection pool
_connection_pool = ConnectionPool()


def get_client(
    dcc_name: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    auto_connect: bool = True,
    connection_timeout: float = 5.0,
    registry_path: Optional[str] = None,
    client_class: Optional[Type[BaseDCCClient]] = None,
    client_factory: Optional[Callable[..., BaseDCCClient]] = None,
    use_zeroconf: bool = False,
) -> BaseDCCClient:
    """Get a client from the global connection pool.

    Args:
        dcc_name: Name of the DCC to connect to
        host: Host of the DCC RPYC server (default: None, auto-discover)
        port: Port of the DCC RPYC server (default: None, auto-discover)
        auto_connect: Whether to automatically connect (default: True)
        connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
        registry_path: Optional path to the registry file (default: None)
        client_class: Optional client class to use (default: None, use registry)
        client_factory: Optional factory function to create clients (default: None, use create_client)
        use_zeroconf: Whether to use ZeroConf for service discovery (default: False)

    Returns:
        A client instance for the specified DCC

    """
    return _connection_pool.get_client(
        dcc_name=dcc_name,
        host=host,
        port=port,
        auto_connect=auto_connect,
        connection_timeout=connection_timeout,
        registry_path=registry_path,
        client_class=client_class,
        client_factory=client_factory,
        use_zeroconf=use_zeroconf,
    )


def close_client(dcc_name: str, host: Optional[str] = None, port: Optional[int] = None) -> bool:
    """Close a client connection from the global connection pool.

    Args:
        dcc_name: Name of the DCC
        host: Host of the DCC RPYC server (default: None)
        port: Port of the DCC RPYC server (default: None)

    Returns:
        True if the client was closed, False otherwise

    """
    return _connection_pool.close_client(dcc_name, host, port)


def close_all_connections():
    """Close all connections in the global connection pool."""
    _connection_pool.close_all_connections()
