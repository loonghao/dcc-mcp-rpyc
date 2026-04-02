"""Base transport abstraction for protocol-agnostic IPC.

This module defines the core transport interface that all protocol implementations
(RPyC, HTTP, WebSocket, Named Pipe) must implement. Upper-level code (clients,
adapters) should depend only on BaseTransport, never on a concrete protocol.
"""

# Import built-in modules
from abc import ABC
from abc import abstractmethod
from enum import Enum
import logging
from typing import Any
from typing import Dict
from typing import Optional

# Import third-party modules
from pydantic import BaseModel
from pydantic import Field

logger = logging.getLogger(__name__)


class TransportState(str, Enum):
    """Connection state of a transport."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class TransportConfig(BaseModel):
    """Configuration for a transport connection.

    Attributes:
        host: Hostname or IP address of the remote service.
        port: Port number of the remote service.
        timeout: Default timeout for operations in seconds.
        retry_count: Number of retries on transient failures.
        retry_delay: Delay between retries in seconds.
        metadata: Protocol-specific configuration options.

    """

    host: str = "localhost"
    port: int = 0
    timeout: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TransportError(Exception):
    """Base exception for transport errors."""

    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        """Initialize transport error.

        Args:
            message: Error description.
            cause: Original exception that caused this error.

        """
        super().__init__(message)
        self.cause = cause


class ConnectionError(TransportError):
    """Raised when a connection cannot be established or is lost."""


class TimeoutError(TransportError):
    """Raised when an operation exceeds its timeout."""


class ProtocolError(TransportError):
    """Raised when the remote side returns a protocol-level error."""


class BaseTransport(ABC):
    """Abstract base class for all transport implementations.

    A transport encapsulates the details of a specific IPC protocol and exposes
    a uniform interface for connecting to remote services, executing actions,
    and managing the connection lifecycle.

    Subclasses must implement all abstract methods. The base class provides
    common state management and logging.
    """

    def __init__(self, config: Optional[TransportConfig] = None) -> None:
        """Initialize the transport.

        Args:
            config: Transport configuration. Uses defaults if not provided.

        """
        self._config = config or TransportConfig()
        self._state = TransportState.DISCONNECTED
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    def config(self) -> TransportConfig:
        """Get the transport configuration."""
        return self._config

    @property
    def state(self) -> TransportState:
        """Get the current transport state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if the transport is currently connected."""
        return self._state == TransportState.CONNECTED

    # ── Connection Lifecycle ─────────────────────────────────────────

    @abstractmethod
    def connect(self) -> None:
        """Establish a connection to the remote service.

        Uses ``self.config.host`` and ``self.config.port`` as the target.

        Raises:
            ConnectionError: If the connection cannot be established.

        """

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection to the remote service.

        This method should be idempotent — calling it on an already-disconnected
        transport must not raise.
        """

    def reconnect(self) -> None:
        """Disconnect and reconnect to the remote service."""
        self.disconnect()
        self.connect()

    # ── Health ───────────────────────────────────────────────────────

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the remote service is reachable and healthy.

        Returns:
            True if the service responded to a health probe.

        """

    # ── Action Execution (core RPC interface) ────────────────────────

    @abstractmethod
    def execute(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute a named action on the remote service.

        This is the primary RPC entry point. All DCC operations (screenshot,
        scene info, execute action, run script, etc.) are dispatched through
        this single method.

        Args:
            action: Name of the action / remote method to invoke.
            params: Parameters to pass to the action.
            timeout: Per-call timeout override. Falls back to ``config.timeout``.

        Returns:
            A dict containing at least ``{"success": bool, ...}``.

        Raises:
            ConnectionError: If the transport is not connected.
            TimeoutError: If the call exceeds the timeout.
            ProtocolError: If the remote side returns an error.

        """

    # ── Raw / Low-Level Access ───────────────────────────────────────

    def execute_python(self, code: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Execute arbitrary Python code on the remote service.

        This is a convenience wrapper around ``execute`` for transports that
        support remote code execution (e.g. RPyC). Transports that do not
        support it should raise ``NotImplementedError``.

        Args:
            code: Python source code to execute.
            context: Optional variable context for the execution.

        Returns:
            The result of the code execution.

        """
        return self.execute(
            "execute_python",
            {"code": code, "context": context or {}},
        )

    def call_function(
        self,
        module_name: str,
        function_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Call a named function on the remote service.

        Args:
            module_name: Fully-qualified module name.
            function_name: Function name within the module.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The return value of the remote function call.

        """
        return self.execute(
            "call_function",
            {
                "module_name": module_name,
                "function_name": function_name,
                "args": list(args),
                "kwargs": kwargs,
            },
        )

    # ── Context Manager ──────────────────────────────────────────────

    def __enter__(self) -> "BaseTransport":
        """Enter context: connect the transport."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context: disconnect the transport."""
        self.disconnect()

    # ── Representation ───────────────────────────────────────────────

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        cls = self.__class__.__name__
        return f"<{cls} host={self._config.host} port={self._config.port} state={self._state.value}>"
