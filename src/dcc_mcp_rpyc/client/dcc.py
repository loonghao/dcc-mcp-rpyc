"""DCC client module for DCC-MCP-RPYC.

This module provides the DCC client class for connecting to DCC RPYC servers and executing
remote calls with connection management, timeout handling, and automatic reconnection.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Dict

# Import local modules
from dcc_mcp_rpyc.client.base import BaseApplicationClient

logger = logging.getLogger(__name__)


class BaseDCCClient(BaseApplicationClient):
    """Base client for connecting to DCC RPYC servers.

    This class provides common functionality for connecting to DCC RPYC servers and
    executing remote calls with connection management, timeout handling, and automatic reconnection.
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
        ----
            dcc_name: Name of the DCC to connect to
            host: Host of the DCC RPYC server (default: None, auto-discover)
            port: Port of the DCC RPYC server (default: None, auto-discover)
            auto_connect: Whether to automatically connect (default: True)
            connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
            registry_path: Optional path to the registry file (default: None)

        """
        super().__init__(dcc_name, host, port, auto_connect, connection_timeout, registry_path)
        self.dcc_name = dcc_name.lower()

    def get_dcc_info(self) -> Dict[str, Any]:
        """Get information about the DCC application.

        Returns
        -------
            Dictionary with DCC information

        Raises
        ------
            ConnectionError: If the client is not connected to the DCC RPYC server
            Exception: If getting DCC information fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.dcc_name} RPYC server")

        try:
            return self.connection.root.get_dcc_info()
        except Exception as e:
            logger.error(f"Failed to get DCC info from {self.dcc_name}: {e}")
            raise

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        Raises
        ------
            ConnectionError: If the client is not connected to the DCC RPYC server
            Exception: If getting scene information fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.dcc_name} RPYC server")

        try:
            return self.connection.root.get_scene_info()
        except Exception as e:
            logger.error(f"Failed to get scene info from {self.dcc_name}: {e}")
            raise

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session.

        Returns
        -------
            Dict with session information

        Raises
        ------
            ConnectionError: If the client is not connected to the DCC RPYC server
            Exception: If getting session information fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.dcc_name} RPYC server")

        try:
            return self.connection.root.get_session_info()
        except Exception as e:
            logger.error(f"Failed to get session info from {self.dcc_name}: {e}")
            raise

    def execute_python(self, code: str) -> Any:
        """Execute Python code in the DCC application.

        Args:
        ----
            code: Python code to execute

        Returns:
        -------
            Result of the Python code execution

        Raises:
        ------
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
        ----
            command: DCC-specific command to execute

        Returns:
        -------
            Result of the command execution

        Raises:
        ------
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

    def create_primitive(self, primitive_type: str, **kwargs) -> Any:
        """Create a primitive object in the DCC application.

        Args:
        ----
            primitive_type: Type of primitive to create
            **kwargs: Additional arguments for the primitive creation

        Returns:
        -------
            Created primitive object or identifier

        Raises:
        ------
            ConnectionError: If the client is not connected to the DCC RPYC server
            Exception: If creating the primitive fails

        """
        if not self.is_connected():
            raise ConnectionError(f"Not connected to {self.dcc_name} RPYC server")

        try:
            return self.connection.root.create_primitive(primitive_type, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create primitive in {self.dcc_name}: {e}")
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
