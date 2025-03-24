"""RPyC parameter processing utilities for the DCC-MCP ecosystem.

This module extends the parameter processing capabilities of dcc_mcp_core
with RPyC-specific functionality to handle remote procedure calls.
"""

# Import built-in modules
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

# Import third-party modules
import rpyc
from rpyc.utils import classic

# Import local modules
from dcc_mcp_core.parameters.processor import process_parameters as core_process_parameters

logger = logging.getLogger(__name__)


def deliver_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """Process parameters and ensure they are delivered as values, not NetRefs.
    
    This function uses rpyc.utils.deliver to convert NetRefs to actual values,
    then processes the parameters using the core parameter processor.
    
    Args:
        params: Dictionary of parameters to process
        
    Returns:
        Processed parameters dictionary with NetRefs converted to values
    """
    # First convert any NetRefs to actual values
    delivered_params = {}
    for key, value in params.items():
        try:
            # Use classic.deliver to convert NetRefs to actual values
            delivered_params[key] = classic.deliver(value)
        except Exception as e:
            logger.warning(f"Error delivering parameter {key}: {e}")
            delivered_params[key] = value
    
    # Then process the parameters using the core processor
    return core_process_parameters(delivered_params)


def process_rpyc_parameters(params: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """Process and normalize parameters for RPyC remote calls.
    
    This function extends the core parameter processor with RPyC-specific
    handling to ensure proper parameter serialization.
    
    Args:
        params: Dictionary or string of parameters to process
        
    Returns:
        Processed parameters dictionary ready for RPyC remote calls
    """
    # First use the core processor to handle basic parameter processing
    processed_params = core_process_parameters(params)
    
    # Then ensure all parameters are delivered as values, not NetRefs
    return deliver_parameters(processed_params)


def execute_remote_command(connection: rpyc.Connection, command: str, *args, **kwargs) -> Any:
    """Execute a command on a remote RPyC connection with proper parameter handling.
    
    This function handles parameter processing and ensures proper delivery
    of arguments to the remote command.
    
    Args:
        connection: RPyC connection to use
        command: Command to execute
        *args: Positional arguments for the command
        **kwargs: Keyword arguments for the command
        
    Returns:
        Result of the remote command execution
    """
    # Process keyword arguments
    processed_kwargs = process_rpyc_parameters(kwargs) if kwargs else {}
    
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
