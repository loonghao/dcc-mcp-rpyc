"""Base adapter classes for DCC-MCP-RPYC.

This module provides abstract base classes and utilities for creating application adapters
that can be used with the MCP server. It defines the common interface that all
application adapters should implement.
"""

# Import built-in modules
from abc import ABC
from abc import abstractmethod
import logging
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel

# Import local modules
from dcc_mcp_rpyc.action_adapter import get_action_adapter
from dcc_mcp_rpyc.client import BaseApplicationClient

# Configure logging
logger = logging.getLogger(__name__)


class ApplicationAdapter(ABC):
    """Abstract base class for application adapters.

    This class provides a common interface for adapting application-specific functionality
    to the MCP protocol. It handles connection to the application, action
    discovery and management, and function execution.

    This is the root class in the adapter hierarchy. Specific adapter types should
    inherit from this class and implement the required abstract methods.

    Hierarchy:
    - ApplicationAdapter (abstract base class)
      - DCCAdapter (for DCC applications requiring remote connections)
      - GenericApplicationAdapter (for local Python environments)

    Attributes:
        app_name: Name of the application
        client: Client instance for communicating with the application
        action_adapter: Adapter for managing actions
        _action_paths: List of paths to search for actions

    """

    def __init__(self, app_name: str) -> None:
        """Initialize the application adapter.

        Args:
            app_name: Name of the application

        """
        self.app_name = app_name
        self.client: Optional[BaseApplicationClient] = None
        self._action_paths = []

        # Initialize the action adapter
        self.action_adapter = get_action_adapter(self.app_name)

        # Initialize the client
        self._initialize_client()

        # Initialize action paths
        self._initialize_action_paths()

    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize the client for communicating with the application.

        This method should be implemented by subclasses to initialize the client
        for the specific application.
        """

    @abstractmethod
    def _initialize_action_paths(self) -> None:
        """Initialize the paths to search for actions.

        This method should be implemented by subclasses to initialize the paths
        to search for actions for the specific application.
        """
        self.action_adapter.set_action_search_paths(self.action_paths)

    @property
    def action_paths(self) -> list:
        """Get the paths to search for actions.

        This property returns the list of paths where the adapter will search for actions.
        Subclasses should override this property to provide application-specific action paths.
        These paths can be extended in the application implementation to include additional
        directories for custom actions and plugins.

        Returns:
            List of paths to search for actions

        """
        return self._action_paths

    @action_paths.setter
    def action_paths(self, paths: list) -> None:
        """Set the paths to search for actions.

        Args:
            paths: List of paths to search for actions

        """
        self._action_paths = paths
        self.action_adapter.set_action_search_paths(paths)

    def register_action(self, action_name: str, action_func: Callable) -> None:
        """Register an action with the adapter.

        This method registers an action with the adapter, making it available for execution.

        Args:
            action_name: Name of the action
            action_func: Function to execute when the action is called

        """
        self.action_adapter.register_action(action_name, action_func)

    def get_available_actions(self) -> List[str]:
        """Get action list.

        Returns
        -------
            action list

        """
        return self.action_adapter.list_actions(names_only=True)

    def get_action_info(self, action_name: str) -> Dict[str, Any]:
        """Get information about an action.

        Args:
            action_name: Name of the action

        Returns:
            Dict with action information

        """
        return self.action_adapter.get_action_info(action_name)

    def execute_action(self, action_name: str, **kwargs) -> Dict[str, Any]:
        """Execute an action.

        Args:
            action_name: Name of the action to execute
            **kwargs: Arguments to pass to the action

        Returns:
            Dict with action execution result

        """
        try:
            result = self.action_adapter.execute_action(action_name, **kwargs)

            # If the result is already an ActionResultModel dict, return it
            if isinstance(result, dict) and "success" in result:
                return result

            # Otherwise, wrap it in an ActionResultModel
            return ActionResultModel(
                success=True, message=f"Successfully executed action {action_name}", context={"result": result}
            ).model_dump()
        except Exception as e:
            logger.error(f"Error executing action {action_name}: {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to execute action {action_name}",
                error=str(e),
                context={"action_name": action_name, "kwargs": kwargs},
            ).model_dump()

    @abstractmethod
    def get_application_info(self) -> Dict[str, Any]:
        """Get information about the application.

        Returns:
            Dict with application information

        """

    def ensure_connected(self) -> bool:
        """Ensure the adapter is connected to the application.

        Returns:
            True if connected, False otherwise

        """
        if self.client is None:
            return False

        if not self.client.is_connected():
            try:
                return self.client.connect()
            except Exception as e:
                logger.error(f"Error connecting to {self.app_name}: {e}")
                return False

        return True
