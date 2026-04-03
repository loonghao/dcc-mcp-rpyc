"""Scene information module for DCC-MCP-IPC.

This package provides unified scene query interfaces across all DCC applications.
It supports multiple transport protocols (RPyC, HTTP) and presents a consistent
API regardless of the underlying DCC.

Module structure:

- ``base``     — Abstract interface (BaseSceneInfo, SceneObject, SceneHierarchy, etc.)
- ``rpyc``     — RPyC transport implementation (Maya, Blender, Houdini)
- ``http``      — HTTP transport implementation (Unreal Engine, Unity)

Standardized return format::

    {
        "objects": [...],
        "hierarchy": {...},
        "materials": [...],
        "cameras": [...],
        "lights": [...],
        "selection": [...]
    }
"""

# Import built-in modules
from typing import Any

# Import local modules
from dcc_mcp_ipc.scene.base import BaseSceneInfo
from dcc_mcp_ipc.scene.base import CameraInfo
from dcc_mcp_ipc.scene.base import LightInfo
from dcc_mcp_ipc.scene.base import MaterialInfo
from dcc_mcp_ipc.scene.base import ObjectTypeInfo
from dcc_mcp_ipc.scene.base import SceneError
from dcc_mcp_ipc.scene.base import SceneHierarchy
from dcc_mcp_ipc.scene.base import SceneInfo
from dcc_mcp_ipc.scene.base import SceneInfoConfig
from dcc_mcp_ipc.scene.base import SceneQueryFilter
from dcc_mcp_ipc.scene.base import TransformMatrix


__all__ = [
    # Abstract base
    "BaseSceneInfo",
    # Config & result models
    "CameraInfo",
    "LightInfo",
    "MaterialInfo",
    "ObjectTypeInfo",
    "SceneError",
    "SceneHierarchy",
    "SceneInfo",
    "SceneInfoConfig",
    "SceneQueryFilter",
    "TransformMatrix",
]


def create_scene_info(
    dcc_name: str,
    transport: str = "rpyc",
    **kwargs: Any,
) -> BaseSceneInfo:
    """Factory function to create the appropriate scene info instance.

    This is the recommended way to create scene info objects. It selects the
    correct implementation based on the specified transport protocol.

    Args:
        dcc_name: Name of the target DCC ("maya", "blender", "unreal", etc.).
        transport: Transport protocol to use ("rpyc" or "http").
        **kwargs: Additional arguments forwarded to the constructor.
            For RPyC: ``execute_func``, for HTTP: ``base_url``.

    Returns:
        A BaseSceneInfo subclass instance configured for the specified DCC.

    Raises:
        ValueError: If the transport type is not supported.

    Example::

        # RPyC scene info for Maya
        scene = create_scene_info("maya", "rpyc", execute_func=my_exec_fn)
        objects = scene.get_objects()

        # HTTP scene info for Unreal
        scene = create_scene_info("unreal", "http", base_url="http://localhost:30010")
        hierarchy = scene.get_hierarchy()
    """
    if transport == "rpyc":
        from dcc_mcp_ipc.scene.rpyc import RPyCSceneInfo

        return RPyCSceneInfo(dcc_name=dcc_name, **kwargs)
    elif transport == "http":
        from dcc_mcp_ipc.scene.http import HTTPSceneInfo

        return HTTPSceneInfo(dcc_type=dcc_name, **kwargs)
    else:
        raise ValueError(
            f"Unsupported transport '{transport}'. "
            f"Supported transports: 'rpyc', 'http'"
        )
