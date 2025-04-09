"""Context management for DCC-MCP-RPYC.

This module provides functions for managing context data that can be shared between
different components of the DCC-MCP-RPYC system.
"""

# Import built-in modules
import logging
import threading
from typing import Any, Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Thread-local storage for context data
_context = threading.local()


def set_context(key: str, value: Any) -> None:
    """Set a value in the context.
    
    Args:
        key: The key to store the value under
        value: The value to store
    """
    if not hasattr(_context, "data"):
        _context.data = {}
    _context.data[key] = value
    logger.debug(f"Set context key '{key}'")


def get_context(key: str, default: Any = None) -> Any:
    """Get a value from the context.
    
    Args:
        key: The key to retrieve the value for
        default: The default value to return if the key is not found
        
    Returns:
        The value associated with the key, or the default value if the key is not found
    """
    if not hasattr(_context, "data") or key not in _context.data:
        logger.debug(f"Context key '{key}' not found, returning default")
        return default
    return _context.data[key]


def clear_context() -> None:
    """Clear all context data."""
    if hasattr(_context, "data"):
        _context.data = {}
    logger.debug("Cleared context data")


def remove_context(key: str) -> None:
    """Remove a key from the context.
    
    Args:
        key: The key to remove
    """
    if hasattr(_context, "data") and key in _context.data:
        del _context.data[key]
        logger.debug(f"Removed context key '{key}'")


def get_all_context() -> Dict[str, Any]:
    """Get all context data.
    
    Returns:
        A dictionary containing all context data
    """
    if not hasattr(_context, "data"):
        return {}
    return dict(_context.data)
