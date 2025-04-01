"""Action adapter for DCC-MCP-RPYC.

This module provides adapters for connecting RPyC services with the dcc-mcp-core Action system.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Type
from typing import Union

# Import third-party modules
from dcc_mcp_core.actions.base import Action
from dcc_mcp_core.actions.manager import ActionManager
from dcc_mcp_core.actions.manager import create_action_manager
from dcc_mcp_core.actions.manager import get_action_manager
from dcc_mcp_core.models import ActionResultModel

# Import local modules
from dcc_mcp_rpyc.utils.decorators import with_action_result
from dcc_mcp_rpyc.utils.decorators import with_error_handling
from dcc_mcp_rpyc.utils.errors import ActionError
from dcc_mcp_rpyc.utils.errors import handle_error

# Configure logging
logger = logging.getLogger(__name__)


class ActionAdapter:
    """Adapter for connecting RPyC services with the dcc-mcp-core Action system.

    This class provides methods for discovering, registering, and calling actions
    through RPyC services. It acts as a bridge between the RPyC service layer and
    the dcc-mcp-core Action system.

    Attributes
    ----------
        name: The name of the adapter, used to identify the ActionManager
        action_manager: The ActionManager instance used by this adapter
        search_paths: List of paths to search for actions

    """

    def __init__(self, name: str):
        """Initialize the action adapter.

        Args:
        ----
            name: The name of the adapter

        """
        self.name = name
        self.action_manager = self._get_or_create_action_manager(name)
        self.search_paths: List[str] = []
        logger.debug(f"Initialized ActionAdapter: {name}")

    def _get_or_create_action_manager(self, name: str) -> ActionManager:
        """Get or create an ActionManager instance.

        Args:
        ----
            name: The name of the ActionManager

        Returns:
        -------
            An ActionManager instance

        """
        # Try to get an existing ActionManager
        manager = get_action_manager(name)

        # If not found, create a new one
        if manager is None:
            manager = create_action_manager(name)

        return manager

    def set_action_search_paths(self, paths: List[str]) -> None:
        """Set the paths to search for actions.

        Args:
        ----
            paths: List of paths to search for actions

        """
        self.search_paths = paths
        logger.debug(f"Set action search paths for {self.name}: {paths}")

    def add_action_search_path(self, path: str) -> None:
        """Add a path to the list of paths to search for actions.

        Args:
        ----
            path: Path to add to the search paths

        """
        if path not in self.search_paths:
            self.search_paths.append(path)
            logger.debug(f"Added action search path for {self.name}: {path}")

    @with_error_handling
    def register_action(self, action: Union[Action, Type[Action]]) -> bool:
        """Register an action with the adapter.

        Args:
        ----
            action: An action instance or class to register

        Returns:
        -------
            True if the action was registered successfully

        """
        try:
            self.action_manager.registry.register(action)
            return True
        except Exception as e:
            logger.error(f"Error registering action: {e}")
            raise ActionError(f"Failed to register action: {e}") from e

    @with_error_handling
    def discover_actions(self, source: str, is_module: bool = False) -> List[str]:
        """Discover and register actions from a module or directory.

        Args:
        ----
            source: The module or directory to search for actions
            is_module: If True, source is a module, otherwise it is a directory

        Returns:
        -------
            True if the action was registered successfully

        """
        try:
            if is_module:
                return self.action_manager.discover_actions_from_module(source)
            else:
                return self.action_manager.discover_actions_from_path(source)
        except Exception as e:
            source_type = "module" if is_module else "path"
            logger.error(f"Error discovering actions from {source_type} {source}: {e}")
            raise ActionError(f"Error discovering actions from {source_type}: {e}", action_name=source, cause=e)

    @with_error_handling
    def discover_all_actions(self) -> List[str]:
        """Discover and register actions from all search paths.

        Returns
        -------
            A list of names of all discovered actions

        """
        discovered = []

        # Discover actions from all search paths
        for path in self.search_paths:
            try:
                discovered.extend(self.discover_actions(path))
            except Exception as e:
                logger.error(f"Error discovering actions from path {path}: {e}")
                # Continue with other paths even if one fails

        return discovered

    @with_error_handling
    def list_actions(self, names_only: bool = False) -> Union[Dict[str, Any], List[str]]:
        """List all registered actions and their metadata.

        Args:
        ----
            names_only: If True, only return action names list, otherwise return full metadata

        Returns:
        -------
            A dictionary mapping action names to metadata if names_only is False
            A list of action names if names_only is True

        """
        try:
            actions_list = self.action_manager.registry.list_actions()
            if names_only:
                return [action["name"] for action in actions_list]
            return {action["name"]: action for action in actions_list}
        except Exception as e:
            logger.error(f"Error listing actions: {e}")
            raise ActionError(f"Error listing actions: {e}", action_name="list_actions", cause=e)

    @with_action_result
    def call_action(self, action_name: str, **kwargs) -> ActionResultModel:
        """Call an action by name with the given parameters.

        Args:
        ----
            action_name: The name of the action to call
            **kwargs: Parameters to pass to the action

        Returns:
        -------
            An ActionResultModel with the result of the action

        """
        try:
            action = self.action_manager.registry.get_action(action_name)
            if action is None:
                return ActionResultModel(
                    success=False,
                    message=f"Action '{action_name}' not found",
                    error=f"Action '{action_name}' not found",
                    context={"available_actions": [a["name"] for a in self.action_manager.registry.list_actions()]},
                )

            result = self.action_manager.call_action(action_name, **kwargs)

            if isinstance(result, ActionResultModel):
                return result

            return ActionResultModel(
                success=True, message=f"Successfully executed {action_name}", context={"result": result}
            )
        except Exception as e:
            return handle_error(e, {"action_name": action_name, "args": kwargs})


def get_action_adapter(name: str) -> ActionAdapter:
    """Get or create an ActionAdapter instance.

    Args:
    ----
        name: The name of the ActionAdapter

    Returns:
    -------
        An ActionAdapter instance

    """
    return ActionAdapter(name)
