# Service Discovery

Service discovery lets MCP clients automatically find running DCC servers without hardcoding host/port values. DCC-MCP-IPC supports two discovery strategies.

## Strategies

| Strategy | Class | How it works |
|----------|-------|--------------|
| **ZeroConf** | `ZeroConfDiscoveryStrategy` | Advertises/discovers via mDNS/DNS-SD on the local network |
| **File-based** | `FileDiscoveryStrategy` | Reads/writes a JSON registry file at a well-known path |

The `ServiceDiscoveryFactory` selects the strategy automatically based on availability:

```python
from dcc_mcp_ipc.discovery import ServiceDiscoveryFactory

factory = ServiceDiscoveryFactory()
strategy = factory.create()  # ZeroConf if available, else file-based
```

## ZeroConf Discovery

Requires the `zeroconf` extra:

```bash
pip install "dcc-mcp-ipc[zeroconf]"
```

### Server-side registration

```python
from dcc_mcp_ipc.discovery import ZeroConfDiscoveryStrategy

strategy = ZeroConfDiscoveryStrategy()
strategy.register("maya", "localhost", 18812, metadata={"version": "2025"})
```

### Client-side lookup

```python
services = strategy.discover("maya")
for svc in services:
    print(svc.dcc_name, svc.host, svc.port)
```

## File-based Discovery

Uses a JSON registry file stored in the OS config directory (resolved by `dcc_mcp_core.get_config_dir()`).

```python
from dcc_mcp_ipc.discovery import FileDiscoveryStrategy

strategy = FileDiscoveryStrategy()
strategy.register("maya", "localhost", 18812)

services = strategy.discover("maya")
```

The registry file lives at `{config_dir}/dcc_mcp_ipc/registry.json`.

## ServiceRegistry

`ServiceRegistry` is an in-memory store for discovered `ServiceInfo` objects:

```python
from dcc_mcp_ipc.discovery import ServiceRegistry, ServiceInfo

registry = ServiceRegistry()
registry.register(ServiceInfo(dcc_name="maya", host="localhost", port=18812))

info = registry.get("maya")
print(info.host, info.port)

registry.unregister("maya")
```

## ServiceInfo

```python
from dcc_mcp_ipc.discovery import ServiceInfo

info = ServiceInfo(
    dcc_name="maya",
    host="localhost",
    port=18812,
    metadata={"version": "2025", "os": "windows"},
)

print(info.dcc_name)  # "maya"
print(info.host)      # "localhost"
print(info.port)      # 18812
```

## Discovery in BaseDCCClient

`BaseDCCClient` uses discovery automatically when no explicit port is provided:

```python
from dcc_mcp_ipc.client import BaseDCCClient

# Auto-discover the Maya server
client = BaseDCCClient("maya", host="localhost")
client.connect()
```

## DEFAULT_REGISTRY_PATH

The default registry file path is exposed as a module constant:

```python
from dcc_mcp_ipc import DEFAULT_REGISTRY_PATH

print(DEFAULT_REGISTRY_PATH)  # e.g., ~/.config/dcc_mcp_ipc/registry.json
```
