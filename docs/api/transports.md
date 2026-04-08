# Transports

## Factory Helpers

```python
from dcc_mcp_ipc.transport import create_transport, get_transport, register_transport
from dcc_mcp_ipc.transport.rpyc_transport import RPyCTransportConfig
from dcc_mcp_ipc.transport.websocket import WebSocketTransport
from dcc_mcp_ipc.transport.websocket import WebSocketTransportConfig

transport = create_transport("rpyc", config=RPyCTransportConfig(host="localhost", port=18812))
cached_http = get_transport("http", host="localhost", port=30010)

register_transport("websocket", WebSocketTransport)
ws_transport = create_transport(
    "websocket",
    config=WebSocketTransportConfig(host="localhost", port=8765),
)
```

Built-in factory registration currently covers `rpyc`, `http`, and `ipc`. Use `register_transport()` for custom protocols or for `WebSocketTransport` when you want factory-based construction.

## IpcClientTransport / IpcServerTransport

```python
from dcc_mcp_core import TransportAddress
from dcc_mcp_ipc.transport.ipc_transport import (
    IpcClientTransport,
    IpcServerTransport,
    IpcTransportConfig,
)

config = IpcTransportConfig(host="localhost", port=19000)
client = IpcClientTransport(config)
client.connect()
result = client.execute("action_name", params={"value": 1})
client.disconnect()

addr = TransportAddress.default_local("maya", 12345)
server = IpcServerTransport(addr, handler=my_handler)
bound_addr = server.start()
server.stop()
```

## HTTPTransport

```python
from dcc_mcp_ipc.transport.http import HTTPTransport
from dcc_mcp_ipc.transport.http import HTTPTransportConfig

config = HTTPTransportConfig(host="localhost", port=30010, base_path="/remote")
transport = HTTPTransport(config)
transport.connect()
result = transport.execute("get_scene_info")
transport.disconnect()
```

## WebSocketTransport

```python
from dcc_mcp_ipc.transport.websocket import WebSocketTransport
from dcc_mcp_ipc.transport.websocket import WebSocketTransportConfig

config = WebSocketTransportConfig(host="localhost", port=8765, path="/ws")
transport = WebSocketTransport(config)
transport.connect()
result = transport.execute("list_actors")
transport.disconnect()
```

## BaseTransport

All transports implement `BaseTransport`:

| Method | Description |
|--------|-------------|
| `connect()` | Establish the underlying connection |
| `disconnect()` | Close the connection and release resources |
| `execute(action, params=None, timeout=None)` | Execute a remote action and return a result dict |
| `health_check()` | Probe whether the remote service is reachable |
| `is_connected` | `bool` property |

