"""Application service implementation for general Python environments.

This module provides a concrete implementation of the ApplicationRPyCService
for any application with a Python interpreter.
"""

# Import built-in modules
import importlib
import logging
import os
import platform
import sys
from typing import Any
from typing import Dict
from typing import Optional

# Import third-party modules
from rpyc.utils.server import ThreadedServer

# Import local modules
from dcc_mcp_rpyc.server import ApplicationRPyCService

# Configure logging
logger = logging.getLogger(__name__)


class ApplicationService(ApplicationRPyCService):
    """RPYC service for general Python environments.

    This class provides a concrete implementation of the ApplicationRPyCService
    for any application with a Python interpreter. It can be used to execute Python code
    and functions in the application's environment.
    """

    def __init__(self, app_name: str = "python", app_version: Optional[str] = None):
        """Initialize the application service.

        Args:
        ----
            app_name: Name of the application (default: "python")
            app_version: Version of the application (default: None, uses sys.version)

        """
        super().__init__()
        self.app_name = app_name
        self.app_version = app_version or sys.version
        logger.info(f"Initialized {self.app_name} service (version {self.app_version})")

    def get_application_info(self) -> Dict[str, Any]:
        """Get information about the application.

        Returns
        -------
            Dict with application information including name, version, etc.

        """
        return {
            "name": self.app_name,
            "version": self.app_version,
            "platform": platform.platform(),
            "executable": sys.executable,
            "pid": os.getpid(),
        }

    def get_environment_info(self) -> Dict[str, Any]:
        """Get information about the Python environment.

        Returns
        -------
            Dict with environment information including Python version, available modules, etc.

        """
        return {
            "python_version": sys.version,
            "python_path": sys.path,
            "platform": platform.platform(),
            "os": os.name,
            "sys_prefix": sys.prefix,
            "cwd": os.getcwd(),
        }

    def execute_python(self, code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Python code in the application's environment.

        Args:
        ----
            code: Python code to execute
            context: Optional context dictionary to use during execution

        Returns:
        -------
            Dict with the result of the code execution

        """
        try:
            # Create a local context for execution
            local_context = context.copy() if context else {}

            # Execute the code in the local context
            exec(compile(code, "<string>", "exec"), globals(), local_context)

            # If the code defines a variable named 'result', return it in a dict
            if "result" in local_context:
                return {"result": local_context["result"]}

            # Otherwise, return the entire local context
            return {"result": local_context}
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            return {"error": str(e)}

    def import_module(self, module_name: str) -> Any:
        """Import a module in the application's environment.

        Args:
        ----
            module_name: Name of the module to import

        Returns:
        -------
            The imported module

        """
        try:
            return importlib.import_module(module_name)
        except Exception as e:
            logger.error(f"Error importing module {module_name}: {e}")
            return None

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
        try:
            # Import the module
            module = self.import_module(module_name)
            if module is None:
                return {"error": f"Module {module_name} not found"}

            # Get the function
            function = getattr(module, function_name, None)
            if function is None or not callable(function):
                return {"error": f"Function {function_name} not found in module {module_name}"}

            # Call the function
            return function(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error calling function {module_name}.{function_name}: {e}")
            return {"error": str(e)}

    def get_actions(self) -> Dict[str, Any]:
        """Get all available actions for the application.

        Returns
        -------
            Dict with action information

        """
        # In a general Python environment, we don't have actions
        # This could be extended in subclasses to provide action discovery
        return {}


def create_application_server(app_name: str = "python", app_version: Optional[str] = None, port: int = 18812):
    """Create and start an application server.

    Args:
    ----
        app_name: Name of the application (default: "python")
        app_version: Version of the application (default: None, uses sys.version)
        port: Port to listen on (default: 18812)

    Returns:
    -------
        The server instance

    """
    service = ApplicationService(app_name, app_version)
    server = ThreadedServer(service, port=port)
    logger.info(f"Starting {app_name} server on port {port}")
    return server


def start_application_server(app_name: str = "python", app_version: Optional[str] = None, port: int = 18812):
    """Start an application server.

    Args:
    ----
        app_name: Name of the application (default: "python")
        app_version: Version of the application (default: None, uses sys.version)
        port: Port to listen on (default: 18812)

    """
    server = create_application_server(app_name, app_version, port)
    server.start()
