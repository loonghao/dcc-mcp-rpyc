# API Reference — Server

## `dcc_mcp_ipc.server`

### `BaseRPyCService(rpyc.SlaveService)`
Base RPyC service with `on_connect` / `on_disconnect` hooks.

### `ApplicationRPyCService(BaseRPyCService, ABC)`
Abstract base class defining the application service interface.

| Abstract Method | Description |
|----------------|-------------|
| `get_application_info() -> dict` | Return application metadata |
| `get_environment_info() -> dict` | Return Python environment info |
| `execute_python(code, context) -> Any` | Execute Python code |
| `import_module(module_name) -> Any` | Import a module |
| `call_function(module, func, *args, **kwargs) -> Any` | Call a function |

### `DCCRPyCService(ApplicationRPyCService)`
DCC-specific service with Action system integration.

### `DCCServer`
Manages the RPyC server lifecycle within a DCC application.

### Factory Functions

| Function | Description |
|----------|-------------|
| `create_dcc_server(dcc_name, port, ...)` | Create a DCC server |
| `create_raw_threaded_server(service, port, ...)` | Create a raw threaded server |
| `create_server(dcc_name, port)` | Create and configure a server |
| `start_server(server)` | Start a server |
| `stop_server(server)` | Stop a server |
| `is_server_running(server) -> bool` | Check if running |
