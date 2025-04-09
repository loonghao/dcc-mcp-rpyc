"""RPyC Action Bridge for DCC-MCP-RPYC.

This module provides a bridge between RPyC services and the dcc-mcp-core Action system.
It supports the Pydantic-based Action system from dcc-mcp-core and handles the
serialization and deserialization of data between RPyC services.
"""

# Import built-in modules
import importlib
import inspect
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Type, Union

# Import third-party modules
from dcc_mcp_core.actions.base import Action
from dcc_mcp_core.actions.manager import ActionManager
from dcc_mcp_core.actions.manager import create_action_manager
from dcc_mcp_core.actions.manager import get_action_manager
from dcc_mcp_core.actions.function_adapter import create_function_adapter
from dcc_mcp_core.actions.function_adapter import create_function_adapters_for_manager
from dcc_mcp_core.models import ActionResultModel
from dcc_mcp_core.utils.result_factory import success_result, error_result

# Import local modules
from dcc_mcp_rpyc.utils.decorators import with_action_result
from dcc_mcp_rpyc.utils.decorators import with_error_handling
from dcc_mcp_rpyc.utils.errors import ActionError
from dcc_mcp_rpyc.utils.errors import handle_error

# Configure logging
logger = logging.getLogger(__name__)


class RPyCActionBridge:
    """Bridge between RPyC services and the dcc-mcp-core Action system.

    This class provides methods for discovering, registering, and calling actions
    through RPyC services. It acts as a bridge between the RPyC service layer and
    the dcc-mcp-core Action system, handling serialization and deserialization of
    data between the two systems.

    Attributes:
        name: The name of the DCC or application
        action_manager: The ActionManager instance used by this bridge
        search_paths: List of paths to search for actions
    """

    def __init__(self, dcc_name: str, manager_name: str = "default"):
        """Initialize the RPyC Action Bridge.

        Args:
            dcc_name: The name of the DCC or application
            manager_name: The name of the action manager (default: "default")
        """
        self.dcc_name = dcc_name
        self.manager_name = manager_name
        self.action_manager = self._get_or_create_action_manager()
        self.search_paths: List[str] = []
        logger.info(f"Initialized RPyCActionBridge for {dcc_name} using manager {manager_name}")

    def _get_or_create_action_manager(self) -> ActionManager:
        """Get or create an ActionManager instance.

        Returns:
            An ActionManager instance for the specified DCC
        """
        # Try to get existing ActionManager
        manager = get_action_manager(
            dcc_name=self.dcc_name,
            name=self.manager_name,
            auto_refresh=True
        )
        logger.debug(f"Using ActionManager: {manager.name} for DCC {manager.dcc_name}")
        return manager

    def set_action_search_paths(self, paths: List[str]) -> None:
        """Set the paths to search for actions.

        Args:
            paths: List of paths to search for actions
        """
        self.search_paths = paths
        logger.debug(f"Set action search paths for {self.dcc_name}: {paths}")

    def add_action_search_path(self, path: str) -> None:
        """Add a path to the list of paths to search for actions.

        Args:
            path: Path to add to the search paths
        """
        if path not in self.search_paths:
            self.search_paths.append(path)
            logger.debug(f"Added action search path for {self.dcc_name}: {path}")

    @with_error_handling
    def register_action_class(self, action_class: Type[Action], source_file: Optional[str] = None) -> None:
        """Register an Action class.

        Args:
            action_class: The Action class to register
            source_file: Optional source file path where the action was defined
        """
        if not issubclass(action_class, Action):
            logger.warning(f"Cannot register {action_class.__name__}, not a subclass of Action")
            return

        # Set DCC name (if not already set)
        if not action_class.dcc:
            action_class.dcc = self.dcc_name

        # Set source file path (if provided)
        if source_file:
            # Store source file path as a class attribute for identification
            setattr(action_class, "_source_file", source_file)
            logger.debug(f"Set source file for {action_class.__name__}: {source_file}")

        # Register Action class
        self.action_manager.registry.register(action_class)
        logger.debug(f"Registered action class: {action_class.__name__} from file {source_file or 'unknown'}")

    @with_error_handling
    def discover_actions(self, source: str, is_module: bool = False) -> List[str]:
        """Discover and register actions from a module or directory.

        Args:
            source: The module or directory to search for actions
            is_module: If True, source is a module, otherwise it is a directory

        Returns:
            List of discovered action names
        """
        try:
            # Create dependencies dictionary
            dependencies = {
                "dcc_name": self.dcc_name,
            }

            discovered_action_names = []

            if is_module:
                # Discover Action classes from module
                discovered_actions = self.action_manager.discover_actions_from_package(
                    source
                )

                # Register discovered Action classes
                for action_class in discovered_actions:
                    self.register_action_class(action_class)
                    discovered_action_names.append(action_class.__name__)

                logger.debug(f"Discovered {len(discovered_actions)} actions from module {source}")
            else:
                # Discover Action classes from directory
                if not os.path.isdir(source):
                    logger.error(f"Source path {source} is not a directory")
                    return discovered_action_names

                # 获取目录中的所有 Python 文件
                for filename in os.listdir(source):
                    if filename.endswith(".py") and not filename.startswith("__"):
                        file_path = os.path.join(source, filename)

                        # Use discover_actions_from_path method
                        file_actions = self.discover_actions_from_path(file_path)

                        # Collect Action names
                        for action_class in file_actions:
                            discovered_action_names.append(action_class.__name__)

                logger.debug(f"Discovered {len(discovered_action_names)} actions from directory {source}")

            return discovered_action_names
        except Exception as e:
            logger.error(f"Error discovering actions from {'module' if is_module else 'path'} {source}: {e}")
            raise ActionError(
                f"Error discovering actions from {'module' if is_module else 'path'}: {e}",
                action_name=source,
                cause=e
            )

    @with_error_handling
    def discover_actions_from_path(self, file_path: str) -> List[Type[Action]]:
        """Discover and register Action classes from a file path.

        Args:
            file_path: Path to the Python file to load

        Returns:
            List of discovered and registered Action classes
        """
        try:
            # Discover Action classes from file path
            discovered_actions = self.action_manager.discover_actions_from_path(file_path)

            # Register discovered Action classes
            for action_class in discovered_actions:
                self.register_action_class(action_class, source_file=file_path)

            logger.debug(f"Discovered {len(discovered_actions)} actions from {file_path}")
            return discovered_actions
        except Exception as e:
            logger.error(f"Error discovering actions from {file_path}: {e}")
            return []

    @with_error_handling
    def list_available_actions(self) -> Dict[str, Any]:
        """List all available actions.

        Returns:
            Dictionary of available actions with their metadata
        """
        # Get actions_info from ActionManager
        result = self.action_manager.get_actions_info()
        return result.model_dump()

    @with_action_result
    def call_action(self, action_name: str, **kwargs) -> ActionResultModel:
        """Call an action by name with the given parameters.

        Args:
            action_name: The name of the action to call
            **kwargs: Parameters to pass to the action

        Returns:
            An ActionResultModel with the result of the action
        """
        try:
            # Extract client information from context (if any)
            context = kwargs.pop("context", {}) or {}
            context["dcc_name"] = self.dcc_name

            # Call Action using ActionManager
            result = self.action_manager.call_action(action_name, context=context, **kwargs)

            # Ensure the result is an ActionResultModel
            if isinstance(result, ActionResultModel):
                return result
            else:
                # If the result is not an ActionResultModel, wrap it
                return success_result(
                    message=f"Successfully executed {action_name}",
                    prompt=None,
                    context={"result": result}
                )
        except Exception as e:
            # Handle exceptions
            logger.error(f"Error calling action {action_name}: {e}")
            return handle_error(e, {"action_name": action_name, "args": kwargs})

    def create_function_adapters(self) -> Dict[str, Callable]:
        """Create function adapters for all available actions.

        This method creates callable function adapters for all actions registered
        with this bridge's ActionManager. These functions can be used directly
        without having to call the call_action method.

        Returns:
            Dictionary mapping action names to function adapters
        """
        return create_function_adapters_for_manager(self.manager_name, self.dcc_name)


# Global RPyCActionBridge instance cache
_bridge_instances: Dict[str, RPyCActionBridge] = {}


def get_action_bridge(dcc_name: str, manager_name: str = "default") -> RPyCActionBridge:
    """Get or create a RPyCActionBridge instance.

    Args:
        dcc_name: The name of the DCC or application
        manager_name: The name of the action manager (default: "default")

    Returns:
        A RPyCActionBridge instance
    """
    # Create cache key
    cache_key = f"{dcc_name}:{manager_name}"

    # Check if instance exists in cache
    if cache_key in _bridge_instances:
        return _bridge_instances[cache_key]

    # Create new instance
    bridge = RPyCActionBridge(dcc_name, manager_name)
    _bridge_instances[cache_key] = bridge

    return bridge
