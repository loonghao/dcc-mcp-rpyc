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
│  │  │  SkillScanner   │  │ SkillWatcher (OS events)│ │   │
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
├── __init__.py              # Lazy-import public API (21 exports)
├── action_adapter.py        # ActionAdapter + get_action_adapter()
├── adapter/                 # DCCAdapter, ApplicationAdapter
├── client/                  # BaseDCCClient, ConnectionPool, AsyncDCCClient
├── server/                  # DCCServer, RPyC services, lifecycle helpers
├── transport/               # Factory helpers + RPyC/HTTP/WebSocket/IPC impl.
├── discovery/               # ServiceDiscoveryFactory, ZeroConf, file-based
├── skills/                  # SkillManager built on SkillScanner/SkillWatcher
├── scene/                   # Scene interface (RPyC + HTTP)
├── snapshot/                # Snapshot interface (RPyC + HTTP)
├── application/             # ApplicationAdapter/Service/Client
├── testing/                 # MockDCCService
└── utils/                   # Errors, DI, decorators, rpyc_utils
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
| `RPyCTransport` | RPyC (TCP) | Maya, Houdini, Blender, 3ds Max, Nuke |
| `IpcClientTransport` / `IpcServerTransport` | Rust FramedChannel (named pipe / TCP) | Rust-based DCC plugins |
| `HTTPTransport` | REST over HTTP | Unreal Engine, Unity |
| `WebSocketTransport` | WebSocket | Any WebSocket-capable DCC |

The transport package exposes `create_transport()`, `get_transport()`, and `register_transport()` helpers. Built-in registration currently covers `rpyc`, `http`, and `ipc`; `WebSocketTransport` is available directly and can be registered explicitly when factory-based construction is desired.


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
