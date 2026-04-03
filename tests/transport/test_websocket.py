"""Tests for the WebSocket transport implementation.

All tests mock the underlying WebSocket connection — no real network is required.
"""

# Import built-in modules
import contextlib
import json
import threading
import time
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.transport.base import ConnectionError
from dcc_mcp_ipc.transport.base import ProtocolError
from dcc_mcp_ipc.transport.base import TimeoutError
from dcc_mcp_ipc.transport.base import TransportState
from dcc_mcp_ipc.transport.websocket import WebSocketTransport
from dcc_mcp_ipc.transport.websocket import WebSocketTransportConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_transport(**config_kwargs) -> WebSocketTransport:
    """Create a WebSocketTransport with a real-but-stubbed connection."""
    config = WebSocketTransportConfig(**config_kwargs)
    return WebSocketTransport(config)


class _FakeWS:
    """Minimal fake WebSocket connection for unit tests."""

    def __init__(self, responses=None):
        """Create fake WS with optional response sequence.

        Args:
            responses: iterable of raw JSON strings the fake WS will return
                from recv(). Raises StopIteration (simulates close) when exhausted.

        """
        self._responses = iter(responses or [])
        self.sent: list = []
        self.closed = False
        self.pinged = False

    def send(self, message: str) -> None:
        self.sent.append(message)

    def recv(self) -> str:
        try:
            return next(self._responses)
        except StopIteration:
            raise OSError("connection closed")

    def ping(self) -> None:
        self.pinged = True

    def close(self) -> None:
        self.closed = True


def _connect_no_threads(t: WebSocketTransport, fake_ws: _FakeWS) -> None:
    """Connect transport without starting background threads (for unit tests)."""
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(t, "_open_connection", return_value=fake_ws))
        stack.enter_context(patch.object(t, "_start_background_threads"))
        t.connect()


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestWebSocketTransportConfig:
    """Tests for WebSocketTransportConfig defaults and field validation."""

    def test_defaults(self):
        config = WebSocketTransportConfig()
        assert config.path == "/ws"
        assert config.ping_interval == 20.0
        assert config.ping_timeout == 10.0
        assert config.max_message_size == 0
        assert config.extra_headers == {}

    def test_custom_values(self):
        config = WebSocketTransportConfig(
            host="dcc-host",
            port=8765,
            path="/realtime",
            ping_interval=5.0,
            extra_headers={"X-Token": "abc"},
        )
        assert config.host == "dcc-host"
        assert config.port == 8765
        assert config.path == "/realtime"
        assert config.ping_interval == 5.0
        assert config.extra_headers == {"X-Token": "abc"}


# ---------------------------------------------------------------------------
# Init / properties
# ---------------------------------------------------------------------------


class TestWebSocketTransportInit:
    """Tests for transport initialisation and property access."""

    def test_default_state_is_disconnected(self):
        t = WebSocketTransport()
        assert t.state == TransportState.DISCONNECTED
        assert t.is_connected is False

    def test_ws_url_plain(self):
        config = WebSocketTransportConfig(host="localhost", port=8765, path="/ws")
        t = WebSocketTransport(config)
        assert t.ws_url == "ws://localhost:8765/ws"

    def test_ws_url_with_path(self):
        config = WebSocketTransportConfig(host="maya", port=9000, path="/realtime/events")
        t = WebSocketTransport(config)
        assert t.ws_url == "ws://maya:9000/realtime/events"

    def test_ws_config_property(self):
        config = WebSocketTransportConfig(host="dcc", port=1234)
        t = WebSocketTransport(config)
        assert t.ws_config is config

    def test_repr(self):
        config = WebSocketTransportConfig(host="maya", port=8765)
        t = WebSocketTransport(config)
        r = repr(t)
        assert "WebSocketTransport" in r
        assert "maya" in r


# ---------------------------------------------------------------------------
# connect() / disconnect()
# ---------------------------------------------------------------------------


class TestWebSocketTransportConnect:
    """Tests for connect() and disconnect() lifecycle."""

    def test_connect_calls_open_connection(self):
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()

        with contextlib.ExitStack() as stack:
            mock_open = stack.enter_context(patch.object(t, "_open_connection", return_value=fake_ws))
            stack.enter_context(patch.object(t, "_start_background_threads"))
            t.connect()
            mock_open.assert_called_once()

        assert t.state == TransportState.CONNECTED
        assert t.is_connected is True
        t.disconnect()

    def test_connect_idempotent(self):
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()

        with contextlib.ExitStack() as stack:
            mock_open = stack.enter_context(patch.object(t, "_open_connection", return_value=fake_ws))
            stack.enter_context(patch.object(t, "_start_background_threads"))
            t.connect()
            t.connect()  # second call should be a no-op
            assert mock_open.call_count == 1

        t.disconnect()

    def test_connect_import_error_raises_connection_error(self):
        t = _make_transport(host="localhost", port=8765)

        with patch.object(t, "_open_connection", side_effect=ImportError("no websockets")):
            with pytest.raises(ConnectionError, match="websockets library"):
                t.connect()

        assert t.state == TransportState.ERROR

    def test_connect_oserror_raises_connection_error(self):
        t = _make_transport(host="localhost", port=8765)

        with patch.object(t, "_open_connection", side_effect=OSError("refused")):
            with pytest.raises(ConnectionError, match="Failed to connect"):
                t.connect()

        assert t.state == TransportState.ERROR

    def test_connect_unexpected_error_raises_connection_error(self):
        t = _make_transport(host="localhost", port=8765)

        with patch.object(t, "_open_connection", side_effect=RuntimeError("kaboom")):
            with pytest.raises(ConnectionError, match="Unexpected error"):
                t.connect()

    def test_disconnect_when_not_connected_is_noop(self):
        t = _make_transport()
        t.disconnect()  # should not raise
        assert t.state == TransportState.DISCONNECTED

    def test_disconnect_sets_state_and_clears_ws(self):
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        t.disconnect()
        assert t.state == TransportState.DISCONNECTED
        assert t._ws is None
        assert fake_ws.closed is True

    def test_disconnect_wakes_pending_requests(self):
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        # Manually insert a pending request
        event = threading.Event()
        container: dict = {}
        t._pending["req-99"] = (event, container)

        t.disconnect()

        assert event.is_set()
        assert isinstance(container.get("error"), ConnectionError)


# ---------------------------------------------------------------------------
# health_check()
# ---------------------------------------------------------------------------


class TestWebSocketTransportHealthCheck:
    """Tests for health_check()."""

    def test_health_check_not_connected_returns_false(self):
        t = _make_transport()
        assert t.health_check() is False

    def test_health_check_connected_pings(self):
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        assert t.health_check() is True
        assert fake_ws.pinged is True
        t.disconnect()

    def test_health_check_ping_error_returns_false(self):
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        fake_ws.pinged = False  # reset
        with patch.object(t, "_send_ping", side_effect=OSError("ping failed")):
            assert t.health_check() is False

        t.disconnect()


# ---------------------------------------------------------------------------
# execute()
# ---------------------------------------------------------------------------


class TestWebSocketTransportExecute:
    """Tests for execute() — synchronous RPC over WebSocket."""

    def _connect_with_fake(self, t: WebSocketTransport) -> _FakeWS:
        """Connect transport without background threads and return the fake WS."""
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)
        return fake_ws

    def test_execute_not_connected_raises(self):
        t = _make_transport()
        with pytest.raises(ConnectionError):
            t.execute("get_scene_info")

    def test_execute_delivers_response(self):
        t = _make_transport(host="localhost", port=8765, timeout=5.0)
        self._connect_with_fake(t)

        # Simulate a response arriving from the server
        response_payload = json.dumps(
            {"type": "response", "id": "req-1", "result": {"success": True, "objects": []}}
        )

        def _simulate_response():
            time.sleep(0.05)
            t._dispatch_message(response_payload)

        threading.Thread(target=_simulate_response, daemon=True).start()

        result = t.execute("get_scene_info")
        assert result["success"] is True
        assert result["objects"] == []

        t.disconnect()

    def test_execute_timeout_raises(self):
        t = _make_transport(host="localhost", port=8765)
        self._connect_with_fake(t)

        with pytest.raises(TimeoutError, match="timed out"):
            t.execute("slow_action", timeout=0.05)

        t.disconnect()

    def test_execute_server_error_message_raises_protocol_error(self):
        t = _make_transport(host="localhost", port=8765, timeout=5.0)
        self._connect_with_fake(t)

        def _simulate_error():
            time.sleep(0.05)
            t._dispatch_message(
                json.dumps(
                    {"type": "error", "id": "req-1", "message": "DCC error: object not found"}
                )
            )

        threading.Thread(target=_simulate_error, daemon=True).start()

        with pytest.raises(ProtocolError, match="DCC error"):
            t.execute("delete_object")

        t.disconnect()

    def test_execute_params_included_in_request(self):
        t = _make_transport(host="localhost", port=8765, timeout=5.0)
        self._connect_with_fake(t)

        # Directly enqueue the send via _enqueue_message override to capture
        sent_messages = []

        def _capture_and_respond(message: str):
            sent_messages.append(message)
            # Immediately simulate a response
            data = json.loads(message)
            t._dispatch_message(
                json.dumps({"type": "response", "id": data["id"], "result": {"success": True}})
            )

        t._enqueue_message = _capture_and_respond  # type: ignore[method-assign]

        t.execute("create_object", params={"type": "sphere", "name": "mySphere"})

        assert len(sent_messages) == 1
        sent_data = json.loads(sent_messages[0])
        assert sent_data["action"] == "create_object"
        assert sent_data["params"]["type"] == "sphere"

        t.disconnect()


# ---------------------------------------------------------------------------
# subscribe / unsubscribe / event dispatch
# ---------------------------------------------------------------------------


class TestWebSocketEventSubscription:
    """Tests for event subscription and dispatch."""

    def test_subscribe_registers_callback(self):
        t = _make_transport()
        cb = MagicMock()
        t.subscribe("selection_changed", cb)
        assert cb in t.subscriptions()["selection_changed"]

    def test_subscribe_same_callback_twice_deduplicates(self):
        t = _make_transport()
        cb = MagicMock()
        t.subscribe("scene_modified", cb)
        t.subscribe("scene_modified", cb)
        assert t.subscriptions()["scene_modified"].count(cb) == 1

    def test_unsubscribe_removes_callback(self):
        t = _make_transport()
        cb = MagicMock()
        t.subscribe("frame_changed", cb)
        t.unsubscribe("frame_changed", cb)
        assert cb not in t.subscriptions().get("frame_changed", [])

    def test_unsubscribe_nonexistent_callback_is_noop(self):
        t = _make_transport()
        cb = MagicMock()
        t.unsubscribe("nonexistent_event", cb)  # should not raise

    def test_dispatch_event_calls_subscriber(self):
        t = _make_transport()
        received = []

        def cb(event_name, data):
            received.append((event_name, data))

        t.subscribe("selection_changed", cb)
        t._dispatch_message(
            json.dumps(
                {"type": "event", "event": "selection_changed", "data": {"objects": ["cube"]}}
            )
        )
        assert len(received) == 1
        assert received[0] == ("selection_changed", {"objects": ["cube"]})

    def test_dispatch_event_wildcard_subscriber(self):
        t = _make_transport()
        received = []
        t.subscribe("*", lambda ev, d: received.append(ev))

        t._dispatch_message(
            json.dumps({"type": "event", "event": "frame_changed", "data": {}})
        )
        assert "frame_changed" in received

    def test_dispatch_event_callback_exception_does_not_propagate(self):
        t = _make_transport()

        def bad_cb(ev, data):
            raise RuntimeError("callback boom")

        t.subscribe("error_event", bad_cb)
        # Should not raise
        t._dispatch_message(
            json.dumps({"type": "event", "event": "error_event", "data": {}})
        )

    def test_dispatch_unknown_type_is_handled_gracefully(self):
        t = _make_transport()
        t._dispatch_message(json.dumps({"type": "unknown_type", "data": {}}))

    def test_dispatch_non_json_is_handled_gracefully(self):
        t = _make_transport()
        t._dispatch_message("not valid json {{{")

    def test_dispatch_event_missing_event_field(self):
        t = _make_transport()
        t._dispatch_message(json.dumps({"type": "event", "data": {}}))

    def test_dispatch_response_missing_id_is_handled(self):
        t = _make_transport()
        t._dispatch_message(json.dumps({"type": "response", "result": {"success": True}}))

    def test_dispatch_error_without_id_logs_only(self):
        t = _make_transport()
        t._dispatch_message(
            json.dumps({"type": "error", "message": "global server error"})
        )


# ---------------------------------------------------------------------------
# _next_request_id (thread safety smoke test)
# ---------------------------------------------------------------------------


class TestWebSocketRequestIdGeneration:
    """Tests for unique request ID generation."""

    def test_ids_are_unique(self):
        t = _make_transport()
        ids = {t._next_request_id() for _ in range(100)}
        assert len(ids) == 100

    def test_ids_increment(self):
        t = _make_transport()
        first = t._next_request_id()
        second = t._next_request_id()
        assert first == "req-1"
        assert second == "req-2"


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestWebSocketContextManager:
    """Tests for __enter__ / __exit__ context manager usage."""

    def test_context_manager_connects_and_disconnects(self):
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()

        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(t, "_open_connection", return_value=fake_ws))
            stack.enter_context(patch.object(t, "_start_background_threads"))
            with t:
                assert t.is_connected is True

        assert t.state == TransportState.DISCONNECTED
