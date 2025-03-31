"""Decorators for DCC-MCP-RPYC servers.

This module provides decorators for adding metadata to server functions,
such as environment information, scene information, and session information.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Callable
from typing import TypeVar

# Import local modules
from dcc_mcp_rpyc.utils.decorators import with_info

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for function
F = TypeVar("F", bound=Callable[..., Any])


def with_environment_info(func: F) -> F:
    """Add environment information to the return value of a function.

    This decorator wraps a function to add the current environment information to its return value.
    The wrapped function's result will be returned as a dictionary with 'result' and 'environment_info' keys.

    Args:
    ----
        func: The function to wrap

    Returns:
    -------
        The wrapped function

    """
    return with_info(lambda self: self.get_environment_info(), "environment_info")(func)


def with_scene_info(func: F) -> F:
    """Add scene information to the return value of a function.

    This decorator wraps a function to add the current scene information to its return value.
    The wrapped function's result will be returned as a dictionary with 'result' and 'scene_info' keys.

    Args:
    ----
        func: The function to wrap

    Returns:
    -------
        The wrapped function

    """
    return with_info(lambda self: self.get_scene_info(), "scene_info")(func)


def with_session_info(func: F) -> F:
    """Add session information to the return value of a function.

    This decorator wraps a function to add the current session information to its return value.
    The wrapped function's result will be returned as a dictionary with 'result' and 'session_info' keys.

    Args:
    ----
        func: The function to wrap

    Returns:
    -------
        The wrapped function

    """
    return with_info(lambda self: self.get_session_info(), "session_info")(func)
