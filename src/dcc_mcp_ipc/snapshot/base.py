"""Base snapshot abstraction for cross-DCC screenshot capture.

This module defines the unified interface for capturing viewport screenshots
and render snapshots across all DCC applications (Maya, Blender, Houdini,
Unreal, Unity, etc.).

The snapshot system is protocol-agnostic: it works over RPyC, HTTP,
or WebSocket transports through the existing ``execute()`` RPC mechanism.

Design principles:
- All implementations return raw ``bytes`` (PNG format) for maximum flexibility.
- The MCP layer converts to base64 when exposing as an Image content type.
- Each DCC subclass only needs to implement 2-3 methods.
"""

# Import built-in modules
from abc import ABC
from abc import abstractmethod
from enum import Enum
from typing import Any
from typing import Dict
from typing import Optional

# Import third-party modules
from pydantic import BaseModel
from pydantic import Field



class SnapshotFormat(str, Enum):
    """Supported image formats for snapshots."""

    PNG = "png"
    JPEG = "jpeg"
    BMP = "bmp"


class ViewportType(str, Enum):
    """Common viewport names across DCC applications."""

    PERSPECTIVE = "perspective"
    TOP = "top"
    FRONT = "front"
    SIDE = "RIGHT"  # Canonical name: side/right
    CAMERA = "camera"


class SnapshotConfig(BaseModel):
    """Configuration for a snapshot capture request.

    Attributes:
        width: Image width in pixels.
        height: Image height in pixels.
        format: Output image format (default: PNG).
        quality: JPEG quality 1-100 (only used for JPEG format).
        include_transparency: Whether to include alpha channel.
        camera: Camera name for CAMERA viewport type.
        viewport: Viewport to capture from.

    """

    width: int = 1920
    height: int = 1080
    format: SnapshotFormat = SnapshotFormat.PNG
    quality: int = 95
    include_transparency: bool = False
    camera: Optional[str] = None
    viewport: ViewportType = ViewportType.PERSPECTIVE


class SnapshotResult(BaseModel):
    """Result of a snapshot capture operation.

    Attributes:
        success: Whether the capture was successful.
        format: The image format of the captured data.
        width: Actual image width (may differ from requested if DCC constrained it).
        height: Actual image height.
        data_size: Size of the image data in bytes.
        error: Error message if the capture failed.
        metadata: Additional DCC-specific metadata (e.g., scene name, frame number).

    """

    success: bool = True
    format: SnapshotFormat = SnapshotFormat.PNG
    width: int = 0
    height: int = 0
    data_size: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseSnapshot(ABC):
    """Abstract base class for DCC snapshot/screenshot operations.

    This class provides a unified interface for capturing images from DCC
    viewports. Subclasses implement DCC-specific capture logic using each
    application's native API (e.g., ``maya.cmds.playblast``,
    ``bpy.ops.render.opengl``, Unreal Remote Control API).

    Lifecycle:
        1. Create instance (typically owned by a DCCAdapter or DCCServer).
        2. Call :meth:`capture_viewport` or :meth:`capture_render`.
        3. Receive raw bytes (PNG) as the result.

    Example::

        class MayaSnapshot(BaseSnapshot):
            def capture_viewport(self, config=None):
                config = config or SnapshotConfig()
                import maya.cmds as cmds
                # Use playblast for viewport capture
                ...

    """

    @abstractmethod
    def capture_viewport(
        self,
        config: Optional[SnapshotConfig] = None,
    ) -> bytes:
        """Capture the current viewport as an image.

        This method captures what is currently visible in the active or
        specified 3D viewport. The implementation should use the DCC's
        native screen-grab or viewport-capture API.

        Args:
            config: Snapshot configuration. Uses defaults if not provided.

        Returns:
            Raw image bytes in the format specified by *config.format*
            (default: PNG).

        Raises:
            SnapshotError: If the capture fails due to DCC API errors,
                invalid configuration, or unsupported operations.

        """
        ...

    def capture_render(
        self,
        config: Optional[SnapshotConfig] = None,
    ) -> bytes:
        """Capture a software-rendered image of the current scene.

        This method performs a full render (not just viewport capture)
        using the DCC's rendering engine. It is typically slower than
        :meth:`capture_viewport` but produces higher-quality output
        with proper lighting, materials, and effects.

        The default implementation raises ``NotImplementedError`. DCC
        subclasses that support programmatic rendering should override this.

        Args:
            config: Snapshot configuration. Uses defaults if not provided.

        Returns:
            Raw image bytes (typically PNG).

        Raises:
            NotImplementedError: If the DCC does not support render capture.
            SnapshotError: If the render fails.

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support render capture. "
            "Use capture_viewport() instead."
        )

    def capture_to_base64(
        self,
        config: Optional[SnapshotConfig] = None,
    ) -> str:
        """Capture and return base64-encoded image data.

        Convenience method that wraps :meth:`capture_viewport` and encodes
        the result as a base64 string. Useful for MCP Tool responses that
        need to return image data as text.

        Args:
            config: Snapshot configuration.

        Returns:
            Base64-encoded image string.

        """
        import base64

        data = self.capture_viewport(config)
        return base64.b64encode(data).decode("ascii")

    def get_snapshot_info(self) -> Dict[str, Any]:
        """Return information about the snapshot capabilities.

        Returns a dict describing what this snapshot implementation supports,
        including available viewports, supported formats, and any constraints.

        Returns:
            Dict with capability information.

        """
        return {
            "type": self.__class__.__name__,
            "supports_viewport": True,
            "supports_render": (
                type(self).capture_render != BaseSnapshot.capture_render
            ),
            "supported_formats": [f.value for f in SnapshotFormat],
            "supported_viewports": [v.value for v in ViewportType],
        }


class SnapshotError(Exception):
    """Raised when a snapshot capture operation fails."""

    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.cause = cause
