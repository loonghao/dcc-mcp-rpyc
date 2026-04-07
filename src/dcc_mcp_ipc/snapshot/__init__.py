"""Snapshot module for DCC-MCP-IPC.

This package provides unified screenshot/snapshot capture functionality
across all DCC applications. It supports multiple transport protocols
(RPyC, HTTP) and presents a consistent API regardless of the underlying DCC.

Module structure:

- ``base`` — Abstract interface (BaseSnapshot, SnapshotConfig, SnapshotResult)
- ``rpyc`` — RPyC transport implementation (Maya, Blender, Houdini, etc.)
- ``http``  — HTTP transport implementation (Unreal Engine, Unity)

Quick start::

    from dcc_mcp_ipc.snapshot import BaseSnapshot, SnapshotConfig

    # RPyC-based snapshot (Maya/Blender/Houdini)
    from dcc_mcp_ipc.snapshot.rpyc import RPyCSnapshot
    snap = RPyCSnapshot(dcc_name="maya", execute_func=conn.root.execute_python)
    png_bytes = snap.capture_viewport(SnapshotConfig(width=1920, height=1080))

    # HTTP-based snapshot (Unreal/Unity)
    from dcc_mcp_ipc.snapshot.http import HTTPSnapshot
    snap = HTTPSnapshot(base_url="http://localhost:30010", dcc_type="unreal")
    png_bytes = snap.capture_viewport()
"""

# Import built-in modules
from typing import Any


# Import local modules
from dcc_mcp_ipc.snapshot.base import BaseSnapshot
from dcc_mcp_ipc.snapshot.base import SnapshotConfig
from dcc_mcp_ipc.snapshot.base import SnapshotError
from dcc_mcp_ipc.snapshot.base import SnapshotFormat
from dcc_mcp_ipc.snapshot.base import SnapshotResult
from dcc_mcp_ipc.snapshot.base import ViewportType


__all__ = [
    # Abstract base
    "BaseSnapshot",
    # Config & result models
    "SnapshotConfig",
    "SnapshotError",
    "SnapshotFormat",
    "SnapshotResult",
    "ViewportType",
]


def create_snapshot(
    dcc_name: str,
    transport: str = "rpyc",
    **kwargs: Any,
) -> BaseSnapshot:
    """Factory function to create the appropriate snapshot instance.

    This is the recommended way to create snapshot objects. It selects the
    correct implementation based on the specified transport protocol.

    Args:
        dcc_name: Name of the target DCC ("maya", "blender", "unreal", etc.).
        transport: Transport protocol to use ("rpyc" or "http").
        **kwargs: Additional arguments forwarded to the snapshot constructor.
            For RPyC: ``execute_func``, for HTTP: ``base_url``.

    Returns:
        A BaseSnapshot subclass instance configured for the specified DCC.

    Raises:
        ValueError: If the transport type is not supported.

    Example::

        # RPyC snapshot for Maya
        snap = create_snapshot("maya", "rpyc", execute_func=my_exec_fn)

        # HTTP snapshot for Unreal
        snap = create_snapshot("unreal", "http", base_url="http://localhost:30010")

    """
    if transport == "rpyc":
        from dcc_mcp_ipc.snapshot.rpyc import RPyCSnapshot

        return RPyCSnapshot(dcc_name=dcc_name, **kwargs)
    elif transport == "http":
        from dcc_mcp_ipc.snapshot.http import HTTPSnapshot

        return HTTPSnapshot(dcc_type=dcc_name, **kwargs)
    else:
        raise ValueError(
            f"Unsupported transport '{transport}'. "
            f"Supported transports: 'rpyc', 'http'"
        )
