"""Asynchronous client base classes for DCC-MCP-RPYC.

This module provides asynchronous client classes for connecting to DCC RPyC services.
These clients use Python's asyncio to provide non-blocking operations.
"""

# Import built-in modules
import asyncio
import logging
from typing import Any
from typing import Dict
from typing import Optional

# Import third-party modules
import rpyc
from rpyc.core.protocol import Connection

# Import local modules
from dcc_mcp_rpyc.utils.di import register_singleton
from dcc_mcp_rpyc.utils.errors import ConnectionError

# Configure logging
logger = logging.getLogger(__name__)


class AsyncBaseApplicationClient:
    """Base class for asynchronous application clients.

    This class provides common functionality for connecting to DCC RPyC servers
    and executing remote calls asynchronously.

    Attributes
    ----------
        host: Hostname or IP address of the RPyC server
        port: Port number of the RPyC server
        service_name: Name of the RPyC service
        config: RPyC connection configuration
        connection: RPyC connection object
        connection_attempts: Number of connection attempts
        connection_timeout: Timeout for connection attempts in seconds
        connection_retry_delay: Delay between connection attempts in seconds

    """

    def __init__(
        self,
        host: str,
        port: int,
        service_name: Optional[str] = None,
        config: Optional[dict] = None,
        connection_attempts: int = 3,
        connection_timeout: float = 5.0,
        connection_retry_delay: float = 1.0,
    ):
        """Initialize the client.

        Args:
        ----
            host: Hostname or IP address of the RPyC server
            port: Port number of the RPyC server
            service_name: Name of the RPyC service (optional)
            config: RPyC connection configuration (optional)
            connection_attempts: Number of connection attempts (default: 3)
            connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
            connection_retry_delay: Delay between connection attempts in seconds (default: 1.0)

        """
        self.host = host
        self.port = port
        self.service_name = service_name
        self.config = config or {}
        self.connection: Optional[Optional[Connection]] = None
        self.connection_attempts = connection_attempts
        self.connection_timeout = connection_timeout
        self.connection_retry_delay = connection_retry_delay

        # Set default configuration
        if "sync_request_timeout" not in self.config:
            self.config["sync_request_timeout"] = 30

    def __del__(self):
        """Clean up resources when the client is garbage collected."""
        self.close()

    def is_connected(self) -> bool:
        """Check if the client is connected to the server.

        Returns
        -------
            True if connected, False otherwise

        """
        return self.connection is not None and not self.connection.closed

    async def connect(self) -> bool:
        """Connect to the RPyC server asynchronously.

        Returns
        -------
            True if connected successfully, False otherwise

        Raises
        ------
            ConnectionError: If connection fails after all attempts

        """
        if self.is_connected():
            return True

        # Try to connect multiple times
        for attempt in range(1, self.connection_attempts + 1):
            try:
                logger.debug(f"Connecting to {self.host}:{self.port} (attempt {attempt}/{self.connection_attempts})")

                # Use asyncio to run the blocking connect operation in a thread pool
                self.connection = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: rpyc.connect(
                        self.host,
                        self.port,
                        service=self.service_name,
                        config=self.config,
                        keepalive=True,
                    ),
                )

                logger.info(f"Connected to {self.host}:{self.port}")
                return True

            except Exception as e:
                logger.warning(f"Connection attempt {attempt} failed: {e}")

                # If this is the last attempt, raise an exception
                if attempt >= self.connection_attempts:
                    raise ConnectionError(
                        f"Failed to connect to {self.host}:{self.port} after {self.connection_attempts} attempts",
                        host=self.host,
                        port=self.port,
                        cause=e,
                    )

                # Otherwise, wait and try again
                await asyncio.sleep(self.connection_retry_delay)

        return False

    def close(self) -> None:
        """Close the connection to the server."""
        if self.connection is not None and not self.connection.closed:
            try:
                self.connection.close()
                logger.debug(f"Closed connection to {self.host}:{self.port}")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self.connection = None

    async def ensure_connected(self) -> None:
        """Ensure that the client is connected to the server.

        If the client is not connected, this method will attempt to reconnect.

        Raises
        ------
            ConnectionError: If the client cannot connect to the server

        """
        if not self.is_connected():
            await self.connect()

    async def execute_python(self, code: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Execute Python code on the server asynchronously.

        Args:
        ----
            code: Python code to execute
            context: Optional context dictionary to use during execution

        Returns:
        -------
            Result of the execution

        Raises:
        ------
            ConnectionError: If the client is not connected
            ExecutionError: If the code execution fails

        """
        await self.ensure_connected()

        # Use asyncio to run the blocking operation in a thread pool
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.connection.root.exposed_execute_python(code, context or {}),
        )

    async def get_application_info(self) -> Dict[str, Any]:
        """Get information about the application asynchronously.

        Returns
        -------
            Dictionary with application information

        Raises
        ------
            ConnectionError: If the client is not connected

        """
        await self.ensure_connected()

        # Use asyncio to run the blocking operation in a thread pool
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.connection.root.get_application_info(),
        )

    async def get_environment_info(self) -> Dict[str, Any]:
        """Get information about the Python environment asynchronously.

        Returns
        -------
            Dictionary with environment information

        Raises
        ------
            ConnectionError: If the client is not connected

        """
        await self.ensure_connected()

        # Use asyncio to run the blocking operation in a thread pool
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.connection.root.get_environment_info(),
        )

    async def call_function(self, module_name: str, function_name: str, *args, **kwargs) -> Any:
        """Call a function on the server asynchronously.

        Args:
        ----
            module_name: Name of the module containing the function
            function_name: Name of the function to call
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
        -------
            Result of the function call

        Raises:
        ------
            ConnectionError: If the client is not connected
            ExecutionError: If the function call fails

        """
        await self.ensure_connected()

        # Use asyncio to run the blocking operation in a thread pool
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.connection.root.exposed_call_function(module_name, function_name, *args, **kwargs),
        )

    async def list_actions(self) -> Dict[str, Dict[str, Any]]:
        """List all available actions on the server asynchronously.

        Returns
        -------
            Dictionary mapping action names to action metadata

        Raises
        ------
            ConnectionError: If the client is not connected

        """
        await self.ensure_connected()

        # Use asyncio to run the blocking operation in a thread pool
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.connection.root.exposed_list_actions(),
        )

    async def call_action(self, action_name: str, **kwargs) -> Any:
        """Call an action on the server asynchronously.

        Args:
        ----
            action_name: Name of the action to call
            **kwargs: Arguments to pass to the action

        Returns:
        -------
            Result of the action call

        Raises:
        ------
            ConnectionError: If the client is not connected
            ActionError: If the action call fails

        """
        await self.ensure_connected()

        # Use asyncio to run the blocking operation in a thread pool
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.connection.root.exposed_call_action(action_name, **kwargs),
        )


# Register the client class with the dependency injection container
register_singleton(AsyncBaseApplicationClient, lambda: None)  # Will be initialized on first use


async def get_async_client(
    host: str,
    port: int,
    service_name: Optional[str] = None,
    config: Optional[dict] = None,
    connection_attempts: int = 3,
    connection_timeout: float = 5.0,
    connection_retry_delay: float = 1.0,
) -> AsyncBaseApplicationClient:
    """Get an asynchronous client for the specified server.

    This function creates a new client instance for the specified server.

    Args:
    ----
        host: Hostname or IP address of the RPyC server
        port: Port number of the RPyC server
        service_name: Name of the RPyC service (optional)
        config: RPyC connection configuration (optional)
        connection_attempts: Number of connection attempts (default: 3)
        connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
        connection_retry_delay: Delay between connection attempts in seconds (default: 1.0)

    Returns:
    -------
        An asynchronous client instance

    """
    return AsyncBaseApplicationClient(
        host=host,
        port=port,
        service_name=service_name,
        config=config,
        connection_attempts=connection_attempts,
        connection_timeout=connection_timeout,
        connection_retry_delay=connection_retry_delay,
    )


async def close_all_async_connections() -> None:
    """Close all open asynchronous client connections.

    This function should be called when the application is shutting down
    to ensure that all connections are properly closed.
    """
    # This is a placeholder for future implementation
    # In a real implementation, we would keep track of all client instances
    # and close them here
