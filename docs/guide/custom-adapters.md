# Custom Adapters

`DCCAdapter` is an abstract base class for creating DCC-specific Python APIs. It wraps a `BaseDCCClient` and provides a clean interface for DCC operations.

## Creating a DCCAdapter

```python
from dcc_mcp_ipc.adapter import DCCAdapter
from dcc_mcp_ipc.client import BaseDCCClient


class MayaAdapter(DCCAdapter):
    def _initialize_client(self) -> None:
        """Create and configure the underlying client."""
        self.client = BaseDCCClient(
            dcc_name="maya",
            host=self.host,
            port=self.port,
            connection_timeout=self.connection_timeout,
        )

    # DCC-specific methods
    def create_sphere(self, radius: float = 1.0, name: str = "sphere1"):
        self.ensure_connected()
        assert self.client is not None
        return self.client.execute_dcc_command(f"polySphere -r {radius} -n {name};")

    def get_scene_info(self):
        self.ensure_connected()
        assert self.client is not None
        return self.client.call("get_scene_info")

    def list_objects(self, obj_type: str = "transform"):
        self.ensure_connected()
        assert self.client is not None
        return self.client.call("list_objects", obj_type=obj_type)
```

## Using the Adapter

```python
adapter = MayaAdapter(host="localhost", port=18812)
adapter.connect()

info = adapter.get_scene_info()
result = adapter.create_sphere(radius=2.0, name="bigSphere")

adapter.disconnect()
```

## ApplicationAdapter

For non-DCC applications (generic REST services, etc.), use `ApplicationAdapter`:

```python
from dcc_mcp_ipc.adapter import ApplicationAdapter

adapter = ApplicationAdapter(host="localhost", port=9000)
adapter.connect()
result = adapter.execute("some_action", param1="value")
```

## get_adapter() Factory

```python
from dcc_mcp_ipc import get_adapter

adapter = get_adapter("maya")  # returns a cached DCCAdapter instance
```

## DCCAdapter API Reference

| Method | Description |
|--------|-------------|
| `connect()` | Establish connection to the DCC server |
| `disconnect()` | Close the connection |
| `ensure_connected()` | Raises if not connected |
| `is_connected` | bool property |
| `_initialize_client()` | **Abstract** — implement to create `self.client` |

## ApplicationRPyCService

For server-side generic application services:

```python
from dcc_mcp_ipc.application import ApplicationRPyCService


class MyAppService(ApplicationRPyCService):
    def exposed_get_status(self):
        return {"status": "running", "uptime": 3600}
```
