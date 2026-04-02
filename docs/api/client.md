# API Reference — Client

## `dcc_mcp_ipc.client`

### `BaseApplicationClient`
Base client for connecting to application RPyC servers.

| Method | Description |
|--------|-------------|
| `connect(rpyc_connect_func=None) -> bool` | Connect to the server |
| `disconnect() -> bool` | Disconnect from the server |
| `reconnect() -> bool` | Reconnect |
| `is_connected() -> bool` | Check connection status |
| `execute_python(code, context) -> Any` | Execute Python remotely |
| `import_module(module_name) -> Any` | Import a remote module |
| `call_function(module, func, *args, **kwargs) -> Any` | Call a remote function |
| `list_actions() -> dict` | List available actions |
| `call_action(action_name, **kwargs) -> Any` | Call an action |

### `BaseDCCClient(BaseApplicationClient)`
DCC-specific client with additional methods for DCC operations.

### `AsyncBaseApplicationClient`
Async version of `BaseApplicationClient` using `asyncio`.

### `AsyncBaseDCCClient`
Async version of `BaseDCCClient`.

### `ConnectionPool`
Manages and reuses connections to DCC servers.

### `ClientRegistry`
Registry for tracking all created client instances.

### Factory Functions

| Function | Description |
|----------|-------------|
| `get_client(app_name, host, port)` | Get or create a client |
| `get_async_client(app_name, host, port)` | Get or create an async client |
| `close_all_connections()` | Close all sync client connections |
| `close_all_async_connections()` | Close all async client connections |
