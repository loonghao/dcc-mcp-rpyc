"""RPyC parameter processing utilities for the DCC-MCP ecosystem.

This module extends the parameter processing capabilities of dcc_mcp_core
with RPyC-specific functionality to handle remote procedure calls.
"""

# Import built-in modules
import logging
from typing import Any, Dict, List, Optional, Tuple, Union, Type, Callable

# Import third-party modules
import rpyc
from rpyc.utils import classic

# Import local modules
from dcc_mcp_core.parameters.processor import process_parameters as core_process_parameters
from dcc_mcp_core.parameters.processor import process_parameter_value

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


def create_service_factory(service_class: Type[rpyc.Service], *args, **kwargs) -> Callable:
    """Create a factory function for a service class with bound arguments.
    
    This is similar to rpyc.utils.helpers.classpartial but with more flexibility
    for DCC-MCP specific needs. It allows creating a service factory that will
    instantiate the service with the provided arguments for each new connection.
    
    Args:
        service_class: The RPyC service class to create a factory for
        *args: Positional arguments to pass to the service constructor
        **kwargs: Keyword arguments to pass to the service constructor
        
    Returns:
        A factory function that creates service instances
    """
    class ServiceFactory:
        """Factory for creating service instances with bound arguments."""
        
        def __init__(self):
            self.service_class = service_class
            self.args = args
            self.kwargs = kwargs
        
        def get_service_name(self):
            """Get the service name from the service class."""
            if hasattr(service_class, 'get_service_name'):
                return service_class.get_service_name()
            # Default behavior: use class name without 'Service' suffix
            name = service_class.__name__
            if name.endswith("Service"):
                name = name[:-7]
            return name.upper()
        
        def get_service_aliases(self):
            """Get the service aliases from the service class."""
            if hasattr(service_class, 'get_service_aliases'):
                return service_class.get_service_aliases()
            return (self.get_service_name(),)
        
        def __call__(self, conn):
            """Create a new service instance for each connection."""
            instance = service_class(*args, **kwargs)
            if hasattr(instance, 'on_connect'):
                instance.on_connect(conn)
            return instance
    
    return ServiceFactory()


def create_shared_service_instance(service_class: Type[rpyc.Service], *args, **kwargs) -> rpyc.Service:
    """Create a shared service instance that will be used for all connections.
    
    This function creates a single instance of the service that will be
    shared among all connections. This is useful when you want to share
    state between different connections.
    
    Args:
        service_class: The RPyC service class to instantiate
        *args: Positional arguments to pass to the service constructor
        **kwargs: Keyword arguments to pass to the service constructor
        
    Returns:
        A service instance that will be shared among all connections
    """
    instance = service_class(*args, **kwargs)
    
    # Create a wrapper that handles on_connect
    class SharedServiceWrapper:
        """Wrapper for a shared service instance."""
        
        def __init__(self, instance):
            self.instance = instance
        
        def get_service_name(self):
            """Get the service name from the instance."""
            if hasattr(instance, 'get_service_name'):
                return instance.get_service_name()
            # Default behavior
            name = service_class.__name__
            if name.endswith("Service"):
                name = name[:-7]
            return name.upper()
        
        def get_service_aliases(self):
            """Get the service aliases from the instance."""
            if hasattr(instance, 'get_service_aliases'):
                return instance.get_service_aliases()
            return (self.get_service_name(),)
        
        def __call__(self, conn):
            """Return the shared instance for each connection."""
            if hasattr(instance, 'on_connect'):
                instance.on_connect(conn)
            return instance
    
    return SharedServiceWrapper(instance)


def get_rpyc_config(allow_all_attrs=False, allow_public_attrs=True, allow_pickle=False):
    """Get a configuration dictionary for RPyC connections.
    
    This function creates a configuration dictionary with common settings
    for RPyC connections in the DCC-MCP ecosystem.
    
    Args:
        allow_all_attrs: Whether to allow access to all attributes
        allow_public_attrs: Whether to allow access to public attributes
        allow_pickle: Whether to allow pickle serialization
        
    Returns:
        A configuration dictionary for RPyC connections
    """
    return {
        'allow_all_attrs': allow_all_attrs,
        'allow_public_attrs': allow_public_attrs,
        'allow_pickle': allow_pickle,
        'sync_request_timeout': 30,
        'allow_safe_attrs': True,
        'allow_exposed_attrs': True,
    }
