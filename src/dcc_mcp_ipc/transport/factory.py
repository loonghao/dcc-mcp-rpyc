"""Transport factory for creating and managing transport instances.

This module provides a registry-based factory for creating transport instances
by protocol name, making it easy to switch between RPyC, HTTP, and WebSocket
transports without changing upper-level code.
"""

# Import built-in modules
import logging
from typing import Dict
from typing import Optional
from typing import Type

# Import local modules
from dcc_mcp_ipc.transport.base import BaseTransport
from dcc_mcp_ipc.transport.base import TransportConfig

logger = logging.getLogger(__name__)

# Global transport class registry: protocol_name -> transport_class
_transport_registry: Dict[str, Type[BaseTransport]] = {}

# Global transport instance cache: (protocol, host, port) -> transport
_transport_instances: Dict[tuple, BaseTransport] = {}


def register_transport(protocol: str, transport_class: Type[BaseTransport]) -> None:
    """Register a transport class for a protocol name.

    Args:
        protocol: Protocol identifier (e.g. ``"rpyc"``, ``"http"``, ``"ws"``).
        transport_class: The transport class to register.

    """
    _transport_registry[protocol.lower()] = transport_class
    logger.debug("Registered transport '%s' -> %s", protocol, transport_class.__name__)


def create_transport(
    protocol: str,
    config: Optional[TransportConfig] = None,
    **kwargs: object,
) -> BaseTransport:
    """Create a new transport instance for the given protocol.

    Args:
        protocol: Protocol identifier (e.g. ``"rpyc"``, ``"http"``).
        config: Transport configuration. If not provided, a default config
            is created using ``**kwargs``.
        **kwargs: If ``config`` is not provided, these are passed to the
            config class for the transport.

    Returns:
        A new transport instance (not yet connected).

    Raises:
        ValueError: If the protocol is not registered.

    """
    protocol = protocol.lower()
    transport_class = _transport_registry.get(protocol)
    if transport_class is None:
        available = ", ".join(sorted(_transport_registry.keys())) or "(none)"
        raise ValueError(
            f"Unknown transport protocol '{protocol}'. Available: {available}"
        )

    return transport_class(config)


def get_transport(
    protocol: str,
    host: str = "localhost",
    port: int = 0,
    config: Optional[TransportConfig] = None,
    **kwargs: object,
) -> BaseTransport:
    """Get or create a cached transport instance.

    If a transport for the same (protocol, host, port) triple already exists
    and is still connected, it is returned directly. Otherwise a new one is
    created and cached.

    Args:
        protocol: Protocol identifier.
        host: Remote host.
        port: Remote port.
        config: Optional transport configuration.
        **kwargs: Extra config kwargs.

    Returns:
        A transport instance (may already be connected).

    """
    key = (protocol.lower(), host, port)
    existing = _transport_instances.get(key)
    if existing is not None and existing.is_connected:
        return existing

    if config is None:
        config = TransportConfig(host=host, port=port)
    transport = create_transport(protocol, config)
    _transport_instances[key] = transport
    return transport


def _register_builtins() -> None:
    """Register built-in transport implementations.

    Called at module load time to ensure RPyC and HTTP transports are always
    available.
    """
    # Lazy imports to avoid circular dependencies and optional deps
    try:
        from dcc_mcp_ipc.transport.rpyc_transport import RPyCTransport

        register_transport("rpyc", RPyCTransport)
    except ImportError:
        logger.debug("RPyC transport not available (rpyc not installed)")

    try:
        from dcc_mcp_ipc.transport.http import HTTPTransport

        register_transport("http", HTTPTransport)
    except ImportError:
        logger.debug("HTTP transport not available")


# Auto-register built-in transports on import
_register_builtins()
