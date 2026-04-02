# 传输层

传输层是 DCC-MCP-IPC 实现协议无关通信的核心抽象。所有传输实现都遵循 `BaseTransport` 接口。

## BaseTransport 接口

```python
class BaseTransport(ABC):
    def connect(self) -> None: ...        # 建立连接
    def disconnect(self) -> None: ...     # 关闭连接（幂等）
    def health_check(self) -> bool: ...   # 健康检查
    def execute(self, action, params, timeout) -> dict: ...  # 执行动作
    def execute_python(self, code, context) -> Any: ...      # 执行 Python 代码
```

## RPyC 传输

适用于内嵌 Python 解释器的 DCC 应用（Maya、Blender、Houdini、3ds Max、Nuke）。

```python
from dcc_mcp_ipc.transport.rpyc_transport import RPyCTransport, RPyCTransportConfig

config = RPyCTransportConfig(host="localhost", port=18812)
with RPyCTransport(config) as transport:
    result = transport.execute("list_actions")
    transport.execute_python("import maya.cmds as cmds; cmds.sphere()")
```

## HTTP 传输

适用于提供 HTTP API 的 DCC 应用（Unreal Engine Remote Control、Unity HttpListener）。

```python
from dcc_mcp_ipc.transport.http import HTTPTransport, HTTPTransportConfig

config = HTTPTransportConfig(host="localhost", port=30010, base_path="/remote")
with HTTPTransport(config) as transport:
    transport.call_remote_object("/Game/MyActor", "SetActorLocation",
        {"NewLocation": {"X": 0, "Y": 0, "Z": 100}})
```

## 传输工厂

```python
from dcc_mcp_ipc.transport import create_transport, get_transport

transport = create_transport("rpyc")             # 创建新实例
transport = get_transport("http", host="localhost", port=30010)  # 获取缓存实例
```
