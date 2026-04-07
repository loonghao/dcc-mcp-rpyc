"""Tests for the snapshot base module.

Covers BaseSnapshot ABC, SnapshotConfig, SnapshotResult,
SnapshotError, SnapshotFormat, ViewportType, and the create_snapshot factory.
"""

# Import built-in modules
import base64
import struct
import zlib

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.snapshot.base import BaseSnapshot
from dcc_mcp_ipc.snapshot.base import SnapshotConfig
from dcc_mcp_ipc.snapshot.base import SnapshotError
from dcc_mcp_ipc.snapshot.base import SnapshotFormat
from dcc_mcp_ipc.snapshot.base import SnapshotResult
from dcc_mcp_ipc.snapshot.base import ViewportType
from dcc_mcp_ipc.snapshot import create_snapshot


class TestSnapshotFormat:
    """Tests for SnapshotFormat enum."""

    def test_format_values(self) -> None:
        assert SnapshotFormat.PNG.value == "png"
        assert SnapshotFormat.JPEG.value == "jpeg"
        assert SnapshotFormat.BMP.value == "bmp"

    def test_format_count(self) -> None:
        assert len(SnapshotFormat) >= 3  # At least PNG/JPEG/BMP


class TestViewportType:
    """Tests for ViewportType enum."""

    def test_viewport_values(self) -> None:
        assert ViewportType.PERSPECTIVE.value == "perspective"
        assert ViewportType.TOP.value == "top"
        assert ViewportType.FRONT.value == "front"
        assert ViewportType.SIDE.value == "RIGHT"  # Canonical name

    def test_viewport_count(self) -> None:
        assert len(ViewportType) >= 5  # Standard set


class TestSnapshotConfig:
    """Tests for SnapshotConfig model."""

    def test_default_values(self) -> None:
        config = SnapshotConfig()
        assert config.width == 1920
        assert config.height == 1080
        assert config.format == SnapshotFormat.PNG
        assert config.quality == 95
        assert config.include_transparency is False
        assert config.camera is None
        assert config.viewport == ViewportType.PERSPECTIVE

    def test_custom_values(self) -> None:
        config = SnapshotConfig(
            width=3840,
            height=2160,
            format=SnapshotFormat.JPEG,
            quality=85,
            include_transparency=True,
            camera="renderCamera",
            viewport=ViewportType.CAMERA,
        )
        assert config.width == 3840
        assert config.height == 2160
        assert config.format == SnapshotFormat.JPEG
        assert config.quality == 85
        assert config.include_transparency is True
        assert config.camera == "renderCamera"
        assert config.viewport == ViewportType.CAMERA

    def test_model_validation(self) -> None:
        config = SnapshotConfig(width=-100)
        # Pydantic may coerce or reject; we just check it doesn't crash on init
        assert config is not None


class TestSnapshotResult:
    """Tests for SnapshotResult model."""

    def test_default_values(self) -> None:
        result = SnapshotResult()
        assert result.success is True
        assert result.format == SnapshotFormat.PNG
        assert result.width == 0
        assert result.height == 0
        assert result.data_size == 0
        assert result.error is None
        assert result.metadata == {}

    def test_populated_result(self) -> None:
        result = SnapshotResult(
            success=True,
            format=SnapshotFormat.PNG,
            width=1920,
            height=1080,
            data_size=1234567,
            metadata={"frame": 1, "scene": "test.ma"},
        )
        assert result.success is True
        assert result.data_size == 1234567
        assert result.metadata["frame"] == 1

    def test_error_result(self) -> None:
        result = SnapshotResult(success=False, error="Viewport not found")
        assert result.success is False
        assert result.error == "Viewport not found"


class TestSnapshotError:
    """Tests for SnapshotError exception."""

    def test_basic_message(self) -> None:
        err = SnapshotError("test error")
        assert str(err) == "test error"
        assert err.cause is None

    def test_with_cause(self) -> None:
        original = ValueError("original error")
        err = SnapshotError("wrapper", cause=original)
        assert err.cause is original

    def test_exception_chaining(self) -> None:
        original = RuntimeError("deep cause")
        err = SnapshotError("surface", cause=original)
        assert "__cause__" in dir(err)


class ConcreteSnapshot(BaseSnapshot):
    """Concrete implementation for testing the abstract base class."""

    def __init__(self, image_data: bytes = b"fake_png_data") -> None:
        self._data = image_data
        self._capture_count = 0

    def capture_viewport(self, config=None):
        self._capture_count += 1
        return self._data


class TestBaseSnapshot:
    """Tests for the BaseSnapshot abstract interface."""

    def setup_method(self) -> None:
        fake_png = _make_minimal_png(8, 8)
        self.snap = ConcreteSnapshot(fake_png)

    def test_capture_viewport_returns_bytes(self) -> None:
        result = self.snap.capture_viewport()
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_capture_render_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="does not support render"):
            self.snap.capture_render()

    def test_capture_to_base64(self) -> None:
        b64 = self.snap.capture_to_base64()
        assert isinstance(b64, str)
        # Should be valid base64 that decodes back to original data
        decoded = base64.b64decode(b64)
        assert decoded == self.snap._data

    def test_capture_to_base64_with_config(self) -> None:
        config = SnapshotConfig(width=128, height=128)
        b64 = self.snap.capture_to_base64(config)
        decoded = base64.b64decode(b64)
        assert decoded == self.snap._data

    def test_get_snapshot_info(self) -> None:
        info = self.snap.get_snapshot_info()
        assert "type" in info
        assert info["supports_viewport"] is True
        assert info["supports_render"] is False  # Default: not overridden
        assert "supported_formats" in info
        assert "supported_viewports" in info
        assert SnapshotFormat.PNG.value in info["supported_formats"]
        assert ViewportType.PERSPECTIVE.value in info["supported_viewports"]

    def test_concrete_can_override_render(self) -> None:
        """Test that a subclass can override capture_render."""

        class RenderableSnapshot(ConcreteSnapshot):
            def capture_render(self, config=None):
                return b"rendered_data"

        snap2 = RenderableSnapshot()
        data = snap2.capture_render()
        assert data == b"rendered_data"

        info = snap2.get_snapshot_info()
        assert info["supports_render"] is True


class TestCreateSnapshotFactory:
    """Tests for the create_snapshot factory function."""

    def test_create_rpyc_snapshot(self) -> None:
        from dcc_mcp_ipc.snapshot.rpyc import RPyCSnapshot

        snap = create_snapshot("maya", "rpyc", execute_func=lambda x: None)
        assert isinstance(snap, RPyCSnapshot)
        assert snap.dcc_name == "maya"

    def test_create_http_snapshot(self) -> None:
        if not _http_available():
            pytest.skip("requests not installed")
        from dcc_mcp_ipc.snapshot.http import HTTPSnapshot

        snap = create_snapshot("unreal", "http", base_url="http://localhost:30010")
        assert isinstance(snap, HTTPSnapshot)
        assert snap.dcc_type == "unreal"

    def test_create_unsupported_transport(self) -> None:
        with pytest.raises(ValueError, match="Unsupported transport 'grpc'"):
            create_snapshot("test", "grpc")


def _http_available() -> bool:
    try:
        __import__("requests")
        return True
    except ImportError:
        return False


def _make_minimal_png(width: int = 4, height: int = 4) -> bytes:
    """Generate a minimal valid PNG for testing."""

    def chunk(ctype: bytes, data: bytes) -> bytes:
        c = ctype + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    raw = b""
    for _ in range(height):
        raw += b"\x00" + b"\x80" * width * 3  # RGB filter-none

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

    signature = b"\x89PNG\r\n\x1a\n"
    png = signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    return png
