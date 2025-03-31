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

    Attributes
    ----------
        app_name: Name of the application
        client: Client instance for communicating with the application
        action_adapter: Adapter for managing actions
        _action_paths: List of paths to search for actions

    """

    def __init__(self, app_name: str) -> None:
        """Initialize the application adapter.

        Args:
        ----
            app_name: Name of the application

        """
        self.app_name = app_name
        self.client: Optional[Optional[BaseApplicationClient]] = None
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

        Returns
        -------
            list: List of paths to search for actions

        """
        return self._action_paths

    @action_paths.setter
    def action_paths(self, paths: list) -> None:
        """Set the paths to search for actions.

        Args:
        ----
            paths: List of paths to search for actions

        """
        self._action_paths = paths
        if self.action_adapter:
            self.action_adapter.set_action_search_paths(paths)

    def connect(self) -> bool:
        """Connect to the application.

        This method connects to the application using the client.

        Returns
        -------
            bool: True if connected successfully, False otherwise

        """
        if self.client is None:
            self._initialize_client()

        if self.client is None:
            logger.error(f"Failed to initialize client for {self.app_name}")
            return False

        try:
            # If the client has a connect method, use it
            if hasattr(self.client, "connect") and callable(getattr(self.client, "connect")):
                return self.client.connect()
            # Otherwise, check if the client is already connected
            return self.client.is_connected() if hasattr(self.client, "is_connected") else True
        except Exception as e:
            logger.error(f"Error connecting to {self.app_name}: {e}")
            return False

    def ensure_connected(self) -> None:
        """Ensure that the client is connected to the application.

        If the client is not connected, this method will attempt to reconnect.

        Raises
        ------
            ConnectionError: If the client cannot connect to the application

        """
        if self.client is None:
            self._initialize_client()

        if not self.client.is_connected():
            logger.info(f"Reconnecting to {self.app_name}...")
            try:
                self.client.connect()
            except Exception as e:
                logger.error(f"Failed to connect to {self.app_name}: {e}")
                raise ConnectionError(f"Failed to connect to {self.app_name}: {e}")

    def get_application_info(self) -> Dict[str, Any]:
        """Get information about the application.

        Returns
        -------
            Dict with application information

        """
        self.ensure_connected()

        try:
            # Get application info from the application
            result = self.client.root.get_application_info()
            return ActionResultModel(
                success=True, message="Successfully retrieved application information", context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error getting application info: {e}")
            return ActionResultModel(
                success=False, message="Failed to retrieve application information", error=str(e)
            ).model_dump()

    def get_environment_info(self) -> Dict[str, Any]:
        """Get information about the Python environment.

        Returns
        -------
            Dict with environment information

        """
        self.ensure_connected()

        try:
            # Get environment info from the application
            result = self.client.root.get_environment_info()
            return ActionResultModel(
                success=True, message="Successfully retrieved environment information", context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error getting environment info: {e}")
            return ActionResultModel(
                success=False, message="Failed to retrieve environment information", error=str(e)
            ).model_dump()

    def execute_python(self, code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Python code in the application's environment.

        Args:
        ----
            code: Python code to execute
            context: Optional context dictionary to use during execution

        Returns:
        -------
            Dict with execution result

        """
        self.ensure_connected()

        try:
            # Execute Python code in the application
            result = self.client.root.exposed_execute_python(code, context or {})
            return ActionResultModel(
                success=True, message="Successfully executed Python code", context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            return ActionResultModel(success=False, message="Failed to execute Python code", error=str(e)).model_dump()

    def import_module(self, module_name: str) -> Dict[str, Any]:
        """Import a module in the application's environment.

        Args:
        ----
            module_name: Name of the module to import

        Returns:
        -------
            Dict with import result

        """
        self.ensure_connected()

        try:
            # Import module in the application
            result = self.client.root.exposed_get_module(module_name)
            if result is None:
                return ActionResultModel(success=False, message=f"Module {module_name} not found").model_dump()
            return ActionResultModel(
                success=True, message=f"Successfully imported module {module_name}", context={"module": result}
            ).model_dump()
        except Exception as e:
            logger.error(f"Error importing module {module_name}: {e}")
            return ActionResultModel(
                success=False, message=f"Failed to import module {module_name}", error=str(e)
            ).model_dump()

    def call_function(self, module_name: str, function_name: str, *args, **kwargs) -> Dict[str, Any]:
        """Call a function in the application's environment.

        Args:
        ----
            module_name: Name of the module containing the function
            function_name: Name of the function to call
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
        -------
            Dict with function call result

        """
        self.ensure_connected()

        try:
            # Call function in the application
            result = self.client.root.exposed_call_function(module_name, function_name, *args, **kwargs)
            return ActionResultModel(
                success=True, message=f"Successfully called function {module_name}.{function_name}", context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error calling function {module_name}.{function_name}: {e}")
            return ActionResultModel(
                success=False, message=f"Failed to call function {module_name}.{function_name}", error=str(e)
            ).model_dump()

    def get_actions(self) -> Dict[str, Any]:
        """Get all available actions for the application.

        Returns
        -------
            Dict with action information

        """
        self.ensure_connected()

        try:
            # Get actions from the application
            result = self.client.root.exposed_list_actions()
            return ActionResultModel(
                success=True,
                message=(
                    f"Successfully retrieved "
                    f"{len(result.get('actions', {})) if isinstance(result, dict) else 0} actions"
                ),
                context=result,
            ).model_dump()
        except Exception as e:
            logger.error(f"Error getting actions: {e}")
            return ActionResultModel(success=False, message="Failed to retrieve actions", error=str(e)).model_dump()

    def call_action(self, action_name: str, **kwargs) -> Dict[str, Any]:
        """Call an action in the application.

        Args:
        ----
            action_name: Name of the action to call
            **kwargs: Arguments for the action

        Returns:
        -------
            Dict with action call result

        """
        self.ensure_connected()

        try:
            # Call the action in the application
            result = self.client.root.exposed_call_action(action_name, **kwargs)

            # If result is already a success/failure dict, return it
            if isinstance(result, dict) and "success" in result:
                return result

            # Otherwise, wrap it in an ActionResultModel
            return ActionResultModel(
                success=True,
                message=f"Successfully called action {action_name}",
                context=result,
            ).model_dump()
        except Exception as e:
            logger.error(f"Error calling action {action_name}: {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to call action {action_name}",
                error=str(e),
            ).model_dump()

    def discover_actions(self) -> List[str]:
        """Discover actions from all configured action paths.

        Returns
        -------
            List of discovered action names

        """
        return self.action_adapter.discover_all_actions()
