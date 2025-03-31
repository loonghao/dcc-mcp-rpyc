"""Asynchronous DCC client classes for DCC-MCP-RPYC.

This module provides asynchronous client classes for connecting to specific DCC applications.
These clients extend the AsyncBaseApplicationClient with DCC-specific functionality.
"""

# Import built-in modules
import asyncio
import logging
from typing import Any
from typing import Dict
from typing import Optional

# Import local modules
from dcc_mcp_rpyc.client.async_base import AsyncBaseApplicationClient

# Configure logging
logger = logging.getLogger(__name__)


class AsyncBaseDCCClient(AsyncBaseApplicationClient):
    """Base class for asynchronous DCC application clients.

    This class extends AsyncBaseApplicationClient with DCC-specific functionality.
    It provides methods for interacting with DCC applications asynchronously.

    Attributes
    ----------
        dcc_name: Name of the DCC application

    """

    def __init__(
        self,
        host: str,
        port: int,
        dcc_name: str,
        service_name: Optional[str] = None,
        config: Optional[dict] = None,
        connection_attempts: int = 3,
        connection_timeout: float = 5.0,
        connection_retry_delay: float = 1.0,
    ):
        """Initialize the DCC client.

        Args:
        ----
            host: Hostname or IP address of the RPyC server
            port: Port number of the RPyC server
            dcc_name: Name of the DCC application
            service_name: Name of the RPyC service (optional)
            config: RPyC connection configuration (optional)
            connection_attempts: Number of connection attempts (default: 3)
            connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
            connection_retry_delay: Delay between connection attempts in seconds (default: 1.0)

        """
        super().__init__(
            host=host,
            port=port,
            service_name=service_name,
            config=config,
            connection_attempts=connection_attempts,
            connection_timeout=connection_timeout,
            connection_retry_delay=connection_retry_delay,
        )
        self.dcc_name = dcc_name

    async def get_dcc_info(self) -> Dict[str, Any]:
        """Get information about the DCC application asynchronously.

        Returns
        -------
            Dictionary with DCC information

        Raises
        ------
            ConnectionError: If the client is not connected

        """
        await self.ensure_connected()

        # Use asyncio to run the blocking operation in a thread pool
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.connection.root.get_dcc_info(),
        )

    async def get_scene_info(self, include_selection: bool = True) -> Dict[str, Any]:
        """Get information about the current scene asynchronously.

        Args:
        ----
            include_selection: Whether to include selection information (default: True)

        Returns:
        -------
            Dictionary with scene information

        Raises:
        ------
            ConnectionError: If the client is not connected
            ActionError: If the action call fails

        """
        return await self.call_action("get_scene_info", include_selection=include_selection)

    async def execute_dcc_command(self, command: str) -> Any:
        """Execute a DCC-specific command asynchronously.

        Args:
        ----
            command: DCC-specific command to execute

        Returns:
        -------
            Result of the command execution

        Raises:
        ------
            ConnectionError: If the client is not connected
            ExecutionError: If the command execution fails

        """
        await self.ensure_connected()

        # Use asyncio to run the blocking operation in a thread pool
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.connection.root.exposed_execute_dcc_command(command),
        )
