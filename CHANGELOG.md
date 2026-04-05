# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0](https://github.com/loonghao/dcc-mcp-ipc/compare/1.0.0...2.0.0) (2026-04-05)


### ⚠ BREAKING CHANGES

* migrate to dcc-mcp-core v0.12.0 Rust/PyO3 API

### Features

* migrate to dcc-mcp-core v0.12.0 Rust/PyO3 API ([da8fcc7](https://github.com/loonghao/dcc-mcp-ipc/commit/da8fcc750ff0ee3934d348af559add3d54162535))
* **skills:** add SkillManager for zero-code SKILL.md-based MCP tool registration ([da8fcc7](https://github.com/loonghao/dcc-mcp-ipc/commit/da8fcc750ff0ee3934d348af559add3d54162535))
* **transport:** add Rust-native IpcClientTransport and IpcServerTransport ([da8fcc7](https://github.com/loonghao/dcc-mcp-ipc/commit/da8fcc750ff0ee3934d348af559add3d54162535))


### Bug Fixes

* **deps:** trim dependencies to rpyc+dcc-mcp-core; make zeroconf optional extra ([cd4e8f0](https://github.com/loonghao/dcc-mcp-ipc/commit/cd4e8f07bfebc46296e904f194ccab051cbd2c62))


### Code Refactoring

* **action_adapter:** rewrite ActionAdapter with ActionRegistry+ActionDispatcher ([da8fcc7](https://github.com/loonghao/dcc-mcp-ipc/commit/da8fcc750ff0ee3934d348af559add3d54162535))
* update all imports and replace model_dump() -&gt; to_dict() globally ([da8fcc7](https://github.com/loonghao/dcc-mcp-ipc/commit/da8fcc750ff0ee3934d348af559add3d54162535))


### Documentation

* update README/README_zh and CHANGELOG for v2.0.0 ([da8fcc7](https://github.com/loonghao/dcc-mcp-ipc/commit/da8fcc750ff0ee3934d348af559add3d54162535))

## [Unreleased] — 2.0.0

### BREAKING CHANGES

- **dcc-mcp-core ≥ 0.12.0 required**: The core library has been fully rewritten
  from Python/Pydantic to Rust/PyO3. Minimum Python version raised to **3.9**.
- `ActionResultModel.model_dump()` → `ActionResultModel.to_dict()`.
- `dcc_mcp_core.models.ActionResultModel` → `dcc_mcp_core.ActionResultModel`.
- `dcc_mcp_core.actions.{base,manager}` removed; replaced by
  `ActionRegistry` + `ActionDispatcher`.
- `dcc_mcp_core.utils.filesystem.get_config_dir` replaced by
  `dcc_mcp_core.get_config_dir`.
- `ActionAdapter.set_action_search_paths()` removed; use
  `SkillManager.load_paths()` instead.

### Added

- **`transport/ipc_transport.py`**: `IpcClientTransport` and `IpcServerTransport`
  backed by the Rust-native `IpcListener` / `FramedChannel` / `connect_ipc` API.
  Registered as the `"ipc"` protocol in the transport factory.
- **`skills/` sub-package**: `SkillManager` wraps `SkillScanner` / `SkillWatcher`
  to auto-discover `SKILL.md`-based zero-code scripts and register them as MCP
  tools via `ActionAdapter`. Supports hot-reload and env-var path configuration.
- New test suite for `transport/ipc_transport.py` and `skills/`.

### Changed

- `ActionAdapter` completely rewritten to use `ActionRegistry` +
  `ActionDispatcher`; action dispatch parameters now JSON-serialised.
- `transport/__init__.py` exports `IpcClientTransport`, `IpcServerTransport`,
  `IpcTransportConfig`.
- `discovery/file_strategy.py` uses `dcc_mcp_core.get_config_dir` with OS fallback.
- `adapter/base.py` `action_paths` setter no longer calls
  `set_action_search_paths` (removed from `ActionAdapter`).



### BREAKING CHANGE

- Package renamed from dcc-mcp-rpyc to dcc-mcp-ipc to reflect
the project's evolution from an RPyC-only implementation to a multi-protocol
IPC adapter layer supporting RPyC, HTTP, and WebSocket transports.

### Feat

- **transport**: add protocol-agnostic transport abstraction layer

### Refactor

- rename dcc-mcp-rpyc to dcc-mcp-ipc

## 0.4.1 (2026-03-29)

### Fix

- FileDiscoveryStrategy overwrites same DCC type instances (#25)

## 0.4.0 (2025-04-01)

### Feat

- **discovery**: Implement service discovery module and strategies

### Refactor

- Refactor imports, methods, and discovery module

## 0.3.0 (2025-03-31)

### Feat

- Add mock DCC services and async client
- Implement Python adapters and server client example
- **parameters**: implement RPyC parameter handling and service factory

### Fix

- resolve DCC integration and Action system test issues
- add missing TypeVar import in server module

### Refactor

- Remove unused modules and update documentation
- move service factory functions to server module

## 0.2.1 (2025-03-24)

### Refactor

- **adapter**: Refactor action paths handling and improve docstrings

## 0.2.0 (2025-03-24)

### Feat

- Enhance client-server functionality and testing

## 0.1.2 (2025-03-20)

### Refactor

- Update README and add PyPI publish config

## 0.1.1 (2025-03-20)

### Refactor

- **release**: Automate release notes generation

## 0.1.0 (2025-03-20)

### Feat

- Update project setup and dependencies

## 0.0.1 (2025-03-18)
