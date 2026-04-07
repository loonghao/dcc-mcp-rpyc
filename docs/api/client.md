# BaseDCCClient

`BaseDCCClient` is the core client for connecting to and calling DCC servers.

## Import

```python
from dcc_mcp_ipc.client import BaseDCCClient, get_client
```

## Constructor

```python
client = BaseDCCClient(
    dcc_name: str,
    host: str = "localhost",
    port: int | None = None,         # None = auto-discover
    connection_timeout: float = 10.0,
)
```

## Methods

| Method | Description |
|--------|-------------|
| `connect()` | Establish RPyC connection (auto-discovers port if not set) |
| `disconnect()` | Close the connection |
| `call(method, *args, **kwargs)` | Call a remote `exposed_<method>` on the service |
| `execute_dcc_command(cmd)` | Execute a string command in the DCC |
| `get_dcc_info()` | Retrieve DCC version/platform info |
| `is_connected` | `bool` property |
| `ensure_connected()` | Raise if not connected |

## get_client Factory

```python
from dcc_mcp_ipc import get_client

client = get_client("maya")  # returns cached client by name
```

## ClientRegistry

```python
from dcc_mcp_ipc.client import ClientRegistry

ClientRegistry.register("maya_local", host="localhost", port=18812)
client = ClientRegistry.get("maya_local")
```

## AsyncDCCClient

For asyncio-based usage:

```python
from dcc_mcp_ipc.client.async_dcc import AsyncDCCClient

client = AsyncDCCClient("maya", host="localhost", port=18812)
await client.connect()
result = await client.call("get_scene_info")
await client.disconnect()
```
