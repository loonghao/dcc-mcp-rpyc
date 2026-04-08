# Transport Layer

DCC-MCP-IPC ships four concrete transport implementations. The `dcc_mcp_ipc.transport` package exports factory helpers for the built-in protocols and direct classes for IPC/WebSocket usage.

## Available Transports

| Protocol | Class | Factory Registration | Use Case |
|----------|-------|----------------------|----------|
| `rpyc` | `RPyCTransport` | Built in | DCCs with embedded Python (Maya, Houdini, Blender, 3ds Max, Nuke) |
| `ipc` | `IpcClientTransport` / `IpcServerTransport` | Built in | Rust-native framed channel; lowest latency |
| `http` | `HTTPTransport` | Built in | REST-based DCCs (Unreal Engine, Unity) |
| `websocket` | `WebSocketTransport` | Manual registration or direct instantiation | WebSocket-capable services |

## RPyC Transport

The default transport for Python-embedded DCCs.

```python
from dcc_mcp_ipc.transport.rpyc_transport import RPyCTransport
from dcc_mcp_ipc.transport.rpyc_transport import RPyCTransportConfig

config = RPyCTransportConfig(host="localhost", port=18812)
transport = RPyCTransport(config)
transport.connect()
result = transport.execute("get_scene_info")
transport.disconnect()
```

## Rust-native IPC Transport

Zero-copy, low-latency messaging via the Rust `IpcListener` / `FramedChannel` / `connect_ipc` API. Ideal for high-frequency calls or large data payloads.

```python
import os
from dcc_mcp_core import TransportAddress
from dcc_mcp_ipc.transport.ipc_transport import (
    IpcClientTransport,
    IpcServerTransport,
    IpcTransportConfig,
)

# Server side (inside DCC plugin / Rust process)
def handle_channel(channel):
    msg = channel.recv()
    channel.send({"success": True, "echo": msg})

addr = TransportAddress.default_local("maya", os.getpid())
server = IpcServerTransport(addr, handler=handle_channel)
server.start()

# Client side
config = IpcTransportConfig(host="localhost", port=19000)
transport = IpcClientTransport(config)
transport.connect()
result = transport.execute("get_scene_info")
transport.disconnect()
```

## HTTP Transport

For DCCs that expose a REST API (for example Unreal Engine Remote Control):

```python
from dcc_mcp_ipc.transport.http import HTTPTransport
from dcc_mcp_ipc.transport.http import HTTPTransportConfig

config = HTTPTransportConfig(host="localhost", port=30010, base_path="/remote")
transport = HTTPTransport(config)
transport.connect()
result = transport.execute("get_scene_info")
transport.disconnect()
```

## WebSocket Transport

```python
from dcc_mcp_ipc.transport.websocket import WebSocketTransport
from dcc_mcp_ipc.transport.websocket import WebSocketTransportConfig

config = WebSocketTransportConfig(host="localhost", port=8765, path="/ws")
transport = WebSocketTransport(config)
transport.connect()
result = transport.execute("list_actors")
transport.disconnect()
```

## Factory Helpers

```python
from dcc_mcp_ipc.transport import create_transport, get_transport, register_transport
from dcc_mcp_ipc.transport.rpyc_transport import RPyCTransportConfig
from dcc_mcp_ipc.transport.websocket import WebSocketTransport
from dcc_mcp_ipc.transport.websocket import WebSocketTransportConfig

transport = create_transport("rpyc", config=RPyCTransportConfig(host="localhost", port=18812))
cached_http = get_transport("http", host="localhost", port=30010)

# WebSocket is available as a class but is not auto-registered.
register_transport("websocket", WebSocketTransport)
ws_transport = create_transport(
    "websocket",
    config=WebSocketTransportConfig(host="localhost", port=8765),
)
```

`create_transport()` and `get_transport()` auto-register the built-in `rpyc`, `http`, and `ipc` protocols on import. Register additional transports explicitly when you need factory-based construction for custom implementations.

## Choosing a Transport

```
Is the DCC's scripting API accessible via Python in the same process?
    → RPyC transport (most DCCs)

Does the DCC expose a REST API?
    → HTTP transport (for example Unreal Engine Remote Control)

Do you need minimum latency with a Rust-based plugin?
    → IPC transport

Does the DCC use WebSockets for streaming or event push?
    → WebSocket transport
```

