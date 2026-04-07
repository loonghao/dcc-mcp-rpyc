"""HTTP snapshot implementation for DCC applications with HTTP APIs.

This module provides HTTP-based snapshot implementations for DCC applications
that expose screenshot capabilities through HTTP endpoints (e.g., Unreal Engine
Remote Control API, Unity built-in HttpListener).

Protocol: Images are fetched via HTTP GET/POST requests and returned as raw bytes.
"""

# Import built-in modules
import base64
import logging
from typing import Any
from typing import Optional

# Import local modules
from dcc_mcp_ipc.snapshot.base import BaseSnapshot
from dcc_mcp_ipc.snapshot.base import SnapshotConfig
from dcc_mcp_ipc.snapshot.base import SnapshotError

# Import third-party modules (optional — graceful fallback)
try:
    # Import third-party modules
    import requests
    from requests.exceptions import RequestException

    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None  # type: ignore[assignment]
    RequestException = Exception  # type: ignore[misc,assignment]
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class HTTPSnapshot(BaseSnapshot):
    """Snapshot implementation for DCC applications with HTTP-based control.

    This class captures screenshots by making HTTP requests to the DCC's
    remote control or web server API.

    Supported DCC types:

    - **Unreal Engine**: Remote Control API (``/remote/object/call``)
    - **Unity**: Custom C# ``HttpListener`` endpoint (``/screenshot``)

    Attributes:
        base_url: Base URL of the DCC HTTP server.
        timeout: Request timeout in seconds.
        session: Optional requests.Session for connection pooling.

    Example::

        # Unreal Engine Remote Control API
        snap = HTTPSnapshot(
            base_url="http://localhost:30010",
            dcc_type="unreal",
        )
        png_data = snap.capture_viewport()

        # Unity custom server
        snap = HTTPSnapshot(
            base_url="http://localhost:8080",
            dcc_type="unity",
        )
        png_data = snap.capture_viewport()

    """

    def __init__(
        self,
        base_url: str,
        dcc_type: str = "generic",
        timeout: float = 30.0,
        session: Optional["requests.Session"] = None,
    ) -> None:
        """Initialize the HTTP snapshot client.

        Args:
            base_url: Base URL of the DCC HTTP API
                (e.g. "http://localhost:30010").
            dcc_type: Type of DCC ("unreal", "unity", etc.).
            timeout: HTTP request timeout in seconds.
            session: Optional pre-configured requests session.

        """
        self.base_url = base_url.rstrip("/")
        self.dcc_type = dcc_type.lower()
        self.timeout = timeout
        self.session = session or requests.Session()

    def capture_viewport(
        self,
        config: Optional[SnapshotConfig] = None,
    ) -> bytes:
        """Capture viewport screenshot via HTTP request.

        Dispatches to the appropriate DCC-specific HTTP capture method based
        on ``dcc_type``.

        Args:
            config: Snapshot configuration.

        Returns:
            Raw image bytes of the captured viewport.

        Raises:
            SnapshotError: If the HTTP request fails or returns an error.

        """
        config = config or SnapshotConfig()

        dispatch = {
            "unreal": self._capture_unreal,
            "unity": self._capture_unity,
        }

        handler = dispatch.get(self.dcc_type, self._capture_generic)
        return handler(config)

    def _capture_unreal(self, config: SnapshotConfig) -> bytes:
        """Capture screenshot using Unreal Engine Remote Control API.

        Uses the ``/remote/object/call`` endpoint with
        ``EditorLevelLibrary.take_screenshot`` or equivalent.

        Args:
            config: Snapshot configuration.

        Returns:
            Raw PNG bytes.

        """
        try:
            # Unreal RC API: call the configured screenshot helper
            url = f"{self.base_url}/remote/object/call"
            payload = {
                "objectPath": "/Game/ThirdPersonBP/ThirdPersonMap.ThirdPersonMap:DefaultSceneRoot",
                "functionName": "GetScreenshot",
                "parameters": {
                    "resolutionX": config.width,
                    "resolutionY": config.height,
                },
                "generateTransaction": True,
            }

            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # Check for UE RPC response format
            if isinstance(data, dict):
                if "ReturnValue" in data:
                    # Screenshot is returned as base64 string in ReturnValue
                    rv = data["ReturnValue"]
                    if isinstance(rv, str):
                        return base64.b64decode(rv)
                if "error" in data or "Error" in data:
                    raise SnapshotError(f"UE Remote Control error: {data}")

            # Fallback: try interpreting entire response as base64
            response_text = response.text.strip()
            return base64.b64decode(response_text)

        except (RequestException, ValueError) as exc:
            raise SnapshotError(
                f"Failed to capture {self.dcc_type} viewport: {exc}",
                cause=exc,
            ) from exc

    def _capture_unity(self, config: SnapshotConfig) -> bytes:
        """Capture screenshot using Unity HTTP server endpoint.

        Calls a custom ``/screenshot`` endpoint on the Unity-side C# server.

        Args:
            config: Snapshot configuration.

        Returns:
            Raw PNG bytes.

        """
        try:
            url = f"{self.base_url}/screenshot"
            params = {
                "width": str(config.width),
                "height": str(config.height),
                "format": config.format.value,
            }

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            # Check content type — should be image/*
            ct = response.headers.get("content-type", "")
            if ct.startswith("image/"):
                return response.content

            # Fallback: JSON response with base64 data
            data = response.json()
            if isinstance(data, dict) and "data" in data:
                return base64.b64decode(data["data"])

            raise SnapshotError(f"Unexpected response from Unity screenshot endpoint: content-type={ct}")

        except (RequestException, ValueError) as exc:
            raise SnapshotError(
                f"Failed to capture {self.dcc_type} viewport: {exc}",
                cause=exc,
            ) from exc

    def _capture_generic(self, config: SnapshotConfig) -> bytes:
        """Provide a generic HTTP screenshot fallback.

        Attempts to fetch from ``/screenshot`` endpoint with standard query
        parameters. Useful for custom DCC HTTP servers that follow conventions.

        Args:
            config: Snapshot configuration.

        Returns:
            Raw image bytes.

        """
        try:
            url = f"{self.base_url}/screenshot"
            params = {
                "width": str(config.width),
                "height": str(config.height),
                "format": config.format.value,
            }

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            ct = response.headers.get("content-type", "")
            if ct.startswith("image/"):
                return response.content

            raise SnapshotError(f"Generic HTTP snapshot returned non-image content: {ct}")

        except (RequestException, SnapshotError) as exc:
            if isinstance(exc, SnapshotError):
                raise
            raise SnapshotError(f"Generic HTTP snapshot failed: {exc}", cause=exc) from exc

    def get_snapshot_info(self) -> dict[str, Any]:
        """Return snapshot capabilities for this HTTP snapshot."""
        info = super().get_snapshot_info()
        info["dcc_type"] = self.dcc_type
        info["base_url"] = self.base_url
        info["transport"] = "http"
        return info

    def health_check(self) -> bool:
        """Check if the HTTP endpoint is reachable.

        Returns:
            True if a basic request to the base URL succeeds.

        """
        try:
            url = f"{self.base_url}/health"
            resp = self.session.get(url, timeout=5.0)
            return resp.status_code < 500
        except Exception:
            # Fall back to root path
            try:
                resp = self.session.get(self.base_url, timeout=5.0)
                return resp.status_code < 500
            except Exception:
                return False
