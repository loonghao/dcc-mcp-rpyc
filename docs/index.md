---
layout: home

hero:
  name: DCC-MCP-IPC
  text: Multi-protocol IPC for DCC + MCP
  tagline: Connect AI assistants to Maya, Houdini, Blender, Unreal Engine and more via Model Context Protocol
  image:
    src: /logo.svg
    alt: DCC-MCP-IPC
  actions:
    - theme: brand
      text: Get Started
      link: /guide/introduction
    - theme: alt
      text: View on GitHub
      link: https://github.com/loonghao/dcc-mcp-ipc

features:
  - icon: 🔌
    title: Protocol-agnostic
    details: RPyC for embedded-Python DCCs (Maya/Houdini/Blender), HTTP for Unreal/Unity, WebSocket, and Rust-native IPC for maximum throughput.

  - icon: ⚡
    title: Zero-code Skills
    details: Drop a SKILL.md file into a directory — SkillManager auto-registers it as an MCP tool. Hot-reload on file changes, no DCC restart needed.

  - icon: 🦀
    title: Rust-powered Core
    details: Action dispatch, validation, and telemetry handled by dcc-mcp-core (Rust/PyO3). Python layer focuses on DCC-specific glue code.

  - icon: 🔍
    title: Service Discovery
    details: ZeroConf (mDNS) + file-based fallback for automatic DCC server detection with no manual configuration.

  - icon: 🔄
    title: Connection Pooling
    details: ConnectionPool with auto-discovery for efficient client-side connection reuse and management.

  - icon: 🧪
    title: Testing-first
    details: MockDCCService lets you test your MCP integration without launching an actual DCC application.
---
