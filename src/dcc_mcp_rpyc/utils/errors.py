"""Error handling utilities for DCC-MCP-RPYC.

This module provides error models and error handling utilities for the DCC-MCP-RPYC package.
"""

# Import built-in modules
import logging
import traceback
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel

# Configure logging
logger = logging.getLogger(__name__)


class DCCMCPError(Exception):
    """Base exception class for DCC-MCP-RPYC errors.

    This class provides a common base for all DCC-MCP-RPYC specific exceptions.
    It includes support for error codes, detailed error messages, and context information.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[Optional[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Optional[Exception]] = None,
    ):
        """Initialize the DCCMCPError.

        Args:
        ----
            message: Human-readable error message
            error_code: Optional error code for categorizing errors
            details: Optional dictionary with additional error details
            cause: Optional original exception that caused this error

        """
        self.message = message
        self.error_code = error_code or "RPYC_ERROR"
        self.details = details or {}
        self.cause = cause

        # Format the error message
        full_message = f"{self.error_code}: {message}"
        if cause:
            full_message += f" (caused by: {type(cause).__name__}: {cause!s})"

        super().__init__(full_message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary.

        Returns
        -------
            Dictionary representation of the error

        """
        result = {
            "error_code": self.error_code,
            "message": self.message,
        }

        if self.details:
            result["details"] = self.details

        if self.cause:
            result["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause),
            }

        if self.cause:
            result["traceback"] = traceback.format_exc()

        return result

    def to_action_result(self, context: Optional[Dict[str, Any]] = None) -> ActionResultModel:
        """Convert the error to an ActionResultModel.

        Args:
        ----
            context: Optional context information to include in the error model

        Returns:
        -------
            ActionResultModel representing the error

        """
        error_dict = self.to_dict()
        error_context = dict(error_dict)

        # Remove redundant information from the context
        error_context.pop("message", None)

        # Add additional context if provided
        if context:
            error_context.update(context)

        return ActionResultModel(
            success=False,
            message=self.message,
            error=str(self),
            context=error_context,
        )


class ConnectionError(DCCMCPError):
    """Error raised when a connection to a service fails."""

    def __init__(
        self,
        message: str,
        host: Optional[Optional[str]] = None,
        port: Optional[Optional[int]] = None,
        service_name: Optional[Optional[str]] = None,
        cause: Optional[Optional[Exception]] = None,
    ):
        """Initialize the ConnectionError.

        Args:
        ----
            message: Human-readable error message
            host: Optional host name or IP address
            port: Optional port number
            service_name: Optional service name
            cause: Optional original exception that caused this error

        """
        details = {}
        if host:
            details["host"] = host
        if port:
            details["port"] = port
        if service_name:
            details["service_name"] = service_name

        super().__init__(
            message=message,
            error_code="RPYC_CONNECTION_ERROR",
            details=details,
            cause=cause,
        )


class ServiceNotFoundError(ConnectionError):
    """Error raised when a requested service is not found."""

    def __init__(
        self,
        service_name: str,
        message: Optional[Optional[str]] = None,
        cause: Optional[Optional[Exception]] = None,
    ):
        """Initialize the ServiceNotFoundError.

        Args:
        ----
            service_name: Name of the service that was not found
            message: Optional human-readable error message
            cause: Optional original exception that caused this error

        """
        if message is None:
            message = f"Service '{service_name}' not found"

        super().__init__(
            message=message,
            service_name=service_name,
            error_code="RPYC_SERVICE_NOT_FOUND",
            cause=cause,
        )


class ExecutionError(DCCMCPError):
    """Error raised when execution of code or a function fails."""

    def __init__(
        self,
        message: str,
        service_name: Optional[Optional[str]] = None,
        function_name: Optional[Optional[str]] = None,
        args: Optional[Optional[List[Any]]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        cause: Optional[Optional[Exception]] = None,
    ):
        """Initialize the ExecutionError.

        Args:
        ----
            message: Human-readable error message
            service_name: Optional name of the service where execution failed
            function_name: Optional name of the function that failed
            args: Optional positional arguments that were passed to the function
            kwargs: Optional keyword arguments that were passed to the function
            cause: Optional original exception that caused this error

        """
        details = {}
        if service_name:
            details["service_name"] = service_name
        if function_name:
            details["function_name"] = function_name
        if args:
            details["args"] = str(args)
        if kwargs:
            details["kwargs"] = str(kwargs)

        super().__init__(
            message=message,
            error_code="RPYC_REMOTE_EXECUTION_ERROR",
            details=details,
            cause=cause,
        )


class ActionError(DCCMCPError):
    """Error raised when an action execution fails."""

    def __init__(
        self,
        message: str,
        action_name: str,
        args: Optional[Dict[str, Any]] = None,
        cause: Optional[Optional[Exception]] = None,
    ):
        """Initialize the ActionError.

        Args:
        ----
            message: Human-readable error message
            action_name: Name of the action that failed
            args: Optional arguments that were passed to the action
            cause: Optional original exception that caused this error

        """
        details = {"action_name": action_name}
        if args:
            details["args"] = args

        super().__init__(
            message=message,
            error_code="RPYC_ACTION_ERROR",
            details=details,
            cause=cause,
        )


def handle_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> ActionResultModel:
    """Handle an exception and convert it to an ActionResultModel.

    This function takes an exception and converts it to an ActionResultModel,
    which can be returned to the client. If the exception is a DCCMCPError,
    its to_action_result method is used. Otherwise, a generic error model is created.

    Args:
    ----
        error: The exception to handle
        context: Optional context information to include in the error model

    Returns:
    -------
        ActionResultModel representing the error

    """
    # Log the error
    logger.error(f"Error: {error}")
    logger.debug(f"Traceback: {traceback.format_exc()}")

    # If it's already a DCCMCPError, use its to_action_result method
    if isinstance(error, DCCMCPError):
        return error.to_action_result(context)

    # Otherwise, create a generic error model
    error_context = context or {}
    error_context["error_type"] = type(error).__name__
    error_context["traceback"] = traceback.format_exc()

    return ActionResultModel(
        success=False,
        message=f"Error: {error!s}",
        error=str(error),
        context=error_context,
    )
