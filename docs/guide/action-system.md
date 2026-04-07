# Action System

The Action System is the central mechanism for registering and dispatching callable operations (MCP tools) in DCC-MCP-IPC. It is backed by the Rust/PyO3 core from `dcc-mcp-core`.

## Overview

```
ActionAdapter
├── ActionRegistry (Rust)   — stores action metadata and handlers
└── ActionDispatcher (Rust) — dispatches calls with JSON-serialised params
```

`ActionResultModel` (from `dcc-mcp-core`) is the uniform return type for all dispatched calls.

## Getting an ActionAdapter

```python
from dcc_mcp_ipc.action_adapter import get_action_adapter

adapter = get_action_adapter("maya")  # cached singleton by name
```

`get_action_adapter(name)` returns the same instance every time for the same name.

## Registering Actions

```python
def create_sphere(radius: float = 1.0, name: str = "sphere1") -> dict:
    """Create a sphere primitive."""
    # Your DCC-specific implementation
    return {
        "success": True,
        "message": f"Created '{name}' with radius {radius}",
        "context": {"name": name, "radius": radius},
    }


adapter.register_action(
    "create_sphere",
    create_sphere,
    description="Create a sphere primitive in the scene",
    category="modeling",
    tags=["primitive", "mesh", "geometry"],
)
```

Parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Unique action identifier (used as MCP tool name) |
| `handler` | `Callable` | The function to call when dispatched |
| `description` | `str` | Human-readable description for MCP tool registration |
| `category` | `str` | Logical grouping (e.g., `"modeling"`, `"rendering"`) |
| `tags` | `list[str]` | Searchable tags |

## Dispatching Actions

```python
result = adapter.call_action("create_sphere", radius=2.0, name="mySphere")
```

All keyword arguments are JSON-serialised before being passed to the Rust dispatcher. The handler function receives them as normal Python arguments.

## ActionResultModel

All dispatched actions return an `ActionResultModel` from `dcc-mcp-core`:

```python
result = adapter.call_action("create_sphere", radius=2.0)

print(result.success)   # bool
print(result.message)   # str — human-readable message
print(result.error)     # str | None — error message if failed
print(result.context)   # dict — arbitrary return data

# Serialise to plain dict
data = result.to_dict()
```

> **Note**: In v2.0.0, `model_dump()` was renamed to `to_dict()`. Update any code using the old name.

## Error Handling

If the handler raises an exception, the dispatcher returns an `ActionResultModel` with `success=False` and the error message populated:

```python
def risky_action() -> dict:
    raise ValueError("Something went wrong")

adapter.register_action("risky", risky_action, description="A risky action")

result = adapter.call_action("risky")
print(result.success)  # False
print(result.error)    # "Something went wrong"
```

## Listing Available Actions

```python
actions = adapter.list_actions()
for action in actions:
    print(action.name, action.description, action.category)
```

## Best Practices

- **Use descriptive names** — action names become MCP tool names visible to the AI.
- **Document parameters** — include type hints and docstrings; they're surfaced in MCP tool schemas.
- **Return structured data** — always return a dict with `success`, `message`, and optionally `context`.
- **Categories** — group related actions with consistent category names for better discoverability.
