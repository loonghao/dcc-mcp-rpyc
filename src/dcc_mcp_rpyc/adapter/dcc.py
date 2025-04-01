"""DCC adapter classes for DCC-MCP-RPYC.

This module provides DCC-specific adapter classes for connecting to DCC applications.
"""

# Import built-in modules
import logging
from typing import Any, Dict, Optional, List

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel

# Import local modules
from dcc_mcp_rpyc.adapter.base import ApplicationAdapter
from dcc_mcp_rpyc.client import BaseDCCClient
from dcc_mcp_rpyc.client.pool import get_client

# Configure logging
logger = logging.getLogger(__name__)


class DCCAdapter(ApplicationAdapter):
    """Base class for DCC application adapters.

    This class provides a common interface for adapting DCC-specific functionality
    to the MCP protocol. It handles connection to the DCC application, action
    discovery and management, and function execution.
    
    DCCAdapter is specifically designed for DCC applications that require remote
    connections through RPyC. It provides methods for scene management, primitive
    creation, and other DCC-specific operations.
    
    Attributes:
        dcc_name: Name of the DCC application
        client: Client instance for communicating with the DCC application
        action_adapter: Adapter for managing actions
    """

    def __init__(self, dcc_name: str, host: Optional[str] = None, port: Optional[int] = None,
                 connection_timeout: float = 5.0) -> None:
        """Initialize the DCC adapter.

        Args:
            dcc_name: Name of the DCC application
            host: Optional host address for the DCC server
            port: Optional port for the DCC server
            connection_timeout: Connection timeout in seconds
        """
        self.dcc_name = dcc_name.lower()
        self.host = host
        self.port = port
        self.connection_timeout = connection_timeout
        self.client: Optional[BaseDCCClient] = None
        
        super().__init__(dcc_name)

    def _initialize_client(self) -> None:
        """Initialize the client for communicating with the DCC application.
        
        This method initializes a BaseDCCClient instance for the specified DCC application.
        It uses the connection pool to get or create a client.
        """
        try:
            self.client = get_client(
                dcc_name=self.dcc_name,
                host=self.host,
                port=self.port,
                auto_connect=True,
                connection_timeout=self.connection_timeout
            )
            logger.info(f"Connected to {self.dcc_name} client: {self.client}")
        except Exception as e:
            logger.error(f"Failed to initialize {self.dcc_name} client: {e}")
            self.client = None

    def get_application_info(self) -> Dict[str, Any]:
        """Get information about the DCC application.

        Returns:
            Dict with application information
        """
        if not self.ensure_connected():
            return ActionResultModel(
                success=False,
                message=f"Not connected to {self.dcc_name}",
                error="Connection error"
            ).model_dump()

        try:
            result = self.client.get_dcc_info()
            return ActionResultModel(
                success=True,
                message=f"Successfully retrieved {self.dcc_name} information",
                context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error getting {self.dcc_name} info: {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to retrieve {self.dcc_name} information",
                error=str(e)
            ).model_dump()

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns:
            Dict with scene information
        """
        if not self.ensure_connected():
            return ActionResultModel(
                success=False,
                message=f"Not connected to {self.dcc_name}",
                error="Connection error"
            ).model_dump()

        try:
            result = self.client.get_scene_info()
            return ActionResultModel(
                success=True,
                message="Successfully retrieved scene information",
                context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error getting scene info: {e}")
            return ActionResultModel(
                success=False,
                message="Failed to retrieve scene information",
                error=str(e)
            ).model_dump()

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session.

        Returns:
            Dict with session information
        """
        if not self.ensure_connected():
            return ActionResultModel(
                success=False,
                message=f"Not connected to {self.dcc_name}",
                error="Connection error"
            ).model_dump()

        try:
            result = self.client.get_session_info()
            return ActionResultModel(
                success=True,
                message="Successfully retrieved session information",
                context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return ActionResultModel(
                success=False,
                message="Failed to retrieve session information",
                error=str(e)
            ).model_dump()

    def create_primitive(self, primitive_type: str, **kwargs) -> Dict[str, Any]:
        """Create a primitive object in the DCC application.

        Args:
            primitive_type: Type of primitive to create
            **kwargs: Additional arguments for the primitive creation

        Returns:
            Dict with primitive creation result
        """
        if not self.ensure_connected():
            return ActionResultModel(
                success=False,
                message=f"Not connected to {self.dcc_name}",
                error="Connection error"
            ).model_dump()

        try:
            result = self.client.create_primitive(primitive_type, **kwargs)
            
            # If result is already an ActionResultModel dict, return it
            if isinstance(result, dict) and "success" in result:
                return result
                
            return ActionResultModel(
                success=True,
                message=f"Successfully created {primitive_type}",
                context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error creating primitive {primitive_type}: {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to create {primitive_type}",
                error=str(e),
                context={"primitive_type": primitive_type, "kwargs": kwargs}
            ).model_dump()

    def execute_command(self, command: str, *args, **kwargs) -> Dict[str, Any]:
        """Execute a command in the DCC application.

        Args:
            command: Command to execute
            *args: Positional arguments for the command
            **kwargs: Keyword arguments for the command

        Returns:
            Dict with command execution result
        """
        if not self.ensure_connected():
            return ActionResultModel(
                success=False,
                message=f"Not connected to {self.dcc_name}",
                error="Connection error"
            ).model_dump()

        try:
            result = self.client.execute_command(command, *args, **kwargs)
            
            # If result is already an ActionResultModel dict, return it
            if isinstance(result, dict) and "success" in result:
                return result
                
            return ActionResultModel(
                success=True,
                message=f"Successfully executed command: {command}",
                context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error executing command {command}: {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to execute command: {command}",
                error=str(e),
                context={"command": command, "args": args, "kwargs": kwargs}
            ).model_dump()

    def execute_script(self, script: str, script_type: str = "python") -> Dict[str, Any]:
        """Execute a script in the DCC application.

        Args:
            script: Script to execute
            script_type: Type of script (default: "python")

        Returns:
            Dict with script execution result
        """
        if not self.ensure_connected():
            return ActionResultModel(
                success=False,
                message=f"Not connected to {self.dcc_name}",
                error="Connection error"
            ).model_dump()

        try:
            if script_type.lower() == "python":
                result = self.client.execute_python(script)
            else:
                # For other script types, use the generic execute_script method
                result = self.client.execute_script(script, script_type)
            
            # If result is already an ActionResultModel dict, return it
            if isinstance(result, dict) and "success" in result:
                return result
                
            return ActionResultModel(
                success=True,
                message=f"Successfully executed {script_type} script",
                context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error executing {script_type} script: {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to execute {script_type} script",
                error=str(e),
                context={"script_type": script_type, "script_length": len(script)}
            ).model_dump()
