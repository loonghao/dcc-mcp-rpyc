"""Rust-native IPC transport implementation.

Wraps the high-performance ``IpcListener`` / ``FramedChannel`` / ``connect_ipc``
API shipped by dcc-mcp-core (Rust/PyO3 backend).

Server side
-----------
Use :class:`IpcServerTransport` inside a DCC plugin:

    addr = TransportAddress.default_local("maya", os.getpid())
    server = IpcServerTransport(addr)
    server.start()           # blocks in a background thread

Client side
-----------
Use :class:`IpcClientTransport` from an MCP server or test:

    config = IpcTransportConfig(host="localhost", port=0)
    transport = IpcClientTransport(addr)
    transport.connect()
    result = transport.execute("get_scene_info")
    transport.disconnect()
"""

# Import built-in modules
import json
import logging
import threading
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional

# Import third-party modules
from dcc_mcp_core import IpcListener
from dcc_mcp_core import ListenerHandle
from dcc_mcp_core import TransportAddress
from dcc_mcp_core import connect_ipc

# Import local modules
from dcc_mcp_ipc.transport.base import BaseTransport
from dcc_mcp_ipc.transport.base import ConnectionError
from dcc_mcp_ipc.transport.base import ProtocolError
from dcc_mcp_ipc.transport.base import TimeoutError
from dcc_mcp_ipc.transport.base import TransportConfig
from dcc_mcp_ipc.transport.base import TransportState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class IpcTransportConfig(TransportConfig):
    """Configuration for the Rust-native IPC transport.

    Attributes:
        address_uri: Optional override for the transport address
            (e.g. ``"tcp://127.0.0.1:18900"``).  When *None* the
            ``host``/``port`` pair from the base config is used to
            construct a ``tcp://`` URI.
        connect_timeout_ms: Connection timeout in milliseconds (default: 10 000).
        call_timeout_ms: Per-RPC call timeout in milliseconds (default: 30 000).

    """

    address_uri: Optional[str] = None
    connect_timeout_ms: int = 10_000
    call_timeout_ms: int = 30_000


# ---------------------------------------------------------------------------
# Client transport
# ---------------------------------------------------------------------------

class IpcClientTransport(BaseTransport):
    """Client-side IPC transport backed by ``FramedChannel``.

    Connects to a DCC-side :class:`IpcServerTransport` (or any service that
    exposes a ``IpcListener``-compatible endpoint) and dispatches RPC calls
    through the ``FramedChannel.call()`` API.
    """

    def __init__(self, config: Optional[IpcTransportConfig] = None) -> None:
        """Initialise the IPC client transport.

        Args:
            config: Optional :class:`IpcTransportConfig`; defaults are used
                when *None*.

        """
        super().__init__(config or IpcTransportConfig())
        self._channel = None  # dcc_mcp_core.FramedChannel

    @property
    def ipc_config(self) -> IpcTransportConfig:
        """Return the IPC-specific configuration."""
        return self._config  # type: ignore[return-value]

    def _resolve_address(self) -> TransportAddress:
        """Build a ``TransportAddress`` from config values."""
        cfg = self.ipc_config
        if cfg.address_uri:
            return TransportAddress.parse(cfg.address_uri)
        return TransportAddress.tcp(cfg.host, cfg.port)

    # -- BaseTransport interface --------------------------------------------

    def connect(self) -> None:
        """Connect to the remote IPC listener."""
        if self._state == TransportState.CONNECTED and self._channel:
            return

        self._state = TransportState.CONNECTING
        try:
            addr = self._resolve_address()
            logger.info("Connecting via Rust IPC to %s", addr)
            self._channel = connect_ipc(addr, timeout_ms=self.ipc_config.connect_timeout_ms)
            self._state = TransportState.CONNECTED
            logger.info("IPC connection established to %s", addr)
        except Exception as exc:
            self._state = TransportState.ERROR
            self._channel = None
            raise ConnectionError(
                f"Failed to connect via IPC: {exc}",
                cause=exc,
            ) from exc

    def disconnect(self) -> None:
        """Close the IPC channel gracefully."""
        if self._channel:
            try:
                self._channel.shutdown()
                logger.info("IPC channel closed")
            except Exception as exc:
                logger.warning("Error closing IPC channel: %s", exc)
            finally:
                self._channel = None
        self._state = TransportState.DISCONNECTED

    def health_check(self) -> bool:
        """Ping the remote service."""
        if not self._channel:
            return False
        try:
            self._channel.ping(timeout_ms=5_000)
            return True
        except Exception:
            self._state = TransportState.ERROR
            return False

    def execute(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute a named action via the IPC channel.

        Parameters are serialised to ``bytes`` (JSON) and sent as a
        ``call()`` on the ``FramedChannel``.

        Args:
            action: Action/method name to invoke on the remote service.
            params: Optional dict of parameters (JSON-serialisable).
            timeout: Per-call timeout in **seconds**; falls back to
                ``ipc_config.call_timeout_ms / 1000``.

        Returns:
            Response dict from the remote service.

        Raises:
            ConnectionError: If not connected.
            TimeoutError: If the call exceeds the timeout.
            ProtocolError: On remote error.

        """
        if not self._channel or self._state != TransportState.CONNECTED:
            raise ConnectionError("Not connected — call connect() first")

        params_bytes: Optional[bytes] = None
        if params:
            try:
                params_bytes = json.dumps(params).encode("utf-8")
            except (TypeError, ValueError) as exc:
                raise ProtocolError(f"Cannot serialise params for '{action}': {exc}", cause=exc) from exc

        timeout_ms = int((timeout or self.ipc_config.call_timeout_ms / 1_000) * 1_000)

        try:
            response = self._channel.call(action, params_bytes, timeout_ms=timeout_ms)
        except Exception as exc:
            err_str = str(exc).lower()
            if "timeout" in err_str:
                raise TimeoutError(f"IPC call '{action}' timed out", cause=exc) from exc
            self._state = TransportState.ERROR
            raise ProtocolError(f"IPC call '{action}' failed: {exc}", cause=exc) from exc

        # response is already a dict from FramedChannel.call()
        if isinstance(response, dict):
            if not response.get("success", True) and response.get("error"):
                raise ProtocolError(f"Remote error on '{action}': {response['error']}")
            return response

        return {"success": True, "result": response}


# ---------------------------------------------------------------------------
# Server transport
# ---------------------------------------------------------------------------

class IpcServerTransport:
    """Server-side IPC listener backed by ``IpcListener``.

    Runs an accept loop in a background daemon thread, invoking a
    *handler* callable for every inbound ``FramedChannel``.

    Example::

        def handle(channel):
            msg = channel.recv()
            # … process and respond …

        addr = TransportAddress.default_local("maya", os.getpid())
        srv = IpcServerTransport(addr, handler=handle)
        srv.start()     # returns immediately
        # …
        srv.stop()

    """

    def __init__(
        self,
        address: TransportAddress,
        handler: Optional[Callable] = None,
        *,
        accept_timeout_ms: int = 1_000,
    ) -> None:
        """Initialise the server transport.

        Args:
            address: ``TransportAddress`` to bind.
            handler: Callable invoked with the accepted ``FramedChannel``.
                Each channel is handled in its own daemon thread.
            accept_timeout_ms: Timeout for each accept() call so the loop
                can check the shutdown flag (default: 1 000 ms).

        """
        self._address = address
        self._handler = handler
        self._accept_timeout_ms = accept_timeout_ms
        self._listener: Optional[IpcListener] = None
        self._handle: Optional[ListenerHandle] = None
        self._thread: Optional[threading.Thread] = None

    # -- Lifecycle ---------------------------------------------------------

    def start(self) -> TransportAddress:
        """Bind the listener and start the accept loop in a daemon thread.

        Returns:
            The actual ``TransportAddress`` the listener is bound to (useful
            when port 0 was requested for auto-assignment).

        """
        self._listener = IpcListener.bind(self._address)
        bound_addr = self._listener.local_address()
        self._handle = self._listener.into_handle()
        logger.info("IPC server listening on %s", bound_addr)

        self._thread = threading.Thread(
            target=self._accept_loop,
            name=f"ipc-server-{bound_addr}",
            daemon=True,
        )
        self._thread.start()
        return bound_addr

    def stop(self) -> None:
        """Request shutdown and wait for the accept thread to exit."""
        if self._handle:
            self._handle.shutdown()
            logger.info("IPC server shutdown requested")
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    @property
    def is_running(self) -> bool:
        """True while the accept loop thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def local_address(self) -> Optional[TransportAddress]:
        """Return the bound address, or *None* before :meth:`start`."""
        if self._listener:
            return self._listener.local_address()
        return None

    # -- Internal ----------------------------------------------------------

    def _accept_loop(self) -> None:
        """Background thread: accept connections until shutdown is requested."""
        if not self._handle:
            return

        while not self._handle.is_shutdown:
            try:
                # Blocking accept with a short timeout so we can poll shutdown
                channel = self._handle.accept(self._accept_timeout_ms)  # type: ignore[attr-defined]
                if channel is None:
                    continue

                if self._handler:
                    t = threading.Thread(
                        target=self._handler,
                        args=(channel,),
                        daemon=True,
                    )
                    t.start()
                else:
                    logger.warning("IPC: accepted connection but no handler registered — closing channel")
                    channel.shutdown()

            except Exception as exc:
                if not self._handle.is_shutdown:
                    logger.error("IPC accept loop error: %s", exc)

        logger.info("IPC accept loop exited")
