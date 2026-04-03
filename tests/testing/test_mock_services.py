"""Tests for dcc_mcp_ipc.testing.mock_services module.

These tests cover MockDCCService, start_mock_dcc_service, stop_mock_dcc_service,
and stop_all_mock_services without requiring a real DCC application.
"""

# Import built-in modules
import sys
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.testing.mock_services import MockDCCService
from dcc_mcp_ipc.testing.mock_services import stop_all_mock_services
from dcc_mcp_ipc.testing.mock_services import stop_mock_dcc_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(dcc_name="test_dcc"):
    """Return a MockDCCService instance bypassing RPyC internals."""
    svc = object.__new__(MockDCCService)
    svc.dcc_name = dcc_name
    return svc


# ---------------------------------------------------------------------------
# MockDCCService - application info
# ---------------------------------------------------------------------------

class TestMockDCCServiceApplicationInfo:
    """Tests for get_application_info / exposed_get_application_info."""

    def test_returns_dcc_name(self):
        svc = _make_service("maya")
        info = svc.get_application_info()
        assert info["name"] == "maya"

    def test_contains_platform_and_executable(self):
        svc = _make_service()
        info = svc.get_application_info()
        assert "platform" in info
        assert "executable" in info
        assert info["platform"] == sys.platform

    def test_version_present(self):
        svc = _make_service()
        info = svc.get_application_info()
        assert info["version"] == "1.0.0"

    def test_exposed_delegates_to_get(self):
        svc = _make_service("blender")
        svc.get_application_info = MagicMock(return_value={"name": "blender"})
        result = svc.exposed_get_application_info()
        svc.get_application_info.assert_called_once()
        assert result["name"] == "blender"


# ---------------------------------------------------------------------------
# MockDCCService - environment info
# ---------------------------------------------------------------------------

class TestMockDCCServiceEnvironmentInfo:
    """Tests for get_environment_info / exposed_get_environment_info."""

    def test_contains_python_version(self):
        svc = _make_service()
        info = svc.get_environment_info()
        assert "python_version" in info
        assert sys.version in info["python_version"]

    def test_contains_modules(self):
        svc = _make_service()
        info = svc.get_environment_info()
        assert "modules" in info
        assert isinstance(info["modules"], dict)

    def test_contains_sys_path(self):
        svc = _make_service()
        info = svc.get_environment_info()
        assert "sys_path" in info

    def test_exposed_delegates(self):
        svc = _make_service()
        svc.get_environment_info = MagicMock(return_value={"python_version": "3.x"})
        result = svc.exposed_get_environment_info()
        svc.get_environment_info.assert_called_once()
        assert result["python_version"] == "3.x"


# ---------------------------------------------------------------------------
# MockDCCService - get_module_version static method
# ---------------------------------------------------------------------------

class TestGetModuleVersion:
    """Tests for the static get_module_version method."""

    def test_known_package_returns_version(self):
        import importlib.metadata as meta
        # Use a package we know exists in the test env
        pkg = "pytest"
        expected = meta.version(pkg)
        mock_module = MagicMock()
        result = MockDCCService.get_module_version(pkg, mock_module)
        assert result == expected

    def test_fallback_to_dunder_version(self):
        import importlib.metadata as real_meta
        mock_module = MagicMock()
        mock_module.__version__ = "9.9.9"
        # Patch only the version function in the module's importlib.metadata reference
        with patch.object(real_meta, "version", side_effect=real_meta.PackageNotFoundError("fake_pkg")):
            result = MockDCCService.get_module_version("fake_pkg", mock_module)
        assert result == "9.9.9"

    def test_fallback_to_version_attr(self):
        import importlib.metadata as real_meta

        class ModuleWithVersion:
            """Module with .version but no .__version__."""

            version = "1.2.3"

        with patch.object(real_meta, "version", side_effect=real_meta.PackageNotFoundError("fake_pkg")):
            result = MockDCCService.get_module_version("fake_pkg", ModuleWithVersion())
        assert result == "1.2.3"

    def test_fallback_to_VERSION_attr(self):
        import importlib.metadata as real_meta

        class FakeModule:
            VERSION = "4.5.6"

        with patch.object(real_meta, "version", side_effect=real_meta.PackageNotFoundError("fake_pkg")):
            result = MockDCCService.get_module_version("fake_pkg", FakeModule())
        assert result == "4.5.6"

    def test_returns_unknown_when_no_attr(self):
        import importlib.metadata as real_meta

        class Bare:
            pass

        with patch.object(real_meta, "version", side_effect=real_meta.PackageNotFoundError("fake_pkg")):
            result = MockDCCService.get_module_version("fake_pkg", Bare())
        assert result == "unknown"


# ---------------------------------------------------------------------------
# MockDCCService - execute_python
# ---------------------------------------------------------------------------

class TestExecutePython:
    """Tests for execute_python / exposed_execute_python."""

    def test_simple_expression(self):
        svc = _make_service()
        result = svc.execute_python("1 + 1")
        assert result == 2

    def test_with_context(self):
        svc = _make_service()
        result = svc.execute_python("x * 2", context={"x": 5})
        assert result == 10

    def test_error_returns_dict(self):
        svc = _make_service()
        result = svc.execute_python("raise ValueError('oops')")
        assert isinstance(result, dict)
        assert "error" in result

    def test_syntax_error_returns_dict(self):
        svc = _make_service()
        result = svc.execute_python("def f(: bad syntax")
        assert isinstance(result, dict)

    def test_exposed_delegates(self):
        svc = _make_service()
        svc.execute_python = MagicMock(return_value=42)
        result = svc.exposed_execute_python("1 + 1")
        svc.execute_python.assert_called_once_with("1 + 1", None)
        assert result == 42


# ---------------------------------------------------------------------------
# MockDCCService - import_module
# ---------------------------------------------------------------------------

class TestImportModule:
    """Tests for import_module / exposed_import_module."""

    def test_import_existing_module(self):
        svc = _make_service()
        result = svc.import_module("sys")
        assert result is sys

    def test_import_nonexistent_module(self):
        svc = _make_service()
        result = svc.import_module("totally_fake_module_xyz123")
        assert isinstance(result, dict)
        assert "error" in result
        assert result["success"] is False

    def test_exposed_delegates(self):
        svc = _make_service()
        svc.import_module = MagicMock(return_value=sys)
        result = svc.exposed_import_module("sys")
        svc.import_module.assert_called_once_with("sys")
        assert result is sys


# ---------------------------------------------------------------------------
# MockDCCService - call_function
# ---------------------------------------------------------------------------

class TestCallFunction:
    """Tests for call_function / exposed_call_function."""

    def test_call_existing_function(self):
        import os
        svc = _make_service()
        result = svc.call_function("os.path", "join", "/tmp", "file.txt")
        assert result == os.path.join("/tmp", "file.txt")

    def test_module_not_found_returns_error(self):
        svc = _make_service()
        result = svc.call_function("fake_module_xyz", "some_func")
        assert isinstance(result, dict)
        assert "error" in result

    def test_function_not_found_returns_error(self):
        svc = _make_service()
        result = svc.call_function("sys", "nonexistent_function_xyz")
        assert isinstance(result, dict)
        assert "error" in result
        assert result["success"] is False

    def test_exposed_delegates(self):
        svc = _make_service()
        svc.call_function = MagicMock(return_value="ok")
        result = svc.exposed_call_function("mod", "func", 1, 2)
        svc.call_function.assert_called_once_with("mod", "func", 1, 2)
        assert result == "ok"


# ---------------------------------------------------------------------------
# MockDCCService - get_scene_info / get_session_info
# ---------------------------------------------------------------------------

class TestSceneAndSessionInfo:
    """Tests for get_scene_info, get_session_info and their exposed variants."""

    def test_get_scene_info_success(self):
        svc = _make_service()
        result = svc.get_scene_info()
        assert isinstance(result, dict)
        assert result["success"] is True
        assert "context" in result

    def test_scene_info_has_objects(self):
        svc = _make_service()
        result = svc.get_scene_info()
        assert "objects" in result["context"]

    def test_get_session_info_success(self):
        svc = _make_service("houdini")
        result = svc.get_session_info()
        assert isinstance(result, dict)
        assert result["success"] is True

    def test_session_info_application_name(self):
        svc = _make_service("houdini")
        result = svc.get_session_info()
        assert result["context"]["application"] == "houdini"

    def test_exposed_get_scene_info(self):
        svc = _make_service()
        svc.get_scene_info = MagicMock(return_value={"success": True})
        result = svc.exposed_get_scene_info()
        svc.get_scene_info.assert_called_once()
        assert result["success"] is True

    def test_exposed_get_session_info(self):
        svc = _make_service()
        svc.get_session_info = MagicMock(return_value={"success": True})
        _ = svc.exposed_get_session_info()
        svc.get_session_info.assert_called_once()


# ---------------------------------------------------------------------------
# MockDCCService - create_primitive
# ---------------------------------------------------------------------------

class TestCreatePrimitive:
    """Tests for create_primitive."""

    def test_create_sphere(self):
        svc = _make_service()
        result = svc.create_primitive("sphere", radius=2.0)
        assert result["success"] is True
        assert result["context"]["type"] == "sphere"
        assert result["context"]["parameters"]["radius"] == 2.0

    def test_create_cube(self):
        svc = _make_service()
        result = svc.create_primitive("cube", size=3.0)
        assert result["success"] is True
        assert result["context"]["type"] == "cube"

    def test_cube_default_dimensions(self):
        svc = _make_service()
        result = svc.create_primitive("cube")
        assert result["context"]["parameters"]["size"] == 1.0

    def test_unknown_primitive_returns_failure(self):
        svc = _make_service()
        result = svc.create_primitive("teapot")
        assert result["success"] is False
        assert "teapot" in result["message"]

    def test_unknown_primitive_has_supported_types(self):
        svc = _make_service()
        result = svc.create_primitive("cone")
        assert "supported_types" in result["context"]


# ---------------------------------------------------------------------------
# MockDCCService - exposed_get_actions
# ---------------------------------------------------------------------------

class TestExposedGetActions:
    """Tests for exposed_get_actions."""

    def test_returns_actions_dict(self):
        svc = _make_service()
        result = svc.exposed_get_actions()
        assert "actions" in result
        assert "create_primitive" in result["actions"]
        assert "get_scene_info" in result["actions"]


# ---------------------------------------------------------------------------
# MockDCCService - exposed_call_action
# ---------------------------------------------------------------------------

class TestExposedCallAction:
    """Tests for exposed_call_action."""

    def test_call_known_action_create_primitive(self):
        svc = _make_service()
        result = svc.exposed_call_action("create_primitive", primitive_type="sphere")
        assert result["success"] is True

    def test_call_known_action_get_scene_info(self):
        svc = _make_service()
        result = svc.exposed_call_action("get_scene_info")
        assert result["success"] is True

    def test_call_unknown_action_returns_failure(self):
        svc = _make_service()
        result = svc.exposed_call_action("nonexistent_action")
        assert result["success"] is False
        assert "nonexistent_action" in result["message"]

    def test_action_exception_returns_failure(self):
        svc = _make_service()
        svc.create_primitive = MagicMock(side_effect=RuntimeError("boom"))
        result = svc.exposed_call_action("create_primitive", primitive_type="sphere")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# MockDCCService - exposed_echo and exposed_add
# ---------------------------------------------------------------------------

class TestExposedEchoAdd:
    """Tests for exposed_echo and exposed_add."""

    def test_echo_string(self):
        svc = _make_service()
        assert svc.exposed_echo("hello") == "hello"

    def test_echo_dict(self):
        svc = _make_service()
        payload = {"key": "value"}
        assert svc.exposed_echo(payload) == payload

    def test_add_integers(self):
        svc = _make_service()
        assert svc.exposed_add(3, 4) == 7

    def test_add_floats(self):
        svc = _make_service()
        result = svc.exposed_add(1.5, 2.5)
        assert abs(result - 4.0) < 1e-9


# ---------------------------------------------------------------------------
# MockDCCService - exposed_execute_dcc_command
# ---------------------------------------------------------------------------

class TestExposedExecuteDccCommand:
    """Tests for exposed_execute_dcc_command."""

    def test_known_command_create_primitive(self):
        svc = _make_service()
        result = svc.exposed_execute_dcc_command("create_primitive", primitive_type="cube")
        assert result["success"] is True

    def test_known_command_get_scene_info(self):
        svc = _make_service()
        result = svc.exposed_execute_dcc_command("get_scene_info")
        assert result["success"] is True

    def test_unknown_command_raises_value_error(self):
        svc = _make_service()
        with pytest.raises(ValueError, match="Unknown command"):
            svc.exposed_execute_dcc_command("nonexistent_cmd")


# ---------------------------------------------------------------------------
# MockDCCService - exposed_get_dcc_info
# ---------------------------------------------------------------------------

class TestExposedGetDccInfo:
    """Tests for exposed_get_dcc_info."""

    def test_returns_name_and_version(self):
        svc = _make_service("maya")
        result = svc.exposed_get_dcc_info()
        assert result["name"] == "maya"
        assert result["version"] == "1.0.0"

    def test_contains_platform(self):
        svc = _make_service()
        result = svc.exposed_get_dcc_info()
        assert "platform" in result
        assert "python_version" in result


# ---------------------------------------------------------------------------
# start_mock_dcc_service / stop_mock_dcc_service / stop_all_mock_services
# ---------------------------------------------------------------------------

class TestMockServiceLifecycle:
    """Tests for module-level start/stop functions."""

    def test_stop_nonexistent_service_does_not_raise(self):
        """Stopping a service that was never started should silently do nothing."""
        stop_mock_dcc_service("never_started_dcc_xyz")

    def test_stop_all_with_no_services_does_not_raise(self):
        """stop_all_mock_services on empty registry should not raise."""
        stop_all_mock_services()

    def test_stop_all_clears_registry(self):
        """After stop_all_mock_services, the internal registry should be empty."""
        from dcc_mcp_ipc.testing import mock_services as ms
        # Manually inject a fake server entry
        fake_server = MagicMock()
        fake_thread = MagicMock()
        ms._mock_servers["fake_dcc_test"] = (fake_server, fake_thread, "localhost", 19999)

        with patch.object(ms, "stop_mock_dcc_service", wraps=ms.stop_mock_dcc_service):
            stop_all_mock_services()

        assert "fake_dcc_test" not in ms._mock_servers
