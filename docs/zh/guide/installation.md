# 安装

## 稳定版本

```bash
pip install dcc-mcp-ipc
```

或使用 Poetry：

```bash
poetry add dcc-mcp-ipc
```

## 从源码安装

```bash
git clone https://github.com/loonghao/dcc-mcp-ipc.git
cd dcc-mcp-ipc
poetry install
```

## 依赖说明

| 包名 | 版本要求 | 用途 |
|------|---------|------|
| `rpyc` | `>=6.0.0,<7.0.0` | RPyC 传输层（Maya、Blender、Houdini） |
| `dcc-mcp-core` | `^0.5.0` | 核心抽象和 Action 框架 |
| `zeroconf` | `>=0.38.0,<0.132.0` | mDNS/ZeroConf 服务发现 |

::: tip 提示
HTTP 传输仅使用 Python 内置的 `http.client`，Unreal Engine 和 Unity 集成无需额外依赖。
:::
