"""Iteration-11 extra coverage for snapshot/http.py.

Covers:
- Lines 28-31: requests module not available (REQUESTS_AVAILABLE=False fallback)
- Lines 153-163: _capture_unreal when ReturnValue is present but non-string,
  and when neither ReturnValue nor error key is present (falls through to text decode)
- Line 157->159 branch: ReturnValue exists but is not a str
"""

# Import built-in modules
import base64
import importlib
import sys
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
from dcc_mcp_ipc.snapshot.http import HTTPSnapshot

pytestmark = pytest.mark.skipif(requests is None, reason="requests not installed")


@pytest.fixture
def mock_session():
    return MagicMock(spec=requests.Session)


# ---------------------------------------------------------------------------
# Lines 153->163 / 157->159: _capture_unreal ReturnValue branches
# ---------------------------------------------------------------------------


class TestCaptureUnrealReturnValueBranches:
    """Additional _capture_unreal coverage."""

    def test_return_value_is_non_string_falls_through_to_text(self, mock_session):
        """ReturnValue present but not a str → skip that branch, fall through to text decode.

        Line 157 branch: isinstance(rv, str) is False → skip b64decode there.
        Then line 163: try response.text as base64.
        """
        img_bytes = b"fake_image_data"
        fake_b64 = base64.b64encode(img_bytes).decode("ascii")

        mock_response = MagicMock()
        # ReturnValue is an int, not a str → branch at line 157 NOT taken
        mock_response.json.return_value = {"ReturnValue": 12345}
        mock_response.text = fake_b64
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:30010",
            dcc_type="unreal",
            session=mock_session,
        )
        result = snap.capture_viewport()
        assert result == img_bytes

    def test_return_value_is_none_falls_through(self, mock_session):
        """ReturnValue is None (falsy) → isinstance(rv, str) is False → text fallback."""
        img_bytes = b"none_rv_fallback"
        fake_b64 = base64.b64encode(img_bytes).decode("ascii")

        mock_response = MagicMock()
        mock_response.json.return_value = {"ReturnValue": None}
        mock_response.text = fake_b64
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:30010",
            dcc_type="unreal",
            session=mock_session,
        )
        result = snap.capture_viewport()
        assert result == img_bytes

    def test_response_has_error_key_lowercase(self, mock_session):
        """Response dict with 'error' key raises SnapshotError."""
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

    def test_response_no_return_value_no_error_uses_text(self, mock_session):
        """Dict response with neither ReturnValue nor error → text fallback."""
        img_bytes = b"plain_text_fallback"
        fake_b64 = base64.b64encode(img_bytes).decode("ascii")

        mock_response = MagicMock()
        mock_response.json.return_value = {"something_else": "value"}
        mock_response.text = fake_b64
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        snap = HTTPSnapshot(
            base_url="http://localhost:30010",
            dcc_type="unreal",
            session=mock_session,
        )
        result = snap.capture_viewport()
        assert result == img_bytes


# ---------------------------------------------------------------------------
# Lines 28-31: REQUESTS_AVAILABLE = False path
# When requests is not available, __init__ should raise since requests.Session() fails
# ---------------------------------------------------------------------------


class TestRequestsUnavailablePath:
    """Tests for the ImportError fallback when requests is not installed."""

    def test_http_snapshot_init_without_requests_raises(self):
        """When requests is unavailable, instantiating HTTPSnapshot raises."""
        with patch.dict(sys.modules, {"requests": None}):
            # Force re-import to simulate missing requests
            if "dcc_mcp_ipc.snapshot.http" in sys.modules:
                del sys.modules["dcc_mcp_ipc.snapshot.http"]

            try:
                from dcc_mcp_ipc.snapshot import http as http_mod  # noqa: F401

                # If REQUESTS_AVAILABLE is False, session = requests.Session() should fail
                if not http_mod.REQUESTS_AVAILABLE:
                    with pytest.raises((TypeError, AttributeError)):
                        http_mod.HTTPSnapshot(base_url="http://localhost:8080")
            finally:
                # Restore the module
                if "dcc_mcp_ipc.snapshot.http" in sys.modules:
                    del sys.modules["dcc_mcp_ipc.snapshot.http"]
                importlib.import_module("dcc_mcp_ipc.snapshot.http")
