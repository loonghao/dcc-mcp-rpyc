"""Action adapter for DCC-MCP-RPYC.

This module provides adapters for connecting RPyC services with the dcc-mcp-core Action system.
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
    def register_action_class(self, action_class: Type[Action], source_file: Optional[str] = None) -> None:
        """Register an Action class.

        Args:
            action_class: The Action class to register
            source_file: Optional source file path where the action was defined

        """
        if not issubclass(action_class, Action):
            logger.warning(f"Cannot register {action_class.__name__}, not a subclass of Action")
            return

        # Set DCC name if not already set
        if not action_class.dcc:
            action_class.dcc = self.name
            
        # Set source file path if provided
        if source_file:
            # Store source file path as class attribute for identification
            setattr(action_class, "_source_file", source_file)
            logger.debug(f"Set source file for {action_class.__name__}: {source_file}")

        # Register the action
        self.action_manager.registry.register(action_class)
        logger.debug(f"Registered action class: {action_class.__name__} from file {source_file or 'unknown'}")

    @with_error_handling
    def discover_actions(self, source: str, is_module: bool = False) -> List[str]:
        """Discover and register actions from a module or directory.
        
        Args:
        ----
            source: The module or directory to search for actions
            is_module: If True, source is a module, otherwise it is a directory
        
        Returns:
        -------
            List of discovered action names
        
        """
        try:
            # 所有导入已移至文件顶部
            discovered_actions = []
            
            if is_module:
                # Discover actions from module
                try:
                    module = importlib.import_module(source)
                    for name, obj in inspect.getmembers(module):
                        # Check if the object is a subclass of Action
                        if inspect.isclass(obj) and issubclass(obj, Action) and obj != Action:
                            try:
                                # Register the action
                                self.register_action_class(obj)
                                discovered_actions.append(name)
                                logger.debug(f"Registered action class: {name} from module {source}")
                            except Exception as e:
                                logger.error(f"Error registering action {name} from module {source}: {e}")
                except Exception as e:
                    logger.error(f"Error importing module {source}: {e}")
            else:
                # Discover actions from directory
                if not os.path.isdir(source):
                    logger.error(f"Source path {source} is not a directory")
                    return discovered_actions
                
                # Add the directory to the Python path temporarily
                if source not in sys.path:
                    sys.path.insert(0, source)
                
                # Get all Python files in the directory
                for filename in os.listdir(source):
                    if filename.endswith(".py") and not filename.startswith("__"):
                        module_name = filename[:-3]  # Remove .py extension
                        try:
                            # Import the module
                            module_path = os.path.join(source, filename)
                            spec = importlib.util.spec_from_file_location(module_name, module_path)
                            if spec is None or spec.loader is None:
                                logger.error(f"Could not load module spec for {module_path}")
                                continue
                                
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            
                            # Find all Action subclasses in the module
                            for name, obj in inspect.getmembers(module):
                                # Check if the object is a subclass of Action
                                if inspect.isclass(obj) and issubclass(obj, Action) and obj != Action:
                                    try:
                                        # Register the action
                                        self.register_action_class(obj, source_file=module_path)
                                        discovered_actions.append(name)
                                        logger.debug(f"Registered action class: {name} from file {module_path}")
                                    except Exception as e:
                                        logger.error(f"Error registering action {name} from file {module_path}: {e}")
                        except Exception as e:
                            logger.error(f"Error loading module {module_name} from {source}: {e}")
                
                # Remove the directory from the Python path
                if source in sys.path:
                    sys.path.remove(source)
            
            return discovered_actions
        except Exception as e:
            logger.error(f"Error discovering actions from {'module' if is_module else 'path'} {source}: {e}")
            raise ActionError(f"Error discovering actions from {'module' if is_module else 'path'}: {e}", action_name=source, cause=e)
    
    @with_error_handling
    def discover_actions_from_path(self, file_path: str) -> List[Type[Action]]:
        """Discover and register Action classes from a file path.

        Args:
            file_path: Path to the Python file to load

        Returns:
            List of discovered and registered Action classes

        """
        # Create dependencies for the module
        dependencies = {
            "dcc_name": self.name,
        }

        # Discover actions from the file
        discovered_actions = self.action_manager.registry.discover_actions_from_path(
            file_path, dependencies=dependencies, dcc_name=self.name
        )

        # Register the actions with source file information
        for action_class in discovered_actions:
            self.register_action_class(action_class, source_file=file_path)

        return discovered_actions
    
    @with_error_handling
    def list_available_actions(self) -> Dict[str, Any]:
        """List all available actions.
        
        Returns:
        -------
            Dictionary of available actions with their metadata
        """
        actions = {}
        
        # Get all registered actions from the registry
        for action_cls in self.action_manager.registry.get_all():
            try:
                # Create an instance of the action to get its metadata
                action = action_cls()
                
                # Get action metadata
                actions[action.name] = {
                    "name": action.name,
                    "description": action.description,
                    "category": action.category,
                    "tags": action.tags,
                    "dcc": action.dcc,
                }
            except Exception as e:
                logger.error(f"Error getting metadata for action {action_cls.__name__}: {e}")
        
        return actions

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
