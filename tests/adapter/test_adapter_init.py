"""Tests for the adapter __init__ module (get_adapter factory function).

Covers the global adapter registry and factory logic.
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.adapter import get_adapter
from dcc_mcp_ipc.adapter.dcc import DCCAdapter
from dcc_mcp_ipc.adapter.session import SessionAdapter


@pytest.fixture(autouse=True)
def clear_adapter_registry():
    """Clear the global adapter registry before each test."""
    with patch("dcc_mcp_ipc.adapter._adapters", {}):
        yield


class TestGetAdapter:
    """Tests for the get_adapter factory function."""

    def test_get_adapter_session_type(self):
        """Test creating a session adapter."""
        with patch("dcc_mcp_ipc.adapter.SessionAdapter") as mock_session_cls:
            mock_adapter = MagicMock()
            mock_session_cls.return_value = mock_adapter

            adapter = get_adapter("maya", adapter_type="session")

            mock_session_cls.assert_called_once_with("maya", session_id=None)
            assert adapter is mock_adapter

    def test_get_adapter_dcc_type(self):
        """Test creating a DCC adapter."""
        with patch("dcc_mcp_ipc.adapter.DCCAdapter") as mock_dcc_cls:
            mock_adapter = MagicMock()
            mock_dcc_cls.return_value = mock_adapter

            adapter = get_adapter("maya", adapter_type="dcc")

            mock_dcc_cls.assert_called_once_with("maya")
            assert adapter is mock_adapter

    def test_get_adapter_unsupported_type(self):
        """Test that unsupported adapter type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported adapter type"):
            get_adapter("maya", adapter_type="unsupported")

    def test_get_adapter_returns_cached(self):
        """Test that the same adapter instance is returned for the same key."""
        mock_adapter = MagicMock()
        key = "maya_session_"
        with patch("dcc_mcp_ipc.adapter._adapters", {key: mock_adapter}):
            adapter = get_adapter("maya", adapter_type="session")
            assert adapter is mock_adapter

    def test_get_adapter_with_session_id(self):
        """Test creating adapter with a session ID."""
        with patch("dcc_mcp_ipc.adapter.SessionAdapter") as mock_session_cls:
            mock_adapter = MagicMock()
            mock_session_cls.return_value = mock_adapter

            adapter = get_adapter("maya", adapter_type="session", session_id="abc123")

            mock_session_cls.assert_called_once_with("maya", session_id="abc123")
            assert adapter is mock_adapter

    def test_get_adapter_registers_in_cache(self):
        """Test that a new adapter is stored in the global registry."""
        registry = {}
        with (
            patch("dcc_mcp_ipc.adapter._adapters", registry),
            patch("dcc_mcp_ipc.adapter.SessionAdapter") as mock_session_cls,
        ):
            mock_adapter = MagicMock()
            mock_session_cls.return_value = mock_adapter

            get_adapter("blender", adapter_type="session")

            assert "blender_session_" in registry


class TestDCCAdapterExtended:
    """Extended tests for DCCAdapter covering previously uncovered lines."""

    def _make_adapter(self, dcc_name="test_dcc", host="localhost", port=8000):
        """Create a concrete DCCAdapter with mocked dependencies."""

        class ConcreteDCCAdapter(DCCAdapter):
            def _initialize_action_paths(self):
                self._action_paths = []

        with (
            patch("dcc_mcp_ipc.adapter.base.get_action_adapter"),
            patch("dcc_mcp_ipc.adapter.dcc.get_client") as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.is_connected.return_value = True
            mock_get_client.return_value = mock_client
            adapter = ConcreteDCCAdapter(dcc_name, host, port)
            return adapter, mock_client

    def test_get_scene_info_success(self):
        """Test get_scene_info returns scene data on success."""
        adapter, mock_client = self._make_adapter()
        mock_client.get_scene_info.return_value = {"objects": ["cube", "sphere"]}

        result = adapter.get_scene_info()

        assert result["success"] is True
        assert result["context"]["objects"] == ["cube", "sphere"]

    def test_get_scene_info_not_connected(self):
        """Test get_scene_info returns error when not connected."""
        adapter, _mock_client = self._make_adapter()
        adapter.client = None

        result = adapter.get_scene_info()

        assert result["success"] is False
        assert "Not connected" in result["message"]

    def test_get_scene_info_exception(self):
        """Test get_scene_info handles exception gracefully."""
        adapter, mock_client = self._make_adapter()
        mock_client.get_scene_info.side_effect = RuntimeError("scene error")

        result = adapter.get_scene_info()

        assert result["success"] is False
        assert "scene error" in result["error"]

    def test_get_session_info_success(self):
        """Test get_session_info returns session data on success."""
        adapter, mock_client = self._make_adapter()
        mock_client.get_session_info.return_value = {"session_id": "s1", "user": "artist"}

        result = adapter.get_session_info()

        assert result["success"] is True
        assert result["context"]["session_id"] == "s1"

    def test_get_session_info_not_connected(self):
        """Test get_session_info returns error when not connected."""
        adapter, _mock_client = self._make_adapter()
        adapter.client = None

        result = adapter.get_session_info()

        assert result["success"] is False

    def test_get_session_info_exception(self):
        """Test get_session_info handles exception gracefully."""
        adapter, mock_client = self._make_adapter()
        mock_client.get_session_info.side_effect = RuntimeError("session error")

        result = adapter.get_session_info()

        assert result["success"] is False

    def test_create_primitive_success(self):
        """Test create_primitive returns success result."""
        adapter, mock_client = self._make_adapter()
        mock_client.create_primitive.return_value = {"name": "cube1"}

        result = adapter.create_primitive("cube", size=1.0)

        assert result["success"] is True
        assert result["context"]["name"] == "cube1"
        mock_client.create_primitive.assert_called_once_with("cube", size=1.0)

    def test_create_primitive_already_dict_result(self):
        """Test create_primitive passes through dict with 'success' key."""
        adapter, mock_client = self._make_adapter()
        mock_client.create_primitive.return_value = {"success": True, "message": "created", "context": {}}

        result = adapter.create_primitive("sphere")

        assert result["success"] is True

    def test_create_primitive_not_connected(self):
        """Test create_primitive returns error when not connected."""
        adapter, _mock_client = self._make_adapter()
        adapter.client = None

        result = adapter.create_primitive("cube")

        assert result["success"] is False

    def test_create_primitive_exception(self):
        """Test create_primitive handles exception gracefully."""
        adapter, mock_client = self._make_adapter()
        mock_client.create_primitive.side_effect = RuntimeError("create error")

        result = adapter.create_primitive("cube")

        assert result["success"] is False
        assert "create error" in result["error"]

    def test_execute_script_python(self):
        """Test execute_script with Python script type."""
        adapter, mock_client = self._make_adapter()
        mock_client.execute_python.return_value = {"result": 42}

        result = adapter.execute_script("print(42)", script_type="python")

        assert result["success"] is True
        mock_client.execute_python.assert_called_once_with("print(42)")

    def test_execute_script_other_type(self):
        """Test execute_script with non-Python script type."""
        adapter, mock_client = self._make_adapter()
        mock_client.execute_script.return_value = {"result": "mel_result"}

        result = adapter.execute_script("polyCube;", script_type="mel")

        assert result["success"] is True
        mock_client.execute_script.assert_called_once_with("polyCube;", "mel")

    def test_execute_script_not_connected(self):
        """Test execute_script returns error when not connected."""
        adapter, _mock_client = self._make_adapter()
        adapter.client = None

        result = adapter.execute_script("print('hi')")

        assert result["success"] is False

    def test_execute_script_exception(self):
        """Test execute_script handles exception gracefully."""
        adapter, mock_client = self._make_adapter()
        mock_client.execute_python.side_effect = RuntimeError("exec error")

        result = adapter.execute_script("bad_code")

        assert result["success"] is False

    def test_execute_command_already_dict_result(self):
        """Test execute_command passes through dict with 'success' key."""
        adapter, mock_client = self._make_adapter()
        mock_client.execute_command.return_value = {"success": False, "error": "denied", "message": ""}

        result = adapter.execute_command("restricted_cmd")

        assert result["success"] is False


class TestApplicationAdapterBase:
    """Tests for ApplicationAdapter base class (adapter/base.py) uncovered lines."""

    def _make_concrete_adapter(self):
        """Create a minimal concrete adapter for testing base class."""
        # Import local modules
        from dcc_mcp_ipc.adapter.base import ApplicationAdapter

        class ConcreteAdapter(ApplicationAdapter):
            def _initialize_client(self):
                self.client = None

            def _initialize_action_paths(self):
                self._action_paths = []

            def get_application_info(self):
                return {}

        with patch("dcc_mcp_ipc.adapter.base.get_action_adapter") as mock_ga:
            mock_action_adapter = MagicMock()
            mock_ga.return_value = mock_action_adapter
            adapter = ConcreteAdapter("test_app")
            return adapter, mock_action_adapter

    def test_ensure_connected_no_client(self):
        """Test ensure_connected returns False when client is None."""
        adapter, _ = self._make_concrete_adapter()
        adapter.client = None

        assert adapter.ensure_connected() is False

    def test_ensure_connected_already_connected(self):
        """Test ensure_connected returns True when already connected."""
        adapter, _ = self._make_concrete_adapter()
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        adapter.client = mock_client

        assert adapter.ensure_connected() is True
        mock_client.connect.assert_not_called()

    def test_ensure_connected_reconnects(self):
        """Test ensure_connected tries to reconnect when disconnected."""
        adapter, _ = self._make_concrete_adapter()
        mock_client = MagicMock()
        mock_client.is_connected.return_value = False
        mock_client.connect.return_value = True
        adapter.client = mock_client

        assert adapter.ensure_connected() is True
        mock_client.connect.assert_called_once()

    def test_ensure_connected_reconnect_fails(self):
        """Test ensure_connected returns False on reconnect failure."""
        adapter, _ = self._make_concrete_adapter()
        mock_client = MagicMock()
        mock_client.is_connected.return_value = False
        mock_client.connect.side_effect = RuntimeError("refused")
        adapter.client = mock_client

        assert adapter.ensure_connected() is False

    def test_action_paths_setter(self):
        """Test action_paths setter updates the internal list."""
        adapter, _mock_action_adapter = self._make_concrete_adapter()

        adapter.action_paths = ["/path/to/actions"]

        assert adapter._action_paths == ["/path/to/actions"]

    def test_execute_action_wraps_non_dict_result(self):
        """Test execute_action wraps non-dict results in ActionResultModel."""
        adapter, mock_action_adapter = self._make_concrete_adapter()
        mock_action_adapter.execute_action.return_value = "raw_string_result"

        result = adapter.execute_action("my_action")

        assert result["success"] is True
        assert result["context"]["result"] == "raw_string_result"

    def test_execute_action_passes_through_dict(self):
        """Test execute_action passes through dicts with 'success' key."""
        adapter, mock_action_adapter = self._make_concrete_adapter()
        mock_action_adapter.execute_action.return_value = {
            "success": True,
            "message": "done",
            "context": {"key": "val"},
        }

        result = adapter.execute_action("my_action")

        assert result["success"] is True
        assert result["context"]["key"] == "val"

    def test_execute_action_exception(self):
        """Test execute_action handles exception."""
        adapter, mock_action_adapter = self._make_concrete_adapter()
        mock_action_adapter.execute_action.side_effect = RuntimeError("action error")

        result = adapter.execute_action("failing_action")

        assert result["success"] is False
        assert "action error" in result["error"]
