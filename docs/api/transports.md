# Transports

## TransportFactory

```python
from dcc_mcp_ipc.transport import TransportFactory

transport = TransportFactory.create(
    protocol: str,   # "rpyc" | "ipc" | "http" | "websocket"
    host: str,
    port: int,
    **kwargs,
) -> BaseTransport
```

## IpcClientTransport / IpcServerTransport

```python
from dcc_mcp_ipc.transport.ipc_transport import (
    IpcClientTransport,
    IpcServerTransport,
    IpcTransportConfig,
)

# Client
config = IpcTransportConfig(host="localhost", port=19000)
client = IpcClientTransport(config)
client.connect()
result = client.execute("action_name", param=value)
client.disconnect()

# Server
server = IpcServerTransport(addr, handler=my_handler)
bound_addr = server.start()
server.stop()
```

## HttpTransport

```python
from dcc_mcp_ipc.transport.http import HttpTransport

t = HttpTransport(host="localhost", port=30010)
t.connect()
result = t.execute("get_scene_info")
t.disconnect()
```

## WebSocketTransport

```python
from dcc_mcp_ipc.transport.websocket import WebSocketTransport

t = WebSocketTransport(host="localhost", port=8765)
t.connect()
result = t.execute("list_actors")
t.disconnect()
```

## BaseTransport

All transports implement `BaseTransport`:

| Method | Description |
|--------|-------------|
| `connect()` | Establish connection |
| `disconnect()` | Close connection |
| `execute(method, **kwargs)` | Execute remote call |
| `is_connected` | `bool` property |
