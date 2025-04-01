"""RPyC utility functions for the DCC-MCP-RPYC package.

This module provides utilities for handling parameters in RPyC remote calls,
including parameter delivery and remote command execution.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Dict

# Import third-party modules
import rpyc
from rpyc.utils import classic

logger = logging.getLogger(__name__)


def deliver_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """Convert NetRefs to actual values in a parameters dictionary.

    Args:
        params: Dictionary of parameters to process

    Returns:
        Processed parameters dictionary with NetRefs converted to values

    """
    # Convert any NetRefs to actual values
    delivered_params = {}
    for key, value in params.items():
        try:
            delivered_params[key] = value
        except Exception as e:
            logger.warning(f"Error delivering parameter {key}: {e}")
            delivered_params[key] = value

    return delivered_params


def execute_remote_command(connection: "rpyc.Connection", command: str, *args, **kwargs) -> Any:
    """Execute a command on a remote RPyC connection with proper parameter handling.

    Args:
        connection: RPyC connection to use
        command: Command to execute
        *args: Positional arguments for the command
        **kwargs: Keyword arguments for the command

    Returns:
        Result of the remote command execution

    """

    # Get the command object from the connection
    cmd = getattr(connection, command)

    # Execute the command with processed arguments
    return cmd(*args, **kwargs)
