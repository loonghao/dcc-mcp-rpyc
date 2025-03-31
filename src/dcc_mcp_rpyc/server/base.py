"""Base server classes for DCC-MCP-RPYC.

This module provides base classes for RPYC services that can be used with DCC applications.
"""

# Import built-in modules
from abc import ABC
from abc import abstractmethod
import logging
from typing import Any
from typing import Dict
from typing import Optional

# Import third-party modules
import rpyc

# Import local modules
from dcc_mcp_rpyc.server.decorators import with_environment_info

# Configure logging
logger = logging.getLogger(__name__)


class BaseRPyCService(rpyc.SlaveService):
    """Base RPYC service for DCC applications.

    This service provides the foundation for exposing DCC functionality via RPYC.
    It can be extended for specific DCC applications.
    """

    def on_connect(self, conn):
        """Handle client connection to the service.

        Args:
        ----
            conn: The connection object

        """
        super().on_connect(conn)
        logger.info(f"Client connected: {conn}")

    def on_disconnect(self, conn):
        """Handle client disconnection from the service.

        Args:
        ----
            conn: The connection object

        """
        super().on_disconnect(conn)
        logger.info(f"Client disconnected: {conn}")


class ApplicationRPyCService(BaseRPyCService, ABC):
    """Abstract base class for application RPYC services.

    This class defines the common interface that all application services should implement.
    It provides methods for connecting to any application with a Python environment and
    executing Python code and functions within that environment.
    """

    @abstractmethod
    def get_application_info(self) -> Dict[str, Any]:
        """Get information about the application.

        Returns
        -------
            Dict with application information including name, version, etc.

        """

    @abstractmethod
    def get_environment_info(self) -> Dict[str, Any]:
        """Get information about the Python environment.

        Returns
        -------
            Dict with environment information including Python version, available modules, etc.

        """

    @abstractmethod
    def execute_python(self, code: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Execute Python code in the application's environment.

        Args:
        ----
            code: Python code to execute
            context: Optional context dictionary to use during execution

        Returns:
        -------
            The result of the code execution

        """

    @abstractmethod
    def import_module(self, module_name: str) -> Any:
        """Import a module in the application's environment.

        Args:
        ----
            module_name: Name of the module to import

        Returns:
        -------
            The imported module

        """

    @abstractmethod
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
            The result of the function call

        """

    @with_environment_info
    def exposed_execute_python(self, code: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Execute Python code in the application's environment.

        Args:
        ----
            code: Python code to execute
            context: Optional context dictionary to use during execution

        Returns:
        -------
            The result of the code execution

        """
        try:
            return self.execute_python(code, context)
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            logger.exception("Detailed exception information:")
            raise

    @with_environment_info
    def exposed_get_module(self, module_name: str) -> Any:
        """Get a module from the application's environment.

        Args:
        ----
            module_name: Name of the module to get

        Returns:
        -------
            The module object

        """
        try:
            return self.import_module(module_name)
        except Exception as e:
            logger.error(f"Error getting module {module_name}: {e}")
            logger.exception("Detailed exception information:")
            raise

    @with_environment_info
    def exposed_call_function(self, module_name: str, function_name: str, *args, **kwargs) -> Any:
        """Call a function in the application's environment.

        Args:
        ----
            module_name: Name of the module containing the function
            function_name: Name of the function to call
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
        -------
            The result of the function call

        """
        try:
            return self.call_function(module_name, function_name, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error calling function {module_name}.{function_name}: {e}")
            logger.exception("Detailed exception information:")
            raise

    def exposed_list_actions(self) -> Dict[str, Any]:
        """List all available actions in this application service.

        Returns
        -------
            Dict with action information

        """
        # Default implementation returns an empty list
        # Subclasses should override this method to provide actual actions
        return {"actions": {}}

    def exposed_call_action(self, action_name: str, **kwargs) -> Any:
        """Call an action in the application.

        Args:
        ----
            action_name: Name of the action to call
            **kwargs: Arguments for the action

        Returns:
        -------
            The result of the action call

        """
        # Default implementation raises NotImplementedError
        # Subclasses should override this method to provide actual action calling
        raise NotImplementedError(f"Action '{action_name}' is not implemented")
