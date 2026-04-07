"""Additional coverage tests for dcc_mcp_ipc.action_adapter module.

Covers error paths in ActionAdapter: register_action failures, list_actions failures,
call_action edge cases, and get_action_adapter factory.

Adapted for the refactored ActionAdapter that directly uses ActionRegistry +
ActionDispatcher from dcc-mcp-core 0.12+.
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest
from dcc_mcp_core import ActionResultModel

# Import local modules
from dcc_mcp_ipc.action_adapter import ActionAdapter
from dcc_mcp_ipc.action_adapter import get_action_adapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter(name="test_adapter_cov"):
    """Return ActionAdapter with fully mocked registry and dispatcher."""
    adapter = object.__new__(ActionAdapter)
    adapter.name = name
    adapter.dcc_name = "python"
    adapter.registry = MagicMock()
    adapter.dispatcher = MagicMock()
    return adapter


# ---------------------------------------------------------------------------
# register_action
# ---------------------------------------------------------------------------

class TestRegisterAction:
    """Tests for register_action."""

    def test_register_success(self):
        adapter = _make_adapter()
        handler = MagicMock()
        result = adapter.register_action("my_action", handler, description="test")
        assert result is True
        adapter.registry.register.assert_called_once()
        adapter.dispatcher.register_handler.assert_called_once_with("my_action", handler)

    def test_register_raises_action_error_on_registry_failure(self):
        from dcc_mcp_ipc.utils.errors import ActionError
        adapter = _make_adapter()
        adapter.registry.register.side_effect = Exception("registry broken")
        with pytest.raises(ActionError):
            adapter.register_action("bad_action", MagicMock())

    def test_register_with_all_kwargs(self):
        adapter = _make_adapter()
        handler = MagicMock()
        result = adapter.register_action(
            "full_action",
            handler,
            description="full description",
            category="scene",
            tags=["create", "mesh"],
            version="2.0.0",
            input_schema='{"type": "object"}',
            output_schema='{"type": "object"}',
            source_file="/some/file.py",
        )
        assert result is True


# ---------------------------------------------------------------------------
# unregister_action
# ---------------------------------------------------------------------------

class TestUnregisterAction:
    """Tests for unregister_action."""

    def test_unregister_existing(self):
        adapter = _make_adapter()
        adapter.dispatcher.remove_handler.return_value = True
        result = adapter.unregister_action("existing_action")
        assert result is True
        adapter.dispatcher.remove_handler.assert_called_once_with("existing_action")

    def test_unregister_nonexistent_returns_false(self):
        adapter = _make_adapter()
        adapter.dispatcher.remove_handler.return_value = False
        result = adapter.unregister_action("nonexistent")
        assert result is False


# ---------------------------------------------------------------------------
# list_actions
# ---------------------------------------------------------------------------

class TestListActions:
    """Tests for list_actions."""

    def test_list_actions_dict_by_default(self):
        adapter = _make_adapter()
        adapter.registry.list_actions.return_value = [
            {"name": "action_a", "description": "desc a"},
            {"name": "action_b", "description": "desc b"},
        ]
        result = adapter.list_actions()
        assert "action_a" in result
        assert "action_b" in result

    def test_list_actions_names_only(self):
        adapter = _make_adapter()
        adapter.registry.list_actions.return_value = [
            {"name": "action_a"},
            {"name": "action_b"},
        ]
        result = adapter.list_actions(names_only=True)
        assert isinstance(result, list)
        assert "action_a" in result
        assert "action_b" in result

    def test_list_actions_failure_raises_action_error(self):
        from dcc_mcp_ipc.utils.errors import ActionError
        adapter = _make_adapter()
        adapter.registry.list_actions.side_effect = Exception("registry error")
        with pytest.raises(ActionError):
            adapter.list_actions()

    def test_list_actions_empty(self):
        adapter = _make_adapter()
        adapter.registry.list_actions.return_value = []
        result = adapter.list_actions()
        assert result == {}

    def test_list_actions_passes_dcc_name(self):
        adapter = _make_adapter()
        adapter.dcc_name = "maya"
        adapter.registry.list_actions.return_value = []
        adapter.list_actions()
        adapter.registry.list_actions.assert_called_once_with("maya")


# ---------------------------------------------------------------------------
# get_action_info
# ---------------------------------------------------------------------------

class TestGetActionInfo:
    """Tests for get_action_info."""

    def test_returns_metadata_when_found(self):
        adapter = _make_adapter()
        expected = {"name": "my_action", "description": "do stuff"}
        adapter.registry.get_action.return_value = expected
        result = adapter.get_action_info("my_action")
        assert result == expected

    def test_returns_none_when_not_found(self):
        adapter = _make_adapter()
        adapter.registry.get_action.return_value = None
        result = adapter.get_action_info("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# call_action
# ---------------------------------------------------------------------------

class TestCallAction:
    """Tests for call_action."""

    def test_call_action_returns_action_result_model_from_dict(self):
        adapter = _make_adapter()
        adapter.dispatcher.dispatch.return_value = {"success": True, "message": "done", "context": {}}
        result = adapter.call_action("existing_action", param="value")
        assert isinstance(result, ActionResultModel)
        assert result.success is True

    def test_call_action_non_dict_result_wrapped(self):
        adapter = _make_adapter()
        adapter.dispatcher.dispatch.return_value = "raw_string_result"
        result = adapter.call_action("existing_action")
        assert isinstance(result, ActionResultModel)
        assert result.success is True

    def test_call_action_exception_returns_error_model(self):
        adapter = _make_adapter()
        adapter.dispatcher.dispatch.side_effect = RuntimeError("action crashed")
        result = adapter.call_action("crashing_action")
        assert isinstance(result, ActionResultModel)
        assert result.success is False

    def test_call_action_no_params(self):
        adapter = _make_adapter()
        adapter.dispatcher.dispatch.return_value = {"success": True, "message": "ok"}
        result = adapter.call_action("simple_action")
        # dispatch should be called with "null" for no params
        call_args = adapter.dispatcher.dispatch.call_args
        assert call_args[0][0] == "simple_action"
        assert call_args[0][1] == "null"

    def test_call_action_with_params_serialised(self):
        adapter = _make_adapter()
        adapter.dispatcher.dispatch.return_value = {"success": True, "message": "ok"}
        adapter.call_action("action_with_params", x=1, y=2)
        call_args = adapter.dispatcher.dispatch.call_args
        import json
        params = json.loads(call_args[0][1])
        assert params == {"x": 1, "y": 2}


# ---------------------------------------------------------------------------
# execute_action
# ---------------------------------------------------------------------------

class TestExecuteAction:
    """Tests for execute_action (returns dict)."""

    def test_execute_returns_dict(self):
        adapter = _make_adapter()
        adapter.dispatcher.dispatch.return_value = {"success": True, "message": "done"}
        result = adapter.execute_action("my_action")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# get_action_adapter module-level factory
# ---------------------------------------------------------------------------

class TestGetActionAdapter:
    """Tests for the get_action_adapter factory function."""

    def test_returns_action_adapter_instance(self):
        adapter = get_action_adapter("my_adapter_cov_unique")
        assert isinstance(adapter, ActionAdapter)
        assert adapter.name == "my_adapter_cov_unique"

    def test_same_name_returns_cached_instance(self):
        a1 = get_action_adapter("cached_adapter_cov")
        a2 = get_action_adapter("cached_adapter_cov")
        assert a1 is a2

    def test_different_names_give_different_instances(self):
        a1 = get_action_adapter("adapter_cov_x")
        a2 = get_action_adapter("adapter_cov_y")
        assert a1.name != a2.name

    def test_dcc_name_passed(self):
        adapter = get_action_adapter("adapter_dcc_cov", dcc_name="maya")
        assert adapter.dcc_name == "maya"
