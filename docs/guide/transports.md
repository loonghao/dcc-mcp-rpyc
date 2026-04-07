# Transport Layer

DCC-MCP-IPC supports multiple transport protocols. The `TransportFactory` selects the right transport from a protocol string.

## Available Transports

| Protocol | Class | Use Case |
|----------|-------|----------|
| `rpyc` | `RpycTransport` | DCCs with embedded Python (Maya, Houdini, Blender, 3ds Max, Nuke) |
| `ipc` | `IpcClientTransport` / `IpcServerTransport` | Rust-native framed channel; lowest latency |
| `http` | `HttpTransport` | REST-based DCCs (Unreal Engine, Unity) |
| `websocket` | `WebSocketTransport` | WebSocket-capable services |

## RPyC Transport

The default transport for Python-embedded DCCs.

```python
from dcc_mcp_ipc.server import create_dcc_server, DCCRPyCService
from dcc_mcp_ipc.client import BaseDCCClient

# Server side
server = create_dcc_server(dcc_name="maya", service_class=MayaService, port=18812)
server.start(threaded=True)

# Client side
client = BaseDCCClient("maya", host="localhost", port=18812)
client.connect()
result = client.call("get_scene_info")
client.disconnect()
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
    # process and respond
    channel.send({"result": "ok"})

addr = TransportAddress.default_local("maya", os.getpid())
server = IpcServerTransport(addr, handler=handle_channel)
bound_addr = server.start()
print(f"IPC server listening at: {bound_addr}")

# Client side
config = IpcTransportConfig(host="localhost", port=19000)
transport = IpcClientTransport(config)
transport.connect()
result = transport.execute("get_scene_info")
transport.disconnect()
```

## HTTP Transport

For DCCs that expose a REST API (e.g., Unreal Engine's Remote Control API, Unity's Editor API):

```python
from dcc_mcp_ipc.transport.http import HttpTransport

transport = HttpTransport(host="localhost", port=30010)
transport.connect()
result = transport.execute("get_scene_info")
transport.disconnect()
```

## WebSocket Transport

```python
from dcc_mcp_ipc.transport.websocket import WebSocketTransport

transport = WebSocketTransport(host="localhost", port=8765)
transport.connect()
result = transport.execute("list_actors")
transport.disconnect()
```

## Transport Factory

```python
from dcc_mcp_ipc.transport import TransportFactory

# protocol → transport instance
transport = TransportFactory.create("rpyc", host="localhost", port=18812)
transport = TransportFactory.create("ipc", host="localhost", port=19000)
transport = TransportFactory.create("http", host="localhost", port=30010)
```

## Choosing a Transport

```
Is the DCC's scripting API accessible via Python in the same process?
    → RPyC transport (most DCCs)

Does the DCC expose a REST API?
    → HTTP transport (Unreal Engine Remote Control, Unity Editor API)

Do you need minimum latency with a Rust-based plugin?
    → IPC transport

Does the DCC use WebSockets for its API?
    → WebSocket transport
```
