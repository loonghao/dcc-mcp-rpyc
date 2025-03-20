# DCC-MCP-RPYC

<div align="center">
    <img src="https://raw.githubusercontent.com/loonghao/dcc-mcp-rpyc/main/logo.svg" alt="DCC-MCP-RPYC Logo" width="200"/>

[![PyPI version](https://badge.fury.io/py/dcc-mcp-rpyc.svg)](https://badge.fury.io/py/dcc-mcp-rpyc)
[![Build Status](https://github.com/loonghao/dcc-mcp-rpyc/workflows/Build%20and%20Release/badge.svg)](https://github.com/loonghao/dcc-mcp-rpyc/actions)
[![Python Version](https://img.shields.io/pypi/pyversions/dcc-mcp-rpyc.svg)](https://pypi.org/project/dcc-mcp-rpyc/)
[![License](https://img.shields.io/github/license/loonghao/dcc-mcp-rpyc.svg)](https://github.com/loonghao/dcc-mcp-rpyc/blob/main/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/ruff-enabled-brightgreen)](https://github.com/astral-sh/ruff)
[![Downloads](https://static.pepy.tech/badge/dcc-mcp-rpyc)](https://pepy.tech/project/dcc-mcp-rpyc)
</div>

[English](README.md) | [中文](README_zh.md)

基于 RPyC 实现的数字内容创建 (DCC) 软件与模型上下文协议 (MCP) 的集成框架。该包提供了通过 RPYC 暴露 DCC 功能的框架，允许远程控制 DCC 应用程序。

## 为什么选择 RPyC？

RPyC（远程 Python 调用）为 DCC 软件集成提供了显著的优势：

- **动态接口暴露**：RPyC 能够动态地暴露 DCC 应用程序内的接口，通过消除创建静态 API 包装器的需求，减少了开发工作量。
- **原生 API 访问**：能够直接使用原生 DCC API，如 Maya 的 `cmds`/`pymel`、Houdini 的 `hou`、Blender 的 `bpy` 和 Nuke 的 Python API，无需额外的转换层。
- **透明的远程执行**：为本地执行编写的代码可以通过最小的更改远程运行，保留了开发者体验。
- **减少样板代码**：与其他进程间通信方法相比，最小化了进程间通信所需的重复代码。
- **对象引用**：维护对远程对象的实时引用，允许跨进程边界进行自然的面向对象编程。

通过利用 RPyC，DCC-MCP-RPYC 提供了一个统一的框架，在启用远程控制功能的同时保留了每个 DCC 原生 API 的使用体验。

## 特性

- 为 DCC 应用程序提供线程安全的 RPYC 服务器实现
- 提供服务发现机制，用于在网络上查找 DCC 服务
- 提供抽象基类，用于创建特定 DCC 的适配器和服务
- 支持多种 DCC 应用程序（Maya、Houdini、3ds Max、Nuke 等）
- 与模型上下文协议 (MCP) 集成，实现 AI 驱动的 DCC 控制

## 架构

DCC-MCP-RPYC 的架构设计旨在为控制各种 DCC 应用程序提供统一的接口：

```mermaid
graph TD
    A[客户端应用<br>AI 助手] --> B[MCP 服务器<br>协调器]
    B --> C[DCC 软件<br>Maya/Houdini]
    A --> D[DCC-MCP<br>核心 API]
    D --> E[DCC-MCP-RPYC<br>传输层]
    E --> C
```

主要组件：

- **DCCServer**：在 DCC 应用程序中管理 RPYC 服务器
- **DCCRPyCService**：通过 RPYC 暴露 DCC 功能的服务基类
- **BaseDCCClient**：用于连接和控制 DCC 应用程序的客户端接口
- **DCCAdapter**：DCC 特定适配器的抽象基类
- **ConnectionPool**：管理和重用与 DCC 服务器的连接

## 安装

```bash
pip install dcc-mcp-rpyc
```

或者使用 Poetry：

```bash
poetry add dcc-mcp-rpyc
```

## 使用方法

### 服务器端（在 DCC 应用程序内）

```python
# 在 Maya 中创建并启动 DCC 服务器
from dcc_mcp_rpyc.server import create_server, DCCRPyCService

# 创建自定义服务类
class MayaService(DCCRPyCService):
    def get_scene_info(self):
        # 实现 Maya 特定的场景信息获取
        return {"scene": "Maya 场景信息"}

    def exposed_execute_cmd(self, cmd_name, *args, **kwargs):
        # 实现 Maya 命令执行
        pass

# 创建并启动服务器
server = create_server(
    dcc_name="maya",
    service_class=MayaService,
    port=18812  # 可选，如果不指定将使用随机端口
)

# 启动服务器（threaded=True 避免阻塞 Maya 的主线程）
server.start(threaded=True)
```

### 客户端

```python
from dcc_mcp_rpyc.client import BaseDCCClient

# 连接到 DCC 服务器
client = BaseDCCClient(
    dcc_name="maya",
    host="localhost",
    port=18812  # 可选，如果不指定将自动发现
)

# 连接到服务器
client.connect()

# 调用远程方法
result = client.call("execute_cmd", "sphere", radius=5)
print(result)

# 获取场景信息
scene_info = client.call("get_scene_info")
print(scene_info)

# 完成后断开连接
client.disconnect()
```

### 使用连接池

```python
from dcc_mcp_rpyc.client import ConnectionPool

# 创建连接池
pool = ConnectionPool()

# 从连接池获取客户端（如果需要，会创建新连接）
with pool.get_client("maya", host="localhost") as client:
    # 在客户端上调用方法
    result = client.call("execute_cmd", "sphere", radius=5)
    print(result)

# 连接自动返回到连接池
```

### 创建 DCC 适配器

```python
from dcc_mcp_rpyc.dcc_adapter import DCCAdapter
from dcc_mcp_rpyc.client import BaseDCCClient

class MayaAdapter(DCCAdapter):
    def _create_client(self) -> BaseDCCClient:
        return BaseDCCClient(
            dcc_name="maya",
            host=self.host,
            port=self.port,
            timeout=self.timeout
        )

    def create_sphere(self, radius=1.0):
        self.ensure_connected()
        return self.dcc_client.call("execute_cmd", "sphere", r=radius)
```

## 开发

### 环境设置

```bash
# 克隆仓库
git clone https://github.com/loonghao/dcc-mcp-rpyc.git
cd dcc-mcp-rpyc

# 使用 Poetry 安装依赖
poetry install
```

### 测试

```bash
# 使用 nox 运行测试
nox -s pytest

# 运行代码检查
nox -s lint

# 修复代码检查问题
nox -s lint_fix
```

## 许可证

MIT
