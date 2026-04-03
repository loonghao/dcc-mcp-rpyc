"""Additional coverage tests for dcc_mcp_ipc.action_adapter module.

Covers error paths in ActionAdapter: register_action failures, discover_actions failures,
discover_all_actions with multiple paths, list_actions failures, call_action edge cases.
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest
from dcc_mcp_core.models import ActionResultModel

# Import local modules
from dcc_mcp_ipc.action_adapter import ActionAdapter
from dcc_mcp_ipc.action_adapter import get_action_adapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter(name="test_adapter_cov"):
    """Return ActionAdapter with fully mocked action_manager."""
    adapter = object.__new__(ActionAdapter)
    adapter.name = name
    adapter.search_paths = []
    mock_manager = MagicMock()
    mock_registry = MagicMock()
    mock_manager.registry = mock_registry
    adapter.action_manager = mock_manager
    return adapter


# ---------------------------------------------------------------------------
# _get_or_create_action_manager
# ---------------------------------------------------------------------------

class TestGetOrCreateActionManager:
    """Tests for _get_or_create_action_manager (lines 72-78)."""

    def test_returns_existing_manager(self):
        mock_mgr = MagicMock()
        with patch("dcc_mcp_ipc.action_adapter.get_action_manager", return_value=mock_mgr):
            adapter = _make_adapter()
            result = adapter._get_or_create_action_manager("some_name")
        assert result is mock_mgr

    def test_creates_new_manager_when_none(self):
        mock_mgr = MagicMock()
        with patch("dcc_mcp_ipc.action_adapter.get_action_manager", return_value=None):
            with patch("dcc_mcp_ipc.action_adapter.create_action_manager", return_value=mock_mgr):
                adapter = _make_adapter()
                result = adapter._get_or_create_action_manager("new_manager")
        assert result is mock_mgr


# ---------------------------------------------------------------------------
# set_action_search_paths / add_action_search_path
# ---------------------------------------------------------------------------

class TestSearchPaths:
    """Tests for search path management (lines 80-101)."""

    def test_set_action_search_paths(self):
        adapter = _make_adapter()
        adapter.set_action_search_paths(["/path/a", "/path/b"])
        assert adapter.search_paths == ["/path/a", "/path/b"]

    def test_add_action_search_path_new(self):
        adapter = _make_adapter()
        adapter.add_action_search_path("/new/path")
        assert "/new/path" in adapter.search_paths

    def test_add_action_search_path_no_duplicate(self):
        adapter = _make_adapter()
        adapter.search_paths = ["/existing"]
        adapter.add_action_search_path("/existing")
        assert adapter.search_paths.count("/existing") == 1

    def test_add_multiple_paths(self):
        adapter = _make_adapter()
        adapter.add_action_search_path("/path/1")
        adapter.add_action_search_path("/path/2")
        assert len(adapter.search_paths) == 2


# ---------------------------------------------------------------------------
# register_action
# ---------------------------------------------------------------------------

class TestRegisterAction:
    """Tests for register_action (lines 103-121)."""

    def test_register_success(self):
        adapter = _make_adapter()
        mock_action = MagicMock()
        result = adapter.register_action(mock_action)
        adapter.action_manager.registry.register.assert_called_once_with(mock_action)
        assert result is True

    def test_register_raises_action_error_on_failure(self):
        adapter = _make_adapter()
        adapter.action_manager.registry.register.side_effect = Exception("registry broken")
        result = adapter.register_action(MagicMock())
        # @with_error_handling catches and returns ActionResultModel on failure
        assert isinstance(result, ActionResultModel)
        assert result.success is False


# ---------------------------------------------------------------------------
# discover_actions
# ---------------------------------------------------------------------------

class TestDiscoverActions:
    """Tests for discover_actions (lines 123-145)."""

    def test_discover_from_path(self):
        adapter = _make_adapter()
        adapter.action_manager.discover_actions_from_path.return_value = ["action_a"]
        result = adapter.discover_actions("/some/path")
        assert result == ["action_a"]
        adapter.action_manager.discover_actions_from_path.assert_called_once_with("/some/path")

    def test_discover_from_module(self):
        adapter = _make_adapter()
        adapter.action_manager.discover_actions_from_module.return_value = ["action_b"]
        result = adapter.discover_actions("my.module", is_module=True)
        assert result == ["action_b"]
        adapter.action_manager.discover_actions_from_module.assert_called_once_with("my.module")

    def test_discover_path_failure_returns_error_model(self):
        adapter = _make_adapter()
        adapter.action_manager.discover_actions_from_path.side_effect = Exception("path error")
        result = adapter.discover_actions("/bad/path")
        # @with_error_handling wraps into ActionResultModel
        assert isinstance(result, ActionResultModel)
        assert result.success is False

    def test_discover_module_failure_returns_error_model(self):
        adapter = _make_adapter()
        adapter.action_manager.discover_actions_from_module.side_effect = Exception("module error")
        result = adapter.discover_actions("bad.module", is_module=True)
        assert isinstance(result, ActionResultModel)
        assert result.success is False


# ---------------------------------------------------------------------------
# discover_all_actions
# ---------------------------------------------------------------------------

class TestDiscoverAllActions:
    """Tests for discover_all_actions (lines 147-166)."""

    def test_empty_search_paths(self):
        adapter = _make_adapter()
        adapter.search_paths = []
        result = adapter.discover_all_actions()
        assert result == []

    def test_single_path_discovered(self):
        adapter = _make_adapter()
        adapter.search_paths = ["/path/a"]
        # discover_actions will call discover_actions_from_path
        adapter.action_manager.discover_actions_from_path.return_value = ["action_x", "action_y"]
        result = adapter.discover_all_actions()
        assert "action_x" in result
        assert "action_y" in result

    def test_multiple_paths_all_discovered(self):
        adapter = _make_adapter()
        adapter.search_paths = ["/path/a", "/path/b"]
        call_count = [0]
        def side_effect(path):
            call_count[0] += 1
            return [f"action_from_{call_count[0]}"]
        adapter.action_manager.discover_actions_from_path.side_effect = side_effect
        result = adapter.discover_all_actions()
        assert len(result) == 2

    def test_one_path_fails_continues_with_others(self):
        """discover_all_actions should continue even if one path fails."""
        adapter = _make_adapter()
        adapter.search_paths = ["/bad/path", "/good/path"]
        call_results = [Exception("path error"), ["action_good"]]
        call_idx = [0]
        def side_effect(path):
            idx = call_idx[0]
            call_idx[0] += 1
            result = call_results[idx]
            if isinstance(result, Exception):
                raise result
            return result
        adapter.action_manager.discover_actions_from_path.side_effect = side_effect
        # The error path in discover_all_actions catches exceptions from discover_actions
        # discover_actions itself wraps with @with_error_handling -> returns ActionResultModel
        result = adapter.discover_all_actions()
        # Should at least be a list (even if one path failed)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# list_actions
# ---------------------------------------------------------------------------

class TestListActions:
    """Tests for list_actions (lines 168-189)."""

    def test_list_actions_dict_by_default(self):
        adapter = _make_adapter()
        adapter.action_manager.registry.list_actions.return_value = [
            {"name": "action_a", "description": "desc a"},
            {"name": "action_b", "description": "desc b"},
        ]
        result = adapter.list_actions()
        assert "action_a" in result
        assert "action_b" in result

    def test_list_actions_names_only(self):
        adapter = _make_adapter()
        adapter.action_manager.registry.list_actions.return_value = [
            {"name": "action_a"},
            {"name": "action_b"},
        ]
        result = adapter.list_actions(names_only=True)
        assert isinstance(result, list)
        assert "action_a" in result

    def test_list_actions_failure_returns_error_model(self):
        adapter = _make_adapter()
        adapter.action_manager.registry.list_actions.side_effect = Exception("registry error")
        result = adapter.list_actions()
        assert isinstance(result, ActionResultModel)
        assert result.success is False


# ---------------------------------------------------------------------------
# call_action
# ---------------------------------------------------------------------------

class TestCallAction:
    """Tests for call_action (lines 191-224)."""

    def test_call_action_not_found(self):
        adapter = _make_adapter()
        adapter.action_manager.registry.get_action.return_value = None
        adapter.action_manager.registry.list_actions.return_value = []
        result = adapter.call_action("nonexistent_action")
        assert isinstance(result, ActionResultModel)
        assert result.success is False
        assert "nonexistent_action" in result.message

    def test_call_action_returns_action_result_model(self):
        adapter = _make_adapter()
        adapter.action_manager.registry.get_action.return_value = MagicMock()
        expected = ActionResultModel(success=True, message="done")
        adapter.action_manager.call_action.return_value = expected
        result = adapter.call_action("existing_action")
        assert result is expected

    def test_call_action_non_model_result_wrapped(self):
        adapter = _make_adapter()
        adapter.action_manager.registry.get_action.return_value = MagicMock()
        adapter.action_manager.call_action.return_value = {"raw": "data"}
        result = adapter.call_action("existing_action")
        assert isinstance(result, ActionResultModel)
        assert result.success is True

    def test_call_action_exception_returns_error(self):
        adapter = _make_adapter()
        adapter.action_manager.registry.get_action.return_value = MagicMock()
        adapter.action_manager.call_action.side_effect = RuntimeError("action crashed")
        result = adapter.call_action("crashing_action")
        assert isinstance(result, ActionResultModel)
        assert result.success is False

    def test_call_action_available_actions_in_error_context(self):
        adapter = _make_adapter()
        adapter.action_manager.registry.get_action.return_value = None
        adapter.action_manager.registry.list_actions.return_value = [
            {"name": "available_a"},
            {"name": "available_b"},
        ]
        result = adapter.call_action("missing_action")
        assert "available_actions" in result.context
        assert "available_a" in result.context["available_actions"]


# ---------------------------------------------------------------------------
# get_action_adapter module-level function
# ---------------------------------------------------------------------------

class TestGetActionAdapter:
    """Tests for the get_action_adapter factory function (lines 227-239)."""

    def test_returns_action_adapter_instance(self):
        adapter = get_action_adapter("my_adapter")
        assert isinstance(adapter, ActionAdapter)
        assert adapter.name == "my_adapter"

    def test_different_names_give_different_instances(self):
        a1 = get_action_adapter("adapter_x")
        a2 = get_action_adapter("adapter_y")
        assert a1.name != a2.name
