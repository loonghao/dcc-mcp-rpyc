"""Tests for the RPyC service classes.

This module contains tests for the DCCRPyCService and ApplicationRPyCService classes.
"""

# Import built-in modules
import sys

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel

# Import local modules
from tests.conftest import MockDCCService


class TestDCCRPyCService:
    """Tests for the DCCRPyCService abstract base class."""

    def test_interface_methods(self):
        """Test that all abstract methods are implemented in MockDCCService."""
        # Create an instance of MockDCCService
        service = MockDCCService()

        # Test that all required methods are implemented
        assert hasattr(service, "get_application_info")
        assert hasattr(service, "get_environment_info")
        assert hasattr(service, "execute_python")
        assert hasattr(service, "import_module")
        assert hasattr(service, "call_function")
        assert hasattr(service, "get_scene_info")
        assert hasattr(service, "get_session_info")
        assert hasattr(service, "create_primitive")

    def test_get_application_info(self):
        """Test get_application_info method."""
        service = MockDCCService()
        info = service.get_application_info()

        # Verify the result structure
        assert "name" in info
        assert "version" in info
        assert "platform" in info
        assert "executable" in info

        # Verify the values
        assert info["name"] == "test_dcc"
        assert info["version"] == "1.0.0"
        assert isinstance(info["platform"], str)
        assert isinstance(info["executable"], str)

    def test_get_environment_info(self):
        """Test get_environment_info method."""
        service = MockDCCService()
        info = service.get_environment_info()

        # Verify the result structure
        assert "python_version" in info
        assert "modules" in info
        assert "sys_path" in info
        assert "environment_variables" in info
        assert "python_path" in info
        assert "platform" in info
        assert "cwd" in info
        assert "os" in info

        # Verify the values
        assert info["python_version"] == sys.version
        assert isinstance(info["modules"], dict)
        assert isinstance(info["sys_path"], list)
        assert isinstance(info["environment_variables"], dict)

    def test_execute_python(self):
        """Test execute_python method."""
        service = MockDCCService()

        # Test simple execution
        result = service.execute_python("2 + 2")
        assert result == 4

        # Test with context
        result = service.execute_python("x + y", {"x": 5, "y": 7})
        assert result == 12

        # Test with exception
        result = service.execute_python("1/0")
        assert isinstance(result, dict)
        assert "error" in result
        assert "division by zero" in result["error"]

    def test_import_module(self):
        """Test import_module method."""
        service = MockDCCService()

        # Test importing a standard module
        result = service.import_module("os")
        assert hasattr(result, "path")

        # Test importing a non-existent module
        result = service.import_module("non_existent_module")
        assert isinstance(result, dict)
        assert "error" in result
        assert "non_existent_module" in result["error"]

    def test_call_function(self):
        """Test call_function method."""
        service = MockDCCService()

        # Test calling a function from a standard module
        result = service.call_function("os.path", "join", "dir", "file.txt")
        expected_path = "dir/file.txt" if "/" in str(result) else "dir\\file.txt"  # Handle different OS path separators
        assert result == expected_path

        # Test calling a non-existent function
        result = service.call_function("os", "non_existent_function")
        assert isinstance(result, dict)
        assert "error" in result

    def test_get_scene_info(self):
        """Test get_scene_info method."""
        service = MockDCCService()
        result = service.get_scene_info()

        # Convert result to ActionResultModel for easier testing
        if not isinstance(result, ActionResultModel):
            # If it's a dict, convert it to an ActionResultModel
            if isinstance(result, dict):
                result = ActionResultModel(**result)

        # Verify the result
        assert result.success is True
        assert "scene" in result.message.lower()
        assert "name" in result.context
        assert "path" in result.context
        assert "modified" in result.context
        assert "objects" in result.context

    def test_get_session_info(self):
        """Test get_session_info method."""
        service = MockDCCService()
        result = service.get_session_info()

        # Convert result to ActionResultModel for testing
        if isinstance(result, dict):
            # If it's a dictionary, convert it to an ActionResultModel
            if isinstance(result, dict):
                result = ActionResultModel(**result)

        # Verify the result
        assert result.success is True
        assert "session" in result.message.lower()
        context = result.context

        # Verify result context
        assert "id" in context
        assert "application" in context
        assert "version" in context
        assert "user" in context
        assert "scene" in context
        assert isinstance(context["scene"], dict)

    def test_create_primitive(self):
        """Test create_primitive method."""
        service = MockDCCService()
        result = service.create_primitive("cube", size=1.0)

        # Convert result to ActionResultModel for testing
        if isinstance(result, dict):
            # If it's a dictionary, check for necessary fields
            assert "success" in result
            assert result["success"] is True
            assert "message" in result
            assert "context" in result
            context = result["context"]
        else:
            context = result

        # 验证结果
        assert "id" in context
        assert "type" in context
        assert "name" in context
        assert "parameters" in context
        assert context["type"] == "cube"
        assert context["parameters"]["size"] == 1.0


class TestApplicationRPyCService:
    """Tests for the ApplicationRPyCService abstract base class."""

    def test_interface_methods(self):
        """Test that all abstract methods are implemented in MockDCCService."""
        # MockDCCService also implements ApplicationRPyCService
        service = MockDCCService()

        # Test that all required methods are implemented
        assert hasattr(service, "get_application_info")
        assert hasattr(service, "get_environment_info")
        assert hasattr(service, "execute_python")
        assert hasattr(service, "import_module")
        assert hasattr(service, "call_function")

    def test_exposed_methods(self):
        """Test that the service has the expected exposed methods."""
        # Create a service instance for testing
        service = MockDCCService()

        # Check required ApplicationRPyCService methods
        required_app_methods = [
            "exposed_get_application_info",
            "exposed_get_environment_info",
            "exposed_execute_python",
            "exposed_get_module",
            "exposed_call_function",
        ]

        for method_name in required_app_methods:
            assert hasattr(service, method_name), f"Missing required method: {method_name}"
            assert callable(getattr(service, method_name)), f"Method is not callable: {method_name}"

        # Check required DCCRPyCService methods
        required_dcc_methods = [
            "exposed_get_scene_info",
            "exposed_get_session_info",
            "exposed_create_primitive",
            "exposed_get_actions",
            "exposed_echo",
            "exposed_add",
            "exposed_execute_cmd",
        ]

        for method_name in required_dcc_methods:
            # If the method is not implemented, skip it
            if not hasattr(service, method_name):
                print(f"Warning: Optional method {method_name} is not implemented")
                continue

            assert callable(getattr(service, method_name)), f"Method is not callable: {method_name}"
