"""Common decorator utilities.

This module provides common decorator factory functions for adding metadata,
error handling, and result conversion.
"""

# Import built-in modules
import functools
import logging
import traceback
from typing import Any
from typing import Callable
from typing import Dict
from typing import TypeVar
from typing import cast

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel

# Configure logging
logger = logging.getLogger(__name__)

# Function type variable
F = TypeVar("F", bound=Callable[..., Any])


def with_error_handling(func: F) -> F:
    """Add error handling.

    This decorator wraps a function to add unified error handling logic. If an
    exception occurs during function execution, it will log the error and return
    an ActionResultModel containing error information.

    Args:
    ----
        func: The function to wrap

    Returns:
    -------
        The wrapped function

    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Call the original function
            return func(*args, **kwargs)
        except Exception as e:
            # Get detailed error information
            error_message = str(e)
            error_traceback = traceback.format_exc()

            # Log the error
            logger.error(f"Error in {func.__name__}: {error_message}")
            logger.debug(f"Traceback: {error_traceback}")

            # If ActionResultModel is used, return error result
            try:
                # Try to get function name as context
                context = {
                    "function": func.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs),
                    "traceback": error_traceback,
                }

                return ActionResultModel(
                    success=False,
                    message=f"Error executing {func.__name__}: {error_message}",
                    error=error_message,
                    context=context,
                )
            except Exception:
                # If ActionResultModel cannot be created, re-raise the original exception
                raise

    return cast(F, wrapper)


def with_result_conversion(func: F) -> F:
    """Convert function result to ActionResultModel.

    This decorator wraps a function to convert its result to an
    ActionResultModel. If the result is already an ActionResultModel or a
    dictionary containing a 'success' key, no conversion is performed.

    Args:
    ----
        func: The function to wrap

    Returns:
    -------
        The wrapped function

    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Call the original function
        result = func(*args, **kwargs)

        # If the result is already an ActionResultModel, return it
        if isinstance(result, ActionResultModel):
            return result

        # If the result is a dictionary containing a 'success' key, it may be a compatible format
        if isinstance(result, dict) and "success" in result:
            # Try to convert it to an ActionResultModel
            try:
                return ActionResultModel(**result)
            except Exception:
                # If conversion fails, continue with standard conversion
                pass

        # Standard conversion: wrap the result in a successful ActionResultModel
        try:
            return ActionResultModel(
                success=True, message=f"Successfully executed {func.__name__}", context={"result": result}
            )
        except Exception as e:
            logger.error(f"Error converting result to ActionResultModel: {e}")
            # If conversion fails, return the original result
            return result

    return cast(F, wrapper)


def with_info(info_getter: Callable[[Any], Dict[str, Any]], info_name: str) -> Callable[[F], F]:
    """Add information to function return value.

    This decorator factory creates a decorator to add specific information to
    the function return value. The wrapped function result will be returned as
    a dictionary containing 'result' and the specified info_name key.

    Args:
    ----
        info_getter: A function that returns the information to be added
        info_name: The key name to add to the result dictionary

    Returns:
    -------
        A decorator function

    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                # Call the original function
                result = func(self, *args, **kwargs)

                # Get the information
                info = info_getter(self)

                # Check if the result is a model and convert to dictionary if needed
                if hasattr(result, "model_dump") and callable(getattr(result, "model_dump")):
                    result_dict = result.model_dump()
                elif hasattr(result, "dict") and callable(getattr(result, "dict")):
                    result_dict = result.dict()
                elif isinstance(result, dict):
                    result_dict = result
                else:
                    # Otherwise, wrap the result
                    result_dict = {"result": result}

                # Add the information to the result dictionary
                result_dict[info_name] = info
                return result_dict
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                logger.exception("Detailed exception information:")
                raise

        return cast(F, wrapper)

    return decorator


def with_action_result(func: F) -> F:
    """Convert function result to ActionResultModel and add error handling.

    This decorator combines error handling and result conversion, ensuring the
    function always returns an ActionResultModel.

    Args:
    ----
        func: The function to wrap

    Returns:
    -------
        The wrapped function

    """
    # Combine decorators: first handle errors, then convert result
    return with_result_conversion(with_error_handling(func))
