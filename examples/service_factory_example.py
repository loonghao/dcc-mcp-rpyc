"""Example demonstrating the use of service factories and parameter handling in DCC-MCP-RPYC.

This example shows how to create custom services with bound parameters and
how to handle RPyC-specific parameter serialization issues.
"""

# Import built-in modules
import logging
import threading
from typing import Any
from typing import Dict
from typing import List

# Import third-party modules
import rpyc

# Import local modules
from dcc_mcp_rpyc.parameters import process_rpyc_parameters
from dcc_mcp_rpyc.server import create_raw_threaded_server
from dcc_mcp_rpyc.server import create_shared_service_instance
from dcc_mcp_rpyc.server import get_rpyc_config

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SceneManager:
    """Example scene manager that maintains state shared between connections."""

    def __init__(self):
        self.scenes = {}
        self.lock = threading.RLock()

    def create_scene(self, scene_name: str, scene_type: str) -> bool:
        """Create a new scene with the given name and type.

        Args:
        ----
            scene_name: Name of the scene to create
            scene_type: Type of scene (e.g., 'maya', 'houdini')

        Returns:
        -------
            True if the scene was created, False if it already exists

        """
        with self.lock:
            if scene_name in self.scenes:
                return False

            self.scenes[scene_name] = {
                "type": scene_type,
                "objects": [],
                "created_at": "2025-03-25",  # In a real app, use datetime
            }
            return True

    def add_object(self, scene_name: str, object_data: Dict[str, Any]) -> bool:
        """Add an object to a scene.

        Args:
        ----
            scene_name: Name of the scene to add the object to
            object_data: Object data to add

        Returns:
        -------
            True if the object was added, False if the scene doesn't exist

        """
        with self.lock:
            if scene_name not in self.scenes:
                return False

            self.scenes[scene_name]["objects"].append(object_data)
            return True

    def get_scene_info(self, scene_name: str) -> Dict[str, Any]:
        """Get information about a scene.

        Args:
        ----
            scene_name: Name of the scene to get information about

        Returns:
        -------
            Scene information or empty dict if the scene doesn't exist

        """
        with self.lock:
            return self.scenes.get(scene_name, {})

    def list_scenes(self) -> List[str]:
        """List all scene names.

        Returns
        -------
            List of scene names

        """
        with self.lock:
            return list(self.scenes.keys())


class SceneService(rpyc.Service):
    """Example RPyC service that uses the SceneManager."""

    def __init__(self, scene_manager: SceneManager):
        # Note: In RPyC 4.0+, connection is passed via on_connect, not __init__
        self.scene_manager = scene_manager

    def on_connect(self, conn):
        """Called when a connection is established.

        Args:
        ----
            conn: The RPyC connection

        """
        self._conn = conn
        logger.info(f"Client connected: {conn}")

    def on_disconnect(self, conn):
        """Called when a connection is closed.

        Args:
        ----
            conn: The RPyC connection

        """
        logger.info(f"Client disconnected: {conn}")

    def exposed_create_scene(self, scene_name, scene_type):
        """Create a new scene (exposed to clients).

        Args:
        ----
            scene_name: Name of the scene to create
            scene_type: Type of scene

        Returns:
        -------
            True if the scene was created, False if it already exists

        """
        # Process parameters to handle RPyC-specific issues
        params = process_rpyc_parameters({"scene_name": scene_name, "scene_type": scene_type})

        result = self.scene_manager.create_scene(params["scene_name"], params["scene_type"])

        return {
            "success": result,
            "message": f"Scene '{scene_name}' {'created' if result else 'already exists'}",
            "error": None if result else "Scene already exists",
            "context": {"scene_name": scene_name, "scene_type": scene_type},
        }

    def exposed_add_object(self, scene_name, object_data):
        """Add an object to a scene (exposed to clients).

        Args:
        ----
            scene_name: Name of the scene to add the object to
            object_data: Object data to add

        Returns:
        -------
            Result dictionary

        """
        # Process parameters to handle RPyC-specific issues
        params = process_rpyc_parameters({"scene_name": scene_name, "object_data": object_data})

        result = self.scene_manager.add_object(params["scene_name"], params["object_data"])

        return {
            "success": result,
            "message": f"Object added to scene '{scene_name}'" if result else f"Scene '{scene_name}' not found",
            "error": None if result else "Scene not found",
            "context": {
                "scene_name": scene_name,
                "object_count": len(self.scene_manager.get_scene_info(scene_name).get("objects", [])) if result else 0,
            },
        }

    def exposed_get_scene_info(self, scene_name):
        """Get information about a scene (exposed to clients).

        Args:
        ----
            scene_name: Name of the scene to get information about

        Returns:
        -------
            Scene information

        """
        # Process parameters to handle RPyC-specific issues
        params = process_rpyc_parameters({"scene_name": scene_name})

        scene_info = self.scene_manager.get_scene_info(params["scene_name"])
        exists = bool(scene_info)

        return {
            "success": exists,
            "message": f"Scene '{scene_name}' information retrieved" if exists else f"Scene '{scene_name}' not found",
            "error": None if exists else "Scene not found",
            "context": scene_info,
        }

    def exposed_list_scenes(self):
        """List all scene names (exposed to clients).

        Returns
        -------
            List of scene names

        """
        scenes = self.scene_manager.list_scenes()

        return {"success": True, "message": f"Found {len(scenes)} scenes", "error": None, "context": {"scenes": scenes}}


def run_server():
    """Run the RPyC server with the SceneService."""
    # Create a shared scene manager
    scene_manager = SceneManager()

    # Method 1: Using create_service_factory to create a new service instance for each connection
    # factory = create_service_factory(SceneService, scene_manager)

    # Method 2: Using create_shared_service_instance to share a single service instance
    service = create_shared_service_instance(SceneService, scene_manager)

    # Get RPyC configuration with appropriate settings
    config = get_rpyc_config(allow_public_attrs=True)

    # Create and start the server
    server = create_raw_threaded_server(service, port=18861, protocol_config=config)

    logger.info("Starting RPyC server on port 18861...")
    server.start()


def run_client():
    """Run a client that connects to the RPyC server."""
    # Get RPyC configuration with appropriate settings
    config = get_rpyc_config(allow_public_attrs=True)

    # Connect to the server
    conn = rpyc.connect("localhost", 18861, config=config)

    try:
        # Create a scene
        result = conn.root.create_scene("my_scene", "maya")
        logger.info(f"Create scene result: {result}")

        # Add an object to the scene
        object_data = {
            "name": "Cube",
            "type": "mesh",
            "position": [0, 0, 0],
            "rotation": [0, 0, 0],
            "scale": [1, 1, 1],
            "visible": True,  # Boolean parameter that needs proper handling
        }
        result = conn.root.add_object("my_scene", object_data)
        logger.info(f"Add object result: {result}")

        # Get scene information
        result = conn.root.get_scene_info("my_scene")
        logger.info(f"Scene info: {result}")

        # List all scenes
        result = conn.root.list_scenes()
        logger.info(f"List scenes: {result}")

    finally:
        # Close the connection
        conn.close()


if __name__ == "__main__":
    # To run the server
    # run_server()

    # To run the client (after starting the server)
    # run_client()

    logger.info("This is an example module. Run the server and client functions separately.")
    logger.info("Uncomment the appropriate function calls in the __main__ block to run them.")
