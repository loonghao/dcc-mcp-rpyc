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
from typing import Any

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

    def _discover_service(
        self,
        dcc_name: str,
        use_zeroconf: bool = False,
        registry_path: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[int]]:
        """Discover a service for the specified application.
        
        This method attempts to discover a service for the specified application
        using ZeroConf (if enabled) and file-based discovery strategies.
        
        Args:
            dcc_name: Name of the application
            use_zeroconf: Whether to use ZeroConf for service discovery
            registry_path: Path to the service registry file
            
        Returns:
            Tuple of (host, port) if discovered, (None, None) otherwise
        """
        host = None
        port = None
        
        # Attempt to discover services using ZeroConf if enabled
        if use_zeroconf:
            logger.info(f"Attempting to discover {dcc_name} service using ZeroConf...")
            try:
                strategy = ZeroConfDiscoveryStrategy()
                services = strategy.discover_services(dcc_name)
                if services:
                    # Use the first matching service
                    service = services[0]
                    host = service.host
                    port = service.port
                    logger.info(f"Discovered {dcc_name} service at {host}:{port} using ZeroConf")
                    # If ZeroConf discovery is successful, return immediately
                    return host, port
            except Exception as e:
                logger.error(f"Error discovering {dcc_name} service using ZeroConf: {e}")

        # Attempt to discover services using file-based discovery as a fallback
        logger.info(f"Attempting to discover {dcc_name} service using file-based discovery...")
        try:
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
        except Exception as e:
            logger.error(f"Error discovering {dcc_name} service using file-based discovery: {e}")
            
        return host, port
    
    def get_client(
        self,
        dcc_name: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        auto_connect: bool = True,
        connection_timeout: float = 5.0,
        registry_path: Optional[str] = None,
        use_zeroconf: bool = False,
    ) -> Any:
        """Get a client for a specific application.

        This method returns a client for the specified application. If a client
        already exists for the specified application, host, and port, it is returned.
        Otherwise, a new client is created and added to the pool.

        Args:
            dcc_name: Name of the application
            host: Host of the application server
            port: Port of the application server
            auto_connect: Whether to automatically connect to the server
            connection_timeout: Connection timeout in seconds
            registry_path: Path to the service registry file
            use_zeroconf: Whether to use ZeroConf for service discovery

        Returns:
            A client for the specified application

        Raises:
            ValueError: If the application is not supported
            ConnectionError: If the connection to the server fails
        """
        # First attempt to discover service if host or port is not specified
        if host is None or port is None:
            discovered_host, discovered_port = self._discover_service(
                dcc_name, use_zeroconf, registry_path
            )
            host = discovered_host or host
            port = discovered_port or port
            
        # If still unable to determine host and port, raise an error
        if host is None or port is None:
            raise ValueError(f"Could not discover {dcc_name} service")
            
        # Get the client class for the application
        client_class = self.get_client_class(dcc_name)

        # Create a key for the client in the pool
        key = (dcc_name.lower(), host, port)

        # Check if the client already exists in the pool
        if key in self.pool:
            client, timestamp = self.pool[key]

            # Check if the client is still valid
            if self._is_client_valid(client):
                # Update last used time
                self.pool[key] = (client, time.time())
                logger.debug(f"Reusing existing client for {dcc_name} at {host}:{port}")
                return client

            # Remove the client from the pool
            logger.debug(f"Removing invalid client for {dcc_name} at {host}:{port}")
            del self.pool[key]

        # Create a new client
        try:
            # First try using app_name parameter
            client = client_class(
                app_name=dcc_name,
                host=host,
                port=port,
                auto_connect=auto_connect,
                connection_timeout=connection_timeout,
                registry_path=registry_path,
            )
        except TypeError:
            # 如果失败，尝试使用 dcc_name 参数
            try:
                client = client_class(
                    dcc_name=dcc_name,
                    host=host,
                    port=port,
                    auto_connect=auto_connect,
                    connection_timeout=connection_timeout,
                    registry_path=registry_path,
                )
            except TypeError:
                # 如果仍然失败，记录警告并尝试不使用应用名称参数
                logger.warning(f"{client_class.__name__} does not accept app_name or dcc_name parameter")
                client = client_class(
                    host=host,
                    port=port,
                    auto_connect=auto_connect,
                    connection_timeout=connection_timeout,
                    registry_path=registry_path,
                )

        # Add the client to the pool with the current timestamp
        self.pool[key] = (client, time.time())

        return client

    def get_client_class(self, dcc_name: str) -> Type[BaseDCCClient]:
        """Get the client class for a specific application.

        Args:
            dcc_name: Name of the application

        Returns:
            The client class for the specified application

        Raises:
            ValueError: If the application is not supported
        """
        from dcc_mcp_rpyc.client.registry import ClientRegistry
        return ClientRegistry.get_client_class(dcc_name)

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

    def cleanup_idle_connections(self) -> None:
        """Clean up idle connections.

        This method removes connections that have been idle for too long.

        """
        now = time.time()
        to_remove = []

        # Find connections to remove
        for key, (client, timestamp) in self.pool.items():
            if now - timestamp > self.max_idle_time:
                to_remove.append(key)
                logger.debug(f"Marking idle connection for removal: {key}")

        # Remove connections
        for key in to_remove:
            client, _ = self.pool[key]
            try:
                if hasattr(client, "close") and callable(client.close):
                    client.close()
                    logger.debug(f"Closed idle connection: {key}")
            except Exception as e:
                logger.debug(f"Error closing client {key}: {e}")
            del self.pool[key]

        # Log cleanup summary
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} idle connection(s)")

        # Update last cleanup time
        self.last_cleanup = now

    def _is_client_valid(self, client: Any) -> bool:
        """Check if a client is still valid.

        This method checks if a client is still valid by verifying its connection
        and attempting a simple operation.

        Args:
            client: The client to check

        Returns:
            True if the client is still valid, False otherwise

        """
        # Check if the client is still connected
        try:
            if hasattr(client, "is_connected") and callable(client.is_connected):
                if not client.is_connected():
                    logger.debug(f"Client {client} is not connected")
                    return False

                # Try to execute a simple operation to verify the connection
                try:
                    # Attempt to ping or get a simple property
                    if hasattr(client, "ping") and callable(client.ping):
                        client.ping()
                    elif hasattr(client.connection, "ping") and callable(client.connection.ping):
                        client.connection.ping()
                    # Connection is valid
                    return True
                except Exception as e:
                    logger.debug(f"Error verifying client connection: {e}")
                    return False
            return True
        except Exception as e:
            logger.debug(f"Error checking if client {client} is connected: {e}")
            return False


# Global connection pool
_connection_pool = ConnectionPool()


def get_client(
    dcc_name: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    auto_connect: bool = True,
    connection_timeout: float = 5.0,
    registry_path: Optional[str] = None,
    use_zeroconf: bool = False,
) -> Any:
    """Get a client from the global connection pool.

    Args:
        dcc_name: Name of the DCC to connect to
        host: Host of the DCC RPYC server (default: None, auto-discover)
        port: Port of the DCC RPYC server (default: None, auto-discover)
        auto_connect: Whether to automatically connect (default: True)
        connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
        registry_path: Optional path to the registry file (default: None)
        use_zeroconf: Whether to use ZeroConf for service discovery (default: False)

    Returns:
        A client instance for the specified DCC

    """
    global _connection_pool

    # Check if we need to clean up idle connections
    current_time = time.time()
    if current_time - _connection_pool.last_cleanup > _connection_pool.cleanup_interval:
        _connection_pool.cleanup_idle_connections()

    # Get a client from the pool
    return _connection_pool.get_client(
        dcc_name=dcc_name,
        host=host,
        port=port,
        auto_connect=auto_connect,
        connection_timeout=connection_timeout,
        registry_path=registry_path,
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
