"""Adapter module for DCC-MCP-RPYC.

This package provides adapter classes for connecting DCC applications to MCP servers.
"""

# Import built-in modules
import logging
from typing import Dict
from typing import Optional

# Import local modules
# Import from submodules
from dcc_mcp_rpyc.adapter.base import ApplicationAdapter
from dcc_mcp_rpyc.adapter.dcc import DCCAdapter
from dcc_mcp_rpyc.adapter.session import SessionAdapter

# Configure logging
logger = logging.getLogger(__name__)

# Global registry of adapters
_adapters: Dict[str, ApplicationAdapter] = {}


def get_adapter(
    app_name: str, adapter_type: str = "session", session_id: Optional[Optional[str]] = None, **kwargs
) -> ApplicationAdapter:
    """Get an adapter for the specified application.

    This function returns an existing adapter for the application if one exists,
    or creates a new one if not.

    Args:
    ----
        app_name: Name of the application
        adapter_type: Type of adapter to create (default: 'session')
        session_id: Optional session ID for session adapters
        **kwargs: Additional arguments for the adapter

    Returns:
    -------
        An adapter instance for the application

    Raises:
    ------
        ValueError: If the adapter type is not supported

    """
    # Create a unique key for the adapter
    adapter_key = f"{app_name}_{adapter_type}_{session_id or ''}"

    # Return existing adapter if available
    if adapter_key in _adapters:
        logger.debug(f"Using existing adapter for {app_name}")
        return _adapters[adapter_key]

    # Create a new adapter based on the type
    if adapter_type == "session":
        adapter = SessionAdapter(app_name, session_id=session_id)
    elif adapter_type == "dcc":
        adapter = DCCAdapter(app_name)
    else:
        raise ValueError(f"Unsupported adapter type: {adapter_type}")

    # Store the adapter in the registry
    _adapters[adapter_key] = adapter
    logger.debug(f"Created new {adapter_type} adapter for {app_name}")

    return adapter


__all__ = [
    # Base classes
    "ApplicationAdapter",
    # Adapter implementations
    "DCCAdapter",
    "SessionAdapter",
    # Factory functions
    "get_adapter",
]
