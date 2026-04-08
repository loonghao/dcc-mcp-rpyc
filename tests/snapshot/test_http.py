"""Tests for the HTTP snapshot implementation.

Covers HTTPSnapshot including capture_viewport for Unreal/Unity/generic,
error handling, and health check. All tests use mock HTTP responses —
no real DCC servers required.
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

try:
    # Import third-party modules
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

# Import local modules
from dcc_mcp_ipc.snapshot.base import SnapshotConfig
from dcc_mcp_ipc.snapshot.base import SnapshotError
from dcc_mcp_ipc.snapshot.base import SnapshotFormat
from dcc_mcp_ipc.snapshot.http import HTTPSnapshot

pytestmark = pytest.mark.skipif(requests is None, reason="requests library not installed (optional dependency)")


@pytest.fixture
def mock_session():
    """Create a mock requests.Session for testing."""
    session = MagicMock(spec=requests.Session)  # type: ignore[arg-type]
    return session


class TestHTTPSnapshotInit:
    """Tests for HTTPSnapshot initialization."""

    def test_default_init(self) -> None:
        snap = HTTPSnapshot(base_url="http://localhost:8080")
        assert snap.base_url == "http://localhost:8080"
        assert snap.dcc_type == "generic"
        assert snap.timeout == 30.0

    def test_url_trailing_slash_stripped(self) -> None:
        snap = HTTPSnapshot(base_url="http://localhost:30010/")
        assert snap.base_url == "http://localhost:30010"

    def test_custom_dcc_type(self) -> None:
        snap = HTTPSnapshot(base_url="http://host", dcc_type="unreal", timeout=60.0)
        assert snap.dcc_type == "unreal"
        assert snap.timeout == 60.0

    def test_session_reuse(self) -> None:
        custom = MagicMock(spec=requests.Session)
        snap = HTTPSnapshot(base_url="http://host", session=custom)
        assert snap.session is custom


class TestHTTPCaptureUnreal:
    """Tests for Unreal Engine Remote Control API capture."""

    def test_unreal_capture_success_with_base64_return(self, mock_session) -> None:
        """Test successful UE capture with base64 in ReturnValue."""
        # Import built-in modules
        import base64 as b64_mod

        fake_png_b64 = b64_mod.b64encode(b"ue_screenshot_data").decode("ascii")
        mock_response = MagicMock()
        mock_response.json.return_value = {"ReturnValue": fake_png_b64}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:30010",
            dcc_type="unreal",
            session=mock_session,
        )
        result = snap.capture_viewport()

        assert result == b"ue_screenshot_data"
        mock_session.post.assert_called_once()

    def test_unreal_capture_error_in_response(self, mock_session) -> None:
        """Test UE capture when response contains error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"Error": "Object not found: invalid path"}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:30010",
            dcc_type="unreal",
            session=mock_session,
        )

        with pytest.raises(SnapshotError, match="UE Remote Control error"):
            snap.capture_viewport()

    def test_unreal_capture_http_error(self, mock_session) -> None:
        """Test UE capture when HTTP request fails."""
        mock_session.post.side_effect = requests.ConnectionError("refused")

        snap = HTTPSnapshot(
            base_url="http://localhost:30010",
            dcc_type="unreal",
            session=mock_session,
        )

        with pytest.raises(SnapshotError, match="Failed to capture unreal"):
            snap.capture_viewport()

    def test_unreal_capture_fallback_to_text(self, mock_session) -> None:
        """Test UE capture with raw text fallback (base64)."""
        # Import built-in modules
        import base64 as b64_mod

        fake_b64 = b64_mod.b64encode(b"text_fallback").decode("ascii")
        mock_response = MagicMock()
        # Return non-dict JSON (fallback path)
        mock_response.text = fake_b64
        # json() raises to trigger fallback
        mock_response.json.return_value = {"no_key": "value"}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:30010",
            dcc_type="unreal",
            session=mock_session,
        )
        result = snap.capture_viewport()
        assert result == b"text_fallback"


class TestHTTPCaptureUnity:
    """Tests for Unity HTTP server capture."""

    def test_unity_capture_image_content_type(self, mock_session) -> None:
        """Test Unity capture returning raw image bytes."""
        fake_image = b"\x89PNG\r\n\x1a\n" + b"fake_unity_image_data"
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/png"}
        mock_response.content = fake_image
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:8080",
            dcc_type="unity",
            session=mock_session,
        )
        result = snap.capture_viewport()

        assert result == fake_image
        mock_session.get.assert_called_once()

    def test_unity_capture_json_base64(self, mock_session) -> None:
        """Test Unity capture returning JSON with base64 data."""
        # Import built-in modules
        import base64 as b64_mod

        img_data = b"unity_screenshot_bytes"
        fake_b64 = b64_mod.b64encode(img_data).decode("ascii")
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"data": fake_b64}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:8080",
            dcc_type="unity",
            session=mock_session,
        )
        result = snap.capture_viewport()

        assert result == img_data

    def test_unity_capture_bad_content_type(self, mock_session) -> None:
        """Test Unity capture with unexpected content type."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/html"}
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:8080",
            dcc_type="unity",
            session=mock_session,
        )

        with pytest.raises(SnapshotError, match="Unexpected response"):
            snap.capture_viewport()

    def test_unity_capture_http_error(self, mock_session) -> None:
        """Test Unity capture when HTTP request fails."""
        mock_session.get.side_effect = requests.Timeout("timed out")

        snap = HTTPSnapshot(
            base_url="http://localhost:8080",
            dcc_type="unity",
            session=mock_session,
        )

        with pytest.raises(SnapshotError, match="Failed to capture unity"):
            snap.capture_viewport()


class TestHTTPCaptureGeneric:
    """Tests for generic HTTP screenshot endpoint capture."""

    def test_generic_capture_image_response(self, mock_session) -> None:
        """Test generic capture with image content type."""
        fake_img = b"generic_image_data"
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/png"}
        mock_response.content = fake_img
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:9000",
            dcc_type="generic",
            session=mock_session,
        )
        result = snap.capture_viewport()

        assert result == fake_img

    def test_generic_capture_non_image_error(self, mock_session) -> None:
        """Test generic capture when response is not an image."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.content = b"not an image"
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:9000",
            dcc_type="generic",
            session=mock_session,
        )

        with pytest.raises(SnapshotError, match="non-image content"):
            snap.capture_viewport()

    def test_generic_capture_connection_error(self, mock_session) -> None:
        """Test generic capture on connection failure."""
        mock_session.get.side_effect = requests.ConnectionError("down")

        snap = HTTPSnapshot(
            base_url="http://localhost:9000",
            dcc_type="generic",
            session=mock_session,
        )

        with pytest.raises(SnapshotError):
            snap.capture_viewport()


class TestHTTPSnapshotConfigPassing:
    """Tests that config parameters are correctly passed to requests."""

    def test_config_width_height_in_params(self, mock_session) -> None:
        """Verify width/height are sent in query parameters."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/png"}
        mock_response.content = b"data"
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        snap = HTTPSnapshot(base_url="http://host", dcc_type="unity", session=mock_session)

        config = SnapshotConfig(width=2560, height=1440)
        snap.capture_viewport(config)

        call_kwargs = mock_session.get.call_args
        assert call_kwargs is not None
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params is not None
        assert params["width"] == "2560"
        assert params["height"] == "1440"


class TestHTTPHealthCheck:
    """Tests for health_check method."""

    def test_health_check_success(self, mock_session) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        snap = HTTPSnapshot(base_url="http://host", session=mock_session)
        assert snap.health_check() is True

    def test_health_check_server_error(self, mock_session) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_session.get.return_value = mock_response

        snap = HTTPSnapshot(base_url="http://host", session=mock_session)
        assert snap.health_check() is False

    def test_health_check_exception_returns_false(self, mock_session) -> None:
        mock_session.get.side_effect = Exception("network error")

        snap = HTTPSnapshot(base_url="http://host", session=mock_session)
        assert snap.health_check() is False


class TestHTTPSnapshotInfo:
    """Tests for get_snapshot_info."""

    def test_info_fields(self, mock_session) -> None:
        snap = HTTPSnapshot(
            base_url="http://localhost:30010",
            dcc_type="unreal",
            session=mock_session,
        )
        info = snap.get_snapshot_info()
        assert info["dcc_type"] == "unreal"
        assert info["base_url"] == "http://localhost:30010"
        assert info["transport"] == "http"


class TestHTTPHealthCheckFallback:
    """Tests for health_check fallback path (base URL when /health fails)."""

    def test_health_check_health_fails_root_succeeds(self, mock_session) -> None:
        """/health raises, but root URL returns 200 → True."""
        ok_resp = MagicMock()
        ok_resp.status_code = 200

        call_count = [0]

        def side_effect(url, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: /health endpoint raises
                raise requests.ConnectionError("health not found")
            return ok_resp

        mock_session.get.side_effect = side_effect
        snap = HTTPSnapshot(base_url="http://localhost:30010", session=mock_session)
        result = snap.health_check()
        assert result is True

    def test_health_check_both_fail_returns_false(self, mock_session) -> None:
        """/health and root both raise → False."""
        mock_session.get.side_effect = requests.ConnectionError("unreachable")
        snap = HTTPSnapshot(base_url="http://localhost:30010", session=mock_session)
        result = snap.health_check()
        assert result is False

    def test_health_check_root_server_error(self, mock_session) -> None:
        """/health raises; root returns 500 → False."""
        err_resp = MagicMock()
        err_resp.status_code = 500

        call_count = [0]

        def side_effect(url, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise requests.ConnectionError("health not found")
            return err_resp

        mock_session.get.side_effect = side_effect
        snap = HTTPSnapshot(base_url="http://localhost:30010", session=mock_session)
        result = snap.health_check()
        assert result is False


class TestHTTPCaptureUnrealEdgeCases:
    """Behavior-focused Unreal fallback tests consolidated from temporary coverage files."""

    def test_unreal_capture_non_string_return_value_falls_back_to_text(self, mock_session) -> None:
        """A non-string ``ReturnValue`` should fall back to decoding ``response.text``."""
        # Import built-in modules
        import base64

        img_bytes = b"fallback_image_data"
        mock_response = MagicMock()
        mock_response.json.return_value = {"ReturnValue": 12345}
        mock_response.text = base64.b64encode(img_bytes).decode("ascii")
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:30010",
            dcc_type="unreal",
            session=mock_session,
        )

        assert snap.capture_viewport() == img_bytes

    def test_unreal_capture_lowercase_error_key_raises_snapshot_error(self, mock_session) -> None:
        """Unreal responses with a lowercase ``error`` key should still be rejected."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Object not found"}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:30010",
            dcc_type="unreal",
            session=mock_session,
        )

        with pytest.raises(SnapshotError, match="UE Remote Control error"):
            snap.capture_viewport()

    def test_unreal_capture_missing_return_value_uses_text_fallback(self, mock_session) -> None:
        """Responses without ``ReturnValue`` or ``error`` should still use the text payload."""
        # Import built-in modules
        import base64

        img_bytes = b"plain_text_fallback"
        mock_response = MagicMock()
        mock_response.json.return_value = {"something_else": "value"}
        mock_response.text = base64.b64encode(img_bytes).decode("ascii")
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:30010",
            dcc_type="unreal",
            session=mock_session,
        )

        assert snap.capture_viewport() == img_bytes


class TestHTTPSnapshotOptionalRequestsDependency:
    """Tests for the optional ``requests`` dependency import fallback."""

    def test_init_without_requests_raises(self) -> None:
        """Re-importing the module without ``requests`` should make instantiation fail fast."""
        # Import built-in modules
        import importlib
        import sys

        with patch.dict(sys.modules, {"requests": None}):
            if "dcc_mcp_ipc.snapshot.http" in sys.modules:
                del sys.modules["dcc_mcp_ipc.snapshot.http"]

            try:
                from dcc_mcp_ipc.snapshot import http as http_mod

                if not http_mod.REQUESTS_AVAILABLE:
                    with pytest.raises((AttributeError, TypeError)):
                        http_mod.HTTPSnapshot(base_url="http://localhost:8080")
            finally:
                if "dcc_mcp_ipc.snapshot.http" in sys.modules:
                    del sys.modules["dcc_mcp_ipc.snapshot.http"]
                importlib.import_module("dcc_mcp_ipc.snapshot.http")


