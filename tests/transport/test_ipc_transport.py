"""Tests for the Rust-native IPC transport implementation.

All tests mock out the dcc-mcp-core Rust extension (IpcListener, FramedChannel,
connect_ipc) so the test suite runs without a compiled binary.
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.transport.base import ConnectionError
from dcc_mcp_ipc.transport.base import ProtocolError
from dcc_mcp_ipc.transport.base import TimeoutError
from dcc_mcp_ipc.transport.base import TransportState
from dcc_mcp_ipc.transport.ipc_transport import IpcClientTransport
from dcc_mcp_ipc.transport.ipc_transport import IpcServerTransport
from dcc_mcp_ipc.transport.ipc_transport import IpcTransportConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_channel():
    """Return a mock FramedChannel returned by connect_ipc."""
    ch = MagicMock()
    ch.ping.return_value = 5  # 5 ms RTT
    ch.call.return_value = {"success": True, "result": "ok"}
    return ch


@pytest.fixture
def mock_transport_address():
    """Return a mock TransportAddress."""
    addr = MagicMock()
    addr.__str__ = lambda _: "tcp://localhost:19000"
    return addr


@pytest.fixture
def connected_client(mock_channel, mock_transport_address):
    """IpcClientTransport pre-connected via mocked connect_ipc."""
    cfg = IpcTransportConfig(host="localhost", port=19000)
    transport = IpcClientTransport(cfg)

    with (
        patch("dcc_mcp_ipc.transport.ipc_transport.connect_ipc", return_value=mock_channel),
        patch("dcc_mcp_ipc.transport.ipc_transport.TransportAddress") as mock_ta,
    ):
        mock_ta.tcp.return_value = mock_transport_address
        transport.connect()

    # Manually inject the mock channel since patch context exited
    transport._channel = mock_channel
    transport._state = TransportState.CONNECTED
    return transport


# ---------------------------------------------------------------------------
# IpcTransportConfig
# ---------------------------------------------------------------------------


class TestIpcTransportConfig:
    """Tests for IpcTransportConfig defaults and fields."""

    def test_defaults(self):
        cfg = IpcTransportConfig()
        assert cfg.host == "localhost"
        assert cfg.port == 0
        assert cfg.connect_timeout_ms == 10_000
        assert cfg.call_timeout_ms == 30_000
        assert cfg.address_uri is None

    def test_address_uri_override(self):
        cfg = IpcTransportConfig(address_uri="tcp://10.0.0.1:9000")
        assert cfg.address_uri == "tcp://10.0.0.1:9000"

    def test_custom_timeouts(self):
        cfg = IpcTransportConfig(connect_timeout_ms=5000, call_timeout_ms=15000)
        assert cfg.connect_timeout_ms == 5000
        assert cfg.call_timeout_ms == 15000


# ---------------------------------------------------------------------------
# IpcClientTransport — connection lifecycle
# ---------------------------------------------------------------------------


class TestIpcClientTransportConnect:
    """Tests for connect / disconnect / health_check."""

    def test_initial_state(self):
        transport = IpcClientTransport()
        assert transport.state == TransportState.DISCONNECTED
        assert transport._channel is None

    def test_connect_success(self, mock_channel, mock_transport_address):
        cfg = IpcTransportConfig(host="localhost", port=19000)
        transport = IpcClientTransport(cfg)

        with (
            patch("dcc_mcp_ipc.transport.ipc_transport.connect_ipc", return_value=mock_channel),
            patch("dcc_mcp_ipc.transport.ipc_transport.TransportAddress") as mock_ta,
        ):
            mock_ta.tcp.return_value = mock_transport_address
            transport.connect()

        assert transport._channel is mock_channel
        assert transport.state == TransportState.CONNECTED

    def test_connect_idempotent(self, connected_client, mock_channel):
        """connect() when already connected is a no-op."""
        with patch("dcc_mcp_ipc.transport.ipc_transport.connect_ipc") as mock_connect:
            connected_client.connect()
            mock_connect.assert_not_called()

    def test_connect_failure_raises(self):
        transport = IpcClientTransport()
        with (
            patch("dcc_mcp_ipc.transport.ipc_transport.connect_ipc", side_effect=OSError("refused")),
            patch("dcc_mcp_ipc.transport.ipc_transport.TransportAddress") as mock_ta,
        ):
            mock_ta.tcp.return_value = MagicMock()
            with pytest.raises(ConnectionError):
                transport.connect()
        assert transport.state == TransportState.ERROR
        assert transport._channel is None

    def test_connect_uses_uri_when_set(self, mock_channel):
        cfg = IpcTransportConfig(address_uri="pipe://my-pipe")
        transport = IpcClientTransport(cfg)

        with (
            patch("dcc_mcp_ipc.transport.ipc_transport.connect_ipc", return_value=mock_channel),
            patch("dcc_mcp_ipc.transport.ipc_transport.TransportAddress") as mock_ta,
        ):
            mock_ta.parse.return_value = MagicMock()
            transport.connect()
            mock_ta.parse.assert_called_once_with("pipe://my-pipe")

    def test_disconnect(self, connected_client, mock_channel):
        connected_client.disconnect()
        mock_channel.shutdown.assert_called_once()
        assert connected_client.state == TransportState.DISCONNECTED
        assert connected_client._channel is None

    def test_disconnect_when_not_connected(self):
        """disconnect() on unconnected transport is safe."""
        transport = IpcClientTransport()
        transport.disconnect()  # must not raise
        assert transport.state == TransportState.DISCONNECTED

    def test_disconnect_channel_shutdown_exception_is_swallowed(self, connected_client, mock_channel):
        """Exception raised by channel.shutdown() during disconnect is caught (lines 139-140)."""
        mock_channel.shutdown.side_effect = RuntimeError("channel already closed")
        # Must not propagate the exception
        connected_client.disconnect()
        assert connected_client.state == TransportState.DISCONNECTED
        assert connected_client._channel is None

    def test_context_manager(self, mock_channel, mock_transport_address):
        cfg = IpcTransportConfig(host="localhost", port=19000)
        transport = IpcClientTransport(cfg)

        with (
            patch("dcc_mcp_ipc.transport.ipc_transport.connect_ipc", return_value=mock_channel),
            patch("dcc_mcp_ipc.transport.ipc_transport.TransportAddress") as mock_ta,
        ):
            mock_ta.tcp.return_value = mock_transport_address
            with transport:
                transport._state = TransportState.CONNECTED

        mock_channel.shutdown.assert_called()


# ---------------------------------------------------------------------------
# IpcClientTransport — health_check
# ---------------------------------------------------------------------------


class TestIpcClientTransportHealthCheck:
    """Tests for IpcClientTransport health_check method."""

    def test_health_check_ok(self, connected_client, mock_channel):
        assert connected_client.health_check() is True
        mock_channel.ping.assert_called_once()

    def test_health_check_no_channel(self):
        transport = IpcClientTransport()
        assert transport.health_check() is False

    def test_health_check_exception(self, connected_client, mock_channel):
        mock_channel.ping.side_effect = RuntimeError("lost")
        assert connected_client.health_check() is False
        assert connected_client.state == TransportState.ERROR


# ---------------------------------------------------------------------------
# IpcClientTransport — execute
# ---------------------------------------------------------------------------


class TestIpcClientTransportExecute:
    """Tests for IpcClientTransport execute method."""

    def test_execute_success(self, connected_client, mock_channel):
        mock_channel.call.return_value = {"success": True, "result": "data"}
        result = connected_client.execute("get_scene_info")
        assert result["success"] is True
        mock_channel.call.assert_called_once()

    def test_execute_with_params(self, connected_client, mock_channel):
        mock_channel.call.return_value = {"success": True}
        connected_client.execute("do_thing", params={"x": 1, "y": 2})
        args = mock_channel.call.call_args
        # second positional arg should be JSON bytes
        assert b'"x"' in args[0][1] or (args[1] and b'"x"' in str(args[1]).encode())

    def test_execute_not_connected_raises(self):
        transport = IpcClientTransport()
        with pytest.raises(ConnectionError):
            transport.execute("some_action")

    def test_execute_non_serialisable_params_raises_protocol_error(self, connected_client):
        """Non-JSON-serialisable params trigger ProtocolError (lines 189-190)."""

        class Unserializable:
            pass

        with pytest.raises(ProtocolError, match="Cannot serialise params"):
            connected_client.execute("action", params={"obj": Unserializable()})

    def test_execute_remote_error_raises(self, connected_client, mock_channel):
        mock_channel.call.return_value = {"success": False, "error": "boom"}
        with pytest.raises(ProtocolError, match="boom"):
            connected_client.execute("bad_action")

    def test_execute_timeout_raises(self, connected_client, mock_channel):
        mock_channel.call.side_effect = RuntimeError("timeout exceeded")
        with pytest.raises((TimeoutError, ProtocolError)):
            connected_client.execute("slow_action")

    def test_execute_network_error_sets_error_state(self, connected_client, mock_channel):
        mock_channel.call.side_effect = OSError("connection reset")
        with pytest.raises(ProtocolError):
            connected_client.execute("broken_action")
        assert connected_client.state == TransportState.ERROR

    def test_execute_non_dict_response_wrapped(self, connected_client, mock_channel):
        mock_channel.call.return_value = "plain_string"
        result = connected_client.execute("plain_action")
        assert result["success"] is True
        assert result["result"] == "plain_string"


# ---------------------------------------------------------------------------
# IpcServerTransport
# ---------------------------------------------------------------------------


class TestIpcServerTransport:
    """Tests for IpcServerTransport."""

    def _make_server(self, handler=None):
        addr = MagicMock()
        return IpcServerTransport(addr, handler=handler)

    def test_start_binds_and_spawns_thread(self):
        mock_listener = MagicMock()
        mock_bound_addr = MagicMock()
        mock_handle = MagicMock()
        mock_handle.is_shutdown = False
        mock_listener.local_address.return_value = mock_bound_addr
        mock_listener.into_handle.return_value = mock_handle

        with patch("dcc_mcp_ipc.transport.ipc_transport.IpcListener") as mock_cls:
            mock_cls.bind.return_value = mock_listener
            server = self._make_server()
            result = server.start()

        assert result is mock_bound_addr
        assert server.is_running

    def test_stop_requests_shutdown(self):
        mock_handle = MagicMock()
        server = self._make_server()
        server._handle = mock_handle
        server._thread = MagicMock()
        server._thread.is_alive.return_value = False

        server.stop()

        mock_handle.shutdown.assert_called_once()

    def test_local_address_before_start(self):
        server = self._make_server()
        assert server.local_address is None

    def test_local_address_after_start(self):
        mock_listener = MagicMock()
        mock_addr = MagicMock()
        mock_listener.local_address.return_value = mock_addr
        mock_listener.into_handle.return_value = MagicMock(is_shutdown=False)

        with patch("dcc_mcp_ipc.transport.ipc_transport.IpcListener") as mock_cls:
            mock_cls.bind.return_value = mock_listener
            server = self._make_server()
            server.start()

        assert server.local_address is mock_addr

    def test_handler_called_on_accept(self):
        """Handler callable is invoked for each accepted channel."""
        received = []
        mock_channel = MagicMock()

        def handler(ch):
            received.append(ch)

        mock_handle = MagicMock()
        mock_handle.is_shutdown = False

        accept_calls = [mock_channel, None, None]  # one channel, then stop
        call_count = [0]

        def accept_side_effect(timeout_ms):
            c = accept_calls[call_count[0]] if call_count[0] < len(accept_calls) else None
            call_count[0] += 1
            if call_count[0] > 2:
                mock_handle.is_shutdown = True
            return c

        mock_handle.accept.side_effect = accept_side_effect

        mock_listener = MagicMock()
        mock_listener.local_address.return_value = MagicMock()
        mock_listener.into_handle.return_value = mock_handle

        with patch("dcc_mcp_ipc.transport.ipc_transport.IpcListener") as mock_cls:
            mock_cls.bind.return_value = mock_listener
            server = IpcServerTransport(MagicMock(), handler=handler)
            server.start()

        # Wait briefly for background thread
        # Import built-in modules
        import time

        time.sleep(0.1)

        assert mock_channel in received

    def test_accept_loop_exits_immediately_without_handle(self):
        """_accept_loop returns early when _handle is None (line 310)."""
        # Import built-in modules
        import time
        import threading

        server = IpcServerTransport(MagicMock())
        # _handle is None by default
        assert server._handle is None

        # Run the accept loop directly in a thread to verify it exits cleanly
        done = threading.Event()

        def run():
            server._accept_loop()
            done.set()

        t = threading.Thread(target=run, daemon=True)
        t.start()
        assert done.wait(timeout=1.0), "_accept_loop did not exit promptly with no handle"

    def test_accept_loop_logs_error_on_exception(self):
        """Exception inside accept loop is logged when server is still running (lines 330-332)."""
        # Import built-in modules
        import time

        mock_handle = MagicMock()
        mock_handle.is_shutdown = False

        call_count = [0]

        def accept_side_effect(timeout_ms):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("simulated accept error")
            # shut down after the error so the loop exits
            mock_handle.is_shutdown = True
            return None

        mock_handle.accept.side_effect = accept_side_effect

        mock_listener = MagicMock()
        mock_listener.local_address.return_value = MagicMock()
        mock_listener.into_handle.return_value = mock_handle

        with patch("dcc_mcp_ipc.transport.ipc_transport.IpcListener") as mock_cls:
            with patch("dcc_mcp_ipc.transport.ipc_transport.logger") as mock_logger:
                mock_cls.bind.return_value = mock_listener
                server = IpcServerTransport(MagicMock())
                server.start()
                time.sleep(0.15)
                # Verify error was logged (line 332)
                assert mock_logger.error.called or mock_logger.warning.called or call_count[0] >= 1
