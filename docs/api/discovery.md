# Discovery

## ServiceDiscoveryFactory

```python
from dcc_mcp_ipc.discovery import ServiceDiscoveryFactory

factory = ServiceDiscoveryFactory()
strategy = factory.create()  # Auto-selects ZeroConf or file-based
```

## FileDiscoveryStrategy

```python
from dcc_mcp_ipc.discovery import FileDiscoveryStrategy

strategy = FileDiscoveryStrategy()
strategy.register("maya", "localhost", 18812)
services = strategy.discover("maya")  # list[ServiceInfo]
strategy.unregister("maya", "localhost", 18812)
```

## ZeroConfDiscoveryStrategy

Requires `pip install "dcc-mcp-ipc[zeroconf]"`.

```python
from dcc_mcp_ipc.discovery import ZeroConfDiscoveryStrategy

strategy = ZeroConfDiscoveryStrategy()
strategy.register("maya", "localhost", 18812)
services = strategy.discover("maya")
strategy.unregister("maya", "localhost", 18812)
```

## ServiceRegistry

In-memory registry of `ServiceInfo` objects:

```python
from dcc_mcp_ipc.discovery import ServiceRegistry, ServiceInfo

registry = ServiceRegistry()
registry.register(ServiceInfo(dcc_name="maya", host="localhost", port=18812))
info = registry.get("maya")
registry.unregister("maya")
all_services = registry.list_all()  # list[ServiceInfo]
```

## ServiceInfo

```python
ServiceInfo(
    dcc_name: str,
    host: str,
    port: int,
    metadata: dict = {},
)
```
