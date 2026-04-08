"""Iteration-11 coverage tests for action_adapter, adapter/dcc, and __init__ lazy-import.

Covers previously uncovered branches:
- ActionAdapter.search_actions (error path)
- ActionAdapter.register_actions_batch (missing/invalid spec, exception paths)
- ActionAdapter.unregister_action (registry.unregister raises → pass)
- ActionAdapter.call_action (output is ActionResultModel, output is non-dict non-ARM scalar)
- DCCAdapter._initialize_client (exception path → client=None)
- DCCAdapter.get_application_info / get_scene_info / get_session_info (error paths)
- DCCAdapter.execute_command / execute_script (error + return-dict paths)
- DCCAdapter.execute_script (non-python type, return dict path)
- dcc_mcp_ipc.__init__ lazy __getattr__ (unknown attribute → AttributeError)
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
from dcc_mcp_core import ActionResultModel
import pytest

# Import local modules
from dcc_mcp_ipc.action_adapter import ActionAdapter
from dcc_mcp_ipc.action_adapter import get_action_adapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adapter(name="iter11_adapter"):
    """Return ActionAdapter with fully mocked registry and dispatcher."""
    adapter = object.__new__(ActionAdapter)
    adapter.name = name
    adapter.dcc_name = "python"
    adapter.registry = MagicMock()
    adapter.dispatcher = MagicMock()
    return adapter


# ---------------------------------------------------------------------------
# ActionAdapter.search_actions — error path (lines 155-163)
# ---------------------------------------------------------------------------


class TestSearchActions:
    """Tests for search_actions edge cases."""

    def test_search_actions_success(self):
        adapter = _make_adapter()
        adapter.registry.search_actions.return_value = [
            {"name": "my_action", "category": "scene"}
        ]
        result = adapter.search_actions(category="scene")
        assert isinstance(result, list)
        assert result[0]["name"] == "my_action"

    def test_search_actions_error_returns_empty_list(self):
        """search_actions catches exception and returns []."""
        adapter = _make_adapter()
        adapter.registry.search_actions.side_effect = AttributeError("not supported")
        result = adapter.search_actions(category="scene", tags=["mesh"])
        assert result == []

    def test_search_actions_no_filters(self):
        adapter = _make_adapter()
        adapter.registry.search_actions.return_value = []
        result = adapter.search_actions()
        adapter.registry.search_actions.assert_called_once_with(
            category=None, tags=None, dcc_name="python"
        )
        assert result == []


# ---------------------------------------------------------------------------
# ActionAdapter.register_actions_batch (lines 181-193)
# ---------------------------------------------------------------------------


class TestRegisterActionsBatch:
    """Tests for register_actions_batch."""

    def test_batch_registers_valid_specs(self):
        adapter = _make_adapter()
        h1 = MagicMock()
        h2 = MagicMock()
        specs = [
            {"name": "action_a", "handler": h1, "description": "first"},
            {"name": "action_b", "handler": h2},
        ]
        count = adapter.register_actions_batch(specs)
        assert count == 2

    def test_batch_skips_spec_without_name(self):
        adapter = _make_adapter()
        specs = [{"handler": MagicMock(), "description": "no name"}]
        count = adapter.register_actions_batch(specs)
        assert count == 0

    def test_batch_skips_spec_without_handler(self):
        adapter = _make_adapter()
        specs = [{"name": "nameless_handler"}]
        count = adapter.register_actions_batch(specs)
        assert count == 0

    def test_batch_handles_register_failure_gracefully(self):
        """If register_action raises, batch continues and skips that entry."""
        adapter = _make_adapter()
        adapter.registry.register.side_effect = Exception("registry error")
        h = MagicMock()
        specs = [{"name": "bad_action", "handler": h}]
        count = adapter.register_actions_batch(specs)
        assert count == 0

    def test_batch_partial_success(self):
        """First spec fails, second succeeds → count=1."""
        adapter = _make_adapter()
        call_count = [0]

        def selective_fail(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("first fails")

        adapter.registry.register.side_effect = selective_fail
        specs = [
            {"name": "action_fail", "handler": MagicMock()},
            {"name": "action_ok", "handler": MagicMock()},
        ]
        count = adapter.register_actions_batch(specs)
        assert count == 1

    def test_batch_empty_list_returns_zero(self):
        adapter = _make_adapter()
        count = adapter.register_actions_batch([])
        assert count == 0


# ---------------------------------------------------------------------------
# ActionAdapter.unregister_action — registry.unregister raises → pass
# (line 131-132 branch)
# ---------------------------------------------------------------------------


class TestUnregisterActionEdgeCases:
    """Edge cases for unregister_action."""

    def test_unregister_with_registry_error_still_returns_true(self):
        """Dispatcher removal succeeds even if registry.unregister raises."""
        adapter = _make_adapter()
        adapter.dispatcher.remove_handler.return_value = True
        adapter.registry.unregister.side_effect = RuntimeError("unregister failed")
        result = adapter.unregister_action("some_action")
        # Should still return True — registry unregister is best-effort
        assert result is True


# ---------------------------------------------------------------------------
# ActionAdapter.call_action — output is ActionResultModel (line 257)
# and output is non-dict non-ARM (line 265)
# ---------------------------------------------------------------------------


class TestCallActionOutputBranches:
    """Tests for call_action dispatch result branches."""

    def test_output_is_action_result_model_returned_directly(self):
        """When output is an ActionResultModel, it should be returned as-is (line 257)."""
        adapter = _make_adapter()
        arm = ActionResultModel(
            success=True,
            message="pre-built result",
            context={"key": "val"},
        )
        adapter.dispatcher.dispatch.return_value = {"output": arm}
        result = adapter.call_action("action_name")
        assert result is arm

    def test_output_is_non_dict_scalar_wrapped(self):
        """When output is a scalar (not dict/ARM), it's wrapped with success_result (line 265)."""
        adapter = _make_adapter()
        adapter.dispatcher.dispatch.return_value = {"output": 42}
        result = adapter.call_action("action_name")
        assert isinstance(result, ActionResultModel)
        assert result.success is True
        # context wraps the raw output
        assert result.context is not None

    def test_output_is_list_wrapped(self):
        """Lists are non-dict non-ARM scalars, also wrapped (line 265)."""
        adapter = _make_adapter()
        adapter.dispatcher.dispatch.return_value = {"output": [1, 2, 3]}
        result = adapter.call_action("action_name")
        assert isinstance(result, ActionResultModel)
        assert result.success is True

    def test_output_is_dict_without_success_key(self):
        """Dict output without 'success' key → success defaults to True."""
        adapter = _make_adapter()
        adapter.dispatcher.dispatch.return_value = {
            "output": {"custom_key": "custom_value"}
        }
        result = adapter.call_action("action_name")
        assert isinstance(result, ActionResultModel)
        assert result.success is True

    def test_output_is_dict_with_error_key(self):
        """Dict output with 'error' key."""
        adapter = _make_adapter()
        adapter.dispatcher.dispatch.return_value = {
            "output": {"success": False, "message": "failed", "error": "oops"}
        }
        result = adapter.call_action("action_name")
        assert isinstance(result, ActionResultModel)
        assert result.success is False
        assert result.error == "oops"


# ---------------------------------------------------------------------------
# DCCAdapter — error and edge-case paths
# ---------------------------------------------------------------------------


def _create_dcc_adapter():
    """Create a DCCAdapter with mocked dependencies."""
    # Import local modules
    from dcc_mcp_ipc.adapter.dcc import DCCAdapter

    class ConcreteDCC(DCCAdapter):
        def _initialize_action_paths(self):
            self._action_paths = []

    with (
        patch("dcc_mcp_ipc.adapter.base.get_action_adapter"),
        patch("dcc_mcp_ipc.adapter.dcc.get_client") as mock_get_client,
    ):
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        mock_get_client.return_value = mock_client
        adapter = ConcreteDCC("maya")
        adapter.client = mock_client
    return adapter


class TestDCCAdapterInitializeClientError:
    """Tests for _initialize_client failure path (lines 76-78)."""

    def test_client_init_exception_sets_client_to_none(self):
        """When get_client raises, _initialize_client sets self.client = None."""
        from dcc_mcp_ipc.adapter.dcc import DCCAdapter

        class ConcreteDCC(DCCAdapter):
            def _initialize_action_paths(self):
                self._action_paths = []

        with (
            patch("dcc_mcp_ipc.adapter.base.get_action_adapter"),
            patch("dcc_mcp_ipc.adapter.dcc.get_client") as mock_get_client,
        ):
            mock_get_client.side_effect = ConnectionRefusedError("DCC not running")
            adapter = ConcreteDCC("maya")

        assert adapter.client is None


class TestDCCAdapterGetAppInfoError:
    """Tests for get_application_info error path (lines 101-103)."""

    def test_get_application_info_client_raises(self):
        adapter = _create_dcc_adapter()
        adapter.client.get_dcc_info.side_effect = RuntimeError("RPC error")
        result = adapter.get_application_info()
        assert result["success"] is False
        assert "Failed to retrieve" in result["message"]
        assert result["error"] is not None


class TestDCCAdapterGetSceneInfoError:
    """Tests for get_scene_info error path."""

    def test_get_scene_info_client_raises(self):
        adapter = _create_dcc_adapter()
        adapter.client.get_scene_info.side_effect = RuntimeError("scene error")
        result = adapter.get_scene_info()
        assert result["success"] is False
        assert "Failed" in result["message"]


class TestDCCAdapterGetSessionInfoError:
    """Tests for get_session_info not-connected and error paths."""

    def test_get_session_info_not_connected(self):
        adapter = _create_dcc_adapter()
        adapter.client = None
        result = adapter.get_session_info()
        assert result["success"] is False
        assert "Not connected" in result["message"]

    def test_get_session_info_client_raises(self):
        adapter = _create_dcc_adapter()
        adapter.client.get_session_info.side_effect = RuntimeError("session error")
        result = adapter.get_session_info()
        assert result["success"] is False


class TestDCCAdapterExecuteCommandEdgeCases:
    """Tests for execute_command edge cases (lines 219, 229-236)."""

    def test_execute_command_not_connected(self):
        adapter = _create_dcc_adapter()
        adapter.client = None
        result = adapter.execute_command("cmd")
        assert result["success"] is False
        assert "Not connected" in result["message"]

    def test_execute_command_returns_dict_with_success_key(self):
        """If client returns a dict with 'success', it should be returned directly."""
        adapter = _create_dcc_adapter()
        adapter.client.execute_command.return_value = {
            "success": True,
            "message": "done",
            "context": {},
        }
        result = adapter.execute_command("cmd")
        # Should be passed through unchanged
        assert result["success"] is True
        assert result["message"] == "done"

    def test_execute_command_client_raises(self):
        """Lines 237-239: exception wrapped in failure result."""
        adapter = _create_dcc_adapter()
        adapter.client.execute_command.side_effect = RuntimeError("cmd failed")
        result = adapter.execute_command("my_cmd", arg="val")
        assert result["success"] is False
        assert "Failed to execute command" in result["message"]
        assert "my_cmd" in result["message"]


class TestDCCAdapterExecuteScriptEdgeCases:
    """Tests for execute_script edge cases (lines 257-287)."""

    def test_execute_script_not_connected(self):
        adapter = _create_dcc_adapter()
        adapter.client = None
        result = adapter.execute_script("print('hi')")
        assert result["success"] is False

    def test_execute_python_script_success(self):
        adapter = _create_dcc_adapter()
        adapter.client.execute_python.return_value = {"output": "hello"}
        result = adapter.execute_script("print('hi')", script_type="python")
        assert result["success"] is True

    def test_execute_python_returns_dict_with_success(self):
        """Lines 271-273: client returns dict with 'success' key → pass-through."""
        adapter = _create_dcc_adapter()
        adapter.client.execute_python.return_value = {
            "success": True,
            "message": "executed",
        }
        result = adapter.execute_script("print('hi')")
        assert result["success"] is True
        assert result["message"] == "executed"

    def test_execute_non_python_script(self):
        """Lines 268-270: non-python scripts call execute_script."""
        adapter = _create_dcc_adapter()
        adapter.client.execute_script.return_value = {"result": "mel_output"}
        result = adapter.execute_script("print #hi", script_type="mel")
        assert result["success"] is True

    def test_execute_script_client_raises(self):
        """Lines 280-286: exception wrapped in failure result."""
        adapter = _create_dcc_adapter()
        adapter.client.execute_python.side_effect = RuntimeError("script error")
        result = adapter.execute_script("invalid_code")
        assert result["success"] is False
        assert "Failed to execute python script" in result["message"]


# ---------------------------------------------------------------------------
# dcc_mcp_ipc.__init__ lazy __getattr__ — error paths
# ---------------------------------------------------------------------------


class TestPackageInit:
    """Tests for __init__.py lazy import machinery."""

    def test_getattr_unknown_name_raises_attribute_error(self):
        """Accessing a name not in _LAZY_IMPORTS raises AttributeError."""
        import dcc_mcp_ipc

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = dcc_mcp_ipc.nonexistent_attribute_xyz

    def test_getattr_known_name_resolves_lazily(self):
        """Accessing a known lazy symbol returns the correct object."""
        import dcc_mcp_ipc

        # ActionAdapter is a known lazy import
        cls = dcc_mcp_ipc.ActionAdapter
        assert cls is not None
        # Second access returns cached value (stored in globals)
        cls2 = dcc_mcp_ipc.ActionAdapter
        assert cls is cls2

    def test_dir_includes_all_public_names(self):
        """__dir__ should include all names in __all__."""
        import dcc_mcp_ipc

        names = dir(dcc_mcp_ipc)
        for public_name in dcc_mcp_ipc.__all__:
            assert public_name in names
