"""Application client implementation for general Python environments.

This module provides a concrete implementation of the BaseApplicationClient
for connecting to any application with a Python interpreter.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Union

# Import local modules
from dcc_mcp_rpyc.client import BaseApplicationClient

# Configure logging
logger = logging.getLogger(__name__)


class ApplicationClient(BaseApplicationClient):
    """Client for connecting to an application RPYC server.

    This class provides methods for connecting to and interacting with
    a general Python application environment through RPYC.
    """

    def __init__(
        self,
        app_name: str = "python",
        host: Optional[Optional[str]] = None,
        port: Optional[Optional[int]] = None,
        auto_connect: bool = True,
        connection_timeout: float = 5.0,
        registry_path: Optional[Optional[str]] = None,
    ):
        """Initialize the application client.

        Args:
        ----
            app_name: Name of the application (default: "python")
            host: Host of the application RPYC server (default: None, auto-discover)
            port: Port of the application RPYC server (default: None, auto-discover)
            auto_connect: Whether to automatically connect (default: True)
            connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
            registry_path: Optional path to the registry file (default: None)

        """
        super().__init__(app_name, host, port, auto_connect, connection_timeout, registry_path)

    def execute_remote_call(self, func_or_name: Union[Callable, str], *args, **kwargs) -> Any:
        """Execute a remote call on the application server.

        This method can be used to execute a remote function on the application server.
        It can accept either a callable (like a lambda) or a string function name.

        Args:
        ----
            func_or_name: Function to call or name of the function to call
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
        -------
            Result of the function call

        Raises:
        ------
            ConnectionError: If the client is not connected to the application server
            Exception: If the function call fails

        """
        if not self.is_connected():
            if not self.connect():
                raise ConnectionError(f"Could not connect to {self.app_name} service")

        try:
            if callable(func_or_name):
                # If func_or_name is a callable (like a lambda), call it with the connection
                return func_or_name(self.connection)
            else:
                # If func_or_name is a string, treat it as a command name
                return self.execute_remote_command(func_or_name, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error executing remote call: {e}")
            raise

    def get_application_info(self) -> Dict[str, Any]:
        """Get information about the application.

        Returns
        -------
            Dict with application information

        Raises
        ------
            ConnectionError: If the client is not connected to the application server
            Exception: If getting application information fails

        """
        return self.execute_remote_call(lambda conn: conn.root.get_application_info())

    def get_environment_info(self) -> Dict[str, Any]:
        """Get information about the Python environment.

        Returns
        -------
            Dict with environment information

        Raises
        ------
            ConnectionError: If the client is not connected to the application server
            Exception: If getting environment information fails

        """
        return self.execute_remote_call(lambda conn: conn.root.get_environment_info())

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
            ConnectionError: If the client is not connected to the application server
            Exception: If the code execution fails

        """
        return self.execute_remote_call(lambda conn: conn.root.execute_python(code, context))

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
            ConnectionError: If the client is not connected to the application server
            Exception: If the module import fails

        """
        return self.execute_remote_call(lambda conn: conn.root.get_module(module_name))

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
            ConnectionError: If the client is not connected to the application server
            Exception: If the function call fails

        """
        return self.execute_remote_call(
            lambda conn: conn.root.call_function(module_name, function_name, *args, **kwargs)
        )

    def get_actions(self) -> Dict[str, Any]:
        """Get all available actions for the application.

        Returns
        -------
            Dict with action information

        Raises
        ------
            ConnectionError: If the client is not connected to the application server
            Exception: If getting actions fails

        """
        return self.execute_remote_call(lambda conn: conn.root.get_actions())


def connect_to_application(
    host: str = "localhost",
    port: int = 18812,
    connection_timeout: float = 5.0,
    auto_connect: bool = True,
    app_name: str = "python",
    registry_path: Optional[Optional[str]] = None,
) -> ApplicationClient:
    """Connect to an application server.

    Args:
    ----
        host: Hostname or IP address of the server (default: "localhost")
        port: Port number of the server (default: 18812)
        connection_timeout: Timeout for connecting to the server in seconds (default: 5.0)
        auto_connect: Whether to automatically connect (default: True)
        app_name: Name of the application (default: "python")
        registry_path: Optional path to the registry file (default: None)

    Returns:
    -------
        An ApplicationClient instance connected to the server

    """
    client = ApplicationClient(
        app_name=app_name,
        host=host,
        port=port,
        auto_connect=auto_connect,
        connection_timeout=connection_timeout,
        registry_path=registry_path,
    )
    return client
