# ActionAdapter

`ActionAdapter` is the central registry and dispatcher for MCP-callable actions. It wraps the Rust/PyO3 `ActionRegistry` and `ActionDispatcher` from `dcc-mcp-core`.

## Import

```python
from dcc_mcp_ipc.action_adapter import ActionAdapter, get_action_adapter
```

## Factory

```python
adapter = get_action_adapter("maya")  # Returns cached instance by name
```

`get_action_adapter(name: str) -> ActionAdapter`

Returns the same `ActionAdapter` instance for the same `name` (singleton per DCC name). Creates a new instance on first call.

## Methods

### `register_action`

```python
adapter.register_action(
    name: str,
    handler: Callable,
    description: str = "",
    category: str = "",
    tags: list[str] | None = None,
) -> None
```

Register a callable as a named action.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Unique action identifier |
| `handler` | `Callable` | Function to invoke when dispatched |
| `description` | `str` | Human-readable description (surfaced in MCP tool schema) |
| `category` | `str` | Logical grouping |
| `tags` | `list[str]` | Searchable tags |

### `call_action`

```python
result = adapter.call_action(name: str, **kwargs) -> ActionResultModel
```

Dispatch a registered action with keyword arguments. All arguments are JSON-serialised.

### `list_actions`

```python
actions = adapter.list_actions() -> list[ActionInfo]
```

Returns metadata for all registered actions.

### `unregister_action`

```python
adapter.unregister_action(name: str) -> None
```

Remove a registered action.

## ActionResultModel

All dispatched actions return an `ActionResultModel` from `dcc-mcp-core`:

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether the action completed successfully |
| `message` | `str` | Human-readable result message |
| `error` | `str \| None` | Error message if `success=False` |
| `context` | `dict` | Arbitrary return data from the handler |

```python
result = adapter.call_action("create_sphere", radius=2.0)
print(result.success)   # True
print(result.message)   # "..."
print(result.context)   # {...}
data = result.to_dict() # Plain dict serialization
```

> **Migration**: `model_dump()` was renamed to `to_dict()` in v2.0.0.
