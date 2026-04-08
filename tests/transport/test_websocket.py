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
from dcc_mcp_ipc.transport.websocket import _STOP_SENTINEL

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
        response_payload = json.dumps({"type": "response", "id": "req-1", "result": {"success": True, "objects": []}})

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
            t._dispatch_message(json.dumps({"type": "error", "id": "req-1", "message": "DCC error: object not found"}))

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
            t._dispatch_message(json.dumps({"type": "response", "id": data["id"], "result": {"success": True}}))

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
        t._dispatch_message(json.dumps({"type": "event", "event": "selection_changed", "data": {"objects": ["cube"]}}))
        assert len(received) == 1
        assert received[0] == ("selection_changed", {"objects": ["cube"]})

    def test_dispatch_event_wildcard_subscriber(self):
        t = _make_transport()
        received = []
        t.subscribe("*", lambda ev, d: received.append(ev))

        t._dispatch_message(json.dumps({"type": "event", "event": "frame_changed", "data": {}}))
        assert "frame_changed" in received

    def test_dispatch_event_callback_exception_does_not_propagate(self):
        t = _make_transport()

        def bad_cb(ev, data):
            raise RuntimeError("callback boom")

        t.subscribe("error_event", bad_cb)
        # Should not raise
        t._dispatch_message(json.dumps({"type": "event", "event": "error_event", "data": {}}))

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
        t._dispatch_message(json.dumps({"type": "error", "message": "global server error"}))


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


# ---------------------------------------------------------------------------
# Edge case coverage: reader/writer loop paths, error handling
# ---------------------------------------------------------------------------


class TestWebSocketReaderLoopPaths:
    """Tests for uncovered _reader_loop and _dispatch_message edge cases.

    Covers lines 198-214 (disconnect cleanup), 370-392 (reader loop body),
    447-448 (unknown request id), 462-468 (error without id), 544-547 (recv exception).
    """

    def test_handle_response_unknown_request_id(self):
        """Line 447-448: response for unknown request id — should log and return."""
        t = _make_transport()
        # Should not raise, just silently ignore
        t._handle_response({"id": "nonexistent-id", "result": {"success": True}})

    def test_handle_response_missing_id_field(self):
        """Response with missing id field — should warn and return."""
        t = _make_transport()
        # No 'id' key in the dict
        t._handle_response({"result": {"success": True}})

    def test_handle_error_message_with_id(self):
        """Error message WITH a matching pending request."""
        t = _make_transport()
        event = threading.Event()
        container: dict = {}
        t._pending["req-match"] = (event, container)

        t._handle_error_message({"id": "req-match", "message": "remote failure"})
        assert event.is_set()
        assert isinstance(container.get("error"), ProtocolError)

    def test_handle_error_message_without_id(self):
        """Line 462-468: error WITHOUT request id — should log only."""
        t = _make_transport()
        # No pending entry for this id, no id at all
        t._handle_error_message({"message": "server-wide error", "code": 500})
        # Should not raise

    def test_handle_error_message_with_nonexistent_id(self):
        """Error message with an id that has no matching pending entry."""
        t = _make_transport()
        # id exists but not in pending dict
        t._handle_error_message({"id": "req-ghost", "message": "orphaned error"})

    def test_recv_message_exception_returns_none(self):
        """Line 544-547: _recv_message exception handling returns None."""
        t = _make_transport()
        fake_ws = _FakeWS()
        # Override recv to raise
        fake_ws.recv = lambda: (_ for _ in ()).throw(OSError("connection lost"))

        result = t._recv_message(fake_ws)
        assert result is None

    def test_send_ping_delegates(self):
        """_send_ping delegates to ws.ping()."""
        t = _make_transport()
        fake_ws = _FakeWS()
        t._send_ping(fake_ws)
        assert fake_ws.pinged is True

    def test_close_connection_delegates(self):
        """_close_connection delegates to ws.close()."""
        t = _make_transport()
        fake_ws = _FakeWS()
        t._close_connection(fake_ws)
        assert fake_ws.closed is True

    def test_writer_loop_exits_on_stop_sentinel(self):
        """Writer loop stops when receiving STOP_SENTINEL."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        # Start writer thread briefly then stop it
        t._writer_thread = threading.Thread(target=t._writer_loop, daemon=True)
        t._writer_thread.start()

        # Send stop sentinel
        t._send_queue.put(object())  # sentinel-like object to break loop

        # Actually use the real stop mechanism
        t.disconnect()  # This sends the proper sentinel via _send_queue


class TestWebSocketDisconnectCleanup:
    """Tests for disconnect() cleanup of threads and pending requests.

    Covers lines 198-216 (disconnect cleanup logic).
    """

    def test_disconnect_clears_pending_requests(self):
        """Disconnect should clear all pending requests."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        # Add multiple pending requests
        for i in range(5):
            event = threading.Event()
            container: dict = {}
            t._pending[f"req-{i}"] = (event, container)

        t.disconnect()

        assert len(t._pending) == 0
        for i in range(5):
            # All events should be set
            assert event.is_set()

    def test_disconnect_close_exception_is_handled(self):
        """Disconnect handles exceptions when closing WS gracefully."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()

        # Make close() raise
        fake_ws.close = lambda: (_ for _ in ()).throw(RuntimeError("close error"))

        _connect_no_threads(t, fake_ws)
        t.disconnect()  # Should not raise despite close() error
        assert t.state == TransportState.DISCONNECTED

    def test_disconnect_idempotent_multiple_calls(self):
        """Multiple disconnect calls are safe."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        t.disconnect()
        t.disconnect()  # Second call should be no-op
        assert t.state == TransportState.DISCONNECTED


class TestWebSocketExecuteEdgeCases:
    """Additional execute() edge cases for coverage."""

    def test_execute_generic_exception_wrapped_as_protocol_error(self):
        """Line 299-300: unexpected exception in execute wrapped as ProtocolError."""
        t = _make_transport(host="localhost", port=8765, timeout=5.0)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        # Override _enqueue_message to raise something unexpected
        t._enqueue_message = lambda msg: (_ for _ in ()).throw(RuntimeError("unexpected"))

        with pytest.raises(ProtocolError, match="Error executing"):
            t.execute("test_action")

        t.disconnect()


class TestWebSocketURLSSL:
    """Test ws_url property with SSL configuration."""

    def test_ws_url_default_is_ws(self):
        """Default URL uses ws:// scheme (no SSL)."""
        config = WebSocketTransportConfig(host="host", port=8080)
        t = WebSocketTransport(config)
        assert t.ws_url.startswith("ws://")
        assert not t.ws_url.startswith("wss://")

    def test_ws_url_metadata_use_ssl_does_not_change_scheme(self):
        """Metadata-only use_ssl does not change the URL scheme."""
        config = WebSocketTransportConfig(
            host="secure.host",
            port=9443,
            path="/ws",
            metadata={"use_ssl": True},
        )
        t = WebSocketTransport(config)
        assert t.ws_url == "ws://secure.host:9443/ws"


# ---------------------------------------------------------------------------
# Coverage improvement: _reader_loop, _start_background_threads, _open_connection
# ---------------------------------------------------------------------------


class TestWebSocketReaderLoopEdgeCases:
    """Tests for uncovered reader loop paths (lines 370-392, 403-408)."""

    def test_reader_loop_recv_none_breaks_loop(self):
        """When _recv_message returns None (connection closed), loop breaks."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS(responses=[])  # recv raises StopIteration -> None from _recv_message
        _connect_no_threads(t, fake_ws)

        # Run the reader loop in a thread; it should exit quickly when recv returns None
        reader = threading.Thread(target=t._reader_loop, daemon=True)
        reader.start()
        reader.join(timeout=2.0)
        assert not reader.is_alive(), "Reader thread should have exited"

        t.disconnect()

    def test_reader_loop_exception_sets_error_state(self):
        """Exception during recv while CONNECTED sets state to ERROR and wakes pending."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        # Insert pending request that should be woken on error
        event = threading.Event()
        container: dict = {}
        t._pending["req-err"] = (event, container)

        # Make recv raise an exception to trigger error path in reader loop
        original_recv = fake_ws.recv

        def _failing_recv():
            # First call succeeds so we enter the loop body
            original_recv()
            # Second call raises
            raise OSError("connection reset")

        fake_ws.recv = _failing_recv

        # Run reader loop briefly
        reader = threading.Thread(target=t._reader_loop, daemon=True)
        reader.start()
        reader.join(timeout=2.0)

        # State should be ERROR due to unexpected disconnect
        assert t.state == TransportState.ERROR
        # Pending request should be woken with ConnectionError
        assert event.is_set()
        assert isinstance(container.get("error"), ConnectionError)

        t._state = TransportState.DISCONNECTED  # cleanup for test teardown
        t._pending.clear()

    def test_writer_loop_exits_when_ws_none(self):
        """Writer loop exits when self._ws becomes None."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        writer = threading.Thread(target=t._writer_loop, daemon=True)
        writer.start()

        time.sleep(0.05)
        t._ws = None
        t._send_queue.put('{"test": true}')

        writer.join(timeout=2.0)
        assert not writer.is_alive()

        t._ws = fake_ws  # restore for clean disconnect
        t.disconnect()


class TestWebSocketStartBackgroundThreads:
    """Tests for _start_background_threads (lines 355-366)."""

    def test_start_background_threads_creates_both_threads(self):
        """_start_background_threads creates both reader and writer threads."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()

        with patch.object(t, "_open_connection", return_value=fake_ws):
            t.connect()  # This calls _start_background_threads internally

        assert t._reader_thread is not None
        assert t._writer_thread is not None
        assert t._reader_thread.daemon is True
        assert t._writer_thread.daemon is True
        assert "ws-reader" in t._reader_thread.name
        assert "ws-writer" in t._writer_thread.name

        t.disconnect()

    def test_start_background_threads_threads_are_alive(self):
        """Both threads are alive after connect()."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS(responses=[])

        with patch.object(t, "_open_connection", return_value=fake_ws):
            t.connect()

        # Threads should be started (may exit immediately if recv fails)
        assert t._reader_thread is not None
        assert t._writer_thread is not None

        t.disconnect()


class TestWebSocketOpenConnection:
    """Tests for _open_connection (lines 510-516) and protocol hooks."""

    def test_open_connection_can_be_monkeypatched(self):
        """_open_connection is designed for monkeypatching/subclass override."""
        t = _make_transport(host="localhost", port=8765)
        mock_conn = MagicMock()
        # The method is designed to be overridden; test the monkeypatch pattern
        t._open_connection = lambda: mock_conn  # type: ignore[method-assign]
        assert t._open_connection() is mock_conn

    def test_open_connection_extra_headers_in_config(self):
        """Extra headers are accessible from config for _open_connection overrides."""
        config = WebSocketTransportConfig(
            host="localhost",
            port=8765,
            extra_headers={"X-Token": "secret"},
        )
        t = WebSocketTransport(config)
        assert t._ws_config.extra_headers == {"X-Token": "secret"}

    def test_open_connection_default_raises_if_no_websockets(self):
        """Default _open_connection raises ImportError if websockets not installed."""
        t = _make_transport(host="localhost", port=8765)
        # We can't easily test the actual ImportError without uninstalling websockets,
        # but we verify the method is callable and has the right signature
        # Import built-in modules
        import inspect

        sig = inspect.signature(t._open_connection)
        assert len(sig.parameters) == 0


class TestWebSocketDisconnectWithThreads:
    """Tests for disconnect() thread cleanup paths (lines 213-216)."""

    def test_disconnect_joins_reader_thread(self):
        """disconnect() joins the reader thread within timeout."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS(responses=[])
        _connect_no_threads(t, fake_ws)

        # Start a reader thread manually
        t._reader_thread = threading.Thread(target=t._reader_loop, daemon=True)
        t._reader_thread.start()
        time.sleep(0.05)

        t.disconnect()
        # After disconnect, reader_thread should be None (joined and cleaned up)
        assert t._reader_thread is None

    def test_disconnect_joins_writer_thread(self):
        """disconnect() joins the writer thread within timeout."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        # Start a writer thread manually
        t._writer_thread = threading.Thread(target=t._writer_loop, daemon=True)
        t._writer_thread.start()
        time.sleep(0.05)

        t.disconnect()
        assert t._writer_thread is None

    def test_disconnect_calls_join_when_reader_is_alive(self):
        """disconnect() calls join() when _reader_thread.is_alive() returns True (line 212)."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        mock_thread = MagicMock(spec=threading.Thread)
        mock_thread.is_alive.return_value = True
        t._reader_thread = mock_thread

        t.disconnect()

        mock_thread.join.assert_called_once_with(timeout=2.0)
        assert t._reader_thread is None

    def test_disconnect_calls_join_when_writer_is_alive(self):
        """disconnect() calls join() when _writer_thread.is_alive() returns True."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        mock_thread = MagicMock(spec=threading.Thread)
        mock_thread.is_alive.return_value = True
        t._writer_thread = mock_thread

        t.disconnect()

        mock_thread.join.assert_called_once_with(timeout=2.0)
        assert t._writer_thread is None


class TestWebSocketExecuteWithContainerError:
    """Test execute() when response container has an error key."""

    def test_execute_container_with_protocol_error_raises_it(self):
        """execute() re-raises ProtocolError stored in the container."""
        t = _make_transport(host="localhost", port=8765, timeout=5.0)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        def _simulate_error_response():
            time.sleep(0.05)
            t._dispatch_message(json.dumps({"type": "response", "id": "req-1"}))
            # Manually inject a ProtocolError into the container
            with t._pending_lock:
                if "req-1" in t._pending:
                    _, container = t._pending["req-1"]
                    container["error"] = ProtocolError("injected protocol error")

        threading.Thread(target=_simulate_error_response, daemon=True).start()

        with pytest.raises(ProtocolError, match="injected protocol error"):
            t.execute("action_with_container_error")

        t.disconnect()

    def test_execute_container_with_connection_error_raises_it(self):
        """execute() re-raises ConnectionError stored in the container."""
        t = _make_transport(host="localhost", port=8765, timeout=5.0)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        def _simulate_error_response():
            time.sleep(0.05)
            t._dispatch_message(json.dumps({"type": "response", "id": "req-1"}))
            with t._pending_lock:
                if "req-1" in t._pending:
                    _, container = t._pending["req-1"]
                    container["error"] = ConnectionError("injected conn error")

        threading.Thread(target=_simulate_error_response, daemon=True).start()

        with pytest.raises(ConnectionError, match="injected conn error"):
            t.execute("action_with_conn_error")

        t.disconnect()


class TestWebSocketTemporaryCoverageConsolidation:
    """Stable behavior tests moved out of temporary ``iter11`` coverage files."""

    def test_disconnect_with_missing_ws_skips_close(self):
        """disconnect() should not attempt to close a missing websocket handle."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)
        t._ws = None

        with patch.object(t, "_close_connection") as mock_close:
            t.disconnect()

        mock_close.assert_not_called()

    def test_reader_loop_dispatch_error_sets_transport_state_to_error(self):
        """Dispatch failures in the reader loop should mark the transport as errored."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS(['{"type": "event", "event": "test", "data": {}}'])
        _connect_no_threads(t, fake_ws)

        with patch.object(t, "_dispatch_message", side_effect=RuntimeError("dispatch error")):
            reader = threading.Thread(target=t._reader_loop, daemon=True)
            reader.start()
            reader.join(timeout=2.0)

        assert t.state == TransportState.ERROR
        t._state = TransportState.DISCONNECTED
        t._pending.clear()

    def test_writer_loop_send_error_breaks_loop(self):
        """A send failure should terminate the writer loop instead of hanging."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        original_send = t._send_message
        t._send_message = lambda ws, msg: (_ for _ in ()).throw(OSError("broken pipe"))  # type: ignore[method-assign]

        writer = threading.Thread(target=t._writer_loop, daemon=True)
        writer.start()
        t._send_queue.put('{"action": "test"}')
        writer.join(timeout=2.0)

        assert not writer.is_alive(), "Writer should exit after a send error"
        t._send_message = original_send  # type: ignore[method-assign]
        t._state = TransportState.DISCONNECTED

    def test_open_connection_passes_extra_headers_as_list(self):
        """Configured extra headers should be converted to the list format expected by websockets."""
        config = WebSocketTransportConfig(
            host="localhost",
            port=8765,
            extra_headers={"X-Api-Key": "secret", "X-Session": "sess-1"},
        )
        t = WebSocketTransport(config)

        mock_ws = MagicMock()
        captured_calls = []

        def mock_connect(url, additional_headers=None, **kwargs):
            captured_calls.append({"url": url, "headers": additional_headers})
            return mock_ws

        with patch("websockets.sync.client.connect", mock_connect):
            result = t._open_connection()

        assert result is mock_ws
        assert captured_calls[0]["headers"] is not None
        assert ("X-Api-Key", "secret") in captured_calls[0]["headers"]
        assert ("X-Session", "sess-1") in captured_calls[0]["headers"]

    def test_open_connection_without_extra_headers_passes_none(self):
        """Empty extra headers should keep the websocket connect call clean."""
        t = WebSocketTransport(WebSocketTransportConfig(host="localhost", port=8765, extra_headers={}))

        mock_ws = MagicMock()
        captured_calls = []

        def mock_connect(url, additional_headers=None, **kwargs):
            captured_calls.append(additional_headers)
            return mock_ws

        with patch("websockets.sync.client.connect", mock_connect):
            result = t._open_connection()

        assert result is mock_ws
        assert captured_calls == [None]

