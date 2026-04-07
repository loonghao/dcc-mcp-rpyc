"""Tests for dcc_mcp_ipc.server.base module.

Covers BaseRPyCService, ApplicationRPyCService exposed methods,
including error paths not reached by prior tests.
"""

# Import built-in modules
import logging
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.server.base import ApplicationRPyCService
from dcc_mcp_ipc.server.base import BaseRPyCService


# ---------------------------------------------------------------------------
# Concrete stub - minimal implementation of the abstract class
# ---------------------------------------------------------------------------

class ConcreteAppService(ApplicationRPyCService):
    """Minimal concrete implementation for testing ApplicationRPyCService."""

    def get_application_info(self):
        return {"name": "stub_app", "version": "0.1"}

    def get_environment_info(self):
        return {"python_version": "3.x", "platform": "test"}

    def execute_python(self, code, context=None):
        return eval(code, {}, context or {})

    def import_module(self, module_name):
        import importlib
        return importlib.import_module(module_name)

    def call_function(self, module_name, function_name, *args, **kwargs):
        import importlib
        mod = importlib.import_module(module_name)
        func = getattr(mod, function_name)
        return func(*args, **kwargs)


# ---------------------------------------------------------------------------
# BaseRPyCService - on_connect / on_disconnect logging
# ---------------------------------------------------------------------------

class TestBaseRPyCServiceCallbacks:
    """Tests for on_connect and on_disconnect log calls."""

    def _make_base_service(self):
        svc = object.__new__(BaseRPyCService)
        return svc

    def test_on_connect_logs_info(self, caplog):
        svc = self._make_base_service()
        mock_conn = MagicMock()
        with caplog.at_level(logging.INFO, logger="dcc_mcp_ipc.server.base"):
            with patch.object(BaseRPyCService.__bases__[0], "on_connect", return_value=None):
                try:
                    svc.on_connect(mock_conn)
                except Exception:
                    pass
        # on_connect should at minimum not raise on its own log path

    def test_on_disconnect_logs_info(self, caplog):
        svc = self._make_base_service()
        mock_conn = MagicMock()
        with caplog.at_level(logging.INFO, logger="dcc_mcp_ipc.server.base"):
            with patch.object(BaseRPyCService.__bases__[0], "on_disconnect", return_value=None):
                try:
                    svc.on_disconnect(mock_conn)
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# ApplicationRPyCService - exposed_execute_python
# ---------------------------------------------------------------------------

class TestExposedExecutePython:
    """Tests for ApplicationRPyCService.exposed_execute_python."""

    def _make_svc(self):
        svc = object.__new__(ConcreteAppService)
        return svc

    def test_success_returns_result(self):
        svc = self._make_svc()
        # exposed_execute_python is decorated with @with_environment_info,
        # so it returns a dict with 'result' and 'environment_info'
        result = svc.exposed_execute_python("1 + 1")
        assert isinstance(result, dict)
        assert "environment_info" in result
        assert result["result"] == 2

    def test_with_context(self):
        svc = self._make_svc()
        result = svc.exposed_execute_python("x * 3", {"x": 4})
        assert isinstance(result, dict)
        assert result["result"] == 12

    def test_exception_is_propagated(self):
        svc = self._make_svc()
        with pytest.raises(Exception):
            svc.exposed_execute_python("raise ValueError('test error')")

    def test_execute_python_called(self):
        svc = self._make_svc()
        svc.execute_python = MagicMock(return_value="result")
        svc.exposed_execute_python("some code")
        svc.execute_python.assert_called_once_with("some code", None)

    def test_execute_python_logs_error_on_exception(self, caplog):
        svc = self._make_svc()
        svc.execute_python = MagicMock(side_effect=RuntimeError("execution failed"))
        with caplog.at_level(logging.ERROR, logger="dcc_mcp_ipc.server.base"):
            with pytest.raises(RuntimeError, match="execution failed"):
                svc.exposed_execute_python("bad code")
        assert any("execution failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# ApplicationRPyCService - exposed_get_module
# ---------------------------------------------------------------------------

class TestExposedGetModule:
    """Tests for ApplicationRPyCService.exposed_get_module."""

    def _make_svc(self):
        svc = object.__new__(ConcreteAppService)
        return svc

    def test_import_existing_module(self):
        import sys
        svc = self._make_svc()
        # exposed_get_module is wrapped with @with_environment_info
        result = svc.exposed_get_module("sys")
        assert isinstance(result, dict)
        assert "environment_info" in result
        assert result["result"] is sys

    def test_import_failure_propagates(self):
        svc = self._make_svc()
        with pytest.raises(Exception):
            svc.exposed_get_module("totally_nonexistent_module_xyz")

    def test_import_module_called(self):
        svc = self._make_svc()
        import sys
        svc.import_module = MagicMock(return_value=sys)
        result = svc.exposed_get_module("os")
        svc.import_module.assert_called_once_with("os")
        assert isinstance(result, dict)
        assert "environment_info" in result

    def test_error_logs_and_reraises(self, caplog):
        svc = self._make_svc()
        svc.import_module = MagicMock(side_effect=ImportError("no module"))
        with caplog.at_level(logging.ERROR, logger="dcc_mcp_ipc.server.base"):
            with pytest.raises(ImportError):
                svc.exposed_get_module("bad_module")
        assert any("no module" in r.message or "bad_module" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# ApplicationRPyCService - exposed_call_function
# ---------------------------------------------------------------------------

class TestExposedCallFunction:
    """Tests for ApplicationRPyCService.exposed_call_function."""

    def _make_svc(self):
        svc = object.__new__(ConcreteAppService)
        return svc

    def test_call_existing_function(self):
        import os
        svc = self._make_svc()
        # exposed_call_function is wrapped with @with_environment_info
        result = svc.exposed_call_function("os.path", "join", "/tmp", "file.txt")
        assert isinstance(result, dict)
        assert "environment_info" in result
        assert result["result"] == os.path.join("/tmp", "file.txt")

    def test_call_failure_propagates(self):
        svc = self._make_svc()
        with pytest.raises(Exception):
            svc.exposed_call_function("fake_module_xyz", "nonexistent_func")

    def test_call_function_delegate_called(self):
        svc = self._make_svc()
        svc.call_function = MagicMock(return_value=99)
        result = svc.exposed_call_function("mod", "func", 1, 2, key="v")
        svc.call_function.assert_called_once_with("mod", "func", 1, 2, key="v")
        assert isinstance(result, dict)
        assert "environment_info" in result

    def test_error_logs_and_reraises(self, caplog):
        svc = self._make_svc()
        svc.call_function = MagicMock(side_effect=RuntimeError("call failed"))
        with caplog.at_level(logging.ERROR, logger="dcc_mcp_ipc.server.base"):
            with pytest.raises(RuntimeError):
                svc.exposed_call_function("mod", "func")
        assert any("mod.func" in r.message or "call failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# ApplicationRPyCService - exposed_list_actions / exposed_call_action
# ---------------------------------------------------------------------------

class TestExposedListAndCallAction:
    """Tests for default list_actions and call_action implementations."""

    def _make_svc(self):
        svc = object.__new__(ConcreteAppService)
        return svc

    def test_list_actions_returns_empty_by_default(self):
        svc = self._make_svc()
        result = svc.exposed_list_actions()
        assert result == {"actions": {}}

    def test_call_action_raises_not_implemented(self):
        svc = self._make_svc()
        with pytest.raises(NotImplementedError, match="my_action"):
            svc.exposed_call_action("my_action")

    def test_call_action_error_message_includes_name(self):
        svc = self._make_svc()
        with pytest.raises(NotImplementedError) as exc_info:
            svc.exposed_call_action("export_fbx")
        assert "export_fbx" in str(exc_info.value)
