# Maya Integration

## Setup

1. Install `dcc-mcp-ipc` in Maya's Python environment:

```bash
mayapy -m pip install dcc-mcp-ipc
```

2. Add the server startup to Maya's `userSetup.py`:

```python
# ~/maya/scripts/userSetup.py
import maya.utils as utils


def start_mcp_server():
    from dcc_mcp_ipc.server import create_dcc_server, DCCRPyCService

    class MayaService(DCCRPyCService):
        def exposed_execute_mel(self, command, conn=None):
            import maya.mel as mel
            return mel.eval(command)

        def exposed_execute_python(self, code, conn=None):
            local_vars = {}
            exec(code, {"cmds": __import__("maya.cmds", fromlist=["cmds"])}, local_vars)
            return local_vars.get("_result")

        def exposed_get_scene_info(self, conn=None):
            import maya.cmds as cmds
            return {
                "scene": cmds.file(query=True, sceneName=True) or "untitled",
                "objects": cmds.ls(type="transform"),
                "cameras": cmds.ls(type="camera"),
            }

        def exposed_create_object(self, obj_type, name=None, conn=None):
            import maya.cmds as cmds
            kwargs = {"name": name} if name else {}
            result = getattr(cmds, obj_type)(**kwargs)
            return {"success": True, "name": result[0] if isinstance(result, list) else result}

    server = create_dcc_server(dcc_name="maya", service_class=MayaService, port=18812)
    server.start(threaded=True)
    print("[dcc-mcp-ipc] Maya server started on port 18812")


utils.executeDeferred(start_mcp_server)
```

## Connecting from MCP Server

```python
from dcc_mcp_ipc.client import BaseDCCClient

client = BaseDCCClient("maya", host="localhost", port=18812)
client.connect()

# Execute MEL
client.call("execute_mel", "polySphere -r 1 -n mySphere;")

# Execute Python
client.call("execute_python", "import maya.cmds; maya.cmds.polySphere(); _result = 'done'")

# Get scene info
info = client.call("get_scene_info")
print(info)

client.disconnect()
```

## Maya Action Adapter

```python
from dcc_mcp_ipc.action_adapter import get_action_adapter
from dcc_mcp_ipc.client import BaseDCCClient

client = BaseDCCClient("maya", host="localhost", port=18812)
client.connect()
adapter = get_action_adapter("maya")


def create_primitive(ptype: str = "sphere", radius: float = 1.0, name: str = "shape1") -> dict:
    """Create a polygon primitive in Maya."""
    cmd_map = {"sphere": "polySphere", "cube": "polyCube", "cylinder": "polyCylinder"}
    cmd = cmd_map.get(ptype, "polySphere")
    return client.call("create_object", cmd, name=name)


adapter.register_action(
    "create_primitive",
    create_primitive,
    description="Create a polygon primitive in Maya",
    category="modeling",
    tags=["primitive", "polygon", "maya"],
)
```
