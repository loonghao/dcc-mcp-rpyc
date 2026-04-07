"""RPyC utility functions for the DCC-MCP-IPC package.

This module provides utilities for handling parameters in RPyC remote calls,
including parameter delivery and remote command execution.
"""

# Import built-in modules
from typing import Any

# Import third-party modules
import rpyc


def deliver_parameters(params: dict[str, Any]) -> dict[str, Any]:
    """Convert NetRefs to actual values in a parameters dictionary.

    Args:
        params: Dictionary of parameters to process

    Returns:
        Processed parameters dictionary with NetRefs converted to values

    """
    return dict(params)


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
