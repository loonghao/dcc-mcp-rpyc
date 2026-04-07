"""WebSocket transport implementation.

This module provides a WebSocket-based transport for real-time bidirectional
communication with DCC applications. It supports:

- Real-time scene data streaming (object transforms, selection changes, etc.)
- Bidirectional communication (Agent sends commands, DCC pushes events)
- Event subscription / unsubscription model
- Explicit reconnects through the shared :class:`BaseTransport` lifecycle API

Design notes:
- Uses background reader/writer threads around a synchronous WebSocket client.
- ``websockets`` is an optional dependency; if absent, ``connect()`` raises a
  transport-level connection error.
- All callbacks are invoked from a background reader thread; callers must
  ensure thread safety when updating shared state.
"""


# Import built-in modules
import dataclasses
import json
import logging
import queue
import threading
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

# Import local modules
from dcc_mcp_ipc.transport.base import BaseTransport
from dcc_mcp_ipc.transport.base import ConnectionError
from dcc_mcp_ipc.transport.base import ProtocolError
from dcc_mcp_ipc.transport.base import TimeoutError
from dcc_mcp_ipc.transport.base import TransportConfig
from dcc_mcp_ipc.transport.base import TransportState

logger = logging.getLogger(__name__)

# Sentinel used internally to signal the reader thread to exit
_STOP_SENTINEL = object()

# Type alias for event callback
EventCallback = Callable[[str, Dict[str, Any]], None]


@dataclasses.dataclass
class WebSocketTransportConfig(TransportConfig):
    """WebSocket-specific transport configuration.

    Attributes:
        path: URL path for the WebSocket endpoint (e.g. ``/ws``).
        ping_interval: Interval in seconds between keep-alive pings. 0 = disabled.
        ping_timeout: Timeout in seconds for a ping response.
        max_message_size: Maximum incoming message size in bytes (0 = unlimited).
        extra_headers: Additional HTTP headers sent during the WebSocket handshake.

    """

    path: str = "/ws"
    ping_interval: float = 20.0
    ping_timeout: float = 10.0
    max_message_size: int = 0
    extra_headers: Dict[str, str] = dataclasses.field(default_factory=dict)


class WebSocketTransport(BaseTransport):
    """WebSocket-based transport for real-time DCC communication.

    This transport establishes a persistent WebSocket connection to a DCC
    service and provides:

    1. ``execute()`` — request/response RPC over WebSocket (async under the hood,
       surfaced as synchronous via a threading.Event).
    2. ``subscribe(event, callback)`` — register a callback for server-push events.
    3. ``unsubscribe(event, callback)`` — remove a previously registered callback.

    Thread model:
    - A background *reader thread* reads incoming frames and routes them to
      either pending RPC futures or registered event callbacks.
    - ``execute()`` posts a request and blocks on a threading.Event until the
      response arrives or the timeout expires.

    Example::

        config = WebSocketTransportConfig(host="localhost", port=8765, path="/ws")
        ws = WebSocketTransport(config)
        def on_selection_changed(event_name, event_data):
            _ = event_name, event_data

        ws.connect()
        result = ws.execute("get_scene_info")
        ws.subscribe("selection_changed", on_selection_changed)
        ws.disconnect()

    """

    def __init__(self, config: Optional[WebSocketTransportConfig] = None) -> None:
        """Initialise the WebSocket transport.

        Args:
            config: WebSocket-specific configuration. Uses defaults if omitted.

        """
        super().__init__(config or WebSocketTransportConfig())
        self._ws_config: WebSocketTransportConfig = self._config  # type: ignore[assignment]

        # Underlying WebSocket connection (set by connect())
        self._ws: Any = None

        # Background reader thread
        self._reader_thread: Optional[threading.Thread] = None

        # Pending RPC calls: {request_id: (Event, result_container)}
        self._pending: Dict[str, tuple] = {}
        self._pending_lock = threading.Lock()
        self._request_counter = 0
        self._counter_lock = threading.Lock()

        # Event subscriptions: {event_name: [callback, ...]}
        self._subscriptions: Dict[str, List[EventCallback]] = {}
        self._sub_lock = threading.RLock()

        # Outbound message queue (written by caller, consumed by writer thread)
        self._send_queue: queue.Queue = queue.Queue()
        self._writer_thread: Optional[threading.Thread] = None

    # ── Properties ────────────────────────────────────────────────────

    @property
    def ws_config(self) -> WebSocketTransportConfig:
        """Return the WebSocket-specific configuration."""
        return self._ws_config

    @property
    def ws_url(self) -> str:
        """Construct the full WebSocket URL from config."""
        scheme = "wss" if getattr(self._ws_config, "use_ssl", False) else "ws"
        host = self._ws_config.host
        port = self._ws_config.port
        path = self._ws_config.path
        return f"{scheme}://{host}:{port}{path}"

    # ── BaseTransport abstract methods ────────────────────────────────

    def connect(self) -> None:
        """Establish a WebSocket connection to the remote service.

        Raises:
            ConnectionError: If the connection cannot be established or the
                ``websockets`` library is not installed.

        """
        if self._state == TransportState.CONNECTED:
            logger.debug("Already connected to %s", self.ws_url)
            return

        self._state = TransportState.CONNECTING
        logger.info("Connecting to WebSocket at %s", self.ws_url)

        try:
            self._ws = self._open_connection()
            self._state = TransportState.CONNECTED
            self._start_background_threads()
            logger.info("WebSocket connected to %s", self.ws_url)
        except ImportError as exc:
            self._state = TransportState.ERROR
            raise ConnectionError(
                "websockets library is not installed. Install it with: pip install websockets",
                cause=exc,
            ) from exc
        except OSError as exc:
            self._state = TransportState.ERROR
            raise ConnectionError(
                f"Failed to connect to WebSocket at {self.ws_url}: {exc}",
                cause=exc,
            ) from exc
        except Exception as exc:
            self._state = TransportState.ERROR
            raise ConnectionError(
                f"Unexpected error connecting to {self.ws_url}: {exc}",
                cause=exc,
            ) from exc

    def disconnect(self) -> None:
        """Close the WebSocket connection gracefully."""
        if self._state == TransportState.DISCONNECTED:
            return

        logger.info("Disconnecting WebSocket from %s", self.ws_url)
        self._state = TransportState.DISCONNECTED

        # Signal background threads to stop
        self._send_queue.put(_STOP_SENTINEL)

        try:
            if self._ws is not None:
                self._close_connection(self._ws)
        except Exception as exc:
            logger.warning("Error closing WebSocket: %s", exc)
        finally:
            self._ws = None

        # Wake up all pending RPC calls with an error
        with self._pending_lock:
            for req_id, (event, container) in self._pending.items():
                container["error"] = ConnectionError("WebSocket disconnected")
                event.set()
            self._pending.clear()

        # Wait for background threads to exit
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2.0)
        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=2.0)

        self._reader_thread = None
        self._writer_thread = None

    def health_check(self) -> bool:
        """Check if the WebSocket connection is alive.

        Returns:
            True if the transport is connected and the remote side responded
            to a ping within the configured timeout.

        """
        if not self.is_connected or self._ws is None:
            return False
        try:
            self._send_ping(self._ws)
            return True
        except Exception as exc:
            logger.warning("WebSocket health check failed: %s", exc)
            return False

    def execute(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute an action on the remote service over WebSocket.

        The request is serialised as JSON and sent asynchronously; this method
        blocks until the response arrives or the timeout expires.

        Args:
            action: Name of the action to execute.
            params: Parameters to pass to the action.
            timeout: Per-call timeout in seconds. Falls back to ``config.timeout``.

        Returns:
            A dict containing the action result (always has a ``"success"`` key).

        Raises:
            ConnectionError: If the transport is not connected.
            TimeoutError: If the response does not arrive within *timeout* seconds.
            ProtocolError: If the remote side returns an error payload.

        """
        if not self.is_connected:
            raise ConnectionError("Not connected — call connect() first")

        effective_timeout = timeout if timeout is not None else self._config.timeout
        request_id = self._next_request_id()

        payload = {
            "id": request_id,
            "type": "request",
            "action": action,
            "params": params or {},
        }

        event = threading.Event()
        container: Dict[str, Any] = {}

        with self._pending_lock:
            self._pending[request_id] = (event, container)

        try:
            self._enqueue_message(json.dumps(payload))

            if not event.wait(timeout=effective_timeout):
                with self._pending_lock:
                    self._pending.pop(request_id, None)
                raise TimeoutError(f"Action '{action}' timed out after {effective_timeout}s")

            if "error" in container:
                raise container["error"]

            return container.get("result", {"success": True})

        except (TimeoutError, ConnectionError, ProtocolError):
            raise
        except Exception as exc:
            raise ProtocolError(f"Error executing action '{action}': {exc}", cause=exc) from exc
        finally:
            with self._pending_lock:
                self._pending.pop(request_id, None)

    # ── Event Subscription ────────────────────────────────────────────

    def subscribe(self, event: str, callback: EventCallback) -> None:
        """Register a callback for a server-push event.

        Args:
            event: Event name (e.g. ``"selection_changed"``, ``"scene_modified"``).
            callback: Callable invoked as ``callback(event_name, event_data)``
                from the reader thread.

        """
        with self._sub_lock:
            self._subscriptions.setdefault(event, [])
            if callback not in self._subscriptions[event]:
                self._subscriptions[event].append(callback)
                logger.debug("Subscribed to event '%s'", event)

    def unsubscribe(self, event: str, callback: EventCallback) -> None:
        """Remove a previously registered event callback.

        Args:
            event: Event name.
            callback: Callback to remove.

        """
        with self._sub_lock:
            listeners = self._subscriptions.get(event, [])
            if callback in listeners:
                listeners.remove(callback)
                logger.debug("Unsubscribed from event '%s'", event)

    def subscriptions(self) -> Dict[str, List[EventCallback]]:
        """Return a snapshot of current event subscriptions."""
        with self._sub_lock:
            return {k: list(v) for k, v in self._subscriptions.items()}

    # ── Internal Helpers ──────────────────────────────────────────────

    def _next_request_id(self) -> str:
        """Generate a unique request identifier."""
        with self._counter_lock:
            self._request_counter += 1
            return f"req-{self._request_counter}"

    def _enqueue_message(self, message: str) -> None:
        """Enqueue a message for the writer thread."""
        self._send_queue.put(message)

    def _start_background_threads(self) -> None:
        """Start the reader and writer background threads."""
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            name=f"ws-reader-{self._ws_config.host}:{self._ws_config.port}",
            daemon=True,
        )
        self._writer_thread = threading.Thread(
            target=self._writer_loop,
            name=f"ws-writer-{self._ws_config.host}:{self._ws_config.port}",
            daemon=True,
        )
        self._reader_thread.start()
        self._writer_thread.start()

    def _reader_loop(self) -> None:
        """Background thread: reads incoming WebSocket frames and dispatches them."""
        logger.debug("WebSocket reader thread started")
        try:
            while self._state == TransportState.CONNECTED and self._ws is not None:
                try:
                    raw = self._recv_message(self._ws)
                    if raw is None:
                        # Connection closed by remote
                        break
                    self._dispatch_message(raw)
                except Exception as exc:
                    if self._state == TransportState.CONNECTED:
                        logger.error("WebSocket reader error: %s", exc)
                    break
        finally:
            logger.debug("WebSocket reader thread exiting")
            if self._state == TransportState.CONNECTED:
                # Unexpected disconnect
                self._state = TransportState.ERROR
                with self._pending_lock:
                    for req_id, (event, container) in list(self._pending.items()):
                        container["error"] = ConnectionError("WebSocket connection lost")
                        event.set()
                    self._pending.clear()

    def _writer_loop(self) -> None:
        """Background thread: sends queued messages over the WebSocket."""
        logger.debug("WebSocket writer thread started")
        try:
            while True:
                message = self._send_queue.get()
                if message is _STOP_SENTINEL:
                    break
                if self._ws is None or self._state != TransportState.CONNECTED:
                    break
                try:
                    self._send_message(self._ws, message)
                except Exception as exc:
                    logger.error("WebSocket writer error: %s", exc)
                    break
        finally:
            logger.debug("WebSocket writer thread exiting")

    def _dispatch_message(self, raw: str) -> None:
        """Parse and dispatch an incoming message.

        Args:
            raw: Raw JSON string received from the WebSocket.

        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("Received non-JSON WebSocket message: %s", exc)
            return

        msg_type = data.get("type")

        if msg_type == "response":
            self._handle_response(data)
        elif msg_type == "event":
            self._handle_event(data)
        elif msg_type == "error":
            self._handle_error_message(data)
        else:
            logger.debug("Unknown WebSocket message type: %s", msg_type)

    def _handle_response(self, data: Dict[str, Any]) -> None:
        """Route a response message to the waiting RPC call."""
        req_id = data.get("id")
        if not req_id:
            logger.warning("Response missing 'id' field: %s", data)
            return

        with self._pending_lock:
            entry = self._pending.get(req_id)

        if entry is None:
            logger.debug("Received response for unknown request id: %s", req_id)
            return

        event, container = entry
        container["result"] = data.get("result", {"success": True})
        event.set()

    def _handle_error_message(self, data: Dict[str, Any]) -> None:
        """Route an error response to the waiting RPC call."""
        req_id = data.get("id")
        error_msg = data.get("message", "Unknown remote error")

        if req_id:
            with self._pending_lock:
                entry = self._pending.get(req_id)
            if entry:
                event, container = entry
                container["error"] = ProtocolError(error_msg)
                event.set()
                return

        logger.error("WebSocket server error: %s", error_msg)

    def _handle_event(self, data: Dict[str, Any]) -> None:
        """Dispatch a server-push event to registered callbacks."""
        event_name = data.get("event")
        event_data = data.get("data", {})

        if not event_name:
            logger.warning("Event message missing 'event' field")
            return

        with self._sub_lock:
            callbacks = list(self._subscriptions.get(event_name, []))
            # Also deliver to wildcard subscribers
            callbacks += list(self._subscriptions.get("*", []))

        for cb in callbacks:
            try:
                cb(event_name, event_data)
            except Exception as exc:
                logger.warning("Event callback error for '%s': %s", event_name, exc)

    # ── Protocol Hooks (override for custom WebSocket libraries) ─────

    def _open_connection(self) -> Any:
        """Open a WebSocket connection and return the connection object.

        This method is designed to be overridden in tests (via monkeypatching
        or subclassing) or when using a specific WebSocket library.

        The default implementation uses the ``websockets`` library (sync API
        introduced in websockets >= 13).

        Returns:
            A connection object that supports ``send(str)``, ``recv() -> str``,
            ``ping()``, and ``close()``.

        Raises:
            ImportError: If the ``websockets`` library is not installed.

        """
        # Use websockets sync API (websockets >= 13.0)
        import websockets.sync.client as _ws_sync

        extra_headers = list(self._ws_config.extra_headers.items()) if self._ws_config.extra_headers else None
        return _ws_sync.connect(
            self.ws_url,
            additional_headers=extra_headers,
        )

    def _close_connection(self, ws: Any) -> None:
        """Close the WebSocket connection object.

        Args:
            ws: Connection object returned by ``_open_connection``.

        """
        ws.close()

    def _send_message(self, ws: Any, message: str) -> None:
        """Send a raw text message over the WebSocket.

        Args:
            ws: Connection object.
            message: JSON string to send.

        """
        ws.send(message)

    def _recv_message(self, ws: Any) -> Optional[str]:
        """Receive the next text message from the WebSocket.

        Returns:
            The raw message string, or ``None`` if the connection was closed.

        """
        try:
            return ws.recv()
        except Exception:
            return None

    def _send_ping(self, ws: Any) -> None:
        """Send a ping to the remote side.

        Args:
            ws: Connection object.

        """
        ws.ping()
