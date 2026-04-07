# Quick Start

This guide shows you how to set up a DCC server inside a DCC application and connect to it from an MCP client.

## 1. Server-side: Inside your DCC application

Create and start an RPyC server inside your DCC (e.g., Maya):

```python
from dcc_mcp_ipc.server import create_dcc_server, DCCRPyCService


class MayaService(DCCRPyCService):
    def get_scene_info(self):
        """Return information about the current scene."""
        return {
            "name": "my_scene.ma",
            "objects": 42,
            "cameras": 2,
        }

    def exposed_execute_cmd(self, cmd_name, *args, **kwargs):
        """Execute a Maya MEL or Python command."""
        import maya.cmds as cmds
        return getattr(cmds, cmd_name)(*args, **kwargs)


# Create and start the server
server = create_dcc_server(
    dcc_name="maya",
    service_class=MayaService,
    port=18812,  # omit for automatic port selection
)
server.start(threaded=True)  # threaded=True avoids blocking Maya's main thread
print("Maya IPC server started")
```

## 2. Client-side: From your MCP server

Connect to the DCC from the MCP server process:

```python
from dcc_mcp_ipc.client import BaseDCCClient

client = BaseDCCClient("maya", host="localhost", port=18812)
client.connect()

scene = client.call("get_scene_info")
print(scene)  # {"name": "my_scene.ma", "objects": 42, "cameras": 2}

client.disconnect()
```

## 3. Using the Action System

For a higher-level approach with MCP tool semantics:

```python
from dcc_mcp_ipc.action_adapter import get_action_adapter

adapter = get_action_adapter("maya")


def create_sphere(radius: float = 1.0, name: str = "sphere1") -> dict:
    """Create a sphere in Maya."""
    import maya.cmds as cmds
    cmds.polySphere(r=radius, name=name)
    return {"success": True, "message": f"Created sphere '{name}' with radius {radius}"}


adapter.register_action(
    "create_sphere",
    create_sphere,
    description="Create a sphere primitive in Maya",
    category="modeling",
    tags=["primitive", "mesh"],
)

# Dispatch the action (parameters are JSON-serialised)
result = adapter.call_action("create_sphere", radius=2.0, name="mySphere")
print(result.success)  # True
print(result.message)  # "Created sphere 'mySphere' with radius 2.0"
print(result.to_dict())
```

## 4. Zero-code with Skills

The simplest approach — no Python code required:

```
my_skills/
  create_sphere/
    SKILL.md
    run.py
```

**`SKILL.md`:**
```markdown
---
name: create_sphere
description: Create a sphere primitive in Maya
category: modeling
tags:
  - primitive
  - mesh
parameters:
  radius:
    type: float
    default: 1.0
    description: Sphere radius
  name:
    type: string
    default: sphere1
    description: Object name
---
```

**`run.py`:**
```python
import maya.cmds as cmds

# Parameters are injected from SKILL.md schema
cmds.polySphere(r=radius, name=name)
result = {"success": True, "name": name}
```

```python
from dcc_mcp_ipc.skills import SkillManager
from dcc_mcp_ipc.action_adapter import get_action_adapter

adapter = get_action_adapter("maya")
mgr = SkillManager(adapter=adapter, dcc_name="maya")
mgr.load_paths(["./my_skills"])
mgr.start_watching()  # Enable hot-reload

result = adapter.call_action("create_sphere", radius=3.0, name="bigSphere")
```

## Next Steps

- [Architecture](./architecture) — understand the component design
- [Action System](./action-system) — deep dive into action registration and dispatch
- [Skills System](./skills) — zero-code tool registration
- [Transport Layer](./transports) — RPyC, HTTP, WebSocket, and IPC transports
