"""DCC server classes for DCC-MCP-RPYC.

This module provides DCC-specific RPYC services and server implementation.
"""

# Import built-in modules
from abc import abstractmethod
import logging
import threading
import time
from typing import Any
from typing import Dict
from typing import Type
from typing import Union

# Import third-party modules
from rpyc.core import service
from rpyc.utils.server import ThreadedServer

# Import local modules
from dcc_mcp_rpyc.server.base import ApplicationRPyCService
from dcc_mcp_rpyc.server.decorators import with_scene_info

# Configure logging
logger = logging.getLogger(__name__)


class DCCRPyCService(ApplicationRPyCService):
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

    @abstractmethod
    def create_primitive(self, primitive_type: str, **kwargs) -> Any:
        """Create a primitive object in the DCC application.

        Args:
        ----
            primitive_type: Type of primitive to create
            **kwargs: Additional arguments for the primitive creation

        Returns:
        -------
            The result of the primitive creation

        """

    @with_scene_info
    def exposed_create_primitive(self, primitive_type: str, **kwargs) -> Any:
        """Create a primitive object in the DCC application.

        Args:
        ----
            primitive_type: Type of primitive to create
            **kwargs: Additional arguments for the primitive creation

        Returns:
        -------
            The result of the primitive creation

        """
        try:
            return self.create_primitive(primitive_type, **kwargs)
        except Exception as e:
            logger.error(f"Error creating primitive {primitive_type}: {e}")
            logger.exception("Detailed exception information:")
            raise


class DCCServer:
    """Unified DCC server class for RPYC services.

    This class provides a thread-safe RPYC server implementation that can run within
    DCC software environments. It handles server lifecycle, including starting,
    stopping, and registering with the discovery service.
    """

    def __init__(
        self,
        dcc_name: str,
        service_class: Type[service.Service],
        host: str = "localhost",
        port: int = 0,
    ):
        """Initialize the DCC server.

        Args:
        ----
            dcc_name: Name of the DCC this server is for
            service_class: Service class to use
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
        # Import local modules
        from dcc_mcp_rpyc.server.factory import create_raw_threaded_server

        return create_raw_threaded_server(
            self.service_class,
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
            if self.is_running():
                logger.info(f"Server for {self.dcc_name} is already running on {self.host}:{self.port}")
                return self.port

            try:
                # Create the server
                self.server = self._create_server()

                # Start the server in a thread if requested
                if threaded:
                    return self._start_in_thread()

                # Otherwise, start the server in the current thread (blocking)
                logger.info(f"Starting RPYC server for {self.dcc_name} on {self.host}:{self.port}")
                self.server.start()
                return self.port
            except Exception as e:
                logger.error(f"Error starting RPYC server for {self.dcc_name}: {e}")
                logger.exception("Detailed exception information:")
                self.server = None
                return False

    def _start_in_thread(self) -> Union[int, bool]:
        """Start the RPYC server in a thread.

        This is a convenience wrapper around start(threaded=True).

        Returns
        -------
            The port the server is running on, or False if the server failed to start

        """
        try:
            # Create a thread to run the server
            thread = threading.Thread(target=self.server.start, daemon=True)
            thread.start()

            # Wait for the server to start
            time.sleep(0.1)

            # Get the port the server is running on
            self.port = self.server.port

            # Register the service
            # Import local modules
            from dcc_mcp_rpyc.server.factory import register_dcc_service

            self.registry_file = register_dcc_service(dcc_name=self.dcc_name, host=self.host, port=self.port)

            self.running = True
            logger.info(f"Started RPYC server for {self.dcc_name} on {self.host}:{self.port}")
            return self.port
        except Exception as e:
            logger.error(f"Error starting RPYC server for {self.dcc_name}: {e}")
            logger.exception("Detailed exception information:")
            self.server = None
            return False

    def stop(self) -> bool:
        """Stop the RPYC server.

        Returns
        -------
            True if the server was stopped successfully, False otherwise

        """
        with self.lock:
            if not self.is_running():
                logger.info(f"Server for {self.dcc_name} is not running")
                return True

            try:
                # Unregister the service
                # Import local modules
                from dcc_mcp_rpyc.server.factory import unregister_dcc_service

                unregister_dcc_service(self.registry_file)

                # Close the server
                self.close()

                self.running = False
                logger.info(f"Stopped RPYC server for {self.dcc_name}")
                return True
            except Exception as e:
                logger.error(f"Error stopping RPYC server for {self.dcc_name}: {e}")
                logger.exception("Detailed exception information:")
                return False

    def is_running(self) -> bool:
        """Check if the server is running.

        Returns
        -------
            True if the server is running, False otherwise

        """
        return self.running and self.server is not None

    def cleanup(self) -> bool:
        """Cleanup function to be called when the DCC application exits.

        Returns
        -------
            True if cleanup was successful, False otherwise

        """
        return self.stop()

    def close(self):
        """Close the RPYC server.

        This method is used to close the server and release any system resources.
        """
        if self.server:
            try:
                self.server.close()
            except Exception as e:
                logger.error(f"Error closing RPYC server for {self.dcc_name}: {e}")
                logger.exception("Detailed exception information:")
            finally:
                self.server = None
