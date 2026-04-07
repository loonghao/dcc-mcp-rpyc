# Blender Integration

## Setup

Install `dcc-mcp-ipc` in Blender's bundled Python:

```bash
# Find Blender's Python
/Applications/Blender.app/Contents/Resources/4.x/python/bin/python3.11 -m pip install dcc-mcp-ipc
```

## Server (Blender addon or script)

```python
import threading
from dcc_mcp_ipc.server import create_dcc_server, DCCRPyCService


class BlenderService(DCCRPyCService):
    def exposed_get_scene_info(self, conn=None):
        import bpy
        return {
            "file": bpy.data.filepath or "untitled",
            "objects": [obj.name for obj in bpy.data.objects],
            "frame": bpy.context.scene.frame_current,
        }

    def exposed_add_primitive(self, ptype="SPHERE", location=(0, 0, 0), conn=None):
        import bpy
        bpy.ops.mesh.primitive_uv_sphere_add(location=location)
        obj = bpy.context.object
        return {"success": True, "name": obj.name}

    def exposed_execute_python(self, code, conn=None):
        import bpy
        local_vars = {}
        exec(code, {"bpy": bpy}, local_vars)
        return local_vars.get("_result")


server = create_dcc_server(dcc_name="blender", service_class=BlenderService, port=18814)
thread = threading.Thread(target=lambda: server.start(threaded=False), daemon=True)
thread.start()
print("Blender IPC server started on port 18814")
```

## Client

```python
from dcc_mcp_ipc.client import BaseDCCClient

client = BaseDCCClient("blender", host="localhost", port=18814)
client.connect()

info = client.call("get_scene_info")
print(f"File: {info['file']}")
print(f"Objects: {info['objects']}")

result = client.call("add_primitive", ptype="SPHERE", location=[1, 0, 0])
print(f"Created: {result['name']}")

client.disconnect()
```
