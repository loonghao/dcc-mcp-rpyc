"""Tests for the Action system in DCC-MCP-IPC.

Tests cover ActionAdapter against the dcc-mcp-core Rust
ActionRegistry + ActionDispatcher backend.
"""

# Import built-in modules
import json

# Import third-party modules
from dcc_mcp_core import ActionResultModel
import pytest

# Import local modules
from dcc_mcp_ipc.action_adapter import ActionAdapter
from dcc_mcp_ipc.action_adapter import get_action_adapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _echo_handler(message: str = "hello") -> dict:
    """Simple handler that echoes the message back."""
    return {"success": True, "message": f"echo: {message}", "context": {"message": message}}


def _add_handler(a: int = 0, b: int = 0) -> dict:
    """Handler that adds two integers."""
    return {"success": True, "message": "ok", "context": {"result": a + b}}


def _failing_handler(**kwargs):
    """Handler that always raises."""
    raise RuntimeError("intentional failure")


# ---------------------------------------------------------------------------
# ActionAdapter unit tests
# ---------------------------------------------------------------------------

class TestActionAdapterCreation:
    """Tests for ActionAdapter initialisation."""

    def test_create_adapter(self):
        """Adapter is created with correct name and fresh registry."""
        adapter = ActionAdapter("unit_test")
        assert adapter.name == "unit_test"
        assert adapter.registry is not None
        assert adapter.dispatcher is not None

    def test_create_adapter_with_dcc_name(self):
        """dcc_name is stored and used for registry queries."""
        adapter = ActionAdapter("maya_test", dcc_name="maya")
        assert adapter.dcc_name == "maya"


class TestActionRegistration:
    """Tests for registering and unregistering actions."""

    def test_register_action(self):
        """Registered action appears in list_actions."""
        adapter = ActionAdapter("reg_test")
        adapter.register_action("echo", _echo_handler, description="Echo action")
        actions = adapter.list_actions()
        assert "echo" in actions

    def test_register_multiple_actions(self):
        """Multiple actions can be registered independently."""
        adapter = ActionAdapter("multi_reg")
        adapter.register_action("echo", _echo_handler)
        adapter.register_action("add", _add_handler)
        names = adapter.list_actions(names_only=True)
        assert "echo" in names
        assert "add" in names

    def test_list_actions_names_only(self):
        """names_only=True returns a list, not a dict."""
        adapter = ActionAdapter("names_only")
        adapter.register_action("echo", _echo_handler)
        result = adapter.list_actions(names_only=True)
        assert isinstance(result, list)
        assert "echo" in result

    def test_list_actions_full_metadata(self):
        """names_only=False returns metadata dicts."""
        adapter = ActionAdapter("full_meta")
        adapter.register_action("echo", _echo_handler, description="Echo it")
        result = adapter.list_actions(names_only=False)
        assert isinstance(result, dict)
        assert "echo" in result
        assert result["echo"]["name"] == "echo"

    def test_unregister_action(self):
        """Unregistered action is no longer dispatched."""
        adapter = ActionAdapter("unreg_test")
        adapter.register_action("echo", _echo_handler)
        removed = adapter.unregister_action("echo")
        assert removed is True
        # dispatcher should no longer have the handler
        assert not adapter.dispatcher.has_handler("echo")

    def test_unregister_nonexistent_returns_false(self):
        """Unregistering a non-existent action returns False."""
        adapter = ActionAdapter("unreg_miss")
        result = adapter.unregister_action("no_such_action")
        assert result is False

    def test_get_action_info(self):
        """get_action_info returns metadata for a registered action."""
        adapter = ActionAdapter("info_test")
        adapter.register_action("echo", _echo_handler, description="My echo")
        info = adapter.get_action_info("echo")
        assert info is not None
        assert info["name"] == "echo"

    def test_get_action_info_not_found(self):
        """get_action_info returns None for unknown actions."""
        adapter = ActionAdapter("info_miss")
        result = adapter.get_action_info("unknown")
        assert result is None


class TestActionDispatch:
    """Tests for calling/dispatching actions."""

    def test_call_action_success(self):
        """call_action returns an ActionResultModel on success."""
        adapter = ActionAdapter("dispatch_ok")
        adapter.register_action("echo", _echo_handler)

        result = adapter.call_action("echo", message="world")

        assert isinstance(result, ActionResultModel)
        assert result.success is True

    def test_call_action_result_contains_data(self):
        """Result context contains the handler's return data."""
        adapter = ActionAdapter("dispatch_data")
        adapter.register_action("add", _add_handler)

        result = adapter.call_action("add", a=3, b=4)

        assert result.success is True
        # The context wraps the handler dict — check either direct context or nested
        ctx = result.context
        assert ctx.get("result") == 7 or ctx.get("context", {}).get("result") == 7

    def test_call_action_failure_returns_error_model(self):
        """A handler that raises returns a failure ActionResultModel."""
        adapter = ActionAdapter("dispatch_fail")
        adapter.register_action("fail", _failing_handler)

        result = adapter.call_action("fail")

        assert isinstance(result, ActionResultModel)
        assert result.success is False

    def test_execute_action_returns_dict(self):
        """execute_action always returns a plain dict."""
        adapter = ActionAdapter("exec_dict")
        adapter.register_action("echo", _echo_handler)

        result = adapter.execute_action("echo", message="hi")

        assert isinstance(result, dict)
        assert "success" in result

    def test_call_unknown_action(self):
        """Dispatching an unknown action returns a failure model."""
        adapter = ActionAdapter("dispatch_unknown")

        result = adapter.call_action("no_such_action")

        assert isinstance(result, ActionResultModel)
        assert result.success is False


class TestActionAdapterFactory:
    """Tests for the module-level get_action_adapter factory."""

    def test_factory_returns_adapter(self):
        """get_action_adapter creates a new adapter."""
        adapter = get_action_adapter("factory_new_unique_123")
        assert isinstance(adapter, ActionAdapter)
        assert adapter.name == "factory_new_unique_123"

    def test_factory_caches_adapter(self):
        """Repeated calls with same name return the same instance."""
        a1 = get_action_adapter("factory_cached_abc")
        a2 = get_action_adapter("factory_cached_abc")
        assert a1 is a2

    def test_factory_different_names(self):
        """Different names produce distinct adapters."""
        a1 = get_action_adapter("fac_distinct_x")
        a2 = get_action_adapter("fac_distinct_y")
        assert a1 is not a2


class TestActionResultModel:
    """Smoke tests for the Rust ActionResultModel."""

    def test_create_success(self):
        """Default ActionResultModel is a success."""
        r = ActionResultModel()
        assert r.success is True

    def test_create_failure(self):
        """Can construct an explicit failure."""
        r = ActionResultModel(success=False, message="oops", error="boom")
        assert r.success is False
        assert r.error == "boom"

    def test_to_dict(self):
        """to_dict() returns a serialisable dict."""
        r = ActionResultModel(success=True, message="ok")
        d = r.to_dict()
        assert isinstance(d, dict)
        assert d["success"] is True
        assert d["message"] == "ok"

    def test_with_error(self):
        """with_error() returns updated model."""
        r = ActionResultModel(success=True).with_error("something went wrong")
        assert r.error == "something went wrong"

    def test_with_context(self):
        """with_context() merges kwargs into context."""
        r = ActionResultModel().with_context(foo="bar", baz=42)
        assert r.context.get("foo") == "bar"
        assert r.context.get("baz") == 42
