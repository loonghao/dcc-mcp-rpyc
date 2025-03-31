"""Base client module for DCC-MCP-RPYC.

This module provides the base client class for connecting to application RPYC servers and executing
remote calls with connection management, timeout handling, and automatic reconnection.
"""

# Import built-in modules
import logging
import os
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

# Import third-party modules
import rpyc

# Import local modules
from dcc_mcp_rpyc.utils import discover_services
from dcc_mcp_rpyc.utils import execute_remote_command as _execute_remote_command
from dcc_mcp_rpyc.utils import find_service_registry_files
from dcc_mcp_rpyc.utils import get_latest_service
from dcc_mcp_rpyc.utils.discovery import _load_registry_file

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

        """
        self.app_name = app_name.lower()
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
        """Discover the host and port of the application RPYC server.

        Returns
        -------
            Tuple of (host, port) if discovered, (None, None) otherwise

        """
        try:
            logger.info(f"Discovering {self.app_name} service...")

            # Method 1: Discover services using the discovery module
            services = discover_services(self.app_name, self.registry_path)
            if services:
                latest_service = get_latest_service(services)
                self.port = latest_service.get("port")
                self.host = latest_service.get("host", self.host or "localhost")
                logger.info(f"Discovered {self.app_name} service at {self.host}:{self.port}")
                return self.host, self.port

            # Method 2: Find services directly from registry files
            registry_files = find_service_registry_files(self.app_name, self.registry_path)
            if not registry_files:
                logger.warning(f"No {self.app_name} service discovered")
                return None, None

            # Get the most recent registry file
            latest_registry_file = max(registry_files, key=os.path.getmtime)

            try:
                # Load registry file and get service information
                registry_data = _load_registry_file(latest_registry_file)
                app_services = registry_data.get(self.app_name.lower(), [])

                if not app_services:
                    logger.warning(f"No services found for {self.app_name} in registry file")
                    return None, None

                # Get the most recent service information
                latest_service = get_latest_service(app_services)
                self.port = latest_service.get("port")
                self.host = latest_service.get("host", self.host or "localhost")

                logger.info(f"Found {self.app_name} service at {self.host}:{self.port} from registry file")
                return self.host, self.port
            except Exception as e:
                logger.warning(f"Error reading registry file: {e}")
                return None, None

        except Exception as e:
            logger.error(f"Error discovering {self.app_name} service: {e}")
            return None, None

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
        """Check if the client is connected to the application RPYC server.

        Returns
        -------
            True if connected, False otherwise

        """
        if not self.connection:
            return False

        try:
            # Try to ping the server to check if the connection is still alive
            self.connection.ping()
            return True
        except Exception:
            self.connection = None
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

        Raises
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

        Raises
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

        Raises
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
