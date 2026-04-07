# Architecture

## Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                   AI Assistant / MCP Client              │
└─────────────────────────┬───────────────────────────────┘
                          │ MCP protocol
┌─────────────────────────▼───────────────────────────────┐
│                      MCP Server                         │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   ActionAdapter                         │
│  ┌──────────────────┐    ┌──────────────────────────┐   │
│  │  ActionRegistry  │    │   ActionDispatcher        │   │
│  │  (Rust/PyO3)     │    │   (Rust/PyO3)            │   │
│  └──────────────────┘    └──────────────────────────┘   │
│               ▲                                          │
│               │  registers                               │
│  ┌────────────┴─────────────────────────────────────┐   │
│  │  SkillManager                                    │   │
│  │  ┌─────────────────┐  ┌────────────────────────┐ │   │
│  │  │  SkillScanner   │  │  SkillWatcher (FSEvents)│ │   │
│  │  └─────────────────┘  └────────────────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   RPyC Transport    IPC Transport    HTTP Transport
        │                 │                 │
   DCC Application   DCC Application  REST API
   (Maya/Houdini/    (Rust plugin)    (Unreal/Unity)
    Blender)
```

## Package Layout

```
src/dcc_mcp_ipc/
├── __init__.py              # Lazy-import public API (37 exports)
├── action_adapter.py         # ActionAdapter + get_action_adapter()
├── adapter/                  # DCCAdapter, ApplicationAdapter
├── client/                   # BaseDCCClient, ConnectionPool, AsyncDCCClient
├── server/                   # DCCServer, BaseRPyCService, factories
├── transport/                # Transport factory + RPyC/HTTP/WS/IPC impl.
├── discovery/                # ServiceDiscoveryFactory, ZeroConf, file-based
├── skills/                   # SkillManager, SkillScanner
├── scene/                    # Scene interface (RPyC + HTTP)
├── snapshot/                 # Snapshot interface (RPyC + HTTP)
├── application/              # ApplicationAdapter/Service/Client
├── testing/                  # MockDCCService
└── utils/                    # Errors, DI, decorators, rpyc_utils
```

## Layers

### 1. Action Layer (`action_adapter.py`)

The `ActionAdapter` is the central registry for callable operations:

- Wraps `ActionRegistry` (Rust) for storing handler metadata
- Wraps `ActionDispatcher` (Rust) for dispatching calls with JSON-serialised parameters
- Factory function `get_action_adapter(name)` returns a cached adapter per DCC name
- `ActionResultModel` (from `dcc-mcp-core`) is the uniform return type

### 2. Skills Layer (`skills/`)

`SkillManager` automates action registration from filesystem:

- `SkillScanner` walks directories looking for `SKILL.md` files
- `SkillWatcher` uses OS filesystem events (debounced) to detect changes
- Each skill corresponds to a `run.py` script executed with injected parameters
- Hot-reload: file changes trigger re-scan and re-registration without DCC restart

### 3. Transport Layer (`transport/`)

| Transport | Protocol | Target DCCs |
|-----------|----------|-------------|
| `RpycTransport` | RPyC (TCP) | Maya, Houdini, Blender, 3ds Max, Nuke |
| `IpcClientTransport` / `IpcServerTransport` | Rust FramedChannel (named pipe / Unix socket) | Rust-based DCC plugins |
| `HttpTransport` | REST over HTTP | Unreal Engine, Unity |
| `WebSocketTransport` | WebSocket | Any WebSocket-capable DCC |

The `TransportFactory` resolves the correct transport from a protocol string.

### 4. Discovery Layer (`discovery/`)

`ServiceDiscoveryFactory` selects a strategy:

- **ZeroConf** (`ZeroConfDiscoveryStrategy`): mDNS/DNS-SD — requires `zeroconf` extra
- **File-based** (`FileDiscoveryStrategy`): JSON registry file at `get_config_dir()` — cross-platform fallback

`ServiceRegistry` holds discovered `ServiceInfo` objects (DCC name, host, port, metadata).

### 5. Server Layer (`server/`)

- `DCCServer`: owns the RPyC `ThreadedServer`, manages start/stop lifecycle
- `BaseRPyCService`: abstract base for all RPyC services
- `DCCRPyCService`: concrete service with standard `exposed_*` API
- Factory functions: `create_service_factory`, `create_shared_service_instance`, `create_raw_threaded_server`
- Lifecycle helpers: `start_server`, `stop_server`, `is_server_running`

### 6. Client Layer (`client/`)

- `BaseDCCClient`: connects to a named DCC server via auto-discovery or explicit host/port
- `ConnectionPool`: manages a pool of `BaseDCCClient` connections
- `ClientRegistry`: global registry of all named clients
- `AsyncDCCClient` / `AsyncBaseClient`: asyncio variants for non-blocking operations

### 7. Adapter Layer (`adapter/`)

- `DCCAdapter`: abstract base — subclass and implement `_initialize_client()` for DCC-specific client setup
- `ApplicationAdapter`: generic app adapter for non-DCC use cases
- `get_adapter(name)` factory — returns cached adapter instance

## Data Flow: Action Dispatch

```
MCP Tool Call ("create_sphere", {radius: 2.0})
    │
    ▼
ActionAdapter.call_action("create_sphere", radius=2.0)
    │
    ▼
ActionDispatcher.dispatch("create_sphere", json_params)  [Rust]
    │
    ▼
Registered handler function:
    create_sphere(radius=2.0)
    │
    ▼
ActionResultModel(success=True, message="...", context={...})  [Rust]
    │
    ▼
Result returned to MCP client
```
