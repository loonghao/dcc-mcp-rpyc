"""HTTP transport implementation.

This module provides an HTTP-based transport for communicating with DCC
applications that expose an HTTP API, such as Unreal Engine (Remote Control
API) and Unity (C# HttpListener).

Key design choices:
- Uses only ``urllib`` from the standard library — no ``requests`` or ``httpx``
  dependency, keeping the DCC side zero-dependency.
- Supports connection keep-alive via ``http.client.HTTPConnection`` pooling.
- All payloads are JSON (``application/json``).
"""

# Import built-in modules
import http.client
import json
import logging
import socket
from typing import Any
from typing import Dict
from typing import Optional
from urllib.parse import urljoin

# Import local modules
from dcc_mcp_rpyc.transport.base import BaseTransport
from dcc_mcp_rpyc.transport.base import ConnectionError
from dcc_mcp_rpyc.transport.base import ProtocolError
from dcc_mcp_rpyc.transport.base import TimeoutError
from dcc_mcp_rpyc.transport.base import TransportConfig
from dcc_mcp_rpyc.transport.base import TransportState

logger = logging.getLogger(__name__)


class HTTPTransportConfig(TransportConfig):
    """HTTP-specific transport configuration.

    Attributes:
        base_path: URL path prefix (e.g. ``/remote`` for Unreal Remote Control).
        use_ssl: Whether to use HTTPS.
        headers: Default HTTP headers to send with every request.
        action_endpoint: Path pattern for action execution.
            ``{action}`` is replaced with the action name.

    """

    base_path: str = ""
    use_ssl: bool = False
    headers: Dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
    action_endpoint: str = "/api/v1/action/{action}"


class HTTPTransport(BaseTransport):
    """Transport implementation using HTTP/HTTPS.

    Designed primarily for:
    - Unreal Engine Remote Control API (default port 30010, path ``/remote``)
    - Unity C# HttpListener-based servers
    - Any DCC exposing a REST-like JSON API

    The transport maintains a persistent ``http.client.HTTPConnection`` for
    connection reuse, falling back to a new connection per request on failure.
    """

    def __init__(self, config: Optional[HTTPTransportConfig] = None) -> None:
        """Initialize the HTTP transport.

        Args:
            config: HTTP transport configuration.

        """
        super().__init__(config or HTTPTransportConfig())
        self._conn: Optional[http.client.HTTPConnection] = None

    @property
    def http_config(self) -> HTTPTransportConfig:
        """Get the HTTP-specific configuration."""
        return self._config  # type: ignore[return-value]

    # ── Connection Lifecycle ─────────────────────────────────────────

    def connect(self) -> None:
        """Establish an HTTP connection (create connection pool)."""
        if self._state == TransportState.CONNECTED and self._conn:
            return

        self._state = TransportState.CONNECTING
        try:
            logger.info("Connecting via HTTP to %s:%s", self._config.host, self._config.port)
            if self.http_config.use_ssl:
                self._conn = http.client.HTTPSConnection(
                    self._config.host,
                    self._config.port,
                    timeout=self._config.timeout,
                )
            else:
                self._conn = http.client.HTTPConnection(
                    self._config.host,
                    self._config.port,
                    timeout=self._config.timeout,
                )
            # Verify connectivity with a quick socket check
            self._conn.connect()
            self._state = TransportState.CONNECTED
            logger.info("HTTP connection established to %s:%s", self._config.host, self._config.port)
        except Exception as exc:
            self._state = TransportState.ERROR
            self._conn = None
            raise ConnectionError(
                f"Failed to connect via HTTP to {self._config.host}:{self._config.port}: {exc}",
                cause=exc,
            ) from exc

    def disconnect(self) -> None:
        """Close the HTTP connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception as exc:
                logger.warning("Error closing HTTP connection: %s", exc)
            finally:
                self._conn = None
        self._state = TransportState.DISCONNECTED

    # ── Health ───────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """Check if the HTTP server is reachable."""
        if not self._conn:
            return False
        try:
            self._conn.request("GET", self.http_config.base_path + "/health")
            response = self._conn.getresponse()
            response.read()  # drain response body
            return 200 <= response.status < 500
        except Exception:
            self._state = TransportState.ERROR
            return False

    # ── HTTP Request Helper ──────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Send an HTTP request and parse the JSON response.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: URL path (will be joined with base_path).
            body: JSON-serializable request body.
            timeout: Per-request timeout override.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            ConnectionError: If not connected.
            TimeoutError: If the request times out.
            ProtocolError: If the response indicates an error.

        """
        if not self._conn or self._state != TransportState.CONNECTED:
            raise ConnectionError("Not connected — call connect() first")

        full_path = self.http_config.base_path + path
        encoded_body = json.dumps(body).encode("utf-8") if body else None

        try:
            self._conn.request(
                method,
                full_path,
                body=encoded_body,
                headers=self.http_config.headers,
            )
            response = self._conn.getresponse()
            response_body = response.read().decode("utf-8")

            if response.status >= 400:
                raise ProtocolError(
                    f"HTTP {response.status} from {method} {full_path}: {response_body}"
                )

            if not response_body:
                return {"success": True}

            try:
                return json.loads(response_body)
            except json.JSONDecodeError:
                return {"success": True, "result": response_body}

        except socket.timeout as exc:
            self._state = TransportState.ERROR
            raise TimeoutError(
                f"HTTP request timed out: {method} {full_path}", cause=exc
            ) from exc
        except (ConnectionError, TimeoutError, ProtocolError):
            raise
        except Exception as exc:
            # Connection may be broken — reset
            self._state = TransportState.ERROR
            self._conn = None
            raise ConnectionError(
                f"HTTP request failed: {method} {full_path}: {exc}", cause=exc
            ) from exc

    # ── Action Execution ─────────────────────────────────────────────

    def execute(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute an action via HTTP POST.

        The action name is interpolated into the ``action_endpoint`` config
        pattern and sent as a POST request with the params as JSON body.

        Args:
            action: Name of the action to invoke.
            params: Parameters forwarded as the JSON body.
            timeout: Per-call timeout override.

        Returns:
            Parsed JSON response.

        """
        path = self.http_config.action_endpoint.replace("{action}", action)
        return self._request("POST", path, body=params, timeout=timeout)

    # ── Unreal Engine Remote Control Shortcuts ───────────────────────

    def call_remote_object(
        self,
        object_path: str,
        function_name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call a function on an Unreal Engine object via Remote Control API.

        Sends a POST to ``/remote/object/call``.

        Args:
            object_path: Path to the UE object (e.g. ``/Game/MyActor``).
            function_name: Function to call on the object.
            params: Parameters for the function call.

        Returns:
            Response from the Unreal Remote Control API.

        """
        body = {
            "objectPath": object_path,
            "functionName": function_name,
        }
        if params:
            body["parameters"] = params
        return self._request("PUT", "/remote/object/call", body=body)

    def get_remote_property(
        self,
        object_path: str,
        property_name: str,
    ) -> Dict[str, Any]:
        """Get a property value from an Unreal Engine object.

        Sends a PUT to ``/remote/object/property``.

        Args:
            object_path: Path to the UE object.
            property_name: Name of the property to get.

        Returns:
            Property value response.

        """
        body = {
            "objectPath": object_path,
            "propertyName": property_name,
            "access": "READ_ACCESS",
        }
        return self._request("PUT", "/remote/object/property", body=body)

    def set_remote_property(
        self,
        object_path: str,
        property_name: str,
        value: Any,
    ) -> Dict[str, Any]:
        """Set a property value on an Unreal Engine object.

        Args:
            object_path: Path to the UE object.
            property_name: Name of the property to set.
            value: New property value.

        Returns:
            Response from the Unreal Remote Control API.

        """
        body = {
            "objectPath": object_path,
            "propertyName": property_name,
            "propertyValue": {"value": value},
            "access": "WRITE_ACCESS",
        }
        return self._request("PUT", "/remote/object/property", body=body)
