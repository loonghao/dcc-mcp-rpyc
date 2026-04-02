# Transport Layer

The transport layer is the core abstraction that makes DCC-MCP-IPC protocol-agnostic. All transports implement the `BaseTransport` interface.

## BaseTransport Interface

```python
class BaseTransport(ABC):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def reconnect(self) -> None: ...
    def health_check(self) -> bool: ...
    def execute(self, action: str, params: dict = None, timeout: float = None) -> dict: ...
    def execute_python(self, code: str, context: dict = None) -> Any: ...
    def call_function(self, module: str, func: str, *args, **kwargs) -> Any: ...
```

All transports support the **context manager** protocol:

```python
with create_transport("rpyc", config=config) as transport:
    result = transport.execute("list_actions")
```

## RPyC Transport

For DCC applications with embedded Python interpreters (Maya, Blender, Houdini, 3ds Max, Nuke).

```python
from dcc_mcp_ipc.transport.rpyc_transport import RPyCTransport, RPyCTransportConfig

config = RPyCTransportConfig(
    host="localhost",
    port=18812,
    sync_request_timeout=30.0,
)
transport = RPyCTransport(config)
transport.connect()

# Execute a remote action
result = transport.execute("list_actions")

# Execute Python code remotely
transport.execute_python("import maya.cmds as cmds; cmds.sphere()")

# Import a remote module
cmds = transport.import_module("maya.cmds")
```

## HTTP Transport

For DCC applications with HTTP APIs (Unreal Engine Remote Control, Unity HttpListener).

```python
from dcc_mcp_ipc.transport.http import HTTPTransport, HTTPTransportConfig

config = HTTPTransportConfig(
    host="localhost",
    port=30010,
    base_path="/remote",
)
transport = HTTPTransport(config)
transport.connect()

# Call a UE Remote Control function
transport.call_remote_object(
    "/Game/MyActor",
    "SetActorLocation",
    {"NewLocation": {"X": 0, "Y": 0, "Z": 100}}
)

# Get a property
prop = transport.get_remote_property("/Game/MyActor", "ActorLocation")
```

## Transport Factory

Use the factory to create transports by protocol name:

```python
from dcc_mcp_ipc.transport import create_transport, get_transport

# Create a new transport
transport = create_transport("rpyc")

# Get a cached transport (reuses existing connections)
transport = get_transport("http", host="localhost", port=30010)
```

## Custom Transport

Implement your own transport by extending `BaseTransport`:

```python
from dcc_mcp_ipc.transport.base import BaseTransport, TransportConfig
from dcc_mcp_ipc.transport.factory import register_transport

class MyTransport(BaseTransport):
    def connect(self): ...
    def disconnect(self): ...
    def health_check(self): ...
    def execute(self, action, params=None, timeout=None): ...

register_transport("my_protocol", MyTransport)
```
