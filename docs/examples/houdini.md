# Houdini Integration

## Setup

Install `dcc-mcp-ipc` using Houdini's Python interpreter:

```bash
hython -m pip install dcc-mcp-ipc
```

## Server (Houdini Python Shell or startup script)

```python
from dcc_mcp_ipc.server import create_dcc_server, DCCRPyCService


class HoudiniService(DCCRPyCService):
    def exposed_get_scene_info(self, conn=None):
        import hou
        return {
            "file": hou.hipFile.path(),
            "nodes": len(hou.node("/obj").children()),
            "fps": hou.fps(),
        }

    def exposed_create_geo(self, name="geo1", conn=None):
        import hou
        obj = hou.node("/obj").createNode("geo", name)
        return {"success": True, "path": obj.path()}

    def exposed_execute_python(self, code, conn=None):
        local_vars = {}
        exec(code, {"hou": __import__("hou")}, local_vars)
        return local_vars.get("_result")


server = create_dcc_server(dcc_name="houdini", service_class=HoudiniService, port=18813)
server.start(threaded=True)
print("Houdini IPC server started on port 18813")
```

## Client

```python
from dcc_mcp_ipc.client import BaseDCCClient

client = BaseDCCClient("houdini", host="localhost", port=18813)
client.connect()

info = client.call("get_scene_info")
print(f"File: {info['file']}, Nodes: {info['nodes']}")

result = client.call("create_geo", name="myGeo")
print(f"Created: {result['path']}")

client.disconnect()
```
