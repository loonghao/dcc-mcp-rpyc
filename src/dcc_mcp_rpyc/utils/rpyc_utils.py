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
            # Use classic.deliver to convert NetRefs to actual values
            delivered_params[key] = classic.deliver(value)
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
    # Process keyword arguments
    processed_kwargs = deliver_parameters(kwargs) if kwargs else {}

    # Process positional arguments
    processed_args = []
    for arg in args:
        try:
            processed_args.append(classic.deliver(arg))
        except Exception as e:
            logger.warning(f"Error delivering positional argument: {e}")
            processed_args.append(arg)

    # Get the command object from the connection
    cmd = getattr(connection, command)

    # Execute the command with processed arguments
    return cmd(*processed_args, **processed_kwargs)
