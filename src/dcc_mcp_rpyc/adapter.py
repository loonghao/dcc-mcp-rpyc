"""DCC Adapter module for DCC-MCP-RPYC.

This module provides abstract base classes and utilities for creating DCC adapters
that can be used with the MCP server. It defines the common interface that all
DCC adapters should implement.
"""

# Import built-in modules
from abc import ABC
from abc import abstractmethod
import logging
from typing import Any
from typing import Dict
from typing import Optional

# Import third-party modules
from dcc_mcp_core.actions.manager import create_action_manager
from dcc_mcp_core.actions.manager import get_action_manager
from dcc_mcp_core.models import ActionResultModel

# Import local modules
from dcc_mcp_rpyc.client import BaseDCCClient

# Configure logging
logger = logging.getLogger(__name__)


class DCCAdapter(ABC):
    """Abstract base class for DCC adapters.

    This class provides a common interface for adapting DCC-specific functionality
    to the MCP protocol. It handles connection to the DCC application, action
    discovery and management, and function execution.

    Attributes
    ----------
        dcc_name: Name of the DCC application
        client: Client instance for communicating with the DCC application
        action_manager: Manager for actions in the DCC application
        action_paths: List of paths to search for actions

    """

    def __init__(self, dcc_name: str) -> None:
        """Initialize the DCC adapter.

        Args:
        ----
            dcc_name: Name of the DCC application

        """
        self.dcc_name = dcc_name
        self.client: Optional[BaseDCCClient] = None
        self.action_manager = None
        self.action_paths: list = []

        # Initialize the client
        self._initialize_client()

        # Initialize the action manager
        self.action_manager = self._create_action_manager(self.dcc_name)

        # Initialize action paths
        self._initialize_action_paths()

    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize the client for communicating with the DCC application.

        This method should be implemented by subclasses to initialize the client
        for the specific DCC application.

        """

    @abstractmethod
    def _initialize_action_paths(self) -> None:
        """Initialize the paths to search for actions.

        This method should be implemented by subclasses to initialize the paths
        to search for actions for the specific DCC application.

        """

    def ensure_connected(self) -> None:
        """Ensure that the client is connected to the DCC application.

        If the client is not connected, this method will attempt to reconnect.

        Raises
        ------
            ConnectionError: If the client cannot connect to the DCC application

        """
        if self.client is None:
            self._initialize_client()

        if not self.client.is_connected():
            logger.info(f"Reconnecting to {self.dcc_name}...")
            try:
                self.client.connect()
            except Exception as e:
                logger.error(f"Failed to connect to {self.dcc_name}: {e}")
                raise ConnectionError(f"Failed to connect to {self.dcc_name}: {e}")

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session.

        Returns
        -------
            Dict with session information

        """
        self.ensure_connected()

        try:
            # Get session info from the DCC application
            result = self.client.root.get_session_info()
            return ActionResultModel(
                success=True, message="Successfully retrieved session information", context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return ActionResultModel(
                success=False, message="Failed to retrieve session information", error=str(e)
            ).model_dump()

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        self.ensure_connected()

        try:
            # Get scene info from the DCC application
            result = self.client.root.get_scene_info()
            return ActionResultModel(
                success=True, message="Successfully retrieved scene information", context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error getting scene info: {e}")
            return ActionResultModel(
                success=False, message="Failed to retrieve scene information", error=str(e)
            ).model_dump()

    def get_actions(self) -> Dict[str, Any]:
        """Get all available actions for the DCC application.

        Returns
        -------
            Dict with action information

        """
        self.ensure_connected()

        try:
            # Get actions from the DCC application
            result = self.client.root.get_actions()
            return ActionResultModel(
                success=True,
                message=f"Successfully retrieved {len(result) if isinstance(result, dict) else 0} actions",
                context=result,
            ).model_dump()
        except Exception as e:
            logger.error(f"Error getting actions: {e}")
            return ActionResultModel(success=False, message="Failed to retrieve actions", error=str(e)).model_dump()

    def call_action_function(
        self, action_name: str, function_name: str, context: Dict[str, Any], *args, **kwargs
    ) -> Dict[str, Any]:
        """Call an action function in the DCC application.

        Args:
        ----
            action_name: Name of the action
            function_name: Name of the function to call
            context: Context provided by the MCP server
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
        -------
            Dict with the result of the function execution and session info

        """
        try:
            # Ensure connection to the DCC application
            self.ensure_connected()

            # Call the action function through the action manager
            result = self._call_action_function(self.dcc_name, action_name, function_name, context, *args, **kwargs)

            # Get session info to include in the response
            try:
                session_info = self.get_session_info()
            except Exception as e:
                logger.warning(f"Failed to get session info: {e}")
                session_info = {"success": False, "context": {}, "error": str(e)}

            # If result is already an ActionResultModel, use it directly
            if hasattr(result, "model_dump") and callable(getattr(result, "model_dump")):
                result_dict = result.model_dump()
            elif isinstance(result, dict) and all(k in result for k in ["success", "message", "context"]):
                # If result has the structure of an ActionResultModel but is a dict, convert it
                result_dict = result
            else:
                # Otherwise, wrap the result in an ActionResultModel
                result_dict = ActionResultModel(
                    success=True,
                    message=f"Successfully executed {action_name}.{function_name}",
                    context={"raw_result": result},
                ).model_dump()

            # Create a combined result with session info
            combined_result = ActionResultModel(
                success=result_dict.get("success", True),
                message=result_dict.get("message", f"Executed {action_name}.{function_name}"),
                prompt=result_dict.get("prompt"),
                error=result_dict.get("error"),
                context={
                    "function_result": result_dict.get("context", {}),
                    "session_info": session_info.get("context", {}),
                },
            ).model_dump()

            return combined_result
        except Exception as e:
            logger.error(f"Error calling action function: {e}")
            logger.exception("Detailed exception information:")
            return ActionResultModel(
                success=False,
                message=f"Failed to execute {action_name}.{function_name}",
                error=str(e),
                context={"action": action_name, "function": function_name},
            ).model_dump()

    def _create_action_manager(self, dcc_name, action_manager_creator=None, fallback_manager_getter=None):
        """Create an action manager for the DCC application.

        This method should be implemented by subclasses to create an action manager
        for the specific DCC application.

        Args:
        ----
            dcc_name: Name of the DCC application
            action_manager_creator: Optional function to create an action manager
                                        (default: None, uses create_action_manager)
            fallback_manager_getter: Optional function to get a fallback action manager
                                        (default: None, uses self._get_action_manager)

        Returns:
        -------
            Action manager instance

        """
        # Use provided functions or defaults
        creator_func = action_manager_creator or create_action_manager
        fallback_func = fallback_manager_getter or self._get_action_manager

        # Try to import from dcc_mcp_core first
        try:
            return creator_func(dcc_name)
        except ImportError:
            # Fallback to local implementation
            return fallback_func(dcc_name)

    def _get_action_manager(self, dcc_name, action_manager_getter=None):
        """Get an action manager for the DCC application.

        This method should be implemented by subclasses to get an action manager
        for the specific DCC application.

        Args:
        ----
            dcc_name: Name of the DCC application
            action_manager_getter: Optional function to get an action manager
                                        (default: None, uses get_action_manager)

        Returns:
        -------
            Action manager instance

        """
        getter_func = action_manager_getter or get_action_manager

        try:
            return getter_func(dcc_name)
        except ImportError:
            logger.warning("Could not import get_action_manager from dcc_mcp_core")
            return None

    def _call_action_function(self, dcc_name, action_name, function_name, context, *args, **kwargs):
        """Call an action function in the DCC application.

        Args:
        ----
            dcc_name: Name of the DCC application
            action_name: Name of the action
            function_name: Name of the function to call
            context: Context provided by the MCP server
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
        -------
            Result of the function execution

        """
        # Since dcc_mcp_core.actions.manager does not have call_action_function function
        # We directly use action_manager to call function
        try:
            if self.action_manager is None:
                self.action_manager = self._create_action_manager(dcc_name)

            # Use action_manager to call function
            if hasattr(self.action_manager, "call_function"):
                return self.action_manager.call_function(action_name, function_name, context, *args, **kwargs)
            else:
                # Fallback to direct call
                logger.warning("Action manager does not have call_function method, falling back to direct call")
                return self.client.root.call_action_function(action_name, function_name, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error calling action function: {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to call {action_name}.{function_name}",
                error=str(e),
                context={"action": action_name, "function": function_name},
            ).model_dump()
