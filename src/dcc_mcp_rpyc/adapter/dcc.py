"""DCC adapter classes for DCC-MCP-RPYC.

This module provides DCC-specific adapter classes for connecting to DCC applications.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Dict
from typing import Optional

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel

# Import local modules
from dcc_mcp_rpyc.adapter.base import ApplicationAdapter
from dcc_mcp_rpyc.client import BaseDCCClient

# Configure logging
logger = logging.getLogger(__name__)


class DCCAdapter(ApplicationAdapter):
    """Abstract base class for DCC adapters.

    This class provides a common interface for adapting DCC-specific functionality
    to the MCP protocol. It handles connection to the DCC application, action
    discovery and management, and function execution.

    Attributes
    ----------
        dcc_name: Name of the DCC application
        client: Client instance for communicating with the DCC application
        action_manager: Manager for actions in the DCC application
        _action_paths: List of paths to search for actions

    """

    def __init__(self, dcc_name: str) -> None:
        """Initialize the DCC adapter.

        Args:
        ----
            dcc_name: Name of the DCC application

        """
        super().__init__(dcc_name)
        self.dcc_name = dcc_name
        self.client: Optional[Optional[BaseDCCClient]] = None

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        self.ensure_connected()

        try:
            # Get scene info from the DCC application
            result = self.client.root.get_scene_info()
            return ActionResultModel(
                success=True, message="Successfully retrieved scene information", context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error getting scene info: {e}")
            return ActionResultModel(
                success=False, message="Failed to retrieve scene information", error=str(e)
            ).model_dump()

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current mcp session.

        Returns
        -------
            Dict with session information

        """
        self.ensure_connected()

        try:
            # Get session info from the DCC application
            result = self.client.root.get_session_info()
            return ActionResultModel(
                success=True, message="Successfully retrieved session information", context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return ActionResultModel(
                success=False, message="Failed to retrieve session information", error=str(e)
            ).model_dump()

    def create_primitive(self, primitive_type: str, **kwargs) -> Dict[str, Any]:
        """Create a primitive object in the DCC application.

        Args:
        ----
            primitive_type: Type of primitive to create
            **kwargs: Additional arguments for the primitive creation

        Returns:
        -------
            Dict with primitive creation result

        """
        self.ensure_connected()

        try:
            # Create primitive in the DCC application
            result = self.client.root.exposed_create_primitive(primitive_type, **kwargs)
            return ActionResultModel(
                success=True, message=f"Successfully created primitive of type {primitive_type}", context=result
            ).model_dump()
        except Exception as e:
            logger.error(f"Error creating primitive: {e}")
            return ActionResultModel(
                success=False, message=f"Failed to create primitive of type {primitive_type}", error=str(e)
            ).model_dump()
