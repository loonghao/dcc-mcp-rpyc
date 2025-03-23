"""Service discovery for DCC RPYC servers.

This module provides mechanisms for discovering and registering RPYC services
for DCC applications.
"""

# Import built-in modules
import glob
import json
import logging
import os
import time
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

# Import third-party modules
from dcc_mcp_core.utils.platform import get_config_dir

# Configure logging
logger = logging.getLogger(__name__)

# Default registry path using dcc-mcp-core
config_dir = get_config_dir(ensure_exists=True)

DEFAULT_REGISTRY_PATH = os.path.join(config_dir, "service_registry.json")

# Service registry cache
_service_registry = {}
_registry_loaded = False


def _load_registry_file(file_path: str) -> Dict[str, Any]:
    """Load data from a registry file.

    Args:
    ----
        file_path: Path to the registry file (JSON format)

    Returns:
    -------
        Loaded registry data as a dictionary

    Raises:
    ------
        FileNotFoundError: If the file does not exist
        ValueError: If the file is empty or invalid JSON

    """
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"Registry file does not exist: {file_path}")
        raise FileNotFoundError(f"Registry file does not exist: {file_path}")

    # Check if file has content
    if os.path.getsize(file_path) == 0:
        logger.error(f"Registry file is empty: {file_path}")
        raise ValueError(f"Registry file is empty: {file_path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to load registry file as JSON: {e}")
        raise ValueError(f"Invalid JSON format in registry file: {e}")


def _save_registry_file(data: Any, file_path: str) -> None:
    """Save data to a registry file.

    Args:
    ----
        data: Data to save
        file_path: Path to the registry file

    Raises:
    ------
        Exception: If there is an error saving the file

    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def register_service(
    dcc_name: str,
    host: str,
    port: int,
    registry_path: Optional[str] = None,
) -> str:
    """Register a DCC RPYC service in the registry.

    Args:
    ----
        dcc_name: Name of the DCC
        host: Host of the RPYC server
        port: Port of the RPYC server
        registry_path: Path to the registry file (default: None, uses default path)

    Returns:
    -------
        Path to the registry file

    """
    global _service_registry, _registry_loaded

    # Normalize DCC name
    dcc_name = dcc_name.lower()

    # If no registry path is specified, create a unique one for this process
    if registry_path is None:
        pid = os.getpid()
        registry_dir = os.path.dirname(DEFAULT_REGISTRY_PATH)
        registry_filename = f"service_registry_{dcc_name}_{pid}.json"
        registry_path = os.path.join(registry_dir, registry_filename)

        # Ensure the directory exists
        os.makedirs(registry_dir, exist_ok=True)

    # Load the registry if not already loaded
    if not _registry_loaded:
        load_registry(registry_path)

    # Create a service entry
    service = {"host": host, "port": port, "timestamp": time.time()}

    # Add the service to the registry
    if dcc_name not in _service_registry:
        _service_registry[dcc_name] = []

    _service_registry[dcc_name].append(service)

    # Save the registry
    if save_registry(registry_path):
        logger.info(f"Registered service: {dcc_name} at {host}:{port} in {registry_path}")
        return registry_path
    else:
        logger.error(f"Failed to register service: {dcc_name} at {host}:{port}")
        return ""


def unregister_service(
    dcc_name: str,
    registry_path: Optional[str] = None,
    registry_loader: Optional[Callable[[str], Dict[str, Any]]] = None,
    registry_saver: Optional[Callable[[Dict[str, Any], str], None]] = None,
) -> bool:
    """Unregister a DCC RPYC service.

    Args:
    ----
        dcc_name: Name of the DCC to unregister
        registry_path: Path to the registry file (default: None, uses default path)
        registry_loader: Optional function to load registry data (default: None, uses _load_registry_file)
        registry_saver: Optional function to save registry data (default: None, uses _save_registry_file)

    Returns:
    -------
        True if the service was unregistered successfully, False otherwise

    """
    # Use default registry path if not provided
    if registry_path is None:
        registry_path = DEFAULT_REGISTRY_PATH

    if not os.path.exists(registry_path):
        logger.warning(f"Registry file does not exist: {registry_path}")
        return True  # Nothing to unregister

    # Use provided functions or defaults
    load_func = registry_loader or _load_registry_file
    save_func = registry_saver or _save_registry_file

    try:
        # Load the registry
        registry = load_func(registry_path)

        # Check if the DCC is in the registry
        if dcc_name in registry:
            # Remove the service
            registry[dcc_name] = []

            # Save the updated registry
            save_func(registry, registry_path)

            logger.info(f"Unregistered service for {dcc_name} at {registry_path}")
        else:
            logger.info(f"No service found for {dcc_name} in {registry_path}")

        return True
    except Exception as e:
        logger.error(f"Error unregistering service: {e}")
        return False


def discover_services(
    dcc_name: Optional[str] = None,
    registry_path: Optional[str] = None,
    max_age: Optional[float] = None,
    registry_loader: Optional[Callable[[str], Dict[str, Any]]] = None,
    registry_files_finder: Optional[Callable[[Optional[str]], List[str]]] = None,
) -> List[Dict[str, Any]]:
    """Discover DCC RPYC services from the registry.

    Args:
    ----
        dcc_name: Name of the DCC to discover services for (default: None, all DCCs)
        registry_path: Path to the registry file (default: None, uses default path)
        max_age: Maximum age of services in seconds (default: None, no limit)
        registry_loader: Optional function to load registry data (default: None, uses _load_registry_file)
        registry_files_finder: Optional function to find registry files
                                    (default: None, uses find_service_registry_files)

    Returns:
    -------
        List of discovered services, each a dictionary with host, port, and timestamp

    """
    services = []
    load_func = registry_loader or _load_registry_file
    find_files_func = registry_files_finder or find_service_registry_files

    # If a specific registry path is provided, only use that one
    if registry_path is not None:
        # Load the registry
        global _service_registry, _registry_loaded
        _registry_loaded = False  # Force reload
        load_registry(registry_path)

        # Clean up stale services
        cleanup_stale_services(max_age, registry_path)

        # Return all services if no DCC name is specified
        if dcc_name is None:
            for dcc, dcc_services in _service_registry.items():
                for service in dcc_services:
                    services.append({"dcc": dcc, **service})
            return services

        # Normalize DCC name
        dcc_name = dcc_name.lower()

        # Return services for the specified DCC
        if dcc_name in _service_registry:
            return [{"dcc": dcc_name, **service} for service in _service_registry[dcc_name]]
        else:
            return []

    # If no specific registry path is provided, search all registry files
    registry_files = find_files_func(dcc_name)

    for registry_file in registry_files:
        try:
            # Load the registry
            registry_data = load_func(registry_file)

            # Filter by DCC name if specified
            if dcc_name is not None:
                dcc_name = dcc_name.lower()
                if dcc_name in registry_data:
                    for service in registry_data[dcc_name]:
                        # Check if the service is stale
                        if max_age is not None and time.time() - service["timestamp"] > max_age:
                            continue
                        services.append({"dcc": dcc_name, **service, "registry_file": registry_file})
            else:
                # Return all services
                for dcc, dcc_services in registry_data.items():
                    for service in dcc_services:
                        # Check if the service is stale
                        if max_age is not None and time.time() - service["timestamp"] > max_age:
                            continue
                        services.append({"dcc": dcc, **service, "registry_file": registry_file})
        except Exception as e:
            logger.error(f"Error loading registry file {registry_file}: {e}")

    return services


def cleanup_stale_services(
    max_age: Optional[float] = None,
    registry_path: Optional[str] = None,
) -> bool:
    """Clean up stale services from the registry.

    Args:
    ----
        max_age: Maximum age of services in seconds (default: None, 1 hour)
        registry_path: Path to the registry file (default: None, uses default path)

    Returns:
    -------
        True if the registry was updated, False otherwise

    """
    global _service_registry, _registry_loaded

    # Load the registry if not already loaded
    if not _registry_loaded:
        load_registry(registry_path)

    # Use default max age if not specified (1 hour)
    if max_age is None:
        max_age = 3600  # 1 hour

    # Get current time
    now = time.time()

    # Track if any changes were made
    changes_made = False

    # Check each DCC
    for dcc_name in list(_service_registry.keys()):
        # Original services count
        original_count = len(_service_registry[dcc_name])

        # Check each service
        _service_registry[dcc_name] = [
            service for service in _service_registry[dcc_name] if now - service["timestamp"] <= max_age
        ]

        # If services were removed, mark changes
        if len(_service_registry[dcc_name]) < original_count:
            changes_made = True

        # Remove the DCC entry if it's empty
        if not _service_registry[dcc_name]:
            del _service_registry[dcc_name]
            changes_made = True

    # Save the registry if changes were made
    if changes_made:
        return save_registry(registry_path)

    return False


def load_registry(registry_path: Optional[str] = None) -> bool:
    """Load the service registry from a file.

    Args:
    ----
        registry_path: Path to the registry file (default: None, uses default path)

    Returns:
    -------
        True if the registry was loaded successfully, False otherwise

    """
    global _service_registry, _registry_loaded

    # Use default registry path if not specified
    if registry_path is None:
        registry_path = DEFAULT_REGISTRY_PATH

    # Check if the registry file exists
    if not os.path.exists(registry_path):
        # Initialize an empty registry
        _service_registry = {}
        _registry_loaded = True
        logger.debug(f"Initialized empty service registry for {registry_path}")
        return True

    try:
        # Load the registry from the file
        loaded_registry = _load_registry_file(registry_path)

        # Verify the loaded registry is a dictionary
        if not isinstance(loaded_registry, dict):
            logger.error(f"Invalid registry format: {registry_path}")
            _service_registry = {}
        else:
            _service_registry = loaded_registry

        _registry_loaded = True
        logger.debug(f"Loaded service registry from {registry_path}")
        return True
    except Exception as e:
        logger.error(f"Error loading service registry: {e}")
        # Initialize an empty registry on error
        _service_registry = {}
        _registry_loaded = True
        return False


def save_registry(registry_path: Optional[str] = None) -> bool:
    """Save the service registry to a file.

    Args:
    ----
        registry_path: Path to the registry file (default: None, uses default path)

    Returns:
    -------
        True if the registry was saved successfully, False otherwise

    """
    global _service_registry

    # Use default registry path if not specified
    if registry_path is None:
        registry_path = DEFAULT_REGISTRY_PATH

    try:
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)

        # Save the registry
        _save_registry_file(_service_registry, registry_path)

        logger.debug(f"Saved service registry to {registry_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving service registry: {e}")
        return False


def find_service_registry_files(dcc_name: Optional[str] = None, registry_path: Optional[str] = None) -> List[str]:
    """Find service registry files for a specific DCC.

    Args:
    ----
        dcc_name: Name of the DCC to find registry files for (default: None, all DCCs)
        registry_path: Path to the registry file (default: None, uses default path)

    Returns:
    -------
        List of paths to registry files

    """
    # Get the registry directory
    if registry_path:
        # If an exact registry path is provided and it exists, use it directly
        if os.path.isfile(registry_path):
            # If no DCC name is specified or if the registry contains the DCC name, return it
            if dcc_name is None:
                return [registry_path]

            try:
                # Try to load the registry file
                registry = _load_registry_file(registry_path)

                # Check if the registry contains the DCC name (case insensitive)
                if dcc_name.lower() in {k.lower() for k in registry.keys()}:
                    return [registry_path]
                return []
            except Exception as e:
                logger.debug(f"Error loading registry file {registry_path}: {e}")
                return []

        # Otherwise, use the directory containing the registry file
        registry_dir = os.path.dirname(registry_path)
    else:
        registry_dir = os.path.dirname(DEFAULT_REGISTRY_PATH)

    # Check if the registry directory exists
    if not os.path.exists(registry_dir):
        return []

    # Find all registry files using glob
    registry_files = glob.glob(os.path.join(registry_dir, "**", "*.json"), recursive=True)

    # If no DCC name specified, return all registry files
    if dcc_name is None:
        return registry_files

    # Filter by DCC name (case insensitive)
    dcc_name = dcc_name.lower()
    filtered_files = []

    for file in registry_files:
        try:
            # Try to load the registry file
            registry = _load_registry_file(file)

            # Check if the registry contains the DCC name (case insensitive)
            if any(k.lower() == dcc_name for k in registry.keys()):
                filtered_files.append(file)
        except Exception as e:
            logger.debug(f"Error loading registry file {file}: {e}")

    return filtered_files


def unregister_dcc_service(registry_file: Optional[str] = None, registry_path: Optional[str] = None) -> bool:
    """Unregister a DCC service.

    Args:
    ----
        registry_file: Path to the registry file (default: None, uses default path)
        registry_path: Path to the registry directory (default: None, uses default path)

    Returns:
    -------
        True if the service was unregistered successfully, False otherwise

    """
    # Use default registry path if not provided
    if registry_path is None:
        registry_path = DEFAULT_REGISTRY_PATH

    if not os.path.exists(registry_path):
        logger.warning(f"Registry file does not exist: {registry_path}")
        return True  # Nothing to unregister

    try:
        # Check if the registry file parameter was provided
        if registry_file and os.path.exists(registry_file):
            # Remove the registry file
            os.remove(registry_file)
            logger.info(f"Removed registry file: {registry_file}")

        return True
    except Exception as e:
        logger.error(f"Error unregistering service: {e}")
        return False


def get_latest_service(services: list) -> dict:
    """Get the latest service from a list of services.

    Args:
    ----
        services: List of service dictionaries

    Returns:
    -------
        Latest service dictionary or empty dict if no services

    """
    if not services:
        return {}

    # Sort by timestamp to get the newest service
    return sorted(services, key=lambda s: s.get("timestamp", 0), reverse=True)[0]
