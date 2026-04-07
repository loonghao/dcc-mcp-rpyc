# API Overview

The public API is exposed via `dcc_mcp_ipc` with lazy imports. All symbols listed below are importable from the top-level package.

## Exported Symbols

```python
from dcc_mcp_ipc import (
    # Actions
    ActionAdapter,

    # Adapters
    DCCAdapter,
    ApplicationAdapter,

    # Clients
    BaseDCCClient,
    BaseApplicationClient,
    ConnectionPool,
    ClientRegistry,

    # Servers
    DCCServer,
    BaseRPyCService,
    ApplicationRPyCService,

    # Discovery
    FileDiscoveryStrategy,
    ZeroConfDiscoveryStrategy,
    ServiceDiscoveryFactory,
    ServiceRegistry,
    ServiceInfo,

    # Convenience helpers
    get_adapter,
    get_client,
    start_server,
    stop_server,
    is_server_running,
    DEFAULT_REGISTRY_PATH,
)
```

## Module Reference

| Module | Key Exports |
|--------|-------------|
| `dcc_mcp_ipc.action_adapter` | `ActionAdapter`, `get_action_adapter` |
| `dcc_mcp_ipc.adapter` | `DCCAdapter`, `ApplicationAdapter`, `get_adapter` |
| `dcc_mcp_ipc.client` | `BaseDCCClient`, `ConnectionPool`, `ClientRegistry`, `get_client` |
| `dcc_mcp_ipc.client.async_dcc` | `AsyncDCCClient` |
| `dcc_mcp_ipc.server` | `DCCServer`, `BaseRPyCService`, `create_dcc_server`, `start_server`, `stop_server`, `is_server_running` |
| `dcc_mcp_ipc.server.factory` | `create_service_factory`, `create_shared_service_instance`, `create_raw_threaded_server` |
| `dcc_mcp_ipc.transport` | `TransportFactory`, `IpcClientTransport`, `IpcServerTransport` |
| `dcc_mcp_ipc.discovery` | `ServiceDiscoveryFactory`, `ServiceRegistry`, `ServiceInfo`, `FileDiscoveryStrategy`, `ZeroConfDiscoveryStrategy` |
| `dcc_mcp_ipc.skills` | `SkillManager` |
| `dcc_mcp_ipc.testing.mock_services` | `MockDCCService` |
| `dcc_mcp_ipc.utils.rpyc_utils` | `deliver_parameters`, `execute_remote_command` |
| `dcc_mcp_ipc.utils.errors` | `ActionError`, `handle_error` |

For detailed documentation on each component, see the individual API pages.
