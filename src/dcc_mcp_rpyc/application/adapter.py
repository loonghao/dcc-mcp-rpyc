"""Application adapter implementation for general Python environments.

This module provides a concrete implementation of the ApplicationAdapter
for any application with a Python interpreter.
"""

# Import built-in modules
import logging
import os
import platform
import sys
from typing import Any
from typing import Dict
from typing import Optional

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel

# Import local modules
from dcc_mcp_rpyc.adapter import ApplicationAdapter

# Configure logging
logger = logging.getLogger(__name__)


class GenericApplicationAdapter(ApplicationAdapter):
    """Adapter for general Python environments.

    This class provides a concrete implementation of the ApplicationAdapter
    for any application with a Python interpreter. It can be used to execute Python code
    and functions in the application's environment.
    """

    def __init__(self, app_name: str = "python", app_version: Optional[str] = None):
        """Initialize the application adapter.

        Args:
        ----
            app_name: Name of the application (default: "python")
            app_version: Version of the application (default: None, uses sys.version)

        """
        super().__init__(app_name)
        self.app_version = app_version or sys.version
        logger.info(f"Initialized {self.app_name} adapter (version {self.app_version})")

        # Register actions
        self.register_action("execute_python", self.execute_python)
        self.register_action("import_module", self.import_module)
        self.register_action("call_function", self.call_function)

    def _initialize_client(self) -> None:
        """Initialize the client for communicating with the application.

        This method initializes the client for the generic application adapter.
        For the generic adapter, we don't need a client as we're running in the
        same process as the application.
        """
        # No client needed for generic adapter as we're in the same process
        self.client = None

    def _initialize_action_paths(self) -> None:
        """Initialize the paths to search for actions.

        This method initializes the action paths for the generic application adapter.
        """
        # Default action paths
        self.action_paths = []

        # If action_manager exists, set the search paths
        if hasattr(self, "action_manager") and self.action_manager:
            self.action_manager.set_action_search_paths(self.action_paths)

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

    def execute_python(self, code: str, context: Optional[Dict[str, Any]] = None) -> ActionResultModel:
        """Execute Python code in the application's environment.

        Args:
        ----
            code: Python code to execute
            context: Optional context dictionary to use during execution

        Returns:
        -------
            ActionResultModel with the result of the code execution

        """
        # Create a local context dictionary with the provided context
        local_context = {}
        if context:
            local_context.update(context)

        try:
            # Execute the code in the local context
            exec(compile(code, "<string>", "exec"), globals(), local_context)

            # If the code defines a variable named 'result', return it
            if "result" in local_context:
                result = local_context["result"]
                return ActionResultModel(
                    success=True,
                    message="Successfully executed Python code",
                    context={"result": result, "local_context": local_context},
                )

            # Otherwise, return the entire local context
            return ActionResultModel(
                success=True,
                message="Successfully executed Python code",
                context={"local_context": local_context},
            )
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            return ActionResultModel(
                success=False,
                message="Failed to execute Python code",
                error=str(e),
                context={"code": code},
            )

    def import_module(self, module_name: str) -> ActionResultModel:
        """Import a module in the application's environment.

        Args:
        ----
            module_name: Name of the module to import

        Returns:
        -------
            ActionResultModel with the imported module

        """
        try:
            # Import built-in modules
            import importlib

            module = importlib.import_module(module_name)
            return ActionResultModel(
                success=True,
                message=f"Successfully imported module {module_name}",
                context={"module": module},
            )
        except Exception as e:
            logger.error(f"Error importing module {module_name}: {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to import module {module_name}",
                error=str(e),
                context={"module_name": module_name},
            )

    def call_function(self, module_name: str, function_name: str, *args, **kwargs) -> ActionResultModel:
        """Call a function in the application's environment.

        Args:
        ----
            module_name: Name of the module containing the function
            function_name: Name of the function to call
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
        -------
            ActionResultModel with the result of the function call

        """
        try:
            # Import the module
            import_result = self.import_module(module_name)
            if not import_result.success:
                return import_result

            module = import_result.context["module"]

            # Get the function
            function = getattr(module, function_name, None)
            if function is None or not callable(function):
                return ActionResultModel(
                    success=False,
                    message=f"Function {function_name} not found in module {module_name}",
                    error=f"Function {function_name} not found in module {module_name}",
                    context={"module_name": module_name, "function_name": function_name},
                )

            # Call the function
            result = function(*args, **kwargs)
            return ActionResultModel(
                success=True,
                message=f"Successfully called function {module_name}.{function_name}",
                context={"result": result},
            )
        except Exception as e:
            logger.error(f"Error calling function {module_name}.{function_name}: {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to call function {module_name}.{function_name}",
                error=str(e),
                context={
                    "module_name": module_name,
                    "function_name": function_name,
                    "args": args,
                    "kwargs": kwargs,
                },
            )

    def register_action(self, name: str, func: callable) -> None:
        """Register an action with the adapter.

        This is a helper method for registering actions with the adapter.
        It's used by the adapter to register its own actions, but can also be used
        by external code to register additional actions.

        Args:
        ----
            name: Name of the action
            func: Function to call when the action is invoked

        """
        if not hasattr(self, "_actions"):
            self._actions = {}
        self._actions[name] = func
        logger.debug(f"Registered action: {name}")
