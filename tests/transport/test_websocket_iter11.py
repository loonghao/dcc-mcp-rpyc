"""Iteration-11 WebSocket transport coverage.

Targets the previously uncovered branches reported at 94%:
- Lines 196→201: disconnect() _close_connection raises (exception in try, finally clears _ws)
- Line 212: disconnect() joins reader thread when alive
- Lines 368→380/374-378: _reader_loop exception path while CONNECTED → ERROR state,
  wakes pending requests
- Lines 381→exit: reader loop exits cleanly without error
- Lines 402-404: _writer_loop send exception
- Lines 507-510: _open_connection extra_headers → list conversion
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
from dcc_mcp_ipc.transport.base import TransportState
from dcc_mcp_ipc.transport.websocket import WebSocketTransport
from dcc_mcp_ipc.transport.websocket import WebSocketTransportConfig
from dcc_mcp_ipc.transport.websocket import _STOP_SENTINEL


class _FakeWS:
    """Minimal fake WS for unit tests."""

    def __init__(self, responses=None, recv_exception=None):
        self._responses = iter(responses or [])
        self._recv_exception = recv_exception
        self.sent = []
        self.closed = False
        self.pinged = False
        self._close_raises = False

    def send(self, message: str) -> None:
        self.sent.append(message)

    def recv(self) -> str:
        if self._recv_exception is not None:
            raise self._recv_exception
        try:
            return next(self._responses)
        except StopIteration:
            raise OSError("connection closed")

    def ping(self) -> None:
        self.pinged = True

    def close(self) -> None:
        if self._close_raises:
            raise RuntimeError("close failed")
        self.closed = True


def _connect_no_threads(t: WebSocketTransport, fake_ws: _FakeWS) -> None:
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(t, "_open_connection", return_value=fake_ws))
        stack.enter_context(patch.object(t, "_start_background_threads"))
        t.connect()


def _make_transport(**config_kwargs) -> WebSocketTransport:
    config = WebSocketTransportConfig(**config_kwargs)
    return WebSocketTransport(config)


# ---------------------------------------------------------------------------
# Lines 196→201: disconnect() _close_connection raises → finally clears _ws
# ---------------------------------------------------------------------------


class TestDisconnectCloseConnectionRaises:
    """Covers the exception branch in disconnect() (lines 196-201)."""

    def test_disconnect_close_raises_ws_still_cleared(self):
        """_close_connection raises → exception is logged, _ws is still set to None."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        fake_ws._close_raises = True  # close() will raise RuntimeError
        _connect_no_threads(t, fake_ws)

        # disconnect() should not propagate the close exception
        t.disconnect()

        assert t._ws is None
        assert t.state == TransportState.DISCONNECTED

    def test_disconnect_with_ws_none_skips_close(self):
        """When _ws is None, _close_connection is not called."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        # Manually set _ws to None before disconnect
        t._ws = None

        with patch.object(t, "_close_connection") as mock_close:
            t.disconnect()
            mock_close.assert_not_called()


# ---------------------------------------------------------------------------
# Line 212: reader thread join
# ---------------------------------------------------------------------------


class TestDisconnectJoinsReaderThread:
    """Covers line 212 — disconnect() joins reader thread."""

    def test_disconnect_joins_alive_reader_thread(self):
        """Reader thread is started and then joined during disconnect()."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS(responses=[])
        _connect_no_threads(t, fake_ws)

        # Start reader thread manually so it's alive
        t._reader_thread = threading.Thread(target=t._reader_loop, daemon=True)
        t._reader_thread.start()

        # Give it a moment to start
        time.sleep(0.05)

        # Should join the reader thread (which exits quickly due to empty responses)
        t.disconnect()

        # After disconnect, thread reference is cleared
        assert t._reader_thread is None


# ---------------------------------------------------------------------------
# Lines 368→380/374-378: reader loop exception → ERROR state + wake pending
# ---------------------------------------------------------------------------


class TestReaderLoopExceptionSetsErrorState:
    """Covers the except branch in _reader_loop (lines 375-388)."""

    def test_reader_loop_recv_exception_sets_state_to_error(self):
        """When _recv_message returns None (connection closed), loop breaks.
        
        Since _recv_message catches exceptions and returns None, we need to 
        ensure the while→None→break path works correctly.
        """
        t = _make_transport(host="localhost", port=8765)
        # recv_exception is caught by _recv_message which returns None
        # This makes raw=None → break → finally checks state
        fake_ws = _FakeWS(recv_exception=OSError("network reset"))
        _connect_no_threads(t, fake_ws)

        reader = threading.Thread(target=t._reader_loop, daemon=True)
        reader.start()
        reader.join(timeout=2.0)

        # The reader loop's finally block should have detected unexpected disconnect
        assert t.state == TransportState.ERROR

        # Cleanup
        t._state = TransportState.DISCONNECTED
        t._pending.clear()

    def test_reader_loop_dispatch_message_raises_triggers_except_branch(self):
        """_dispatch_message raising causes lines 375-378 to execute (except branch)."""
        t = _make_transport(host="localhost", port=8765)
        
        # Provide a valid message so recv() returns data (not None)
        valid_msg = '{"type": "event", "event": "test", "data": {}}'
        fake_ws = _FakeWS(responses=[valid_msg])
        _connect_no_threads(t, fake_ws)

        # Make _dispatch_message raise on first call
        with patch.object(t, "_dispatch_message", side_effect=RuntimeError("dispatch error")):
            reader = threading.Thread(target=t._reader_loop, daemon=True)
            reader.start()
            reader.join(timeout=2.0)

        # Loop exits via except branch → finally sets state to ERROR
        assert t.state == TransportState.ERROR

        # Cleanup
        t._state = TransportState.DISCONNECTED
        t._pending.clear()

    def test_reader_loop_while_condition_false_skips_body(self):
        """When state is DISCONNECTED from the start, while body is never entered (368→380)."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        # Manually set to DISCONNECTED before running reader loop
        t._state = TransportState.DISCONNECTED

        reader = threading.Thread(target=t._reader_loop, daemon=True)
        reader.start()
        reader.join(timeout=1.0)

        # State stays DISCONNECTED (finally block only sets ERROR if CONNECTED)
        assert t.state == TransportState.DISCONNECTED

    def test_reader_loop_wakes_pending_on_unexpected_disconnect(self):
        """Pending requests get ConnectionError when reader loop fails unexpectedly."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS(recv_exception=ConnectionResetError("peer closed"))
        _connect_no_threads(t, fake_ws)

        event = threading.Event()
        container: dict = {}
        t._pending["req-lost"] = (event, container)

        reader = threading.Thread(target=t._reader_loop, daemon=True)
        reader.start()
        reader.join(timeout=2.0)

        # Pending request should be woken with a ConnectionError
        assert event.is_set()
        assert isinstance(container.get("error"), ConnectionError)

        # Cleanup
        t._state = TransportState.DISCONNECTED
        t._pending.clear()

    def test_reader_loop_no_error_state_when_already_disconnected(self):
        """If state changes to DISCONNECTED before the error, final block is a no-op."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        call_count = [0]

        def recv_that_changes_state():
            call_count[0] += 1
            if call_count[0] == 1:
                # Simulate we're already being disconnected
                t._state = TransportState.DISCONNECTED
            raise OSError("closed after disconnect")

        fake_ws.recv = recv_that_changes_state

        event = threading.Event()
        container: dict = {}
        t._pending["req-safe"] = (event, container)

        reader = threading.Thread(target=t._reader_loop, daemon=True)
        reader.start()
        reader.join(timeout=2.0)

        # State should remain DISCONNECTED (not ERROR), pending NOT woken
        assert t.state == TransportState.DISCONNECTED
        t._pending.clear()


# ---------------------------------------------------------------------------
# Lines 402-404: _writer_loop send raises
# ---------------------------------------------------------------------------


class TestWriterLoopSendRaises:
    """Covers the exception in _writer_loop body (lines 400-404)."""

    def test_writer_loop_send_error_breaks_loop(self):
        """When _send_message raises, the writer loop exits."""
        t = _make_transport(host="localhost", port=8765)
        fake_ws = _FakeWS()
        _connect_no_threads(t, fake_ws)

        # Make _send_message raise on the first call
        original_send = t._send_message

        def failing_send(ws, msg):
            raise OSError("broken pipe")

        t._send_message = failing_send  # type: ignore[method-assign]

        writer = threading.Thread(target=t._writer_loop, daemon=True)
        writer.start()

        # Enqueue a real message to trigger the send
        t._send_queue.put('{"action": "test"}')
        writer.join(timeout=2.0)

        assert not writer.is_alive(), "Writer should have exited after send error"

        # Restore and cleanup
        t._send_message = original_send  # type: ignore[method-assign]
        t._state = TransportState.DISCONNECTED


# ---------------------------------------------------------------------------
# Lines 507-510: _open_connection with extra_headers
# ---------------------------------------------------------------------------


class TestOpenConnectionExtraHeaders:
    """Covers lines 507-510: _open_connection with extra_headers in actual method body."""

    def test_open_connection_passes_extra_headers_as_list(self):
        """Lines 507-510: extra_headers dict → list of tuples passed to ws_sync.connect."""
        import websockets.sync.client as ws_sync  # noqa: F401 (ensure importable)

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
        assert len(captured_calls) == 1
        headers = captured_calls[0]["headers"]
        assert isinstance(headers, list)
        assert ("X-Api-Key", "secret") in headers
        assert ("X-Session", "sess-1") in headers

    def test_open_connection_no_extra_headers_passes_none(self):
        """Lines 507-510: empty extra_headers → additional_headers=None."""
        config = WebSocketTransportConfig(host="localhost", port=8765, extra_headers={})
        t = WebSocketTransport(config)

        mock_ws = MagicMock()
        captured_calls = []

        def mock_connect(url, additional_headers=None, **kwargs):
            captured_calls.append({"headers": additional_headers})
            return mock_ws

        with patch("websockets.sync.client.connect", mock_connect):
            result = t._open_connection()

        assert result is mock_ws
        headers = captured_calls[0]["headers"]
        assert headers is None
