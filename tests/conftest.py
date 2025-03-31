"""Pytest configuration for DCC-MCP-RPYC tests.

This module provides fixtures and configuration for pytest tests.
"""

# Import built-in modules
import importlib.metadata
import os
import sys
import tempfile
import time
from typing import Any
from typing import Dict
from typing import Optional

# Import third-party modules
# Import dcc_mcp_core modules
from dcc_mcp_core.models import ActionResultModel
import pytest
from rpyc.utils.server import ThreadedServer

# Import local modules
# Import dcc_mcp_rpyc modules
from dcc_mcp_rpyc.server.base import BaseRPyCService
from dcc_mcp_rpyc.server.dcc import DCCRPyCService
from dcc_mcp_rpyc.server.dcc import DCCServer
from dcc_mcp_rpyc.utils.discovery import cleanup_stale_services
from dcc_mcp_rpyc.utils.discovery import register_service
from dcc_mcp_rpyc.utils.discovery import unregister_service


@pytest.fixture
def temp_registry_path():
    """Provide a temporary registry file path."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name

    yield temp_path

    # Clean up the temporary file
    try:
        os.unlink(temp_path)
    except OSError:
        pass


class TestRPyCService(BaseRPyCService):
    """Test RPYC service for testing."""

    def exposed_echo(self, arg):
        """Echo the argument back."""
        return arg

    def exposed_add(self, a, b):
        """Add two numbers."""
        return a + b


@pytest.fixture
def rpyc_server():
    """Create a RPYC server for testing.

    Yields
    ------
        Tuple of (server, port)

    """
    # Create a server
    server = ThreadedServer(
        TestRPyCService,
        port=0,  # Use a random port
        protocol_config={
            "allow_public_attrs": True,
            "allow_pickle": True,
            "sync_request_timeout": 30,
        },
    )

    # Start the server in a separate thread
    server_thread = server.start()

    # Wait for the server to start
    time.sleep(0.1)

    # Get the port
    port = server.port

    # Yield the server and port
    yield server, port

    # Close the server
    server.close()

    # Wait for the server thread to finish
    server_thread.join(timeout=1)


@pytest.mark.usefixtures()  #
class MockDCCService(DCCRPyCService):
    """Mock DCC RPYC service for testing."""

    def get_application_info(self):
        """Get information about the application.

        Returns
        -------
            Dict with application information including name, version, etc.

        """
        return {
            "name": "test_dcc",
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
            "application": "test_dcc",
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

    def exposed_execute_cmd(self, cmd_name: str, *args, **kwargs):
        """Execute a command.

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


@pytest.fixture
def dcc_rpyc_server():
    """Create a DCC RPYC server for testing.

    Yields
    ------
        Tuple of (server, port)

    """
    # Create a server
    server = ThreadedServer(
        MockDCCService,
        port=0,  # Use a random port
        protocol_config={
            "allow_public_attrs": True,
            "allow_pickle": True,
            "sync_request_timeout": 30,
        },
    )

    # Start the server in a separate thread
    server_thread = server.start()

    # Wait for the server to start
    time.sleep(0.1)

    # Get the port
    port = server.port

    # Yield the server and port
    yield server, port

    # Close the server
    server.close()

    # Wait for the server thread to finish
    server_thread.join(timeout=1)


@pytest.fixture
def dcc_server(temp_registry_path: str):
    """Create a DCC server for testing.

    Args:
    ----
        temp_registry_path: Fixture providing a temporary registry file path

    Yields:
    ------
        Tuple of (server, port)

    """
    # Create a server
    server = DCCServer(
        service=MockDCCService,
        host="localhost",
        port=0,  # Use a random port
        registry_path=temp_registry_path,
        service_name="MockDCC",
        service_info={
            "name": "MockDCC",
            "version": "1.0.0",
            "platform": sys.platform,
        },
    )

    # Start the server
    server.start()

    # Wait for the server to start
    time.sleep(0.1)

    # Get the port
    port = server.port

    # Register the service
    register_service(
        name="MockDCC",
        host="localhost",
        port=port,
        registry_path=temp_registry_path,
        service_info={
            "name": "MockDCC",
            "version": "1.0.0",
            "platform": sys.platform,
        },
    )

    # Yield the server and port
    try:
        yield server, port
    finally:
        server.stop()
        unregister_service("MockDCC", "localhost", port)
        cleanup_stale_services()
        try:
            os.remove(temp_registry_path)
        except (FileNotFoundError, PermissionError):
            pass
        time.sleep(0.1)


@pytest.fixture
def dcc_service():
    """Create a DCC service for testing.

    Returns
    -------
        MockDCCService instance

    """
    return MockDCCService()
