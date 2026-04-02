# API Reference — Transport

## `dcc_mcp_ipc.transport.base`

### `TransportState`
Connection state enum: `DISCONNECTED`, `CONNECTING`, `CONNECTED`, `ERROR`.

### `TransportConfig`
Pydantic model for transport configuration.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | `str` | `"localhost"` | Remote host |
| `port` | `int` | `0` | Remote port |
| `timeout` | `float` | `30.0` | Default timeout (seconds) |
| `retry_count` | `int` | `3` | Retry count on failure |
| `retry_delay` | `float` | `1.0` | Delay between retries |
| `metadata` | `dict` | `{}` | Protocol-specific options |

### `BaseTransport`
Abstract base class for all transports.

| Method | Description |
|--------|-------------|
| `connect()` | Establish connection |
| `disconnect()` | Close connection (idempotent) |
| `reconnect()` | Disconnect then connect |
| `health_check() -> bool` | Check if service is reachable |
| `execute(action, params, timeout) -> dict` | Execute a named action |
| `execute_python(code, context) -> Any` | Execute Python code remotely |
| `call_function(module, func, *args, **kwargs) -> Any` | Call a remote function |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `TransportError` | Base transport exception |
| `ConnectionError` | Connection failed or lost |
| `TimeoutError` | Operation timed out |
| `ProtocolError` | Remote protocol error |

## `dcc_mcp_ipc.transport.rpyc_transport`

### `RPyCTransportConfig(TransportConfig)`
| Field | Type | Default |
|-------|------|---------|
| `sync_request_timeout` | `float` | `30.0` |
| `allow_all_attrs` | `bool` | `True` |
| `allow_public_attrs` | `bool` | `True` |

### `RPyCTransport(BaseTransport)`
RPyC-based transport. Additional properties: `connection`, `root`, `rpyc_config`.

Additional methods: `import_module(module_name)`.

## `dcc_mcp_ipc.transport.http`

### `HTTPTransportConfig(TransportConfig)`
| Field | Type | Default |
|-------|------|---------|
| `base_path` | `str` | `""` |
| `use_ssl` | `bool` | `False` |
| `headers` | `dict` | `{"Content-Type": "application/json"}` |
| `action_endpoint` | `str` | `"/api/v1/action/{action}"` |

### `HTTPTransport(BaseTransport)`
HTTP-based transport for Unreal Engine and Unity.

Additional methods:
- `call_remote_object(object_path, function_name, params)` — UE Remote Control
- `get_remote_property(object_path, property_name)` — UE property read
- `set_remote_property(object_path, property_name, value)` — UE property write

## `dcc_mcp_ipc.transport.factory`

| Function | Description |
|----------|-------------|
| `register_transport(protocol, cls)` | Register a transport class |
| `create_transport(protocol, config)` | Create a new transport instance |
| `get_transport(protocol, host, port)` | Get or create a cached instance |
