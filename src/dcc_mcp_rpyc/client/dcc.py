"""DCC client module for DCC-MCP-RPYC.

This module provides the DCC client class for connecting to DCC RPYC servers and executing
remote calls with connection management, timeout handling, and automatic reconnection.
"""

# Import built-in modules
from contextlib import contextmanager
import logging
from typing import Any
from typing import Callable
from typing import Dict
from typing import TypeVar

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel

# Import local modules
from dcc_mcp_rpyc.client.base import BaseApplicationClient

logger = logging.getLogger(__name__)

# Type variable for the return type of execute_with_connection
T = TypeVar("T")


class BaseDCCClient(BaseApplicationClient):
    """Base client for connecting to DCC RPYC servers.

    This class provides common functionality for connecting to DCC RPYC servers and
    executing remote calls with connection management, timeout handling, and automatic reconnection.

    It extends BaseApplicationClient with DCC-specific functionality such as scene management,
    session information, and primitive creation.

    Attributes:
        dcc_name: Name of the DCC application
        connection: Active RPYC connection

    """

    def __init__(
        self,
        dcc_name: str,
        host=None,
        port=None,
        auto_connect=True,
        connection_timeout=5.0,
        registry_path=None,
    ):
        """Initialize the client.

        Args:
            dcc_name: Name of the DCC to connect to
            host: Host of the DCC RPYC server (default: None, auto-discover)
            port: Port of the DCC RPYC server (default: None, auto-discover)
            auto_connect: Whether to automatically connect (default: True)
            connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
            registry_path: Optional path to the registry file (default: None)

        """
        super().__init__(dcc_name, host, port, auto_connect, connection_timeout, registry_path)
        self.dcc_name = dcc_name.lower()

    @contextmanager
    def ensure_connection(self):
        """Context manager to ensure the client is connected.

        This context manager ensures the client is connected before executing code
        within its scope. If the client is not connected, it attempts to connect.

        Raises:
            ConnectionError: If the client cannot connect

        Yields:
            The active connection

        """
        if not self.is_connected():
            if not self.connect():
                raise ConnectionError(f"Failed to connect to {self.dcc_name} service")

        try:
            yield self.connection
        except Exception as e:
            logger.error(f"Error during connection to {self.dcc_name}: {e}")
            raise

    def execute_with_connection(self, func: Callable[[Any], T]) -> T:
        """Execute a function with an ensured connection.

        This method ensures the client is connected before executing the provided function.
        It handles connection errors and provides a consistent interface for remote calls.

        Args:
            func: Function to execute with the connection as its argument

        Returns:
            Result of the function

        Raises:
            ConnectionError: If the client cannot connect
            Exception: If the function execution fails

        """
        with self.ensure_connection() as connection:
            return func(connection)

    def get_dcc_info(self) -> Dict[str, Any]:
        """Get information about the DCC application.

        Returns:
            Dictionary with DCC information

        Raises:
            ConnectionError: If the client is not connected to the DCC RPYC server
            Exception: If getting DCC information fails

        """
        return self.execute_with_connection(lambda conn: conn.root.get_dcc_info())

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns:
            Dict with scene information

        Raises:
            ConnectionError: If the client is not connected to the DCC RPYC server
            Exception: If getting scene information fails

        """
        return self.execute_with_connection(lambda conn: conn.root.get_scene_info())

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session.

        Returns:
            Dict with session information

        Raises:
            ConnectionError: If the client is not connected to the DCC RPYC server
            Exception: If getting session information fails

        """
        return self.execute_with_connection(lambda conn: conn.root.get_session_info())

    def create_primitive(self, primitive_type: str, **kwargs) -> Dict[str, Any]:
        """Create a primitive object in the DCC application.

        Args:
            primitive_type: Type of primitive to create
            **kwargs: Additional arguments for the primitive creation

        Returns:
            Result of the primitive creation as an ActionResultModel dict

        Raises:
            ConnectionError: If the client is not connected to the DCC RPYC server

        """
        try:
            return self.execute_with_connection(lambda conn: conn.root.create_primitive(primitive_type, **kwargs))
        except Exception as e:
            # Return a structured error response
            return ActionResultModel(
                success=False,
                message=f"Failed to create {primitive_type}",
                error=str(e),
                context={"primitive_type": primitive_type, "kwargs": kwargs},
            ).model_dump()

    def execute_command(self, command: str, *args, **kwargs) -> Dict[str, Any]:
        """Execute a command in the DCC application.

        Args:
            command: Command to execute
            *args: Positional arguments for the command
            **kwargs: Keyword arguments for the command

        Returns:
            Result of the command execution as an ActionResultModel dict

        Raises:
            ConnectionError: If the client is not connected to the DCC RPYC server

        """
        try:
            return self.execute_with_connection(lambda conn: conn.root.execute_command(command, *args, **kwargs))
        except Exception as e:
            # Return a structured error response
            return ActionResultModel(
                success=False,
                message=f"Failed to execute command: {command}",
                error=str(e),
                context={"command": command, "args": args, "kwargs": kwargs},
            ).model_dump()

    def execute_script(self, script: str, script_type: str = "python") -> Dict[str, Any]:
        """Execute a script in the DCC application.

        Args:
            script: Script to execute
            script_type: Type of script (default: "python")

        Returns:
            Result of the script execution as an ActionResultModel dict

        Raises:
            ConnectionError: If the client is not connected to the DCC RPYC server

        """
        try:
            return self.execute_with_connection(lambda conn: conn.root.execute_script(script, script_type))
        except Exception as e:
            # Return a structured error response
            return ActionResultModel(
                success=False,
                message=f"Failed to execute {script_type} script",
                error=str(e),
                context={"script_type": script_type, "script_length": len(script)},
            ).model_dump()

    def execute_python(self, code: str) -> Any:
        """Execute Python code in the DCC application.

        Args:
            code: Python code to execute

        Returns:
            Result of the Python code execution

        Raises:
            ConnectionError: If the client is not connected to the DCC RPYC server
            Exception: If executing the Python code fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.dcc_name} RPYC server")

        try:
            return self.connection.root.execute_python(code)
        except Exception as e:
            logger.error(f"Failed to execute Python code in {self.dcc_name}: {e}")
            raise

    def execute_dcc_command(self, command: str) -> Any:
        """Execute a DCC-specific command.

        Args:
            command: DCC-specific command to execute

        Returns:
            Result of the command execution

        Raises:
            ConnectionError: If the client is not connected to the DCC RPYC server
            Exception: If executing the command fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.dcc_name} RPYC server")

        try:
            return self.connection.root.execute_dcc_command(command)
        except Exception as e:
            logger.error(f"Failed to execute DCC command in {self.dcc_name}: {e}")
            raise

    def close(self):
        """Close the connection to the DCC RPYC server.

        This method disconnects from the DCC RPYC server if connected.
        It is recommended to call this method when you are done with the client
        to free up resources.
        """
        if self.is_connected():
            logger.debug(f"Closing connection to {self.dcc_name} RPYC server")
            self.disconnect()
        else:
            logger.debug(f"No active connection to {self.dcc_name} RPYC server to close")
