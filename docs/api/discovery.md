# API Reference — Discovery

## `dcc_mcp_ipc.discovery`

### `ServiceInfo(BaseModel)`
Pydantic model for discovered service information.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Service name |
| `host` | `str` | Hostname or IP |
| `port` | `int` | Port number |
| `dcc_type` | `str` | DCC type (e.g., `"maya"`, `"houdini"`) |
| `metadata` | `dict` | Additional metadata |

### `ServiceDiscoveryStrategy(ABC)`
Abstract base class for discovery strategies.

| Method | Description |
|--------|-------------|
| `discover_services(service_type) -> list[ServiceInfo]` | Find services |
| `register_service(service_info) -> bool` | Register a service |
| `unregister_service(service_info) -> bool` | Unregister a service |

### `FileDiscoveryStrategy`
File-based service discovery using a local JSON registry.

### `ZeroConfDiscoveryStrategy`
mDNS/ZeroConf-based service discovery for LAN auto-detection.

### `ServiceRegistry`
Central registry that manages multiple discovery strategies.

### `ServiceDiscoveryFactory`
Factory for creating discovery strategy instances.
