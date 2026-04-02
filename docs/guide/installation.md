# Installation

## Stable Release

```bash
pip install dcc-mcp-ipc
```

Or with Poetry:

```bash
poetry add dcc-mcp-ipc
```

## From Source

```bash
git clone https://github.com/loonghao/dcc-mcp-ipc.git
cd dcc-mcp-ipc
poetry install
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `rpyc` | `>=6.0.0,<7.0.0` | RPyC transport (Maya, Blender, Houdini) |
| `dcc-mcp-core` | `^0.5.0` | Core abstractions and Action framework |
| `zeroconf` | `>=0.38.0,<0.132.0` | mDNS/ZeroConf service discovery |

::: tip
The HTTP transport uses only Python's built-in `http.client` — no extra dependencies needed for Unreal Engine or Unity integration.
:::
