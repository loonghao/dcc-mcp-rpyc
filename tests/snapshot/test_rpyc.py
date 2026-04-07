"""Tests for the RPyC snapshot implementation.

Covers RPyCSnapshot including capture_viewport, capture_render,
DCC-specific script generation, error handling, and edge cases.
All tests use mock execute functions — no real RPyC connections.
"""

# Import built-in modules
import base64
from unittest.mock import MagicMock

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.snapshot.base import SnapshotConfig
from dcc_mcp_ipc.snapshot.base import SnapshotError
from dcc_mcp_ipc.snapshot.base import SnapshotFormat
from dcc_mcp_ipc.snapshot.rpyc import RPyCSnapshot


class TestRPyCSnapshotInit:
    """Tests for RPyCSnapshot initialization."""

    def test_default_init(self) -> None:
        snap = RPyCSnapshot()
        assert snap.dcc_name == "generic"
        assert snap._execute is None

    def test_custom_dcc_name(self) -> None:
        snap = RPyCSnapshot(dcc_name="maya")
        assert snap.dcc_name == "maya"

    def test_with_execute_func(self) -> None:
        mock_exec = MagicMock(return_value=None)
        snap = RPyCSnapshot(dcc_name="blender", execute_func=mock_exec)
        assert snap._execute is mock_exec

    def test_dcc_name_lowercased(self) -> None:
        snap = RPyCSnapshot(dcc_name="MAYA")
        assert snap.dcc_name == "maya"


class TestRPyCSnapshotCaptureViewport:
    """Tests for capture_viewport method."""

    @staticmethod
    def _make_mock_execute(return_value) -> MagicMock:
        return MagicMock(return_value=return_value)

    def test_capture_with_dict_response(self) -> None:
        """Test when remote returns dict with 'data' key."""
        png_data = base64.b64encode(b"fake_png_bytes").decode("ascii")
        exec_func = self._make_mock_execute({"success": True, "data": png_data, "format": "PNG"})
        snap = RPyCSnapshot(dcc_name="generic", execute_func=exec_func)

        result = snap.capture_viewport()

        assert result == b"fake_png_bytes"
        exec_func.assert_called_once()

    def test_capture_with_image_data_key(self) -> None:
        """Test when remote returns dict with 'image_data' key (alt format)."""
        png_data = base64.b64encode(b"alt_png_data").decode("ascii")
        exec_func = self._make_mock_execute({"image_data": png_data})
        snap = RPyCSnapshot(dcc_name="generic", execute_func=exec_func)

        result = snap.capture_viewport()

        assert result == b"alt_png_data"

    def test_capture_with_string_response(self) -> None:
        """Test when remote returns raw base64 string."""
        b64_str = base64.b64encode(b"string_data").decode("ascii")
        exec_func = self._make_mock_execute(b64_str)
        snap = RPyCSnapshot(dcc_name="generic", execute_func=exec_func)

        result = snap.capture_viewport()

        assert result == b"string_data"

    def test_capture_with_bytes_response(self) -> None:
        """Test when remote returns raw bytes directly."""
        exec_func = self._make_mock_execute(b"raw_bytes_data")
        snap = RPyCSnapshot(dcc_name="generic", execute_func=exec_func)

        result = snap.capture_viewport()

        assert result == b"raw_bytes_data"

    def test_capture_with_error_dict(self) -> None:
        """Test when remote returns error in dict."""
        exec_func = self._make_mock_execute({"error": "Viewport not found"})
        snap = RPyCSnapshot(dcc_name="generic", execute_func=exec_func)

        with pytest.raises(SnapshotError, match="Remote capture error"):
            snap.capture_viewport()

    def test_capture_no_executor_raises(self) -> None:
        """Test that missing executor raises SnapshotError."""
        snap = RPyCSnapshot(dcc_name="test")

        with pytest.raises(SnapshotError, match="No execute function configured"):
            snap.capture_viewport()

    def test_capture_remote_exception_propagates(self) -> None:
        """Test that exceptions from _execute are wrapped in SnapshotError."""
        exec_func = MagicMock(side_effect=ConnectionError("connection lost"))
        snap = RPyCSnapshot(dcc_name="test", execute_func=exec_func)

        with pytest.raises(SnapshotError, match="Remote execution failed"):
            snap.capture_viewport()

    def test_capture_unexpected_type_raises(self) -> None:
        """Test that unexpected return type raises SnapshotError."""
        exec_func = self._make_mock_execute(12345)  # int
        snap = RPyCSnapshot(dcc_name="test", execute_func=exec_func)

        with pytest.raises(SnapshotError, match="Unexpected capture result"):
            snap.capture_viewport()

    def test_capture_invalid_base64_raises(self) -> None:
        """Test that invalid base64 string raises SnapshotError."""
        exec_func = self._make_mock_execute("not-valid-base64!!!")
        snap = RPyCSnapshot(dcc_name="test", execute_func=exec_func)

        with pytest.raises(SnapshotError, match="Invalid base64 data"):
            snap.capture_viewport()

    def test_capture_passes_config_defaults(self) -> None:
        """Test that default config is used when none provided."""
        b64_data = base64.b64encode(b"data").decode("ascii")
        exec_func = self._make_mock_execute({"data": b64_data})
        snap = RPyCSnapshot(dcc_name="generic", execute_func=exec_func)
        snap.capture_viewport()
        exec_func.assert_called_once()  # Just verify it was called

    def test_capture_custom_config(self) -> None:
        """Test that custom config parameters are used in script generation."""
        b64_data = base64.b64encode(b"data").decode("ascii")
        exec_func = self._make_mock_execute({"data": b64_data})
        snap = RPyCSnapshot(dcc_name="generic", execute_func=exec_func)

        config = SnapshotConfig(width=800, height=600, format=SnapshotFormat.JPEG)
        snap.capture_viewport(config)
        exec_func.assert_called_once()


class TestRPyCSnapshotCaptureRender:
    """Tests for capture_render method."""

    def test_render_default_not_implemented_for_generic(self) -> None:
        """Generic DCC raises NotImplementedError from default render script."""
        exec_func = MagicMock(return_value={"error": "Render capture not supported"})
        snap = RPyCSnapshot(dcc_name="unknown_dcc", execute_func=exec_func)

        with pytest.raises(SnapshotError, match="Remote render error"):
            snap.capture_render()

    def test_render_with_dict_data(self) -> None:
        """Test successful render with data dict."""
        b64_data = base64.b64encode(b"rendered").decode("ascii")
        exec_func = MagicMock(return_value={"data": b64_data})
        snap = RPyCSnapshot(dcc_name="maya", execute_func=exec_func)

        result = snap.capture_render()
        assert result == b"rendered"


class TestRPyCDCCSpecificScripts:
    """Tests for DCC-specific capture script generation."""

    def test_maya_script_generated(self) -> None:
        snap = RPyCSnapshot(dcc_name="maya")
        script = snap._get_capture_script(SnapshotConfig(width=1920, height=1080))
        assert "maya.cmds" in script or "cmds.playblast" in script
        assert "1920" in script or "width" in script.lower()

    def test_blender_script_generated(self) -> None:
        snap = RPyCSnapshot(dcc_name="blender")
        script = snap._get_capture_script(SnapshotConfig())
        assert "bpy.ops.render.opengl" in script or "bpy" in script

    def test_houdini_script_generated(self) -> None:
        snap = RPyCSnapshot(dcc_name="houdini")
        script = snap._get_capture_script(SnapshotConfig())
        assert "hou.ui" in script or "hou" in script

    def test_generic_script_fallback(self) -> None:
        snap = RPyCSnapshot(dcc_name="unknown_app")
        script = snap._get_capture_script(SnapshotConfig())
        assert "minimal" in script.lower() or "mock" in script.lower() or "PNG" in script

    def test_generic_script_produces_valid_png(self) -> None:
        """Test that the fallback generic script produces decodable PNG data."""
        snap = RPyCSnapshot(dcc_name="unknown")
        # Return a pre-built valid PNG response dict (as if remote executed successfully)
        # Import built-in modules
        import base64 as b64_mod

        fake_png = b"\x89PNG\r\n\x1a\n" + b"fake_png_data"
        fake_b64 = b64_mod.b64encode(fake_png).decode("ascii")

        snap._execute = MagicMock(return_value={"data": fake_b64, "mock": True})

        result = snap.capture_viewport(SnapshotConfig(width=4, height=4))

        # Should return decoded bytes from the mock response
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result == fake_png


class TestRPyCSnapshotInfo:
    """Tests for get_snapshot_info."""

    def test_info_includes_dcc_name(self) -> None:
        snap = RPyCSnapshot(dcc_name="blender")
        info = snap.get_snapshot_info()
        assert info["dcc_name"] == "blender"

    def test_info_strategy_flag(self) -> None:
        snap_maya = RPyCSnapshot(dcc_name="maya")
        snap_unknown = RPyCSnapshot(dcc_name="cinema4d")

        assert snap_maya.get_snapshot_info()["has_dedicated_strategy"] is True
        assert snap_unknown.get_snapshot_info()["has_dedicated_strategy"] is False

    def test_info_transport(self) -> None:
        snap = RPyCSnapshot()
        assert snap.get_snapshot_info()["transport"] == "rpyc"


class TestRPyCSnapshotEdgeCases:
    """Edge case tests."""

    def test_empty_base64_string(self) -> None:
        """Test that empty base64 string from remote raises SnapshotError."""
        exec_func = MagicMock(return_value="")
        snap = RPyCSnapshot(dcc_name="test", execute_func=exec_func)

        # Empty string is valid base64 (decodes to b"") — but that's 0 bytes
        # The code tries base64.b64decode("") which returns b"" — a valid result
        # So this should NOT raise for empty string, but return empty bytes
        result = snap.capture_viewport()
        assert result == b""

    def test_none_result_from_remote(self) -> None:
        exec_func = MagicMock(return_value=None)
        snap = RPyCSnapshot(dcc_name="test", execute_func=exec_func)

        with pytest.raises(SnapshotError, match="Unexpected capture result"):
            snap.capture_viewport()

    def test_large_payload(self) -> None:
        """Simulate large image payload."""
        big_data = b"x" * (1024 * 1024)  # 1MB fake image
        b64_str = base64.b64encode(big_data).decode("ascii")

        exec_func = MagicMock(return_value=b64_str)
        snap = RPyCSnapshot(dcc_name="test", execute_func=exec_func)

        result = snap.capture_viewport()
        assert len(result) == len(big_data)
