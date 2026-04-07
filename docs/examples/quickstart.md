# Quick Start Example

A minimal end-to-end example: a DCC server and an MCP client.

## Server (runs inside DCC)

```python
# maya_server.py — run inside Maya's script editor or startup hook
from dcc_mcp_ipc.server import create_dcc_server, DCCRPyCService


class MayaService(DCCRPyCService):
    def exposed_get_scene_info(self, conn=None):
        import maya.cmds as cmds
        return {
            "scene": cmds.file(query=True, sceneName=True),
            "objects": len(cmds.ls()),
        }

    def exposed_create_sphere(self, radius=1.0, name="sphere1", conn=None):
        import maya.cmds as cmds
        cmds.polySphere(r=radius, name=name)
        return {"success": True, "name": name}


server = create_dcc_server(dcc_name="maya", service_class=MayaService, port=18812)
server.start(threaded=True)
print("Maya IPC server started on port 18812")
```

## Client (runs in MCP server process)

```python
# mcp_handler.py
from dcc_mcp_ipc.client import BaseDCCClient

client = BaseDCCClient("maya", host="localhost", port=18812)
client.connect()

info = client.call("get_scene_info")
print(f"Scene: {info['scene']}, Objects: {info['objects']}")

result = client.call("create_sphere", radius=2.0, name="bigSphere")
print(f"Created: {result['name']}")

client.disconnect()
```

## Using Action System

```python
# actions.py — register MCP tools as named actions
from dcc_mcp_ipc.action_adapter import get_action_adapter
from dcc_mcp_ipc.client import BaseDCCClient

client = BaseDCCClient("maya", host="localhost", port=18812)
client.connect()

adapter = get_action_adapter("maya")


def create_sphere(radius: float = 1.0, name: str = "sphere1") -> dict:
    return client.call("create_sphere", radius=radius, name=name)


adapter.register_action(
    "maya_create_sphere",
    create_sphere,
    description="Create a sphere in Maya",
    category="modeling",
    tags=["primitive", "mesh"],
)

result = adapter.call_action("maya_create_sphere", radius=3.0)
print(result.to_dict())
```
