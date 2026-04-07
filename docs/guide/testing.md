# Testing

DCC-MCP-IPC provides `MockDCCService` so you can test your MCP integration without launching an actual DCC application.

## MockDCCService

`MockDCCService` is a pre-built RPyC service that simulates a DCC application:

```python
import threading
import rpyc
from rpyc.utils.server import ThreadedServer
from dcc_mcp_ipc.testing.mock_services import MockDCCService
from dcc_mcp_ipc.client import BaseDCCClient

# Start mock server
server = ThreadedServer(
    MockDCCService,
    port=18812,
    protocol_config={"allow_public_attrs": True},
)
thread = threading.Thread(target=server.start, daemon=True)
thread.start()

# Connect a real client to the mock
client = BaseDCCClient("mock_dcc", host="localhost", port=18812)
client.connect()

info = client.get_dcc_info()
print(info)  # {"name": "mock_dcc", "version": "1.0.0", ...}

client.disconnect()
server.close()
```

## Writing Tests

```python
import pytest
import threading
import rpyc
from rpyc.utils.server import ThreadedServer
from dcc_mcp_ipc.testing.mock_services import MockDCCService
from dcc_mcp_ipc.client import BaseDCCClient


@pytest.fixture
def mock_server():
    server = ThreadedServer(
        MockDCCService,
        port=0,  # random available port
        protocol_config={"allow_public_attrs": True},
    )
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    yield server
    server.close()


def test_get_dcc_info(mock_server):
    client = BaseDCCClient("mock_dcc", host="localhost", port=mock_server.port)
    client.connect()
    info = client.get_dcc_info()
    assert info["name"] == "mock_dcc"
    client.disconnect()
```

## Custom Mock Services

Extend `MockDCCService` to add DCC-specific mock behaviour:

```python
import rpyc
from dcc_mcp_ipc.testing.mock_services import MockDCCService


class MockMayaService(MockDCCService):
    def exposed_get_scene_info(self, conn=None):
        return {
            "name": "test_scene.ma",
            "objects": ["pSphere1", "pCube1"],
            "cameras": ["persp", "front"],
        }

    def exposed_create_sphere(self, radius=1.0, name="sphere1", conn=None):
        return {
            "success": True,
            "name": name,
            "radius": radius,
        }
```

## Testing Action Adapters

```python
from dcc_mcp_ipc.action_adapter import get_action_adapter


def test_action_registration():
    adapter = get_action_adapter("test_dcc")

    def my_action(value: int = 0) -> dict:
        return {"result": value * 2}

    adapter.register_action(
        "double",
        my_action,
        description="Double a value",
        category="math",
    )

    result = adapter.call_action("double", value=5)
    assert result.success
    assert result.context["result"] == 10
```

## Running the Test Suite

```bash
nox -s pytest
```

The test suite has 68 test files organized to mirror the source layout.
