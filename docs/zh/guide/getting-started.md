# 快速开始

DCC-MCP-IPC 是 DCC-MCP 生态中的**通用 IPC 适配层**，提供协议无关的通信机制，连接 AI 助手与各种数字内容创作（DCC）软件。

## 生态架构

```
dcc-mcp-core              ← 核心协议、传输抽象、Action 框架
    ↑
dcc-mcp-ipc               ← 本项目：多协议通用 IPC 适配层
  ├── transport/           ← 协议无关传输抽象层（核心）
  │   ├── base.py          ← BaseTransport 抽象接口
  │   ├── rpyc_transport.py← RPyC 实现（Maya/Blender/Houdini）
  │   └── http.py          ← HTTP 实现（Unreal/Unity）
  ├── adapter/             ← DCC 适配器基类
  ├── server/              ← DCC 侧服务器基类
  ├── client/              ← MCP 侧客户端基类
  ├── discovery/           ← 服务发现（file、zeroconf、mdns）
  └── testing/             ← Mock 服务
    ↑
dcc-mcp-maya              ← Maya 具体实现（RPyC 协议）
dcc-mcp-unreal            ← Unreal Engine 实现（HTTP 协议）
```

## 协议选型矩阵

| DCC 软件 | 协议 | DCC 侧依赖 | 特殊限制 |
|---------|------|-----------|---------|
| Maya 2022-2025 | RPyC | `rpyc>=6.0.0` | 主线程限制 |
| Blender 3.x-4.x | RPyC | `rpyc>=6.0.0` | addon 生命周期 |
| Houdini 19-20 | RPyC | `rpyc>=6.0.0` | HOM 线程安全 |
| Unreal Engine 5.x | HTTP | **零依赖** | GameThread |
| Unity 2022+ | HTTP | **零依赖** | 主线程 |

## 快速示例

```python
from dcc_mcp_ipc.transport import create_transport
from dcc_mcp_ipc.transport.rpyc_transport import RPyCTransportConfig

# 通过 RPyC 连接 Maya
with create_transport("rpyc", config=RPyCTransportConfig(
    host="localhost", port=18812
)) as transport:
    result = transport.execute("list_actions")
    print(result)
```
