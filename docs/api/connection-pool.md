# ConnectionPool

`ConnectionPool` manages a pool of `BaseDCCClient` connections for efficient resource reuse.

## Import

```python
from dcc_mcp_ipc.client import ConnectionPool
```

## Constructor

```python
pool = ConnectionPool(
    max_connections: int = 5,
    connection_timeout: float = 10.0,
    idle_timeout: float = 300.0,
)
```

## Usage

```python
with pool.get_client("maya", host="localhost", port=18812) as client:
    result = client.call("get_scene_info")
# Connection automatically returned to pool
```

## Methods

| Method | Description |
|--------|-------------|
| `get_client(dcc_name, host, port)` | Context manager — acquires and returns a client |
| `close()` | Close all pooled connections |
| `size(dcc_name)` | Number of idle connections for a DCC |
