"""Tests for dcc_mcp_ipc.server.decorators module.

Covers with_environment_info, with_scene_info, and with_session_info.
"""

# Import built-in modules
from unittest.mock import MagicMock

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.server.decorators import with_environment_info
from dcc_mcp_ipc.server.decorators import with_scene_info
from dcc_mcp_ipc.server.decorators import with_session_info


class _FakeService:
    """Minimal service stub that mimics a DCC service object."""

    def get_environment_info(self):
        return {"platform": "test", "python": "3.x"}

    def get_scene_info(self):
        return {"scene": "test_scene", "objects": []}

    def get_session_info(self):
        return {"session_id": "abc123", "connected": True}

    @with_environment_info
    def action_with_env(self):
        return {"data": "env_payload"}

    @with_scene_info
    def action_with_scene(self):
        return {"data": "scene_payload"}

    @with_session_info
    def action_with_session(self):
        return {"data": "session_payload"}

    @with_environment_info
    def action_returns_non_dict(self):
        return "plain_string"

    @with_scene_info
    def action_raises(self):
        raise RuntimeError("action failed")


class TestWithEnvironmentInfo:
    """Tests for with_environment_info decorator."""

    def test_adds_environment_info_key(self) -> None:
        svc = _FakeService()
        result = svc.action_with_env()
        assert "environment_info" in result
        assert result["environment_info"]["platform"] == "test"

    def test_preserves_original_result(self) -> None:
        svc = _FakeService()
        result = svc.action_with_env()
        assert result["data"] == "env_payload"

    def test_non_dict_result_wrapped(self) -> None:
        svc = _FakeService()
        result = svc.action_returns_non_dict()
        assert "environment_info" in result
        # Non-dict gets wrapped in {"result": ...}
        assert "result" in result or "data" in result


class TestWithSceneInfo:
    """Tests for with_scene_info decorator."""

    def test_adds_scene_info_key(self) -> None:
        svc = _FakeService()
        result = svc.action_with_scene()
        assert "scene_info" in result
        assert result["scene_info"]["scene"] == "test_scene"

    def test_preserves_original_result(self) -> None:
        svc = _FakeService()
        result = svc.action_with_scene()
        assert result["data"] == "scene_payload"

    def test_exception_propagates(self) -> None:
        svc = _FakeService()
        with pytest.raises(RuntimeError, match="action failed"):
            svc.action_raises()


class TestWithSessionInfo:
    """Tests for with_session_info decorator — covers line 74."""

    def test_adds_session_info_key(self) -> None:
        svc = _FakeService()
        result = svc.action_with_session()
        assert "session_info" in result
        assert result["session_info"]["session_id"] == "abc123"
        assert result["session_info"]["connected"] is True

    def test_preserves_original_result(self) -> None:
        svc = _FakeService()
        result = svc.action_with_session()
        assert result["data"] == "session_payload"

    def test_returns_function(self) -> None:
        """with_session_info should return a callable."""

        def dummy(self):
            return {}

        wrapped = with_session_info(dummy)
        assert callable(wrapped)
