---
layout: home

hero:
  name: DCC-MCP-IPC
  text: Multi-Protocol IPC for DCC Software
  tagline: Protocol-agnostic communication layer between AI assistants and Digital Content Creation applications
  image:
    src: /logo.svg
    alt: DCC-MCP-IPC
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/loonghao/dcc-mcp-ipc

features:
  - icon: 🔌
    title: Protocol Agnostic
    details: Support RPyC, HTTP, and WebSocket transports. Upper-level code never sees the underlying protocol.
  - icon: 🎨
    title: Multi-DCC Support
    details: Maya, Blender, Houdini, 3ds Max, Nuke (RPyC), Unreal Engine (HTTP), Unity (HTTP).
  - icon: 🤖
    title: MCP Integration
    details: Expose unified MCP Tools (screenshot, scene info, execute action) for AI-driven DCC control.
  - icon: 🔍
    title: Service Discovery
    details: Automatic discovery via file registry, ZeroConf/mDNS, or Unreal Remote Control auto-detection.
  - icon: ⚡
    title: Zero Dependency (DCC Side)
    details: HTTP transport requires no extra Python packages on the DCC side — perfect for Unreal and Unity.
  - icon: 🧪
    title: Mock Services
    details: Built-in MockDCCService for testing without actual DCC applications.
---
