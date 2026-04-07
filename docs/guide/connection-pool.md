# Connection Pool

`ConnectionPool` manages a pool of `BaseDCCClient` connections for efficient resource reuse. It is useful when your MCP server handles many concurrent requests to the same DCC application.

## Basic Usage

```python
from dcc_mcp_ipc.client import ConnectionPool

pool = ConnectionPool()

# Acquire a client (creates new if none available)
with pool.get_client("maya", host="localhost", port=18812) as client:
    result = client.call("get_scene_info")
    print(result)
# Connection is automatically returned to the pool
```

## Configuration

```python
pool = ConnectionPool(
    max_connections=10,       # max connections per DCC name
    connection_timeout=30.0,  # seconds to wait for a connection
    idle_timeout=300.0,       # seconds before idle connections are closed
)
```

## ClientRegistry

`ClientRegistry` provides a global named registry of clients:

```python
from dcc_mcp_ipc.client import ClientRegistry, get_client

# Register a named client
ClientRegistry.register("maya_prod", host="maya-server-01", port=18812)

# Retrieve by name
client = get_client("maya_prod")
client.connect()
result = client.call("get_scene_info")
```

## Best Practices

- Use a single `ConnectionPool` instance per process (make it a module-level singleton or inject it via DI).
- Use the context manager (`with pool.get_client(...)`) to ensure connections are always returned.
- Set `max_connections` to match the number of worker threads in your MCP server.
