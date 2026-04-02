# Getting Started

DCC-MCP-IPC is the **universal IPC adapter layer** in the DCC-MCP ecosystem. It provides protocol-agnostic communication between AI assistants and Digital Content Creation (DCC) software.

## What is DCC-MCP-IPC?

```
dcc-mcp-core              ← Core protocol, transport abstractions, Action framework
    ↑
dcc-mcp-ipc               ← This project: multi-protocol IPC adapter layer
  ├── transport/           ← Protocol-agnostic transport abstraction (core)
  │   ├── base.py          ← BaseTransport abstract interface
  │   ├── rpyc_transport.py← RPyC implementation (Maya/Blender/Houdini)
  │   └── http.py          ← HTTP implementation (Unreal/Unity)
  ├── adapter/             ← DCC adapter base classes
  ├── server/              ← DCC-side server base classes
  ├── client/              ← MCP-side client base classes
  ├── discovery/           ← Service discovery (file, zeroconf, mdns)
  └── testing/             ← Mock services for testing
    ↑
dcc-mcp-maya              ← Maya-specific implementation
dcc-mcp-blender           ← Blender-specific implementation
dcc-mcp-unreal            ← Unreal Engine implementation (HTTP)
```

## Protocol Selection Matrix

| DCC | Protocol | DCC-Side Dependency | Special Constraints |
|-----|----------|-------------------|-------------------|
| Maya 2022-2025 | RPyC | `rpyc>=6.0.0` | Main thread limitation |
| Blender 3.x-4.x | RPyC | `rpyc>=6.0.0` | Addon lifecycle |
| Houdini 19-20 | RPyC | `rpyc>=6.0.0` | HOM thread safety |
| 3ds Max 2024+ | RPyC | `rpyc>=6.0.0` | COM STA thread |
| Nuke 14+ | RPyC | `rpyc>=6.0.0` | Main thread UI |
| Unreal Engine 5.x | HTTP | **Zero dependency** | GameThread |
| Unity 2022+ | HTTP | **Zero dependency** | Main thread |

## Quick Example

```python
from dcc_mcp_ipc.transport import create_transport

# Connect to Maya via RPyC
transport = create_transport("rpyc", config=RPyCTransportConfig(
    host="localhost", port=18812
))
with transport:
    result = transport.execute("list_actions")
    print(result)

# Connect to Unreal via HTTP
transport = create_transport("http", config=HTTPTransportConfig(
    host="localhost", port=30010, base_path="/remote"
))
with transport:
    result = transport.execute("get_scene_info")
    print(result)
```
