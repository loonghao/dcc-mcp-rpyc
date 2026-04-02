# 使用示例

## 基本连接

```python
from dcc_mcp_ipc.application import connect_to_application

client = connect_to_application("localhost", 18812)
result = client.execute_python("2 + 2")
client.close()
```

## DCC 集成（Maya）

```python
from dcc_mcp_ipc.client import BaseDCCClient

maya_client = BaseDCCClient("maya", "localhost", 18812)
maya_client.connect()
maya_client.execute_dcc_command("sphere -name mySphere;")
maya_client.close()
```

## 自定义 Action

```python
from dcc_mcp_core.actions.base import Action
from dcc_mcp_core.models import ActionResultModel
from pydantic import BaseModel, Field

class CreateSphereInput(BaseModel):
    name: str = Field(description="球体名称")
    radius: float = Field(default=1.0, description="球体半径")

class CreateSphereAction(Action):
    """在 Maya 中创建球体。"""
    name = "create_sphere"
    input_model = CreateSphereInput

    def execute(self, input_data: CreateSphereInput) -> ActionResultModel:
        import maya.cmds as cmds
        sphere = cmds.sphere(name=input_data.name, radius=input_data.radius)[0]
        return ActionResultModel(success=True, message=f"创建球体: {sphere}")
```
