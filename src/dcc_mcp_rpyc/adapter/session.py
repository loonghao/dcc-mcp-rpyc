"""Session adapter for DCC-MCP-RPYC.

This module provides a session adapter for connecting to DCC applications and managing
session state across multiple requests.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Dict
from typing import Optional

# Import local modules
from dcc_mcp_rpyc.action_adapter import get_action_adapter
from dcc_mcp_rpyc.adapter.base import ApplicationAdapter
from dcc_mcp_rpyc.client import get_client
from dcc_mcp_rpyc.utils.decorators import with_error_handling

# Configure logging
logger = logging.getLogger(__name__)


class SessionAdapter(ApplicationAdapter):
    """Adapter for connecting to DCC applications and managing session state.

    This class provides functionality for connecting to DCC applications,
    managing session state, and executing actions and functions.

    Attributes
    ----------
        app_name: Name of the application
        client: Client instance for communicating with the application
        action_adapter: Adapter for managing actions
        session_id: Unique identifier for the session
        session_data: Dictionary containing session-specific data

    """

    def __init__(self, app_name: str, session_id: Optional[Optional[str]] = None):
        """Initialize the session adapter.

        Args:
        ----
            app_name: Name of the application
            session_id: Optional unique identifier for the session

        """
        super().__init__(app_name)
        self.session_id = session_id or f"{app_name}_session_{id(self)}"
        self.session_data = {}
        self.action_adapter = get_action_adapter(self.session_id)
        logger.debug(f"Initialized SessionAdapter for {app_name} with session ID {self.session_id}")

    def connect(self, host: Optional[Optional[str]] = None, port: Optional[Optional[int]] = None, **kwargs) -> bool:
        """Connect to the application.

        Args:
        ----
            host: Host of the application server (default: None, auto-discover)
            port: Port of the application server (default: None, auto-discover)
            **kwargs: Additional arguments for the connection

        Returns:
        -------
            True if connected successfully, False otherwise

        """
        try:
            self.client = get_client(self.app_name, host, port, **kwargs)
            self.client.connect()
            logger.info(f"Connected to {self.app_name} at {self.client.host}:{self.client.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.app_name}: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from the application.

        Returns
        -------
            True if disconnected successfully, False otherwise

        """
        if self.client and self.client.is_connected():
            try:
                self.client.disconnect()
                logger.info(f"Disconnected from {self.app_name}")
                return True
            except Exception as e:
                logger.error(f"Error disconnecting from {self.app_name}: {e}")
                return False
        return True  # Already disconnected

    def ensure_connected(self) -> bool:
        """Ensure that the adapter is connected to the application.

        Returns
        -------
            True if connected, False otherwise

        """
        if not self.client:
            return self.connect()
        if not self.client.is_connected():
            try:
                self.client.connect()
                return True
            except Exception as e:
                logger.error(f"Failed to reconnect to {self.app_name}: {e}")
                return False
        return True

    def is_connected(self) -> bool:
        """Check if the adapter is connected to the application.

        Returns
        -------
            True if connected, False otherwise

        """
        return self.client is not None and self.client.is_connected()

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session.

        Returns
        -------
            Dictionary with session information

        """
        info = {
            "session_id": self.session_id,
            "app_name": self.app_name,
            "connected": self.is_connected(),
        }

        # Add connection info if connected
        if self.is_connected():
            info["connection"] = {
                "host": self.client.host,
                "port": self.client.port,
            }

        # Add session data
        info["session_data"] = self.session_data

        return info

    def set_session_data(self, key: str, value: Any) -> None:
        """Set session data.

        Args:
        ----
            key: Key to set
            value: Value to set

        """
        self.session_data[key] = value
        logger.debug(f"Set session data {key}={value} for session {self.session_id}")

    def get_session_data(self, key: str, default: Optional[Any] = None) -> Any:
        """Get session data.

        Args:
        ----
            key: Key to get
            default: Default value to return if key is not found

        Returns:
        -------
            Value associated with the key, or default if not found

        """
        return self.session_data.get(key, default)

    def clear_session_data(self) -> None:
        """Clear all session data."""
        self.session_data.clear()
        logger.debug(f"Cleared session data for session {self.session_id}")

    def execute_python(self, code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Python code in the application's environment.

        Args:
        ----
            code: Python code to execute
            context: Optional context dictionary to use during execution

        Returns:
        -------
            Dictionary with the result of the execution

        """
        self.ensure_connected()
        try:
            if self.is_connected():
                result = self.client.call("execute_python", code, context or {})
                return {"success": True, "result": result}
            else:
                return {
                    "success": False,
                    "error": "Not connected to application",
                    "message": f"Failed to execute Python code: Not connected to {self.app_name}",
                }
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to execute Python code: {e}",
            }

    @with_error_handling
    def call_action_function(
        self, action_name: str, function_name: str, context: Optional[Dict[str, Any]] = None, *args, **kwargs
    ) -> Dict[str, Any]:
        """Call a function on an action.

        Args:
        ----
            action_name: Name of the action
            function_name: Name of the function to call
            context: Context dictionary with additional parameters
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
        -------
            Result of the action function call in ActionResultModel format

        """
        self.ensure_connected()
        try:
            # Call the call_action_function method of the DCC client
            if self.is_connected():
                return self.client.call("call_action_function", action_name, function_name, context, *args, **kwargs)
            else:
                # Return error information if not connected
                return {
                    "success": False,
                    "message": f"Failed to call action function: Not connected to {self.app_name}",
                    "prompt": "Please check the connection to the DCC application",
                    "error": f"Not connected to {self.app_name}",
                    "context": {"action_name": action_name, "function_name": function_name},
                }
        except Exception as e:
            logging.error(f"Error calling action function: {e}")
            # Return error information in ActionResultModel format
            return {
                "success": False,
                "message": f"Failed to call action function: {e}",
                "prompt": "Please check the error message and try again",
                "error": str(e),
                "context": {"action_name": action_name, "function_name": function_name},
            }
