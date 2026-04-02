# Usage Examples

## Basic Connection (Application Server)

```python
from dcc_mcp_ipc.application import connect_to_application

client = connect_to_application("localhost", 18812)
result = client.execute_python("2 + 2")
print(f"2 + 2 = {result}")
client.close()
```

## DCC Integration (Maya)

```python
from dcc_mcp_ipc.client import BaseDCCClient

maya_client = BaseDCCClient("maya", "localhost", 18812)
maya_client.connect()

dcc_info = maya_client.get_dcc_info()
print(f"DCC: {dcc_info['name']}, Version: {dcc_info['version']}")

maya_client.execute_dcc_command("sphere -name mySphere;")
maya_client.close()
```

## Async Client

```python
import asyncio
from dcc_mcp_ipc.client import AsyncBaseDCCClient

async def main():
    client = AsyncBaseDCCClient("localhost", 18812, "maya")
    await client.connect()
    result = await client.execute_python(
        "import maya.cmds as cmds; cmds.sphere(name='asyncSphere')"
    )
    print(f"Result: {result}")
    await client.close()

asyncio.run(main())
```

## Custom Action

```python
from dcc_mcp_core.actions.base import Action
from dcc_mcp_core.models import ActionResultModel
from pydantic import BaseModel, Field

class CreateSphereInput(BaseModel):
    name: str = Field(description="Name of the sphere")
    radius: float = Field(default=1.0, description="Radius of the sphere")

class CreateSphereAction(Action):
    """Create a sphere in Maya."""
    name = "create_sphere"
    input_model = CreateSphereInput

    def execute(self, input_data: CreateSphereInput) -> ActionResultModel:
        import maya.cmds as cmds
        sphere = cmds.sphere(name=input_data.name, radius=input_data.radius)[0]
        return ActionResultModel(
            success=True,
            message=f"Created sphere: {sphere}",
            data={"name": sphere, "radius": input_data.radius}
        )
```

## Server Side

```python
from dcc_mcp_ipc.server import create_server, start_server

server = create_server("maya", port=18812)
start_server(server)
```
