"""RPyC transport implementation.

This module provides the RPyC-based transport, wrapping the existing RPyC
connection logic behind the ``BaseTransport`` interface. It is the default
transport for DCC applications that embed a Python interpreter
(Maya, Blender, Houdini, 3ds Max, Nuke).
"""

# Import built-in modules
import dataclasses
import logging
from typing import Any
from typing import Optional

# Import third-party modules
import rpyc

# Import local modules
from dcc_mcp_ipc.transport.base import BaseTransport
from dcc_mcp_ipc.transport.base import ConnectionError
from dcc_mcp_ipc.transport.base import ProtocolError
from dcc_mcp_ipc.transport.base import TransportConfig
from dcc_mcp_ipc.transport.base import TransportState

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class RPyCTransportConfig(TransportConfig):
    """RPyC-specific transport configuration.

    Attributes:
        sync_request_timeout: RPyC sync request timeout in seconds.
        allow_all_attrs: Whether to allow access to all object attributes.
        allow_public_attrs: Whether to allow access to public attributes.

    """

    sync_request_timeout: float = 30.0
    allow_all_attrs: bool = True
    allow_public_attrs: bool = True


class RPyCTransport(BaseTransport):
    """Transport implementation using RPyC (Remote Python Call).

    This transport wraps ``rpyc.connect`` and provides a uniform interface
    for executing remote actions, Python code, and function calls within
    DCC applications that embed a Python interpreter.
    """

    def __init__(self, config: Optional[RPyCTransportConfig] = None) -> None:
        """Initialize the RPyC transport.

        Args:
            config: RPyC transport configuration.

        """
        super().__init__(config or RPyCTransportConfig())
        self._connection: Optional[rpyc.Connection] = None
        self._connect_func = rpyc.connect

    @property
    def rpyc_config(self) -> RPyCTransportConfig:
        """Get the RPyC-specific configuration."""
        return self._config  # type: ignore[return-value]

    @property
    def connection(self) -> Optional[rpyc.Connection]:
        """Get the underlying RPyC connection (may be None)."""
        return self._connection

    @property
    def root(self) -> Any:
        """Get the RPyC root service proxy.

        Returns:
            The root object of the RPyC connection.

        Raises:
            ConnectionError: If not connected.

        """
        if not self._connection:
            raise ConnectionError("Not connected — call connect() first")
        return self._connection.root

    # ── Connection Lifecycle ─────────────────────────────────────────

    def connect(self) -> None:
        """Establish an RPyC connection to the remote service."""
        if self._state == TransportState.CONNECTED and self._connection:
            logger.debug("Already connected to %s:%s", self._config.host, self._config.port)
            return

        self._state = TransportState.CONNECTING
        rpyc_cfg = {
            "sync_request_timeout": self.rpyc_config.sync_request_timeout,
            "allow_all_attrs": self.rpyc_config.allow_all_attrs,
            "allow_public_attrs": self.rpyc_config.allow_public_attrs,
        }

        try:
            logger.info("Connecting via RPyC to %s:%s", self._config.host, self._config.port)
            self._connection = self._connect_func(
                self._config.host,
                self._config.port,
                config=rpyc_cfg,
            )
            self._state = TransportState.CONNECTED
            logger.info("RPyC connection established to %s:%s", self._config.host, self._config.port)
        except Exception as exc:
            self._state = TransportState.ERROR
            self._connection = None
            raise ConnectionError(
                f"Failed to connect via RPyC to {self._config.host}:{self._config.port}: {exc}",
                cause=exc,
            ) from exc

    def disconnect(self) -> None:
        """Close the RPyC connection."""
        if self._connection:
            try:
                self._connection.close()
                logger.info("RPyC connection closed for %s:%s", self._config.host, self._config.port)
            except Exception as exc:
                logger.warning("Error closing RPyC connection: %s", exc)
            finally:
                self._connection = None
        self._state = TransportState.DISCONNECTED

    # ── Health ───────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """Ping the remote RPyC service."""
        if not self._connection:
            return False
        try:
            self._connection.ping()
            return True
        except Exception:
            self._state = TransportState.ERROR
            return False

    # ── Action Execution ─────────────────────────────────────────────

    def execute(
        self,
        action: str,
        params: Optional[dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        """Execute a named action via the RPyC service proxy.

        The method maps *action* to ``exposed_{action}`` on the RPyC root
        object, following RPyC's method-exposure convention.

        Args:
            action: Name of the remote action (without ``exposed_`` prefix).
            params: Keyword arguments forwarded to the remote method.
            timeout: Not used directly (RPyC uses ``sync_request_timeout``).

        Returns:
            Result dict from the remote method call.

        Raises:
            ConnectionError: If not connected.
            ProtocolError: If the remote method raises.

        """
        if not self.is_connected or not self._connection:
            raise ConnectionError("Not connected — call connect() first")

        params = params or {}
        method_name = f"exposed_{action}"

        try:
            method = getattr(self._connection.root, method_name, None)
            if method is None:
                # Fall back to non-prefixed name (some services expose without prefix)
                method = getattr(self._connection.root, action, None)
            if method is None:
                raise ProtocolError(f"Remote service has no method '{method_name}' or '{action}'")

            result = method(**params)

            # Normalise result to dict
            if isinstance(result, dict):
                return result
            return {"success": True, "result": result}

        except (ConnectionError, ProtocolError):
            raise
        except Exception as exc:
            raise ProtocolError(f"Error executing '{action}': {exc}", cause=exc) from exc

    # ── Convenience: raw RPyC access ─────────────────────────────────

    def execute_python(self, code: str, context: Optional[dict[str, Any]] = None) -> Any:
        """Execute Python code on the remote service via RPyC.

        Args:
            code: Python source code.
            context: Optional variable context.

        Returns:
            Result of the code execution.

        """
        if not self.is_connected or not self._connection:
            raise ConnectionError("Not connected — call connect() first")

        try:
            return self._connection.root.exposed_execute_python(code, context or {})
        except Exception as exc:
            raise ProtocolError(f"Error executing Python code: {exc}", cause=exc) from exc

    def call_function(
        self,
        module_name: str,
        function_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Call a function on the remote service via RPyC.

        Args:
            module_name: Module containing the function.
            function_name: Function to call.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Return value of the remote function.

        """
        if not self.is_connected or not self._connection:
            raise ConnectionError("Not connected — call connect() first")

        try:
            return self._connection.root.exposed_call_function(module_name, function_name, *args, **kwargs)
        except Exception as exc:
            raise ProtocolError(
                f"Error calling {module_name}.{function_name}: {exc}",
                cause=exc,
            ) from exc

    def import_module(self, module_name: str) -> Any:
        """Import a module on the remote service via RPyC.

        Args:
            module_name: Name of the module to import.

        Returns:
            The remote module proxy.

        """
        if not self.is_connected or not self._connection:
            raise ConnectionError("Not connected — call connect() first")

        try:
            return self._connection.root.exposed_get_module(module_name)
        except Exception as exc:
            raise ProtocolError(f"Error importing module {module_name}: {exc}", cause=exc) from exc
