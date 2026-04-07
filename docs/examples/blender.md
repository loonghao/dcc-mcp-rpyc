# Blender Integration

This guide shows how to integrate **DCC-MCP-IPC** with [Blender](https://www.blender.org/) to expose Blender's Python API (`bpy`) as MCP tools.

## Prerequisites

- Blender 3.x or 4.x (with bundled Python 3.10+)
- `dcc-mcp-ipc` installed in Blender's Python environment

## Installation

Install `dcc-mcp-ipc` into Blender's bundled Python interpreter:

```bash
# Blender 4.x on macOS
/Applications/Blender.app/Contents/Resources/4.x/python/bin/python3.11 -m pip install dcc-mcp-ipc

# Blender 4.x on Linux
/path/to/blender/4.x/python/bin/python3.11 -m pip install dcc-mcp-ipc

# Blender 4.x on Windows
"C:\Program Files\Blender Foundation\Blender 4.x\4.x\python\bin\python.exe" -m pip install dcc-mcp-ipc
```

## Server (Blender Add-on or Script)

Run this inside Blender's scripting workspace or package it as an add-on:

```python
import threading
from dcc_mcp_ipc.server import create_dcc_server, DCCRPyCService

BLENDER_IPC_PORT = 18814


class BlenderService(DCCRPyCService):
    """Blender RPyC service — exposes bpy operations over IPC."""

    def exposed_get_scene_info(self, conn=None):
        """Return metadata about the current Blender scene."""
        import bpy
        return {
            "file": bpy.data.filepath or "untitled",
            "objects": [obj.name for obj in bpy.data.objects],
            "frame_current": bpy.context.scene.frame_current,
            "frame_start": bpy.context.scene.frame_start,
            "frame_end": bpy.context.scene.frame_end,
            "render_engine": bpy.context.scene.render.engine,
        }

    def exposed_add_primitive(self, ptype="SPHERE", location=(0, 0, 0), conn=None):
        """Add a mesh primitive to the scene.

        Args:
            ptype: One of SPHERE, CUBE, CYLINDER, CONE, TORUS, PLANE.
            location: (x, y, z) world-space coordinates.

        Returns:
            dict with success flag and the new object's name.
        """
        import bpy

        loc = tuple(location)
        dispatch = {
            "SPHERE": bpy.ops.mesh.primitive_uv_sphere_add,
            "CUBE": bpy.ops.mesh.primitive_cube_add,
            "CYLINDER": bpy.ops.mesh.primitive_cylinder_add,
            "CONE": bpy.ops.mesh.primitive_cone_add,
            "TORUS": bpy.ops.mesh.primitive_torus_add,
            "PLANE": bpy.ops.mesh.primitive_plane_add,
        }
        op = dispatch.get(ptype.upper(), bpy.ops.mesh.primitive_uv_sphere_add)
        op(location=loc)
        obj = bpy.context.object
        return {"success": True, "name": obj.name, "type": ptype}

    def exposed_set_object_location(self, name, location, conn=None):
        """Move an existing object to a new world-space location."""
        import bpy

        obj = bpy.data.objects.get(name)
        if obj is None:
            return {"success": False, "error": f"Object '{name}' not found"}
        obj.location = location
        return {"success": True, "name": name, "location": list(obj.location)}

    def exposed_delete_object(self, name, conn=None):
        """Delete an object by name."""
        import bpy

        obj = bpy.data.objects.get(name)
        if obj is None:
            return {"success": False, "error": f"Object '{name}' not found"}
        bpy.data.objects.remove(obj, do_unlink=True)
        return {"success": True, "deleted": name}

    def exposed_render_preview(self, output_path="/tmp/preview.png", conn=None):
        """Render a preview frame to disk."""
        import bpy

        bpy.context.scene.render.filepath = output_path
        bpy.ops.render.render(write_still=True)
        return {"success": True, "output": output_path}

    def exposed_execute_python(self, code, conn=None):
        """Execute arbitrary Python code with `bpy` in scope.

        The code may set ``_result`` to return a value.

        .. warning::
            Use only in trusted, local development environments.
        """
        import bpy

        local_vars: dict = {}
        exec(code, {"bpy": bpy}, local_vars)  # noqa: S102
        return local_vars.get("_result")


def start_blender_server():
    """Start the DCC-MCP-IPC server inside Blender."""
    server = create_dcc_server(
        dcc_name="blender",
        service_class=BlenderService,
        port=BLENDER_IPC_PORT,
    )
    thread = threading.Thread(
        target=lambda: server.start(threaded=False),
        daemon=True,
        name="dcc-mcp-ipc-blender",
    )
    thread.start()
    print(f"[DCC-MCP-IPC] Blender server started on port {BLENDER_IPC_PORT}")
    return server


# Run when the script is executed inside Blender
if __name__ == "__main__":
    start_blender_server()
```

## Client

Connect from any Python process outside Blender:

```python
from dcc_mcp_ipc.client import BaseDCCClient

client = BaseDCCClient("blender", host="localhost", port=18814)
client.connect()

# Query scene information
info = client.call("get_scene_info")
print(f"File   : {info['file']}")
print(f"Objects: {info['objects']}")
print(f"Frame  : {info['frame_current']}")

# Add a sphere at (2, 0, 0)
result = client.call("add_primitive", ptype="SPHERE", location=[2, 0, 0])
print(f"Created: {result['name']}")

# Move the object
client.call("set_object_location", name=result["name"], location=[3, 1, 0])

# Delete it
client.call("delete_object", name=result["name"])

client.disconnect()
```

## Using the Action System

Wrap Blender operations as typed Actions via `ActionAdapter`:

```python
from dcc_mcp_ipc.action_adapter import get_action_adapter
from dcc_mcp_ipc.client import BaseDCCClient


def create_blender_adapter(host="localhost", port=18814):
    adapter = get_action_adapter("blender")
    client = BaseDCCClient("blender", host=host, port=port)
    client.connect()

    def _get_scene_info() -> dict:
        return client.call("get_scene_info")

    def _add_primitive(ptype: str = "SPHERE", location: list = None) -> dict:
        return client.call("add_primitive", ptype=ptype, location=location or [0, 0, 0])

    adapter.register_action(
        "blender_get_scene",
        _get_scene_info,
        description="Get current Blender scene metadata",
        category="scene",
        tags=["blender", "scene"],
    )
    adapter.register_action(
        "blender_add_primitive",
        _add_primitive,
        description="Add a mesh primitive to the Blender scene",
        category="modeling",
        tags=["blender", "mesh", "primitive"],
    )
    return adapter, client


adapter, client = create_blender_adapter()

result = adapter.call_action("blender_get_scene")
print(result.success, result.to_dict())

result = adapter.call_action("blender_add_primitive", ptype="CUBE", location=[0, 0, 1])
print(result.success, result.to_dict())

client.disconnect()
```

## E2E Testing with MockDCCService

For CI/CD pipelines where Blender is not available, use `MockDCCService` to simulate the Blender server:

```python
import pytest
from dcc_mcp_ipc.testing.mock_services import MockDCCService
from dcc_mcp_ipc.client import BaseDCCClient

BLENDER_TEST_PORT = 18814


@pytest.fixture(scope="module")
def blender_server():
    server = MockDCCService.start(port=BLENDER_TEST_PORT)
    yield server
    server.stop()


@pytest.fixture
def blender_client(blender_server):
    client = BaseDCCClient("blender", host="localhost", port=BLENDER_TEST_PORT)
    client.connect()
    yield client
    client.disconnect()


def test_get_dcc_info(blender_client):
    info = blender_client.get_dcc_info()
    assert isinstance(info, dict)


def test_connection_lifecycle(blender_server):
    client = BaseDCCClient("blender", host="localhost", port=BLENDER_TEST_PORT)
    client.connect()
    assert client.is_connected()
    client.disconnect()
    assert not client.is_connected()
```

See [`tests/e2e/test_blender_ipc.py`](https://github.com/loonghao/dcc-mcp-ipc/blob/main/tests/e2e/test_blender_ipc.py) for the full E2E test suite.

## Tips

- **Port convention**: Blender uses port `18814` by convention. Maya uses `18812`, Houdini `18813`.
- **Threading**: Always start the RPyC server in a daemon thread so Blender's event loop is not blocked.
- **Service discovery**: Register the server with `ZeroConf` for automatic discovery by MCP clients on the same network.
- **Security**: `exposed_execute_python` allows arbitrary code execution — restrict it to local development only.
