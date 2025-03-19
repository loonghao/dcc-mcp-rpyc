# DCC-MCP-RPYC 架构

## 组件关系图

```mermaid
graph TD
    %% 定义节点样式
    classDef aiNode fill:#f9d5e5,stroke:#333,stroke-width:2px,color:#000000,font-weight:bold;
    classDef mcpNode fill:#eeac99,stroke:#333,stroke-width:2px,color:#000000,font-weight:bold;
    classDef dccNode fill:#b6dcfe,stroke:#333,stroke-width:2px,color:#000000,font-weight:bold;
    classDef serviceNode fill:#d6eadf,stroke:#333,stroke-width:2px,color:#000000,font-weight:bold;
    classDef pluginNode fill:#fff8e1,stroke:#333,stroke-width:2px,color:#000000,font-weight:bold;

    %% 定义节点
    AI[AI/用户] --> |请求| MCP[MCP服务器]

    %% DCC软件进程
    subgraph "DCC软件进程"
        style DCC软件进程 fill:#e6f7ff,stroke:#1890ff,stroke-width:2px,color:#000000,font-weight:bold
        DCCPluginServer --> |初始化| DCCService
        DCCService --> |暴露功能| RPyCServer[RPYC服务器]
        RPyCServer --> |注册服务| Discovery[服务发现系统]
    end

    %% MCP服务器进程
    subgraph "MCP服务器进程"
        style MCP服务器进程 fill:#f6ffed,stroke:#52c41a,stroke-width:2px,color:#000000,font-weight:bold
        MCP --> |查找服务| Discovery
        MCP --> |连接| RPyCServer
        DCCAdapter --> |创建| DCCClient
        DCCClient --> |连接| RPyCServer
        DCCAdapter --> |调用| PluginManager[plugin_manager]
        PluginManager --> |加载和管理| Plugins[DCC插件]
        DCCAdapter --> |执行命令| DCCClient
    end

    %% 返回结果
    MCP --> |响应| AI

    %% 应用样式
    class AI aiNode;
    class MCP mcpNode;
    class DCCPluginServer,DCCService,RPyCServer dccNode;
    class DCCAdapter,DCCClient serviceNode;
    class PluginManager,Plugins,Discovery pluginNode;
```

## 类关系图

```mermaid
classDiagram
    %% 核心类
    class DCCPluginServer {
        <<abstract>>
        +initialize()
        +start_server()
        +cleanup()
    }

    class DCCService {
        <<abstract>>
        +get_scene_info()
        +call_plugin_function()
    }

    class DCCAdapter {
        <<abstract>>
        +ensure_connected()
        +get_scene_info()
        +get_plugins_info()
        +call_plugin_function()
    }

    class DCCClient {
        +connect()
        +reconnect()
        +is_connected()
        +call()
    }

    class DCCRPyCServer {
        <<abstract>>
        +start()
        +stop()
        +is_running()
    }

    %% Maya特定实现
    class MayaDCCPluginServer {
        +initialize()
    }

    class MayaService {
        +get_scene_info()
        +execute_command()
        +execute_mel()
        +create_primitive()
    }

    class MayaAdapter {
        +ensure_connected()
        +get_scene_info()
        +execute_command()
        +execute_mel()
        +create_primitive()
    }

    class MayaRPyCServer {
        +start()
    }

    %% 继承关系
    DCCPluginServer <|-- MayaDCCPluginServer
    DCCService <|-- MayaService
    DCCAdapter <|-- MayaAdapter
    DCCRPyCServer <|-- MayaRPyCServer

    %% 关联关系
    DCCPluginServer --> DCCService : uses
    DCCPluginServer --> DCCRPyCServer : creates
    DCCAdapter --> DCCClient : uses

    %% 样式
    style DCCPluginServer fill:#ffcdd2,stroke:#c62828,stroke-width:2px
    style DCCService fill:#ffcdd2,stroke:#c62828,stroke-width:2px
    style DCCAdapter fill:#ffcdd2,stroke:#c62828,stroke-width:2px
    style DCCRPyCServer fill:#ffcdd2,stroke:#c62828,stroke-width:2px
    style DCCClient fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style MayaDCCPluginServer fill:#bbdefb,stroke:#1565c0,stroke-width:2px
    style MayaService fill:#bbdefb,stroke:#1565c0,stroke-width:2px
    style MayaAdapter fill:#bbdefb,stroke:#1565c0,stroke-width:2px
    style MayaRPyCServer fill:#bbdefb,stroke:#1565c0,stroke-width:2px
```

## 序列图

```mermaid
sequenceDiagram
    %% 样式设置
    participant AI as AI/用户
    participant MCP as MCP服务器
    participant Adapter as DCCAdapter
    participant Client as DCCClient
    participant Server as DCCRPyCServer
    participant Service as DCCService
    participant Plugin as DCCPluginServer

    %% 初始化阶段
    Plugin->>Plugin: initialize()
    Plugin->>Service: 创建服务
    Plugin->>Server: 创建服务器
    Server->>Server: start()
    Server-->>Plugin: 返回端口号

    %% 请求处理阶段
    AI->>MCP: 发送请求
    MCP->>Adapter: 调用适配器方法
    Adapter->>Client: 创建客户端
    Client->>Server: 连接服务器
    Adapter->>Client: 调用远程方法
    Client->>Service: 执行方法
    Service-->>Client: 返回结果
    Client-->>Adapter: 返回结果
    Adapter-->>MCP: 返回结果
    MCP-->>AI: 返回响应

    %% 清理阶段
    Plugin->>Plugin: cleanup()
    Plugin->>Server: stop()
```

## 工作流程说明

1. **初始化阶段**：
   - DCC软件加载插件（`MayaDCCPluginServer`）
   - 插件初始化并创建服务（`MayaService`）
   - 插件启动RPYC服务器（`MayaRPyCServer`）
   - 服务器注册到服务发现系统

2. **连接阶段**：
   - MCP服务器通过服务发现系统查找DCC服务
   - MCP服务器创建适配器（`MayaAdapter`）
   - 适配器创建客户端（`DCCClient`）并连接到RPYC服务器

3. **请求处理阶段**：
   - AI/用户向MCP服务器发送请求
   - MCP服务器调用适配器方法
   - 适配器通过客户端调用远程服务方法
   - 服务执行方法并返回结果
   - 结果通过客户端、适配器返回给MCP服务器
   - MCP服务器将结果返回给AI/用户

4. **清理阶段**：
   - DCC软件卸载插件时调用清理方法
   - 插件停止RPYC服务器
   - 服务器从服务发现系统注销
