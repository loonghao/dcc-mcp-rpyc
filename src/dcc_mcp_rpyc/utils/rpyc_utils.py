"""RPyC utility functions for the DCC-MCP-RPYC package.

This module provides utilities for handling parameters in RPyC remote calls,
including parameter delivery and remote command execution.
"""

# Import built-in modules
import logging
import json
from typing import Any
from typing import Dict
from typing import List
from typing import Union

# Import third-party modules
import rpyc

logger = logging.getLogger(__name__)


def is_pydantic_model(obj: Any) -> bool:
    """Check if an object is a Pydantic model.
    
    Args:
        obj: Object to check
        
    Returns:
        True if the object is a Pydantic model, False otherwise
    """
    try:
        # Check if it's a class (not an instance)
        if isinstance(obj, type):
            return False
            
        # Check for common Pydantic model attributes
        pydantic_attributes = [
            # Common to both v1 and v2
            'model_fields', 'model_config',
            # v1 specific
            'schema', 'construct', 'parse_obj',
            # v2 specific
            'model_dump', 'model_dump_json', 'model_validate'
        ]
        
        # Check if object has any of these attributes
        for attr in pydantic_attributes:
            if hasattr(obj, attr):
                return True
                
        # Additional check for __pydantic_fields__ attribute (v1)
        if hasattr(obj, '__pydantic_fields__') or hasattr(obj, '__fields__'):
            return True
            
        # Check for model_validate method (v2)
        if hasattr(obj.__class__, 'model_validate') and callable(obj.__class__.model_validate):
            return True
            
        # Check for dict method with specific signature (v1)
        if hasattr(obj, 'dict') and callable(obj.dict):
            # Try to inspect the signature to confirm it's likely a Pydantic model
            import inspect
            sig = inspect.signature(obj.dict)
            if 'exclude_unset' in sig.parameters or 'exclude_defaults' in sig.parameters:
                return True
    except Exception as e:
        logger.debug(f"Error checking if object is a Pydantic model: {e}")
    
    return False


def serialize_pydantic_model(model: Any) -> Dict[str, Any]:
    """Serialize a Pydantic model to a dictionary.
    
    Args:
        model: Pydantic model to serialize
        
    Returns:
        Dictionary representation of the model
    """
    try:
        # Try Pydantic v2 method first
        if hasattr(model, 'model_dump') and callable(model.model_dump):
            try:
                return model.model_dump()
            except Exception as e:
                logger.warning(f"Error using model_dump: {e}")
        
        # Fall back to Pydantic v1 method
        if hasattr(model, 'dict') and callable(model.dict):
            try:
                return model.dict()
            except Exception as e:
                logger.warning(f"Error using dict method: {e}")
        
        # Try __dict__ approach
        if hasattr(model, '__dict__'):
            # Filter out private attributes
            return {k: v for k, v in model.__dict__.items() 
                   if not k.startswith('_') and not callable(v)}
                   
        # Last resort: try to convert to dict using vars()
        try:
            return vars(model)
        except Exception:
            pass
            
        # If all else fails, try to serialize as string
        return {"__str__": str(model)}
    except Exception as e:
        logger.warning(f"Error serializing Pydantic model: {e}")
        # Return a minimal dict with error info
        return {"__error__": f"Failed to serialize {type(model).__name__}: {str(e)}"}


def is_action_result_model(obj: Any) -> bool:
    """Check if an object is an ActionResultModel.
    
    Args:
        obj: Object to check
        
    Returns:
        True if the object is an ActionResultModel, False otherwise
    """
    try:
        # Check if it's a class (not an instance)
        if isinstance(obj, type):
            return False
            
        # Check for ActionResultModel specific attributes
        required_attrs = ['success', 'message', 'prompt', 'error', 'context']
        has_all_attrs = all(hasattr(obj, attr) for attr in required_attrs)
        
        # Check for class name
        class_name = obj.__class__.__name__
        
        return has_all_attrs and class_name == 'ActionResultModel'
    except Exception as e:
        logger.debug(f"Error checking if object is an ActionResultModel: {e}")
    
    return False


def serialize_action_result_model(model: Any) -> Dict[str, Any]:
    """Serialize an ActionResultModel to a dictionary.
    
    Args:
        model: ActionResultModel to serialize
        
    Returns:
        Dictionary representation of the model
    """
    try:
        # Create a simple dictionary with the model's attributes
        result = {
            'success': model.success,
            'message': model.message,
            'prompt': model.prompt,
            'error': model.error,
            'context': convert_complex_object(model.context)
        }
        return result
    except Exception as e:
        logger.warning(f"Error serializing ActionResultModel: {e}")
        # Return a minimal dict with error info
        return {
            "success": False,
            "message": "Error serializing action result",
            "error": str(e),
            "context": {}
        }


def convert_complex_object(obj: Any) -> Any:
    """Convert complex objects to simple Python types for RPyC transmission.
    
    Args:
        obj: Object to convert
        
    Returns:
        Converted object suitable for RPyC transmission
    """
    # Handle None
    if obj is None:
        return None
        
    # Handle Pydantic models
    if is_pydantic_model(obj):
        try:
            return serialize_pydantic_model(obj)
        except Exception as e:
            logger.warning(f"Error serializing Pydantic model: {e}")
            # Try to get a basic representation
            return {"__type__": type(obj).__name__, "__str__": str(obj)}
        
    # Handle ActionResultModel
    if is_action_result_model(obj):
        try:
            return serialize_action_result_model(obj)
        except Exception as e:
            logger.warning(f"Error serializing ActionResultModel: {e}")
            # Try to get a basic representation
            return {"__type__": type(obj).__name__, "__str__": str(obj)}
        
    # Handle lists and tuples
    if isinstance(obj, (list, tuple)):
        return [convert_complex_object(item) for item in obj]
        
    # Handle dictionaries
    if isinstance(obj, dict):
        # Check for special serialization cases
        if "__pydantic_self__" in obj:
            # This appears to be a Pydantic internal dictionary
            # Filter out internal keys
            return {k: convert_complex_object(v) for k, v in obj.items() 
                   if not k.startswith("__pydantic") and not k.startswith("_")}
        return {k: convert_complex_object(v) for k, v in obj.items()}
        
    # Handle basic types that are JSON serializable
    if isinstance(obj, (str, int, float, bool)):
        return obj
        
    # Handle special types that need custom serialization
    try:
        # Try to see if it's JSON serializable
        import json
        json.dumps(obj)
        return obj
    except (TypeError, OverflowError):
        pass
        
    # Try to convert to dictionary if it has a __dict__ attribute
    if hasattr(obj, "__dict__") and not callable(obj):
        try:
            return {"__type__": type(obj).__name__, 
                    "__data__": convert_complex_object(obj.__dict__)}
        except Exception:
            pass
    
    # Try to convert to string as a last resort
    try:
        return str(obj)
    except Exception:
        return f"<Unserializable object of type {type(obj).__name__}>"


def deliver_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """Convert NetRefs and complex objects to actual values in a parameters dictionary.

    Args:
        params: Dictionary of parameters to process

    Returns:
        Processed parameters dictionary with NetRefs and complex objects converted to values

    """
    # Convert any NetRefs to actual values and handle complex objects
    delivered_params = {}
    for key, value in params.items():
        try:
            # First, get the actual value (in case it's a NetRef)
            actual_value = value
            
            # Then convert complex objects to simple types
            delivered_params[key] = convert_complex_object(actual_value)
        except Exception as e:
            logger.warning(f"Error delivering parameter {key}: {e}")
            # Fall back to original value if conversion fails
            delivered_params[key] = value

    return delivered_params


def deliver_result(result: Any) -> Any:
    """Convert complex result objects to simple Python types for RPyC transmission.
    
    Args:
        result: Result object to convert
        
    Returns:
        Converted result suitable for RPyC transmission
    """
    return convert_complex_object(result)


def execute_remote_command(conn: rpyc.Connection, command: str, *args, **kwargs) -> Any:
    """Execute a command on the remote server via RPyC connection.
    
    Args:
        conn: RPyC connection to the remote server
        command: Command to execute on the remote server
        *args: Positional arguments to pass to the command
        **kwargs: Keyword arguments to pass to the command
        
    Returns:
        Result of the command execution
        
    Raises:
        Exception: If the command execution fails
    """
    try:
        # Get the remote module
        remote_module = conn.root
        
        # Get the command function from the remote module
        if not hasattr(remote_module, command):
            raise AttributeError(f"Remote server has no command '{command}'")
            
        remote_func = getattr(remote_module, command)
        
        # Convert complex objects in args and kwargs
        processed_args = [convert_complex_object(arg) for arg in args]
        processed_kwargs = deliver_parameters(kwargs)
        
        # Execute the command and get the result
        result = remote_func(*processed_args, **processed_kwargs)
        
        # Convert the result to a simple Python type for transmission
        return deliver_result(result)
    except Exception as e:
        logger.error(f"Error executing remote command '{command}': {e}")
        raise
