"""Base client module for DCC-MCP-RPYC.

This module provides the base client class for connecting to application RPYC servers and executing
remote calls with connection management, timeout handling, and automatic reconnection.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import List

# Import third-party modules
import rpyc

# Import local modules
from dcc_mcp_rpyc.discovery import FileDiscoveryStrategy
from dcc_mcp_rpyc.discovery import ServiceRegistry
from dcc_mcp_rpyc.discovery import ZEROCONF_AVAILABLE
from dcc_mcp_rpyc.discovery import ZeroConfDiscoveryStrategy
from dcc_mcp_rpyc.discovery.base import ServiceInfo
from dcc_mcp_rpyc.utils import execute_remote_command as _execute_remote_command

# Configure logging
logger = logging.getLogger(__name__)


class BaseApplicationClient:
    """Base client for connecting to application RPYC servers.

    This class provides common functionality for connecting to any application with a Python environment
    via RPYC servers and executing remote calls with connection management, timeout handling,
    and automatic reconnection.
    """

    def __init__(
        self,
        app_name: str,
        host: Optional[Optional[str]] = None,
        port: Optional[Optional[int]] = None,
        auto_connect: bool = True,
        connection_timeout: float = 5.0,
        registry_path: Optional[Optional[str]] = None,
        use_zeroconf: bool = True,
    ):
        """Initialize the client.

        Args:
        ----
            app_name: Name of the application to connect to
            host: Host of the application RPYC server (default: None, auto-discover)
            port: Port of the application RPYC server (default: None, auto-discover)
            auto_connect: Whether to automatically connect (default: True)
            connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
            registry_path: Optional path to the registry file (default: None)
            use_zeroconf: Whether to use ZeroConf for service discovery (default: True)

        """
        self.app_name = app_name.lower()
        self.host = host
        self.port = port
        self.connection = None
        self.connection_timeout = connection_timeout
        self.registry_path = registry_path
        self.use_zeroconf = use_zeroconf and ZEROCONF_AVAILABLE

        # Auto-discover host and port if not provided
        if (self.host is None or self.port is None) and auto_connect:
            self._discover_service()

        # Auto-connect if requested
        if auto_connect and self.host and self.port:
            self.connect()

    def _discover_service(self) -> Tuple[Optional[str], Optional[int]]:
        """Discover the host and port of the application RPYC server.

        This method attempts to discover a service of the specified application type.
        If multiple services are found, it will use the first one by default.
        For more control over service selection, use get_available_dcc_instances().

        Returns
        -------
            Tuple of (host, port) if discovered, (None, None) otherwise

        """
        try:
            logger.info(f"Discovering {self.app_name} service...")

            # Get all available services
            services = self.get_available_services()
            
            # If services found, use the first one
            if services:
                service = services[0]  # Use the first discovered service
                self.port = service.port
                self.host = service.host
                logger.info(f"Discovered {self.app_name} service at {self.host}:{self.port}")
                return self.host, self.port
            
            # If no services found
            logger.warning(f"No {self.app_name} service discovered")
            return None, None

        except Exception as e:
            logger.error(f"Error discovering {self.app_name} service: {e}")
            return None, None

    def get_available_services(self) -> List[ServiceInfo]:
        """Get all available services for the application type.

        This method attempts to discover all services of the specified application type
        using both ZeroConf and file-based discovery strategies.

        Returns
        -------
            List of ServiceInfo objects for the discovered services

        """
        services = []
        registry = ServiceRegistry()

        # Try ZeroConf discovery first if available
        if self.use_zeroconf:
            logger.info(f"Attempting to discover {self.app_name} service using ZeroConf...")
            strategy = registry.ensure_strategy("zeroconf")
            
            # Find services
            zeroconf_services = registry.discover_services("zeroconf", self.app_name)
            if zeroconf_services:
                services.extend(zeroconf_services)
                logger.info(f"Discovered {len(zeroconf_services)} {self.app_name} service(s) using ZeroConf")

        # Try file-based discovery
        logger.info(f"Attempting to discover {self.app_name} service using file-based discovery...")
        strategy = registry.ensure_strategy("file", registry_path=self.registry_path)
        
        # Find services
        file_services = registry.discover_services("file", self.app_name)
        if file_services:
            # Add only services that aren't already in the list
            for service in file_services:
                if not any(s.host == service.host and s.port == service.port for s in services):
                    services.append(service)
            logger.info(f"Discovered {len(file_services)} {self.app_name} service(s) using file-based discovery")

        return services

    def get_available_dcc_instances(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all available DCC instances grouped by DCC type.

        This method performs a service discovery using all registered strategies
        and returns a dictionary of DCC instances grouped by DCC type.

        Returns
        -------
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
        registry = ServiceRegistry()
        
        # Ensure we have both file and zeroconf strategies registered
        registry.ensure_strategy("file", registry_path=self.registry_path)
        if self.use_zeroconf:
            registry.ensure_strategy("zeroconf")
            
        # Get available DCC instances
        return registry.get_available_dcc_instances(refresh=True)

    def connect_to_instance(self, instance_info: Dict[str, Any]) -> bool:
        """Connect to a specific DCC instance.

        Args:
        ----
            instance_info: Dictionary with instance information (must contain 'host' and 'port')

        Returns:
        -------
            True if connected successfully, False otherwise

        """
        if not instance_info or 'host' not in instance_info or 'port' not in instance_info:
            logger.error("Invalid instance information: missing host or port")
            return False

        self.host = instance_info['host']
        self.port = instance_info['port']
        return self.connect()

    def connect(self, rpyc_connect_func=None) -> bool:
        """Connect to the application RPYC server.

        Args:
        ----
            rpyc_connect_func: Optional function to use for connecting (default: None, uses rpyc.connect)

        Returns:
        -------
            True if connected successfully, False otherwise

        """
        if self.is_connected():
            logger.info(f"Already connected to {self.app_name} service at {self.host}:{self.port}")
            return True

        if not self.host or not self.port:
            logger.warning(f"Cannot connect to {self.app_name} service: host or port not specified")
            return False

        # Use provided connect function or default to rpyc.connect
        connect_func = rpyc_connect_func or rpyc.connect

        try:
            logger.info(f"Connecting to {self.app_name} service at {self.host}:{self.port}")
            self.connection = connect_func(
                self.host, self.port, config={"sync_request_timeout": self.connection_timeout}
            )

            # Check if the connection is valid by trying to ping the server
            if not self.is_connected():
                logger.error(f"Failed to establish a valid connection to {self.app_name} service")
                self.connection = None
                return False

            logger.info(f"Connected to {self.app_name} service at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to {self.app_name} service at {self.host}:{self.port}: {e}")
            self.connection = None
            return False

    def disconnect(self) -> bool:
        """Disconnect from the application RPYC server.

        Returns
        -------
            True if disconnected successfully, False otherwise

        """
        if not self.connection:
            return True

        try:
            logger.info(f"Disconnecting from {self.app_name} service at {self.host}:{self.port}")
            self.connection.close()
            self.connection = None
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from {self.app_name} service: {e}")
            self.connection = None
            return False

    def reconnect(self) -> bool:
        """Reconnect to the application RPYC server.

        Returns
        -------
            True if reconnected successfully, False otherwise

        """
        self.disconnect()
        return self.connect()

    def is_connected(self) -> bool:
        """Check if the client is connected to the application server.

        Returns
        -------
            True if connected, False otherwise

        """
        return self.connection is not None and not getattr(self.connection, "closed", True)

    def ping(self) -> bool:
        """Ping the server to check if the connection is still alive.
        
        Returns
        -------
            True if the ping was successful, False otherwise
            
        """
        if not self.is_connected():
            return False
            
        try:
            # Try to ping the connection
            if hasattr(self.connection, "ping"):
                self.connection.ping()
                return True
                
            # If no ping method, try to access a simple property
            self.connection.root.get_service_info()
            return True
        except Exception as e:
            logger.debug(f"Ping failed: {e}")
            return False

    def execute_remote_command(self, command: str, *args, **kwargs) -> Any:
        """Execute a remote command on the application RPYC server.

        Args:
        ----
            command: Command to execute
            *args: Positional arguments to pass to the command
            **kwargs: Keyword arguments to pass to the command

        Returns:
        -------
            Result of the command execution

        Raises:
        ------
            ConnectionError: If the client is not connected to the application RPYC server
            Exception: If the command execution fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.app_name} service")

        try:
            # Use the execute_remote_command function to execute the command
            return _execute_remote_command(self.connection, command, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error executing remote command {command}: {e}")
            raise

    def execute_python(self, code: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Execute Python code in the application's environment.

        Args:
        ----
            code: Python code to execute
            context: Optional context dictionary to use during execution

        Returns:
        -------
            Result of the code execution

        Raises:
        ------
            ConnectionError: If the client is not connected to the application RPYC server
            Exception: If the code execution fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.app_name} service")

        try:
            return self.connection.root.exposed_execute_python(code, context or {})
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            raise

    def import_module(self, module_name: str) -> Any:
        """Import a module in the application's environment.

        Args:
        ----
            module_name: Name of the module to import

        Returns:
        -------
            The imported module

        Raises:
        ------
            ConnectionError: If the client is not connected to the application RPYC server
            Exception: If the module import fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.app_name} service")

        try:
            return self.connection.root.exposed_get_module(module_name)
        except Exception as e:
            logger.error(f"Error importing module {module_name}: {e}")
            raise

    def call_function(self, module_name: str, function_name: str, *args, **kwargs) -> Any:
        """Call a function in the application's environment.

        Args:
        ----
            module_name: Name of the module containing the function
            function_name: Name of the function to call
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
        -------
            Result of the function call

        Raises:
        ------
            ConnectionError: If the client is not connected to the application RPYC server
            Exception: If the function call fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.app_name} service")

        try:
            return self.connection.root.exposed_call_function(module_name, function_name, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error calling function {module_name}.{function_name}: {e}")
            raise

    def get_application_info(self) -> Dict[str, Any]:
        """Get information about the application.

        Returns
        -------
            Dict with application information

        Raises:
        ------
            ConnectionError: If the client is not connected to the application RPYC server
            Exception: If getting application information fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.app_name} service")

        try:
            return self.connection.root.get_application_info()
        except Exception as e:
            logger.error(f"Error getting application info: {e}")
            raise

    def get_environment_info(self) -> Dict[str, Any]:
        """Get information about the Python environment.

        Returns
        -------
            Dict with environment information

        Raises:
        ------
            ConnectionError: If the client is not connected to the application RPYC server
            Exception: If getting environment information fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.app_name} service")

        try:
            return self.connection.root.get_environment_info()
        except Exception as e:
            logger.error(f"Error getting environment info: {e}")
            raise

    def list_actions(self) -> Dict[str, Any]:
        """List all available actions in the application.

        Returns
        -------
            Dict with action information

        Raises:
        ------
            ConnectionError: If the client is not connected to the application RPYC server
            Exception: If listing actions fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.app_name} service")

        try:
            return self.connection.root.exposed_list_actions()
        except Exception as e:
            logger.error(f"Error listing actions: {e}")
            raise

    def call_action(self, action_name: str, **kwargs) -> Any:
        """Call an action in the application.

        Args:
        ----
            action_name: Name of the action to call
            **kwargs: Arguments for the action

        Returns:
        -------
            Result of the action call

        Raises:
        ------
            ConnectionError: If the client is not connected to the application RPYC server
            Exception: If the action call fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.app_name} service")

        try:
            return self.connection.root.exposed_call_action(action_name, **kwargs)
        except Exception as e:
            logger.error(f"Error calling action {action_name}: {e}")
            raise

    @property
    def root(self) -> Any:
        """Get the root object of the RPYC connection.

        Returns
        -------
            Root object of the RPYC connection

        Raises
        ------
            ConnectionError: If the client is not connected to the application RPYC server

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.app_name} service")

        return self.connection.root


# Global client registry to track all created clients
_clients = {}


def get_client(
    app_name: str, host: Optional[Optional[str]] = None, port: Optional[Optional[int]] = None, **kwargs
) -> BaseApplicationClient:
    """Get a client for the specified application.

    This function creates a new client or returns an existing one from the registry.

    Args:
    ----
        app_name: Name of the application to connect to
        host: Host of the application RPYC server (default: None, auto-discover)
        port: Port of the application RPYC server (default: None, auto-discover)
        **kwargs: Additional arguments to pass to the client constructor

    Returns:
    -------
        A client for the specified application

    """
    # Create a unique key for this client configuration
    key = (app_name, host, port)

    # Check if we already have a client for this configuration
    if key in _clients:
        client = _clients[key]
        # If the client is not connected, try to reconnect
        if not client.is_connected():
            try:
                client.connect()
            except Exception as e:
                logger.warning(f"Failed to reconnect to {app_name}: {e}")
        return client

    # Create a new client
    client = BaseApplicationClient(app_name, host, port, **kwargs)
    _clients[key] = client
    return client


def close_all_connections():
    """Close all client connections.

    This function closes all client connections in the registry.
    """
    for client in _clients.values():
        try:
            client.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting client: {e}")
    _clients.clear()
