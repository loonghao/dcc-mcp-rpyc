"""Application adapter implementation for general Python environments.

This module provides a concrete implementation of the ApplicationAdapter
for any application with a Python interpreter.
"""

# Import built-in modules
import logging
import os
import platform
import sys
import importlib
from typing import Any, Dict, Optional, List, Callable, Union

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel

# Import local modules
from dcc_mcp_rpyc.adapter.base import ApplicationAdapter

# Configure logging
logger = logging.getLogger(__name__)


class GenericApplicationAdapter(ApplicationAdapter):
    """Adapter for general Python environments.

    This class provides a concrete implementation of the ApplicationAdapter
    for any application with a Python interpreter. It can be used to execute Python code
    and functions in the application's environment.
    
    Unlike DCCAdapter, GenericApplicationAdapter is designed for local Python environments
    where no remote connection is needed. It runs in the same process as the application
    and provides direct access to the Python environment.
    
    Attributes:
        app_name: Name of the application
        app_version: Version of the application
    """

    def __init__(self, app_name: str = "python", app_version: Optional[str] = None):
        """Initialize the application adapter.

        Args:
            app_name: Name of the application (default: "python")
            app_version: Version of the application (default: None, uses sys.version)
        """
        self.app_version = app_version or sys.version
        super().__init__(app_name)
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

    def get_application_info(self) -> ActionResultModel:
        """Get information about the application.

        Returns:
            ActionResultModel with application information including name, version, etc.
        """
        info = {
            "name": self.app_name,
            "version": self.app_version,
            "platform": platform.platform(),
            "executable": sys.executable,
            "pid": os.getpid(),
        }
        
        return ActionResultModel(
            success=True,
            message="Successfully retrieved application information",
            context=info
        )

    def get_environment_info(self) -> ActionResultModel:
        """Get information about the Python environment.

        Returns:
            ActionResultModel with environment information including Python version, available modules, etc.
        """
        info = {
            "python_version": sys.version,
            "python_path": sys.path,
            "platform": platform.platform(),
            "os": os.name,  
            "pid": os.getpid(),
            "cwd": os.getcwd(),
            "sys_prefix": sys.prefix,  
        }
        
        return ActionResultModel(
            success=True,
            message="Successfully retrieved environment information",
            context=info
        )

    def execute_python(self, code: str, context: Optional[Dict[str, Any]] = None) -> ActionResultModel:
        """Execute Python code in the application's environment.

        Args:
            code: Python code to execute
            context: Optional context dictionary to use during execution

        Returns:
            ActionResultModel with execution result
        """
        context = context or {}
        local_vars = {}
        
        try:
            # Add context variables to locals
            local_vars.update(context)
            
            # Execute the code
            exec(code, globals(), local_vars)
            
            # Return the result
            return ActionResultModel(
                success=True,
                message="Successfully executed Python code",
                context=local_vars
            )
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            return ActionResultModel(
                success=False,
                message="Failed to execute Python code",
                error=str(e),
                context={"code_length": len(code)}
            )

    def import_module(self, module_name: str) -> ActionResultModel:
        """Import a module in the application's environment.

        Args:
            module_name: Name of the module to import

        Returns:
            ActionResultModel with import result
        """
        try:
            # Try to import the module
            module = importlib.import_module(module_name)
            
            # Get module attributes
            attributes = [attr for attr in dir(module) if not attr.startswith("_")]
            
            return ActionResultModel(
                success=True,
                message=f"Successfully imported module {module_name}",
                context={
                    "module": module,
                    "attributes": attributes,
                    "file": getattr(module, "__file__", "<unknown>")
                }
            )
        except ImportError as e:
            logger.error(f"Error importing module {module_name}: {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to import module {module_name}",
                error=str(e)
            )

    def call_function(self, module_name: str, function_name: str, *args, **kwargs) -> ActionResultModel:
        """Call a function in the application's environment.

        Args:
            module_name: Name of the module containing the function
            function_name: Name of the function to call
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            ActionResultModel with function call result
        """
        try:
            # Import the module
            module = importlib.import_module(module_name)
            
            # Get the function
            func = getattr(module, function_name)
            
            # Call the function
            result = func(*args, **kwargs)
            
            return ActionResultModel(
                success=True,
                message=f"Successfully called function {module_name}.{function_name}",
                context={"result": result}
            )
        except ImportError as e:
            logger.error(f"Error importing module {module_name}: {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to call function {module_name}.{function_name}",
                error=f"No module named '{module_name}'"
            )
        except AttributeError as e:
            logger.error(f"Function {function_name} not found in module {module_name}: {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to call function {module_name}.{function_name}",
                error=f"Function '{function_name}' not found in module '{module_name}'"
            )
        except Exception as e:
            logger.error(f"Error calling function {module_name}.{function_name}: {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to call function {module_name}.{function_name}",
                error=str(e),
                context={"module": module_name, "function": function_name, "args": args, "kwargs": kwargs}
            )
