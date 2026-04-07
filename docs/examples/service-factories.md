# Service Factories

Service factories give you control over how service instances are created for each connection.

## Pattern 1: Per-connection Instance

Each client connection gets its own service instance. Use this when services hold connection-specific state:

```python
from dcc_mcp_ipc.server import create_service_factory, create_raw_threaded_server, DCCRPyCService


class SessionManager:
    def __init__(self):
        self.active_selections = []


class MayaService(DCCRPyCService):
    def __init__(self, session_manager):
        self.sessions = session_manager

    def exposed_select(self, obj_name, conn=None):
        self.sessions.active_selections.append(obj_name)
        return {"selected": obj_name}


shared_manager = SessionManager()
service_factory = create_service_factory(MayaService, shared_manager)
server = create_raw_threaded_server(service_factory, port=18812)
server.start()
```

## Pattern 2: Shared Instance

All connections share a single service instance. Use this for stateless services or when sharing a thread-safe resource:

```python
from dcc_mcp_ipc.server import create_shared_service_instance, create_raw_threaded_server


shared_service = create_shared_service_instance(MayaService, shared_manager)
server = create_raw_threaded_server(shared_service, port=18812)
server.start()
```

## Pattern 3: Module-level Lifecycle Helpers

```python
from dcc_mcp_ipc.server import start_server, stop_server, is_server_running


start_server("maya", MayaService, port=18812)
print(is_server_running("maya"))  # True

stop_server("maya")
print(is_server_running("maya"))  # False
```

## When to Use Each Pattern

| Pattern | Use When |
|---------|----------|
| Per-connection | Service holds per-connection state (selections, undo history, etc.) |
| Shared | Service is stateless or wraps a thread-safe shared resource |
| Module-level helpers | You want a simple global server registry |
