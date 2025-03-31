Usage
=====

To use DCC-MCP-RPYC in a project::

    import dcc_mcp_rpyc

基本连接示例 (Basic Connection Example)
---------------------------------

以下是如何使用 DCC-MCP-RPYC 连接到应用程序服务器的基本示例::

    from dcc_mcp_rpyc.application import connect_to_application
    
    # 连接到应用程序服务器
    client = connect_to_application("localhost", 18812)
    
    # 执行 Python 代码
    result = client.execute_python("2 + 2")
    print(f"2 + 2 = {result}")
    
    # 关闭连接
    client.close()

DCC 集成示例 (DCC Integration Example)
--------------------------------

以下是如何使用 DCC-MCP-RPYC 连接到 DCC 应用程序（如 Maya、Houdini 或 Nuke）的示例::

    from dcc_mcp_rpyc.client import BaseDCCClient
    
    # 创建 DCC 客户端
    maya_client = BaseDCCClient("maya", "localhost", 18812)
    
    # 连接到 Maya
    maya_client.connect()
    
    # 获取 Maya 版本信息
    dcc_info = maya_client.get_dcc_info()
    print(f"DCC Name: {dcc_info['name']}, Version: {dcc_info['version']}")
    
    # 执行 MEL 命令
    maya_client.execute_dcc_command("sphere -name mySphere;")
    
    # 关闭连接
    maya_client.close()

异步客户端示例 (Async Client Example)
------------------------------

以下是如何使用异步客户端的示例::

    import asyncio
    from dcc_mcp_rpyc.client import AsyncBaseDCCClient
    
    async def main():
        # 创建异步 DCC 客户端
        client = AsyncBaseDCCClient("localhost", 18812, "maya")
        
        # 连接到服务器
        await client.connect()
        
        # 执行 Python 代码
        result = await client.execute_python("import maya.cmds as cmds; cmds.sphere(name='asyncSphere')")
        print(f"Result: {result}")
        
        # 关闭连接
        await client.close()
    
    # 运行异步主函数
    asyncio.run(main())

自定义 Action 示例 (Custom Action Example)
--------------------------------

以下是如何创建和使用自定义 Action 的示例::

    from dcc_mcp_core.actions.base import Action
    from dcc_mcp_core.models import ActionResultModel
    from pydantic import BaseModel, Field
    
    # 定义 Action 输入模型
    class CreateSphereInput(BaseModel):
        name: str = Field(description="Name of the sphere")
        radius: float = Field(default=1.0, description="Radius of the sphere")
    
    # 定义自定义 Action
    class CreateSphereAction(Action):
        """Create a sphere in Maya."""
        name = "create_sphere"
        input_model = CreateSphereInput
        
        def execute(self, input_data: CreateSphereInput) -> ActionResultModel:
            # 在这里实现 Action 逻辑
            import maya.cmds as cmds
            
            # 创建球体
            sphere = cmds.sphere(name=input_data.name, radius=input_data.radius)[0]
            
            # 返回结果
            return ActionResultModel(
                success=True,
                message=f"Created sphere: {sphere}",
                data={"name": sphere, "radius": input_data.radius}
            )

服务器示例 (Server Example)
----------------------

以下是如何启动 DCC 服务器的示例::

    from dcc_mcp_rpyc.server import create_server, start_server
    
    # 创建服务器
    server = create_server("maya", port=18812)
    
    # 启动服务器
    start_server(server)
    
    # 服务器将在后台运行，直到应用程序关闭或调用 stop_server(server)
