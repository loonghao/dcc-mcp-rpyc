# DCCServer

`DCCServer` manages the RPyC server lifecycle inside a DCC process.

## Import

```python
from dcc_mcp_ipc.server import (
    DCCServer,
    DCCRPyCService,
    BaseRPyCService,
    create_dcc_server,
    create_service_factory,
    create_shared_service_instance,
    create_raw_threaded_server,
    start_server,
    stop_server,
    is_server_running,
)
```

## create_dcc_server

```python
server = create_dcc_server(
    dcc_name: str,
    service_class: type[BaseRPyCService],
    port: int = 0,           # 0 = pick random available port
    host: str = "localhost",
) -> DCCServer
```

Convenience factory for the common case.

## DCCServer

```python
server.start(threaded: bool = True) -> None
server.stop() -> None
server.is_running() -> bool
server.port  # int — actual bound port
```

## BaseRPyCService / DCCRPyCService

Subclass `DCCRPyCService` to implement your DCC service:

```python
from dcc_mcp_ipc.server import DCCRPyCService


class MayaService(DCCRPyCService):
    def exposed_get_scene_info(self, conn=None):
        return {"scene": "my_scene.ma"}

    def exposed_execute_cmd(self, cmd_name, *args, **kwargs):
        import maya.cmds as cmds
        return getattr(cmds, cmd_name)(*args, **kwargs)
```

All public methods must be prefixed with `exposed_` to be callable via RPyC.

## Service Factories

### create_service_factory

Creates a new service instance per connection:

```python
factory = create_service_factory(MayaService, shared_manager)
server = create_raw_threaded_server(factory, port=18812)
server.start()
```

### create_shared_service_instance

All connections share a single service instance:

```python
shared = create_shared_service_instance(MayaService, shared_manager)
```

### create_raw_threaded_server

Direct `ThreadedServer` creation:

```python
server = create_raw_threaded_server(service_or_factory, port=18812)
server.start()
```

## Module-level Lifecycle Helpers

```python
start_server("maya", MayaService, port=18812)
is_server_running("maya")  # True
stop_server("maya")
```
