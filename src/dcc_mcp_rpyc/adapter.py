"""DCC Adapter module for DCC-MCP-RPYC.

This module provides abstract base classes and utilities for creating DCC adapters
that can be used with the MCP server. It defines the common interface that all
DCC adapters should implement.
"""

# Import built-in modules
from abc import ABC
from abc import abstractmethod
import logging
import time
from typing import Any
from typing import Dict
from typing import Optional

# Import third-party modules
from dcc_mcp_core.plugin_manager import call_plugin_function
from dcc_mcp_core.plugin_manager import get_plugin_manager
from dcc_mcp_core.plugin_manager import get_plugins_info

# Import local modules
from dcc_mcp_rpyc.client import BaseDCCClient

# Setup logging
logger = logging.getLogger(__name__)


class DCCAdapter(ABC):
    """Abstract base class for DCC adapters.

    This class defines the common interface that all DCC adapters should implement.
    It provides methods for connecting to a DCC application and executing commands.
    """

    def __init__(self, host: str = "localhost", port: Optional[int] = None, timeout: int = 5):
        """Initialize DCC adapter.

        Args:
        ----
            host: Host where the DCC RPYC server is running
            port: Port number of the DCC RPYC server. If None, it will be discovered automatically.
            timeout: Connection timeout in seconds

        """
        logger.info(f"Initializing {self.__class__.__name__} with host={host}, port={port}, timeout={timeout}")
        self.host = host
        self.port = port
        self.timeout = timeout
        self.dcc_client = None
        self.last_connection_check = 0
        self.connection_check_interval = 20  # seconds
        self.dcc_name = self.__class__.__name__.replace("Adapter", "").lower()

        # Initialize the client
        self._initialize_client()

        # Initialize the plugin manager
        self.plugin_manager = get_plugin_manager(self.dcc_name)

    def _initialize_client(self):
        """Initialize the DCC client.

        This method creates a new DCCClient instance and connects to the DCC application.
        """
        self.dcc_client = self._create_client()

    @abstractmethod
    def _create_client(self) -> BaseDCCClient:
        """Create a DCC client instance.

        This method should be implemented by subclasses to create a specific
        DCCClient instance for their DCC application.

        Returns
        -------
            BaseDCCClient: A BaseDCCClient instance

        """

    def is_connected(self) -> bool:
        """Check if the adapter is connected to the DCC application.

        Returns
        -------
            bool: True if connected, False otherwise

        """
        if self.dcc_client is None:
            return False
        return self.dcc_client.is_connected()

    def ensure_connected(self) -> bool:
        """Ensure that we have a connection to the DCC application.

        This method checks if the connection is still valid and reconnects if necessary.

        Returns
        -------
            bool: True if connected, False otherwise

        """
        # Check if we need to refresh the connection
        current_time = time.time()
        if current_time - self.last_connection_check > self.connection_check_interval:
            logger.debug("Connection check interval reached, checking connection status")
            self.last_connection_check = current_time

            # Check if the client is connected
            if not self.is_connected():
                logger.warning("Client is not connected, attempting to reconnect")
                return self.dcc_client.reconnect()

        return True

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        self.ensure_connected()
        try:
            # Call the get_scene_info function on the DCC client
            return self.dcc_client.call("get_scene_info")
        except Exception as e:
            logger.error(f"Error getting scene info: {e}")
            return {"error": str(e)}

    def get_plugins_info(self) -> Dict[str, Any]:
        """Get information about available plugins.

        Returns
        -------
            Dict with plugin information

        """
        return get_plugins_info(self.dcc_name)

    def call_plugin_function(
        self, plugin_name: str, function_name: str, context: Dict[str, Any], *args, **kwargs
    ) -> Dict[str, Any]:
        """Call a plugin function in the DCC application.

        Args:
        ----
            plugin_name: Name of the plugin
            function_name: Name of the function to call
            context: Context provided by the MCP server
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
        -------
            Dict with the result of the function execution and scene info

        """
        self.ensure_connected()

        try:
            # Call the plugin function through the plugin manager
            result = call_plugin_function(self.dcc_name, plugin_name, function_name, context, *args, **kwargs)

            # Get scene info to include in the response
            scene_info = self.get_scene_info()

            # Return result with scene info
            return {"result": result, "scene_info": scene_info}
        except Exception as e:
            logger.error(f"Error calling plugin function: {e}")
            logger.exception("Detailed exception information:")
            return {"error": str(e), "scene_info": self.get_scene_info()}
