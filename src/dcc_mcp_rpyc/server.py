"""RPYC server implementation for DCC software.

This module provides a thread-safe RPYC server implementation that can run within
DCC software environments, with specific handling for different DCC threading models.
"""

# Import built-in modules
from abc import ABC
from abc import abstractmethod
import functools
import logging
import os
import threading
import time
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union
from typing import cast

# Import third-party modules
import rpyc
from rpyc.core import service
from rpyc.utils.server import ThreadedServer

# Import local modules
from dcc_mcp_rpyc import discovery
from dcc_mcp_rpyc.discovery import _load_registry_file

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for the decorator
F = TypeVar("F", bound=Callable[..., Any])


class BaseRPyCService(rpyc.SlaveService):
    """Base RPYC service for DCC applications.

    This service provides the foundation for exposing DCC functionality via RPYC.
    It can be extended for specific DCC applications.
    """

    def on_connect(self, conn):
        """Handle client connection to the service.

        Args:
        ----
            conn: The connection object

        """
        try:
            client_ip = conn._channel.stream.sock.getpeername()[0]
            logger.info(f"Client connected from {client_ip}")
        except Exception as e:
            logger.info(f"Client connected (error getting IP: {e})")

    def on_disconnect(self, conn):
        """Handle client disconnection from the service.

        Args:
        ----
            conn: The connection object

        """
        logger.info("Client disconnected")


class DCCRPyCService(BaseRPyCService, ABC):
    """Abstract base class for DCC RPYC services.

    This class defines the common interface that all DCC services should implement.
    It provides methods for connecting to a DCC application and executing commands.
    """

    @abstractmethod
    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """

    @abstractmethod
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session.

        Returns
        -------
            Dict with session information

        """

    @staticmethod
    def with_scene_info(func: F) -> F:
        """Add scene information to the return value of a function.

        This decorator wraps a function to add the current scene information to its return value.
        The wrapped function's result will be returned as a dictionary with 'result' and 'scene_info' keys.

        Args:
        ----
            func: The function to wrap

        Returns:
        -------
            The wrapped function

        """

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                # Call the original function
                result = func(self, *args, **kwargs)

                # Get current scene info
                scene_info = self.get_scene_info()

                # Check if result is an ActionResultModel and convert to dict if needed
                if hasattr(result, "dict") and callable(getattr(result, "dict")):
                    result_dict = result.dict()
                elif isinstance(result, dict):
                    result_dict = result
                else:
                    # Otherwise, wrap the result
                    result_dict = {"result": result}

                # Add scene_info to the result dict
                result_dict["scene_info"] = scene_info
                return result_dict
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                logger.exception("Detailed exception information:")
                raise

        return cast(F, wrapper)

    @staticmethod
    def with_session_info(func: F) -> F:
        """Add session information to the return value of a function.

        This decorator wraps a function to add the current session information to its return value.
        The wrapped function's result will be returned as a dictionary with 'result' and 'session_info' keys.

        Args:
        ----
            func: The function to wrap

        Returns:
        -------
            The wrapped function

        """

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                # Call the original function
                result = func(self, *args, **kwargs)

                # Get current session info
                session_info = self.get_session_info()

                # Check if result is an ActionResultModel and convert to dict if needed
                if hasattr(result, "dict") and callable(getattr(result, "dict")):
                    result_dict = result.dict()
                elif isinstance(result, dict):
                    result_dict = result
                else:
                    # Otherwise, wrap the result
                    result_dict = {"result": result}

                # Add session_info to the result dict
                result_dict["session_info"] = session_info
                return result_dict
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                logger.exception("Detailed exception information:")
                raise

        return cast(F, wrapper)


class DCCServer:
    """Unified DCC server class for RPYC services.

    This class provides a thread-safe RPYC server implementation that can run within
    DCC software environments. It handles server lifecycle, including starting,
    stopping, and registering with the discovery service.
    """

    def __init__(
        self,
        dcc_name: str,
        service_class: Type[service.Service] = BaseRPyCService,
        host: str = "localhost",
        port: int = 0,
    ):
        """Initialize the DCC server.

        Args:
        ----
            dcc_name: Name of the DCC this server is for
            service_class: Service class to use (default: BaseRPyCService)
            host: Host to bind the server to (default: 'localhost')
            port: Port to bind the server to (default: 0, auto-select)

        """
        self.dcc_name = dcc_name.lower()
        self.service_class = service_class
        self.host = host
        self.port = port
        self.server = None
        self.running = False
        self.lock = threading.RLock()
        self.registry_file = None
        self.clients = []  # List to track active clients

    def _create_server(self) -> ThreadedServer:
        """Create a RPYC server.

        Returns
        -------
            A ThreadedServer instance

        """
        return create_raw_threaded_server(
            service_class=self.service_class,
            hostname=self.host,
            port=self.port,
        )

    def start(self, threaded: bool = True) -> Union[int, bool]:
        """Start the RPYC server.

        Args:
        ----
            threaded: Whether to run the server in a separate thread (default: True)

        Returns:
        -------
            The port the server is running on, or False if the server failed to start

        """
        with self.lock:
            if self.running:
                logger.warning("Server is already running")
                return self.port

            try:
                # Create the server
                self.server = self._create_server()

                # Start the server
                if threaded:
                    self.server._start_in_thread()
                else:
                    self.server.start()

                # Update the port (in case it was auto-assigned)
                self.port = self.server.port

                # Register the service
                self.registry_file = register_dcc_service(dcc_name=self.dcc_name, host=self.host, port=self.port)

                self.running = True
                logger.info(f"Started RPYC server for {self.dcc_name} on {self.host}:{self.port}")
                return self.port
            except Exception as e:
                logger.error(f"Failed to start RPYC server: {e}")
                return False

    def _start_in_thread(self) -> int:
        """Start the RPYC server in a thread.

        This is a convenience wrapper around start(threaded=True).

        Returns
        -------
            The port the server is running on, or False if the server failed to start

        """
        return self.start(threaded=True)

    def stop(self) -> bool:
        """Stop the RPYC server.

        Returns
        -------
            True if the server was stopped successfully, False otherwise

        """
        with self.lock:
            if not self.running:
                logger.warning("Server is not running")
                return True

            try:
                # Unregister the service
                if self.registry_file and os.path.exists(self.registry_file):
                    unregister_dcc_service(registry_file=self.registry_file)
                    self.registry_file = None

                # Stop the server
                if self.server:
                    # Wait for any active clients to finish, but with a timeout
                    if hasattr(self.server, "clients") and self.server.clients:
                        logger.info(f"Waiting for {len(self.server.clients)} clients to disconnect")
                        max_wait = 3.0  # Maximum seconds to wait for clients
                        wait_interval = 0.1
                        waited = 0
                        while self.server.clients and waited < max_wait:
                            time.sleep(wait_interval)
                            waited += wait_interval

                        # Force close any remaining clients
                        if self.server.clients:
                            logger.warning(f"Forcing close of {len(self.server.clients)} remaining clients")
                            for conn in list(self.server.clients):
                                try:
                                    conn.close()
                                except Exception as e:
                                    logger.debug(f"Error closing client connection: {e}")

                    # Close the server
                    self.server.close()
                    self.server = None

                self.running = False
                logger.info(f"Stopped {self.dcc_name} RPYC server")
                return True
            except Exception as e:
                logger.error(f"Error stopping RPYC server: {e}")
                return False

    def is_running(self) -> bool:
        """Check if the server is running.

        Returns
        -------
            True if the server is running, False otherwise

        """
        with self.lock:
            return self.running and self.server is not None

    def cleanup(self) -> bool:
        """Cleanup function to be called when the DCC application exits.

        Returns
        -------
            True if cleanup was successful, False otherwise

        """
        logger.info(f"Cleaning up {self.dcc_name} RPYC server")
        return self.stop()

    def close(self) -> None:
        """Close the RPYC server.

        This method is used to close the server and release any system resources.
        """
        if self.server:
            self.server.close()
            self.server = None


def register_dcc_service(dcc_name: str, host: str, port: int) -> str:
    """Register a DCC service for discovery.

    This function registers a DCC service with the discovery service,
    making it discoverable by clients.

    Args:
    ----
        dcc_name: The name of the DCC
        host: The hostname of the server
        port: The port the server is running on

    Returns:
    -------
        The path to the registry file

    """
    return discovery.register_service(dcc_name, host, port)


def unregister_dcc_service(registry_file: Optional[str] = None, registry_path: Optional[str] = None) -> bool:
    """Unregister a DCC service.

    This function unregisters a DCC service from the discovery service.

    Args:
    ----
        registry_file: The path to the registry file or DCC name (deprecated, kept for compatibility)
        registry_path: Optional alternative registry path

    Returns:
    -------
        True if successful, False otherwise

    """
    try:
        if registry_file:
            is_file_path = os.path.exists(registry_file)

            if is_file_path:
                try:
                    registry_data = _load_registry_file(registry_file)
                    if registry_data and isinstance(registry_data, dict) and registry_data:
                        dcc_name = next(iter(registry_data.keys()))
                    else:
                        dcc_name = "unknown_dcc"
                        logger.warning(f"Could not extract DCC name from registry file, using {dcc_name}")

                    return discovery.unregister_service(dcc_name, registry_path=registry_path)
                except Exception as e:
                    logger.error(f"Error loading registry file: {e}")
                    return False
            # if registry_file is a string without path separators, treat it as a DCC name
            elif not any(sep in registry_file for sep in ["/", "\\"]):
                dcc_name = registry_file
                return discovery.unregister_service(dcc_name, registry_path=registry_path)

        # If we cannot determine the DCC name, use the default value
        dcc_name = "unknown_dcc"
        logger.warning(f"Could not determine DCC name from registry file, using {dcc_name}")
        return discovery.unregister_service(dcc_name, registry_path=registry_path)
    except Exception as e:
        logger.error(f"Error unregistering service: {e}")
        return False


def cleanup_server(
    server_instance: Optional[ThreadedServer],
    registry_file: Optional[str],
    timeout: float = 5.0,
    server_closer: Optional[Callable[[Any], None]] = None,
) -> bool:
    """Clean up a server instance and unregister its service.

    This function stops a server and unregisters its service from the discovery service.

    Args:
    ----
        server_instance: The server instance to stop
        registry_file: The path to the registry file
        timeout: Timeout for cleanup operations in seconds (default: 5.0)
        server_closer: Optional custom function to close the server (default: None)

    Returns:
    -------
        True if successful, False otherwise

    """
    success = True

    # Stop the server if it's running
    if server_instance:
        try:
            logger.info("Stopping RPYC server")

            # Wait for clients to disconnect if possible
            if hasattr(server_instance, "clients"):
                max_wait = min(timeout, 3.0)  # Maximum seconds to wait for clients
                wait_interval = 0.1
                waited = 0
                while server_instance.clients and waited < max_wait:
                    time.sleep(wait_interval)
                    waited += wait_interval

            # Use custom server closer if provided
            if server_closer:
                try:
                    server_closer(server_instance)
                except Exception as e:
                    logger.error(f"Error using custom server closer: {e}")
                    success = False
            else:
                # Use default closing mechanism with timeout
                # Import built-in modules
                import threading

                def close_with_timeout():
                    server_instance.close()

                close_thread = threading.Thread(target=close_with_timeout)
                close_thread.daemon = True  # Allow the thread to be killed if timeout occurs
                close_thread.start()
                close_thread.join(timeout)  # Wait for the thread to finish with timeout

                if close_thread.is_alive():
                    logger.warning(f"Server close operation timed out after {timeout} seconds")
                    success = False
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            success = False

    # Unregister the service
    if registry_file and success:
        try:
            logger.info("Unregistering RPYC service")
            if not unregister_dcc_service(registry_file):
                logger.warning("Failed to unregister service")
                success = False
        except Exception as e:
            logger.error(f"Error unregistering service: {e}")
            success = False

    return success


def create_raw_threaded_server(
    service_class: Type[service.Service],
    hostname: str = "localhost",
    port: Optional[int] = None,
    protocol_config: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
) -> ThreadedServer:
    """Create a ThreadedServer with standard configuration.

    This function creates a ThreadedServer with a standard configuration,
    reducing code duplication across the codebase.

    Args:
    ----
        service_class: The service class to use
        hostname: The hostname to bind to (default: 'localhost')
        port: The port to bind to (default: None, let OS choose)
        protocol_config: Custom protocol configuration (default: None)
        timeout: Timeout for sync requests in seconds (default: 60.0)

    Returns:
    -------
        A configured ThreadedServer instance

    """
    # Use default protocol config if none provided
    if protocol_config is None:
        protocol_config = {
            "allow_public_attrs": True,
            "allow_all_attrs": True,
            "allow_pickle": True,
            "sync_request_timeout": timeout,
        }

    # Create and return the server
    return ThreadedServer(
        service_class,
        hostname=hostname,
        port=0 if port is None else port,
        protocol_config=protocol_config,
    )


def create_dcc_server(
    dcc_name: str,
    service_class: Type[service.Service] = BaseRPyCService,
    host: str = "localhost",
    port: int = 0,
) -> DCCServer:
    """Create a high-level DCC RPYC server with discovery and management features.

    This function creates a DCCServer instance which provides additional
    functionality on top of the basic RPyC server, including service discovery,
    registration, and lifecycle management.

    Args:
    ----
        dcc_name: Name of the DCC to create a server for
        service_class: Service class to use (default: BaseRPyCService)
        host: Host to bind the server to (default: 'localhost')
        port: Port to bind the server to (default: 0, auto-select)

    Returns:
    -------
        A DCCServer instance

    """
    return DCCServer(
        dcc_name,
        service_class=service_class,
        host=host,
        port=port,
    )


__all__ = [
    "DCCRPyCService",
    "DCCServer",
    "create_dcc_server",
    "create_raw_threaded_server",
]
