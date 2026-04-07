# Introduction

**DCC-MCP-IPC** is a multi-protocol IPC adapter layer that bridges DCC (Digital Content Creation) applications — such as Maya, Houdini, Blender, Unreal Engine, and Unity — with the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

It is built on top of **[dcc-mcp-core](https://pypi.org/project/dcc-mcp-core/)** (a Rust/PyO3 backend) and exposes DCC functionality as MCP tools via pluggable transport protocols.

## What Problem Does It Solve?

AI assistants (Claude, GPT-4, etc.) can use MCP tools to interact with external software. However, DCC applications each have their own scripting APIs, inter-process communication mechanisms, and plugin models. Without a unified adapter, you'd need a separate MCP integration for each DCC.

DCC-MCP-IPC provides:

1. **A single API surface** — `ActionAdapter`, `SkillManager`, transports — regardless of the underlying DCC or protocol.
2. **Zero-code skill registration** — write a `SKILL.md` file instead of a full Python MCP tool implementation.
3. **Performance** — Rust-native IPC transport for latency-sensitive operations; RPyC for DCC-embedded Python; HTTP/WebSocket for REST-based DCCs.

## How It Works

```
AI Assistant (MCP Client)
        ↓
    MCP Server
        ↓
  ActionAdapter  ←──  SkillManager (SKILL.md auto-discovery)
        ↓
  Transport Layer
    ├── RPyC   → Maya / Houdini / Blender (embedded Python)
    ├── IPC    → Rust-native FramedChannel (low-latency)
    ├── HTTP   → Unreal Engine / Unity (REST API)
    └── WS     → WebSocket-based services
```

The **ActionAdapter** wraps the Rust `ActionRegistry` and `ActionDispatcher` from `dcc-mcp-core`. Actions are registered with a name, handler function, description, category, and tags. When an MCP tool call arrives, the adapter dispatches it with JSON-serialised parameters.

The **SkillManager** makes this even simpler: drop a `SKILL.md` file with frontmatter metadata into a directory, and the `SkillScanner` automatically registers it as an action. The `SkillWatcher` watches for file changes and hot-reloads skills without restarting the DCC.

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Action** | A named callable registered with the `ActionAdapter`. Has description, category, and tags. |
| **Skill** | A zero-code action defined by a `SKILL.md` file. Executed via `run.py` in the same directory. |
| **Transport** | The protocol used to communicate between the MCP server and the DCC. |
| **Adapter** | A `DCCAdapter` wraps a `BaseDCCClient` to provide a DCC-specific Python API. |
| **Service** | A `DCCRPyCService` or `ApplicationRPyCService` runs inside the DCC and handles RPC calls. |
| **Discovery** | Mechanisms for MCP clients to find running DCC servers (ZeroConf or file-based). |

## Version 2.0.0 Changes

v2.0.0 is the current unreleased version with significant breaking changes:

- **dcc-mcp-core ≥ 0.12.0 required** — fully rewritten from Python/Pydantic to Rust/PyO3.
- `ActionResultModel.model_dump()` → `ActionResultModel.to_dict()`
- `ActionRegistry` + `ActionDispatcher` replace old `actions.base` / `actions.manager` modules.
- New **Rust-native IPC transport** (`IpcClientTransport`, `IpcServerTransport`).
- New **Skills system** (`SkillManager`, `SkillScanner`, `SkillWatcher`).
- Package renamed from `dcc-mcp-rpyc` → `dcc-mcp-ipc`.

See the full [CHANGELOG](https://github.com/loonghao/dcc-mcp-ipc/blob/main/CHANGELOG.md) for details.

## Next Steps

- [Installation](./installation) — Install the package and its dependencies.
- [Quick Start](./quickstart) — Server + client in 5 minutes.
- [Architecture](./architecture) — Deep dive into the component design.
