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
from typing import Optional

# Import third-party modules
from dcc_mcp_core.utils.filesystem import get_config_dir

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
    registry_path: Optional[Optional[str]] = None,
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
    registry_path: Optional[Optional[str]] = None,
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
    dcc_name: Optional[Optional[str]] = None,
    registry_path: Optional[Optional[str]] = None,
    max_age: Optional[Optional[float]] = None,
    registry_loader: Optional[Callable[[str], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Discover DCC RPYC services.

    Args:
    ----
        dcc_name: Name of the DCC to discover services for (default: None, all DCCs)
        registry_path: Path to the registry file (default: None, uses default path)
        max_age: Maximum age of services in seconds (default: None, no limit)
        registry_loader: Optional function to load registry data (default: None, uses _load_registry_file)

    Returns:
    -------
        Dictionary of discovered services by DCC name

    """
    # Use default registry path if not provided
    if registry_path is None:
        registry_path = DEFAULT_REGISTRY_PATH

    # Use provided function or default
    load_func = registry_loader or _load_registry_file

    # Find all registry files
    registry_files = find_service_registry_files(dcc_name, registry_path)

    # Collect services from all registry files
    services = {}

    for registry_file in registry_files:
        try:
            # Load the registry file
            registry = load_func(registry_file)

            # Filter by DCC name if specified
            if dcc_name is not None:
                dcc_name = dcc_name.lower()
                if dcc_name in registry:
                    # Add services to the collection
                    if dcc_name not in services:
                        services[dcc_name] = []
                    services[dcc_name].extend(registry[dcc_name])
            else:
                # Add all services to the collection
                for dcc, dcc_services in registry.items():
                    if dcc not in services:
                        services[dcc] = []
                    services[dcc].extend(dcc_services)
        except Exception as e:
            logger.warning(f"Error loading registry file {registry_file}: {e}")

    # Filter by age if specified
    if max_age is not None:
        now = time.time()
        for dcc, dcc_services in list(services.items()):
            filtered_services = [service for service in dcc_services if now - service.get("timestamp", 0) <= max_age]
            if filtered_services:
                services[dcc] = filtered_services
            else:
                del services[dcc]

    return services


def cleanup_stale_services(
    max_age: Optional[Optional[float]] = None,
    registry_path: Optional[Optional[str]] = None,
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
    # Use default max age if not provided (1 hour)
    if max_age is None:
        max_age = 3600  # 1 hour

    # Use default registry path if not provided
    if registry_path is None:
        registry_path = DEFAULT_REGISTRY_PATH

    # Check if registry file exists
    if not os.path.exists(registry_path):
        logger.warning(f"Registry file does not exist: {registry_path}")
        return False

    try:
        # Load the registry
        registry = _load_registry_file(registry_path)

        # Get current time
        now = time.time()

        # Track if any services were removed
        updated = False

        # Check each DCC in the registry
        for dcc, services in list(registry.items()):
            # Filter out stale services
            filtered_services = [service for service in services if now - service.get("timestamp", 0) <= max_age]

            # Update the registry if services were removed
            if len(filtered_services) < len(services):
                registry[dcc] = filtered_services
                updated = True

        # Save the registry if it was updated
        if updated:
            _save_registry_file(registry, registry_path)
            logger.info(f"Cleaned up stale services in {registry_path}")

        return updated
    except Exception as e:
        logger.error(f"Error cleaning up stale services: {e}")
        return False


def load_registry(registry_path: Optional[Optional[str]] = None) -> bool:
    """Load the service registry from a file.

    Args:
    ----
        registry_path: Path to the registry file (default: None, uses default path)

    Returns:
    -------
        True if the registry was loaded successfully, False otherwise

    """
    global _service_registry, _registry_loaded

    # Use default registry path if not provided
    if registry_path is None:
        registry_path = DEFAULT_REGISTRY_PATH

    # Reset the registry
    _service_registry = {}

    # Check if registry file exists
    if not os.path.exists(registry_path):
        # Create an empty registry file
        try:
            os.makedirs(os.path.dirname(registry_path), exist_ok=True)
            with open(registry_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            _registry_loaded = True
            return True
        except Exception as e:
            logger.error(f"Error creating registry file: {e}")
            _registry_loaded = False
            return False

    try:
        # Load the registry file
        _service_registry = _load_registry_file(registry_path)
        _registry_loaded = True
        return True
    except Exception as e:
        logger.error(f"Error loading registry file: {e}")
        _registry_loaded = False
        return False


def save_registry(registry_path: Optional[Optional[str]] = None) -> bool:
    """Save the service registry to a file.

    Args:
    ----
        registry_path: Path to the registry file (default: None, uses default path)

    Returns:
    -------
        True if the registry was saved successfully, False otherwise

    """
    global _service_registry

    # Use default registry path if not provided
    if registry_path is None:
        registry_path = DEFAULT_REGISTRY_PATH

    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)

        # Save the registry file
        _save_registry_file(_service_registry, registry_path)
        return True
    except Exception as e:
        logger.error(f"Error saving registry file: {e}")
        return False


def find_service_registry_files(
    dcc_name: Optional[Optional[str]] = None, registry_path: Optional[Optional[str]] = None
) -> list:
    """Find service registry files for a specific DCC.

    Args:
    ----
        dcc_name: Name of the DCC to find registry files for (default: None, all DCCs)
        registry_path: Path to the registry file (default: None, uses default path)

    Returns:
    -------
        List of paths to registry files

    """
    # Use default registry path if not provided
    if registry_path is None:
        registry_path = DEFAULT_REGISTRY_PATH

    # Get the registry directory
    registry_dir = os.path.dirname(registry_path)

    # Check if the registry directory exists
    if not os.path.exists(registry_dir):
        logger.warning(f"Registry directory does not exist: {registry_dir}")
        return []

    # Find all registry files
    if dcc_name is not None:
        # Normalize DCC name
        dcc_name = dcc_name.lower()

        # Find registry files for the specific DCC
        pattern = os.path.join(registry_dir, f"service_registry_{dcc_name}_*.json")
        registry_files = glob.glob(pattern)

        # Add the default registry file if it exists
        default_registry = os.path.join(registry_dir, "service_registry.json")
        if os.path.exists(default_registry) and default_registry not in registry_files:
            registry_files.append(default_registry)
    else:
        # Find all registry files
        pattern = os.path.join(registry_dir, "service_registry*.json")
        registry_files = glob.glob(pattern)

    return registry_files


def unregister_dcc_service(
    registry_file: Optional[Optional[str]] = None, registry_path: Optional[Optional[str]] = None
) -> bool:
    """Unregister a DCC service.

    Args:
    ----
        registry_file: Path to the registry file (default: None, uses default path)
        registry_path: Path to the registry directory (default: None, uses default path)

    Returns:
    -------
        True if the service was unregistered successfully, False otherwise

    """
    # Use registry_file if provided
    if registry_file is not None:
        # Check if the registry file exists
        if os.path.exists(registry_file):
            try:
                # Remove the registry file
                os.remove(registry_file)
                logger.info(f"Removed registry file: {registry_file}")
                return True
            except Exception as e:
                logger.error(f"Error removing registry file: {e}")
                return False
        else:
            logger.warning(f"Registry file does not exist: {registry_file}")
            return True  # Nothing to unregister

    # Use registry_path if provided, otherwise use default
    if registry_path is None:
        registry_path = os.path.dirname(DEFAULT_REGISTRY_PATH)

    return True


def get_latest_service(services: list) -> Dict[str, Any]:
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

    # Sort services by timestamp (newest first)
    sorted_services = sorted(services, key=lambda s: s.get("timestamp", 0), reverse=True)

    # Return the newest service
    return sorted_services[0]
