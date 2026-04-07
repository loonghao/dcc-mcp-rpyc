"""Tests for application/service.py (ApplicationService).

Covers execute_python, import_module, call_function, get_actions,
and the server factory functions.
"""

# Import built-in modules
import sys
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.application.service import ApplicationService
from dcc_mcp_ipc.application.service import create_application_server
from dcc_mcp_ipc.application.service import start_application_server


class TestApplicationServiceInit:
    """Tests for ApplicationService.__init__."""

    def test_default_app_name(self):
        """Test default app name is 'python'."""
        service = ApplicationService()
        assert service.app_name == "python"

    def test_default_version_is_sys_version(self):
        """Test default version uses sys.version."""
        service = ApplicationService()
        assert service.app_version == sys.version

    def test_custom_name_and_version(self):
        """Test custom app name and version."""
        service = ApplicationService("maya", "2025.0")
        assert service.app_name == "maya"
        assert service.app_version == "2025.0"


class TestGetApplicationInfo:
    """Tests for ApplicationService.get_application_info."""

    def test_returns_expected_keys(self):
        """Test that get_application_info returns required keys."""
        service = ApplicationService("blender", "4.0")
        info = service.get_application_info()

        assert info["name"] == "blender"
        assert info["version"] == "4.0"
        assert "platform" in info
        assert "executable" in info
        assert "pid" in info

    def test_pid_is_integer(self):
        """Test that pid is an integer."""
        service = ApplicationService()
        info = service.get_application_info()
        assert isinstance(info["pid"], int)


class TestGetEnvironmentInfo:
    """Tests for ApplicationService.get_environment_info."""

    def test_returns_expected_keys(self):
        """Test that get_environment_info returns required keys."""
        service = ApplicationService()
        info = service.get_environment_info()

        assert "python_version" in info
        assert "python_path" in info
        assert "platform" in info
        assert "os" in info
        assert "sys_prefix" in info
        assert "cwd" in info

    def test_python_version_matches(self):
        """Test that python_version matches sys.version."""
        service = ApplicationService()
        info = service.get_environment_info()
        assert info["python_version"] == sys.version


class TestExecutePython:
    """Tests for ApplicationService.execute_python."""

    def test_returns_result_variable(self):
        """Test that 'result' variable is extracted from code."""
        service = ApplicationService()
        output = service.execute_python("result = 1 + 1")
        assert output == {"result": 2}

    def test_returns_full_context_when_no_result(self):
        """Test that full context dict is returned when no 'result' variable."""
        service = ApplicationService()
        output = service.execute_python("x = 42")
        assert "x" in output["result"]

    def test_with_explicit_context(self):
        """Test that provided context variables are accessible in code."""
        service = ApplicationService()
        output = service.execute_python("result = val * 2", context={"val": 5})
        assert output == {"result": 10}

    def test_syntax_error_returns_error(self):
        """Test that a syntax error returns an error dict."""
        service = ApplicationService()
        output = service.execute_python("def broken(: pass")
        assert "error" in output

    def test_runtime_exception_returns_error(self):
        """Test that a runtime exception returns an error dict."""
        service = ApplicationService()
        output = service.execute_python("raise ValueError('bad')")
        assert "error" in output
        assert "bad" in output["error"]

    def test_empty_context_defaults_to_empty_dict(self):
        """Test that None context is treated as empty dict."""
        service = ApplicationService()
        output = service.execute_python("result = 99", context=None)
        assert output == {"result": 99}


class TestImportModule:
    """Tests for ApplicationService.import_module."""

    def test_import_existing_module(self):
        """Test importing an existing module."""
        service = ApplicationService()
        mod = service.import_module("os")
        # Import built-in modules
        import os

        assert mod is os

    def test_import_nonexistent_returns_none(self):
        """Test that importing a nonexistent module returns None."""
        service = ApplicationService()
        result = service.import_module("nonexistent_module_xyz_abc")
        assert result is None


class TestCallFunction:
    """Tests for ApplicationService.call_function."""

    def test_call_existing_function(self):
        """Test calling an existing function from a module."""
        service = ApplicationService()
        result = service.call_function("os.path", "join", "/tmp", "test.txt")
        # Import built-in modules
        import os.path

        assert result == os.path.join("/tmp", "test.txt")

    def test_call_function_module_not_found(self):
        """Test calling function from nonexistent module."""
        service = ApplicationService()
        result = service.call_function("nonexistent_xyz", "some_func")
        assert "error" in result
        assert "nonexistent_xyz" in result["error"]

    def test_call_function_not_found(self):
        """Test calling nonexistent function from valid module."""
        service = ApplicationService()
        result = service.call_function("os", "nonexistent_func_xyz")
        assert "error" in result
        assert "nonexistent_func_xyz" in result["error"]

    def test_call_non_callable(self):
        """Test calling a non-callable attribute."""
        service = ApplicationService()
        # os.sep is a string attribute, not callable
        result = service.call_function("os", "sep")
        assert "error" in result

    def test_call_function_exception(self):
        """Test that exceptions from function calls are handled."""
        service = ApplicationService()

        with patch.object(service, "import_module") as mock_import:
            mock_mod = MagicMock()
            mock_func = MagicMock(side_effect=RuntimeError("func error"))
            mock_mod.failing_func = mock_func
            mock_import.return_value = mock_mod

            result = service.call_function("fake_mod", "failing_func")

        assert "error" in result
        assert "func error" in result["error"]


class TestGetActions:
    """Tests for ApplicationService.get_actions."""

    def test_returns_empty_dict(self):
        """Test that get_actions returns an empty dict for generic Python env."""
        service = ApplicationService()
        result = service.get_actions()
        assert result == {}


class TestServerFactoryFunctions:
    """Tests for create_application_server and start_application_server."""

    def test_create_application_server_returns_server(self):
        """Test that create_application_server returns a ThreadedServer."""
        with patch("dcc_mcp_ipc.application.service.ThreadedServer") as mock_server_cls:
            mock_server = MagicMock()
            mock_server_cls.return_value = mock_server

            server = create_application_server("test_app", "1.0", port=19999)

            assert server is mock_server
            mock_server_cls.assert_called_once()

    def test_start_application_server_calls_start(self):
        """Test that start_application_server calls server.start()."""
        with patch("dcc_mcp_ipc.application.service.ThreadedServer") as mock_server_cls:
            mock_server = MagicMock()
            mock_server_cls.return_value = mock_server

            start_application_server("test_app", port=19998)

            mock_server.start.assert_called_once()
