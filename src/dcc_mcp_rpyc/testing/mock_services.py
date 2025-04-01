"""Mock services for testing DCC-MCP-RPYC.

This module provides mock services for testing DCC-MCP-RPYC without requiring
actual DCC applications. These mock services can be used in integration tests
and for development purposes.
"""

# Import built-in modules
import importlib
import importlib.metadata
import sys
import threading
from typing import Any
from typing import Dict
from typing import Optional

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel
from rpyc.utils.server import ThreadedServer

# Import local modules
from dcc_mcp_rpyc.server import DCCRPyCService
from dcc_mcp_rpyc.discovery import ServiceRegistry, ServiceInfo, FileDiscoveryStrategy

# Dictionary to store mock servers for cleanup
_mock_servers = {}


class MockDCCService(DCCRPyCService):
    """Mock DCC RPYC service for testing.

    This class provides a mock implementation of a DCC RPYC service that can be used
    for testing without requiring an actual DCC application. It implements all the
    basic functionality expected from a DCC service, including executing Python code,
    getting scene information, and creating primitives.

    Example:
        >>> from rpyc.utils.server import ThreadedServer
        >>> from dcc_mcp_rpyc.testing import MockDCCService
        >>> server = ThreadedServer(MockDCCService, port=18812)
        >>> server.start()

    """

    def __init__(self, *args, **kwargs):
        """Initialize the mock DCC service.

        Args:
            *args: Variable length argument list for compatibility with RPyC
            **kwargs: Arbitrary keyword arguments for compatibility with RPyC

        """
        # Call the parent class constructor
        super().__init__(*args, **kwargs)

        # Set default DCC name
        self.dcc_name = kwargs.get("dcc_name", "test_dcc")

    def get_application_info(self):
        """Get information about the application.

        Returns
        -------
            Dict with application information including name, version, etc.

        """
        return {
            "name": self.dcc_name,
            "version": "1.0.0",
            "platform": sys.platform,
            "executable": sys.executable,
        }

    def get_environment_info(self):
        """Get information about the Python environment.

        Returns
        -------
            Dict with environment information including Python version, available modules, etc.

        """
        # Import built-in modules
        import os

        modules = {}
        for name, module in sys.modules.items():
            if not name.startswith("_") and not name.startswith("rpyc"):
                try:
                    modules[name] = self.get_module_version(name, module)
                except Exception:
                    pass

        return {
            "python_version": sys.version,
            "platform": sys.platform,
            "modules": modules,
            "sys_path": sys.path,
            "environment_variables": dict(os.environ),
            "python_path": sys.executable,
            "cwd": os.getcwd(),
            "os": os.name,
        }

    @staticmethod
    def get_module_version(module_name, module):
        """Get the version of a module.

        Args:
        ----
            module_name: Name of the module
            module: Module object

        Returns:
        -------
            Version string

        """
        try:
            # First try using importlib.metadata.version
            return importlib.metadata.version(module_name)
        except (importlib.metadata.PackageNotFoundError, ValueError):
            # If importlib.metadata fails, try other methods
            try:
                return module.__version__
            except AttributeError:
                try:
                    return module.version
                except AttributeError:
                    try:
                        return module.VERSION
                    except AttributeError:
                        return "unknown"

    def execute_python(self, code: str, context: Optional[Dict[str, Any]] = None):
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
            # Create a local context
            local_context = {}
            if context:
                local_context.update(context)

            # Execute the code
            result = eval(code, globals(), local_context)
            return result
        except Exception as e:
            return {"error": str(e), "code": code, "context": context or {}}

    def import_module(self, module_name: str):
        """Import a module in the application's environment.

        Args:
        ----
            module_name: Name of the module to import

        Returns:
        -------
            The imported module or a dict with error information

        """
        try:
            module = importlib.import_module(module_name)
            return module
        except ImportError as e:
            return {"error": str(e), "name": module_name, "success": False}

    def call_function(self, module_name: str, function_name: str, *args, **kwargs):
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
            module_result = self.import_module(module_name)
            if isinstance(module_result, dict) and "error" in module_result:
                return module_result

            module = module_result

            # Get the function
            function = getattr(module, function_name, None)
            if function is None:
                return {
                    "error": f"Function {function_name} not found in module {module_name}",
                    "module": module_name,
                    "function": function_name,
                    "success": False,
                }

            # Call the function
            result = function(*args, **kwargs)
            return result
        except Exception as e:
            return {
                "error": str(e),
                "module": module_name,
                "function": function_name,
                "args": args,
                "kwargs": kwargs,
                "success": False,
            }

    def get_scene_info(self):
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        scene_info = {
            "name": "scene.ma",
            "path": "/path/to/scene.ma",
            "modified": False,
            "objects": ["pSphere1", "pCube1"],
        }
        return ActionResultModel(
            success=True,
            message="Scene information retrieved successfully",
            prompt="You can use this information to understand the current scene state",
            error=None,
            context=scene_info,
        ).model_dump()

    def get_session_info(self):
        """Get information about the current session.

        Returns
        -------
            Dict with session information

        """
        session_info = {
            "id": "session_123",
            "application": self.dcc_name,
            "version": "1.0.0",
            "user": "test_user",
            "scene": {
                "name": "scene.ma",
                "path": "/path/to/scene.ma",
            },
        }
        return ActionResultModel(
            success=True,
            message="Session information retrieved successfully",
            prompt="You can use this information to understand the current session",
            error=None,
            context=session_info,
        ).model_dump()

    def create_primitive(self, primitive_type: str, **kwargs):
        """Create a primitive object in the DCC application.

        Args:
        ----
            primitive_type: Type of primitive to create
            **kwargs: Additional arguments for the primitive creation

        Returns:
        -------
            The result of the primitive creation in ActionResultModel format, including success, message, and context.

        """
        try:
            if primitive_type == "sphere":
                result = {
                    "id": "sphere1",
                    "name": "pSphere1",
                    "type": "sphere",
                    "parameters": {
                        "radius": kwargs.get("radius", 1.0),
                    },
                }
                prompt = "You can modify this sphere using modify_sphere function"
            elif primitive_type == "cube":
                result = {
                    "id": "cube1",
                    "name": "pCube1",
                    "type": "cube",
                    "parameters": {
                        "size": kwargs.get("size", 1.0),
                        "width": kwargs.get("width", 1.0),
                        "height": kwargs.get("height", 1.0),
                        "depth": kwargs.get("depth", 1.0),
                    },
                }
                prompt = "You can modify this cube using modify_cube function"
            else:
                return ActionResultModel(
                    success=False,
                    message=f"Failed to create primitive: Unknown type {primitive_type}",
                    prompt="Please try with a supported primitive type like 'sphere' or 'cube'",
                    error=f"Unknown primitive type: {primitive_type}",
                    context={"supported_types": ["sphere", "cube"]},
                ).model_dump()

            return ActionResultModel(
                success=True,
                message=f"Created {primitive_type} successfully",
                prompt=prompt,
                error=None,
                context=result,
            ).model_dump()
        except Exception as e:
            return ActionResultModel(
                success=False,
                message=f"Failed to create {primitive_type}",
                prompt="Please check the error message and try again",
                error=str(e),
                context={"attempted_type": primitive_type},
            ).model_dump()

    def exposed_get_application_info(self):
        """Get information about the application.

        Returns
        -------
            Dict with application information

        """
        return self.get_application_info()

    def exposed_get_environment_info(self):
        """Get information about the Python environment.

        Returns
        -------
            Dict with environment information

        """
        return self.get_environment_info()

    def exposed_execute_python(self, code: str, context: Optional[Dict[str, Any]] = None):
        """Execute Python code in the application's environment.

        Args:
        ----
            code: Python code to execute
            context: Optional context dictionary to use during execution

        Returns:
        -------
            The result of the code execution

        """
        return self.execute_python(code, context)

    def exposed_import_module(self, module_name: str):
        """Import a module in the application's environment.

        Args:
        ----
            module_name: Name of the module to import

        Returns:
        -------
            The imported module or a dict with error information

        """
        return self.import_module(module_name)

    def exposed_call_function(self, module_name: str, function_name: str, *args, **kwargs):
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
        return self.call_function(module_name, function_name, *args, **kwargs)

    def exposed_get_scene_info(self):
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        return self.get_scene_info()

    def exposed_get_session_info(self):
        """Get information about the current session.

        Returns
        -------
            Dict with session information

        """
        return self.get_session_info()

    def exposed_get_actions(self):
        """Get all available actions for the DCC application.

        Returns
        -------
            Dict with action information

        """
        return {
            "actions": {
                "create_primitive": {
                    "name": "create_primitive",
                    "description": "Create a primitive object",
                    "parameters": {
                        "primitive_type": {
                            "type": "string",
                            "description": "Type of primitive to create",
                            "required": True,
                        },
                    },
                },
                "get_scene_info": {
                    "name": "get_scene_info",
                    "description": "Get information about the current scene",
                    "parameters": {},
                },
            }
        }

    def exposed_call_action(self, action_name: str, *args, **kwargs) -> Dict[str, Any]:
        """Call an action by name.

        Args:
        ----
            action_name: Name of the action to call
            *args: Positional arguments for the action
            **kwargs: Keyword arguments for the action

        Returns:
        -------
            Result of the action in ActionResultModel format

        """
        # Map action names to methods
        action_map = {
            "create_primitive": self.create_primitive,
            "get_scene_info": self.get_scene_info,
        }

        # Get the action function
        action_func = action_map.get(action_name)
        if action_func is None:
            return ActionResultModel(
                success=False,
                message=f"Unknown action: {action_name}",
                error=f"Action {action_name} not found",
            ).model_dump()

        # Call the action function
        try:
            result = action_func(*args, **kwargs)
            # If the result is already in ActionResultModel format, return it directly
            if isinstance(result, dict) and "success" in result:
                return result
            # Otherwise, wrap it in an ActionResultModel
            return ActionResultModel(
                success=True,
                message=f"Action {action_name} executed successfully",
                context=result if isinstance(result, dict) else {"result": result},
            ).model_dump()
        except Exception as e:
            return ActionResultModel(
                success=False,
                message=f"Failed to execute action {action_name}",
                error=str(e),
            ).model_dump()

    def exposed_echo(self, arg):
        """Echo the argument back.

        Args:
        ----
            arg: The argument to echo back

        Returns:
        -------
            The same argument

        """
        return arg

    def exposed_add(self, a, b):
        """Add two numbers.

        Args:
        ----
            a: First number
            b: Second number

        Returns:
        -------
            Sum of a and b

        """
        return a + b

    def exposed_execute_dcc_command(self, cmd_name: str, *args, **kwargs):
        """Execute a DCC-specific command.

        Args:
        ----
            cmd_name: Name of the command to execute
            *args: Positional arguments for the command
            **kwargs: Keyword arguments for the command

        Returns:
        -------
            Result of the command

        """
        # Map command names to methods
        cmd_map = {
            "create_primitive": self.create_primitive,
            "get_scene_info": self.get_scene_info,
        }

        # Get the command function
        cmd_func = cmd_map.get(cmd_name)
        if cmd_func is None:
            raise ValueError(f"Unknown command: {cmd_name}")

        # Call the command function
        return cmd_func(*args, **kwargs)

    def exposed_get_dcc_info(self, conn=None):
        """Get information about the DCC application.

        Returns
        -------
            Dict with DCC information including name, version, etc.

        """
        return {
            "name": self.dcc_name,
            "version": "1.0.0",
            "platform": sys.platform,
            "python_version": sys.version,
        }


def start_mock_dcc_service(dcc_name="mock_dcc", host="localhost", port=0):
    """Start a mock DCC service.

    This function creates and starts a mock DCC service for testing purposes.
    The service is started in a separate thread and registered for discovery.

    Args:
        dcc_name: Name of the DCC application to simulate (default: "mock_dcc")
        host: Host name (default: "localhost")
        port: Port number (default: 0, which means use a random available port)

    Returns:
        Tuple of (host, port) where the service is running

    Example:
        >>> from dcc_mcp_rpyc.testing.mock_services import start_mock_dcc_service
        >>> host, port = start_mock_dcc_service("maya")
        >>> print(f"Mock Maya service running at {host}:{port}")

    """
    # Create service instance
    service = MockDCCService(dcc_name=dcc_name)

    # Create server
    server = ThreadedServer(
        service,
        hostname=host,
        port=port,
        protocol_config={"allow_public_attrs": True},
        logger=None,
    )

    # Get actual port
    if port == 0:
        port = server.port

    # Register service
    registry = ServiceRegistry()
    service_info = ServiceInfo(
        name=dcc_name,
        host=host,
        port=port,
        dcc_type=dcc_name,
        metadata={"version": "1.0.0"}
    )
    registry.register_service_with_strategy("file", service_info)

    # Start server in new thread
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()

    # Store server instance for later closing
    _mock_servers[dcc_name] = (server, thread, host, port)

    # Wait for server to start
    # Import built-in modules
    import time

    time.sleep(0.5)

    return host, port


def stop_mock_dcc_service(dcc_name):
    """Stop a mock DCC service.

    This function stops a previously started mock DCC service.

    Args:
        dcc_name: Name of the DCC service to stop

    Example:
        >>> from dcc_mcp_rpyc.testing.mock_services import stop_mock_dcc_service
        >>> stop_mock_dcc_service("maya")

    """
    if dcc_name in _mock_servers:
        server, thread, host, port = _mock_servers[dcc_name]
        
        # Unregister the service
        registry = ServiceRegistry()
        service_info = ServiceInfo(
            name=dcc_name,
            host=host,
            port=port,
            dcc_type=dcc_name,
            metadata={"version": "1.0.0"}
        )
        registry.register_service_with_strategy("file", service_info, unregister=True)
        
        # Close the server
        server.close()
        thread.join(timeout=1)
        del _mock_servers[dcc_name]


def stop_all_mock_services():
    """Stop all running mock DCC services.

    This function stops all previously started mock DCC services.
    It's useful for cleanup in test teardown.

    Example:
        >>> from dcc_mcp_rpyc.testing.mock_services import stop_all_mock_services
        >>> stop_all_mock_services()

    """
    for dcc_name in list(_mock_servers.keys()):
        stop_mock_dcc_service(dcc_name)
