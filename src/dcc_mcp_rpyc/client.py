"""RPYC client implementation for connecting to DCC software.

This module provides utilities for connecting to DCC RPYC servers and executing
remote calls with connection management, timeout handling, and automatic reconnection.
"""

# Import built-in modules
import logging
import os
from typing import Any
from typing import Callable
from typing import ClassVar
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Type

# Import third-party modules
import rpyc

# Import local modules
from dcc_mcp_rpyc import discovery

# Configure logging
logger = logging.getLogger(__name__)

__all__ = ["BaseDCCClient", "ClientRegistry", "ConnectionPool"]


class BaseDCCClient:
    """Base client for connecting to DCC RPYC servers.

    This class provides common functionality for connecting to DCC RPYC servers and
    executing remote calls with connection management, timeout handling, and automatic reconnection.
    """

    def __init__(
        self,
        dcc_name: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        auto_connect: bool = True,
        connection_timeout: float = 5.0,
        registry_path: Optional[str] = None,
    ):
        """Initialize the client.

        Args:
        ----
            dcc_name: Name of the DCC to connect to
            host: Host of the DCC RPYC server (default: None, auto-discover)
            port: Port of the DCC RPYC server (default: None, auto-discover)
            auto_connect: Whether to automatically connect (default: True)
            connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
            registry_path: Optional path to the registry file (default: None)

        """
        self.dcc_name = dcc_name.lower()
        self.host = host
        self.port = port
        self.connection = None
        self.connection_timeout = connection_timeout
        self.registry_path = registry_path

        # Auto-discover host and port if not provided
        if (self.host is None or self.port is None) and auto_connect:
            self._discover_service()

        # Auto-connect if requested
        if auto_connect and self.host and self.port:
            self.connect()

    def _discover_service(self) -> Tuple[Optional[str], Optional[int]]:
        """Discover the host and port of the DCC RPYC server.

        Returns
        -------
            Tuple of (host, port) if discovered, (None, None) otherwise

        """
        try:
            logger.info(f"Discovering {self.dcc_name} service...")

            # Method 1: Discover services using the discovery module
            services = discovery.discover_services(self.dcc_name, self.registry_path)
            if services:
                latest_service = discovery.get_latest_service(services)
                self.port = latest_service.get("port")
                self.host = latest_service.get("host", self.host or "localhost")
                logger.info(f"Discovered {self.dcc_name} service at {self.host}:{self.port}")
                return self.host, self.port

            # Method 2: Find services directly from registry files
            registry_files = discovery.find_service_registry_files(self.dcc_name, self.registry_path)
            if not registry_files:
                logger.warning(f"No {self.dcc_name} service discovered")
                return None, None

            # Get the most recent registry file
            latest_registry_file = max(registry_files, key=os.path.getmtime)

            try:
                # Load registry file and get service information
                registry_data = discovery._load_registry_file(latest_registry_file)
                dcc_services = registry_data.get(self.dcc_name.lower(), [])

                if not dcc_services:
                    logger.warning(f"No services found for {self.dcc_name} in registry file")
                    return None, None

                # Get the most recent service information
                latest_service = discovery.get_latest_service(dcc_services)
                self.port = latest_service.get("port")
                self.host = latest_service.get("host", self.host or "localhost")

                logger.info(f"Found {self.dcc_name} service at {self.host}:{self.port} from registry file")
                return self.host, self.port
            except Exception as e:
                logger.warning(f"Error reading registry file: {e}")
                return None, None

        except Exception as e:
            logger.error(f"Error discovering {self.dcc_name} service: {e}")
            return None, None

    def connect(self, rpyc_connect_func=None) -> bool:
        """Connect to the DCC RPYC server.

        Args:
        ----
            rpyc_connect_func: Optional function to use for connecting (default: None, uses rpyc.connect)

        Returns:
        -------
            True if connected successfully, False otherwise

        """
        if self.is_connected():
            logger.info(f"Already connected to {self.dcc_name} service at {self.host}:{self.port}")
            return True

        if not self.host or not self.port:
            logger.warning(f"Cannot connect to {self.dcc_name} service: host or port not specified")
            return False

        # Use provided connect function or default to rpyc.connect
        connect_func = rpyc_connect_func or rpyc.connect

        try:
            logger.info(f"Connecting to {self.dcc_name} service at {self.host}:{self.port}")
            self.connection = connect_func(
                self.host, self.port, config={"sync_request_timeout": self.connection_timeout}
            )

            # Check if the connection is valid by trying to ping the server
            if not self.is_connected():
                logger.error(f"Failed to establish a valid connection to {self.dcc_name} service")
                self.connection = None
                return False

            logger.info(f"Connected to {self.dcc_name} service at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to {self.dcc_name} service at {self.host}:{self.port}: {e}")
            self.connection = None
            return False

    def disconnect(self) -> bool:
        """Disconnect from the DCC RPYC server.

        Returns
        -------
            True if disconnected successfully, False otherwise

        """
        if not self.connection:
            return True

        try:
            logger.info(f"Disconnecting from {self.dcc_name} service at {self.host}:{self.port}")
            self.connection.close()
            self.connection = None
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from {self.dcc_name} service: {e}")
            self.connection = None
            return False

    def reconnect(self) -> bool:
        """Reconnect to the DCC RPYC server.

        Returns
        -------
            True if reconnected successfully, False otherwise

        """
        self.disconnect()
        return self.connect()

    def is_connected(self) -> bool:
        """Check if the client is connected to the server.

        Returns
        -------
            bool: True if connected, False otherwise

        """
        if self.connection is None:
            return False
        try:
            # Try to ping the server
            # ping() returns None on success, raises an exception on failure
            self.connection.ping()
            return True
        except Exception:
            return False

    def echo(self, message: str) -> str:
        """Echo a message back from the server.

        This method is useful for testing the connection to the server.

        Args:
        ----
            message: The message to echo

        Returns:
        -------
            The echoed message

        Raises:
        ------
            ConnectionError: If not connected to the server

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.dcc_name} service")

        try:
            return self.connection.root.exposed_echo(message)
        except Exception as e:
            logger.error(f"Error echoing message: {e}")
            self.disconnect()
            raise

    def execute_command(self, cmd_name: str, *args, **kwargs) -> Any:
        """Execute a command on the DCC RPYC server.

        Args:
        ----
            cmd_name: Name of the command to execute
            *args: Positional arguments to pass to the command
            **kwargs: Keyword arguments to pass to the command

        Returns:
        -------
            The result of the command execution

        Raises:
        ------
            ConnectionError: If not connected to the server
            AttributeError: If the command doesn't exist
            Exception: If the command execution fails

        """
        if not self.is_connected():
            if not self.reconnect():
                raise ConnectionError(f"Not connected to {self.dcc_name} service")

        try:
            # Get the command from the root object
            command = getattr(self.connection.root, cmd_name)

            # Execute the command
            return command(*args, **kwargs)
        except AttributeError:
            logger.error(f"Command '{cmd_name}' not found on {self.dcc_name} service")
            raise
        except Exception as e:
            logger.error(f"Error executing command '{cmd_name}' on {self.dcc_name} service: {e}")
            raise

    def call(self, method_name: str, *args, **kwargs) -> Any:
        """Call a method on the DCC RPYC server.

        This is a convenience method that calls execute_command with the
        appropriate method name prefix.

        Args:
        ----
            method_name: Name of the method to call
            *args: Positional arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method

        Returns:
        -------
            The result of the method call

        Raises:
        ------
            ConnectionError: If not connected to the server
            AttributeError: If the method doesn't exist
            Exception: If the method call fails

        """
        # Ensure we're connected
        self.ensure_connected()

        # Call the method using execute_command
        return self.execute_command(f"exposed_{method_name}", *args, **kwargs)

    def ensure_connected(self) -> None:
        """Ensure the client is connected to the server.

        If not connected, try to reconnect.

        Raises
        ------
            ConnectionError: If not connected and cannot reconnect

        """
        if not self.is_connected():
            if not self.reconnect():
                raise ConnectionError(f"Not connected to {self.dcc_name} service")

    def __enter__(self):
        """Enter context manager.

        Returns
        -------
            The client instance

        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager.

        Args:
        ----
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback

        """
        self.disconnect()


def create_client(
    dcc_name: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    auto_connect: bool = True,
    connection_timeout: float = 5.0,
    client_class: Type[BaseDCCClient] = BaseDCCClient,
    registry_path: Optional[str] = None,
) -> BaseDCCClient:
    """Create a client for a specific DCC.

    Args:
    ----
        dcc_name: Name of the DCC to connect to
        host: Host of the DCC RPYC server (default: None, auto-discover)
        port: Port of the DCC RPYC server (default: None, auto-discover)
        auto_connect: Whether to automatically connect (default: True)
        connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
        client_class: The client class to instantiate (default: BaseDCCClient)
        registry_path: Optional path to the registry file (default: None)

    Returns:
    -------
        A client instance for the specified DCC

    """
    return client_class(
        dcc_name=dcc_name.lower(),
        host=host,
        port=port,
        auto_connect=auto_connect,
        connection_timeout=connection_timeout,
        registry_path=registry_path,
    )


# Client registry for custom client classes
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
    def register(cls, dcc_name: str, client_class: Type[BaseDCCClient]) -> None:
        """Register a client class for a DCC.

        Args:
        ----
            dcc_name: Name of the DCC to register the client class for
            client_class: The client class to register

        """
        cls._registry[dcc_name.lower()] = client_class
        logger.debug(f"Registered client class {client_class.__name__} for DCC {dcc_name}")

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
        client_class = cls._registry.get(dcc_name.lower(), BaseDCCClient)
        logger.debug(f"Using client class {client_class.__name__} for DCC {dcc_name}")
        return client_class


# Connection pool for reusing connections
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
        host: Optional[str] = None,
        port: Optional[int] = None,
        auto_connect: bool = True,
        connection_timeout: float = 5.0,
        registry_path: Optional[str] = None,
        client_class: Optional[Type[BaseDCCClient]] = None,
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
        dcc_name = dcc_name.lower()

        # Try to get an existing client from the pool
        client = self._get_existing_client(dcc_name, host, port)
        if client:
            return client

        # Create a new client
        client = self._create_new_client(
            dcc_name, host, port, auto_connect, connection_timeout, registry_path, client_class, client_factory
        )

        # Try again to get an existing client with the resolved host and port
        # This handles the case where auto-discovery was used
        client = self._get_existing_client(dcc_name, client.host, client.port) or client

        # Add the new client to the pool if it's not already there
        if client not in self.pool.values():
            self.pool[(dcc_name, client.host, client.port)] = client
            logger.debug(f"Added new connection to {dcc_name} at {client.host}:{client.port} to pool")

        return client

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
        if host is not None and port is not None:
            key = (dcc_name, host, port)
            if key in self.pool:
                pooled_client = self.pool[key]
                # Check if the pooled client is still connected
                if pooled_client.is_connected():
                    logger.debug(f"Using pooled connection to {dcc_name} at {host}:{port}")
                    return pooled_client
                else:
                    # Remove the stale connection from the pool
                    logger.debug(f"Removing stale connection to {dcc_name} from pool")
                    del self.pool[key]
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
        # Get the client class from the registry if not specified
        if client_class is None:
            client_class = ClientRegistry.get_client_class(dcc_name)

        # Use the provided factory or the default create_client function
        factory = client_factory or create_client

        # Create a new client
        return factory(
            dcc_name,
            host,
            port,
            auto_connect,
            connection_timeout,
            client_class=client_class,
            registry_path=registry_path,
        )

    def release_client(self, client: BaseDCCClient) -> None:
        """Release a client back to the pool.

        Args:
        ----
            client: The client to release

        """
        # Nothing to do, the client is already in the pool

    def close_all(self) -> None:
        """Close all connections in the pool."""
        for client in self.pool.values():
            client.disconnect()

        self.pool.clear()
        logger.info("Closed all connections in the pool")


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
        dcc_name, host, port, auto_connect, connection_timeout, registry_path, client_class, client_factory
    )


def close_all_connections() -> None:
    """Close all connections in the global connection pool."""
    _connection_pool.close_all()
