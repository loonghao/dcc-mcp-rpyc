"""Tests for the GenericApplicationAdapter class.

This module contains tests for the GenericApplicationAdapter class in the application.adapter module.
"""

# Import built-in modules
import os
import platform
import sys
from unittest import mock

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.application.adapter import GenericApplicationAdapter


class TestGenericApplicationAdapter:
    """Tests for the GenericApplicationAdapter class."""

    @pytest.fixture
    def adapter(self):
        """Create a GenericApplicationAdapter instance for testing."""
        with mock.patch("dcc_mcp_rpyc.action_adapter.get_action_adapter") as mock_get_action_adapter:
            mock_action_adapter = mock.MagicMock()
            mock_get_action_adapter.return_value = mock_action_adapter

            # Rewrite _initialize_action_paths method to avoid calling set_action_search_paths
            with mock.patch.object(GenericApplicationAdapter, "_initialize_action_paths", autospec=True):
                adapter = GenericApplicationAdapter(app_name="test_app", app_version="1.0.0")
                return adapter

    def test_init(self):
        """Test initialization of GenericApplicationAdapter."""
        # Mock action_adapter
        with mock.patch("dcc_mcp_rpyc.action_adapter.get_action_adapter") as mock_get_action_adapter:
            mock_action_adapter = mock.MagicMock()
            mock_get_action_adapter.return_value = mock_action_adapter

            # Rewrite _initialize_action_paths method to avoid calling set_action_search_paths
            with mock.patch.object(GenericApplicationAdapter, "_initialize_action_paths", autospec=True):
                # Test with explicit app_name and app_version
                adapter = GenericApplicationAdapter(app_name="test_app", app_version="1.0.0")
                assert adapter.app_name == "test_app"
                assert adapter.app_version == "1.0.0"
                assert adapter.client is None

                # Test with default app_name and app_version
                adapter = GenericApplicationAdapter()
                assert adapter.app_name == "python"
                assert adapter.app_version == sys.version
                assert adapter.client is None

    def test_get_application_info(self, adapter):
        """Test get_application_info method."""
        info = adapter.get_application_info()
        assert info["name"] == "test_app"
        assert info["version"] == "1.0.0"
        assert info["platform"] == platform.platform()
        assert info["executable"] == sys.executable
        assert info["pid"] == os.getpid()

    def test_get_environment_info(self, adapter):
        """Test get_environment_info method."""
        info = adapter.get_environment_info()
        assert info["python_version"] == sys.version
        assert info["platform"] == platform.platform()
        assert info["os"] == os.name
        assert info["sys_prefix"] == sys.prefix
        assert "python_path" in info
        assert isinstance(info["python_path"], list)

    def test_execute_python_success(self, adapter):
        """Test successful Python code execution."""
        # Store result in variable named result
        result = adapter.execute_python("result = 2 + 2")
        assert result.success is True
        assert result.context["result"] == 4

    def test_execute_python_with_context(self, adapter):
        """Test Python code execution with context."""
        context = {"x": 10, "y": 5}
        result = adapter.execute_python("result = x + y", context)
        assert result.success is True
        assert result.context["result"] == 15

    def test_execute_python_exception(self, adapter):
        """Test Python code execution with exception."""
        result = adapter.execute_python("1/0")
        assert result.success is False
        assert "division by zero" in result.error

    def test_import_module_success(self, adapter):
        """Test successful module import."""
        result = adapter.import_module("os")
        assert result.success is True
        assert result.context["module"].__name__ == "os"

    def test_import_module_failure(self, adapter):
        """Test module import failure."""
        result = adapter.import_module("non_existent_module")
        assert result.success is False
        assert "No module named" in result.error

    def test_call_function_success(self, adapter):
        """Test successful function call."""
        result = adapter.call_function("os.path", "join", "dir", "file.txt")
        assert result.success is True
        expected_path = os.path.join("dir", "file.txt")
        assert result.context["result"] == expected_path

    def test_call_function_module_not_found(self, adapter):
        """Test function call with module not found."""
        result = adapter.call_function("non_existent_module", "function")
        assert result.success is False
        assert "No module named" in result.error

    def test_call_function_function_not_found(self, adapter):
        """Test function call with function not found."""
        result = adapter.call_function("os", "non_existent_function")
        assert result.success is False
        assert "not found" in result.error

    def test_call_function_exception(self, adapter):
        """Test function call with exception."""
        result = adapter.call_function("os.path", "join", 1, 2)  # Wrong argument types
        assert result.success is False
        # Check complete error message, not just error type
        assert "expected str, bytes or os.PathLike object, not int" in result.error
