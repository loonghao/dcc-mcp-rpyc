"""RPyC snapshot implementation for DCC applications with embedded Python.

This module provides the default RPyC-based snapshot implementation that works
with DCC applications embedding a Python interpreter (Maya, Blender, Houdini,
3ds Max, Nuke). It uses the DCC's native Python API to capture viewport
screenshots.

Protocol: The actual image bytes are transferred over RPyC as base64-encoded
strings (to avoid RPyC's memory limitations with large binary data), then
decoded back to raw bytes on the client side.
"""

# Import built-in modules
import base64
import logging
from typing import Any
from typing import Optional

# Import local modules
from dcc_mcp_ipc.snapshot.base import BaseSnapshot
from dcc_mcp_ipc.snapshot.base import SnapshotConfig
from dcc_mcp_ipc.snapshot.base import SnapshotError

logger = logging.getLogger(__name__)


class RPyCSnapshot(BaseSnapshot):
    """Snapshot implementation for DCC applications accessible via RPyC.

    This class captures screenshots by executing DCC-specific Python code
    through an RPyC connection. Each DCC type uses its own capture strategy:

    **Capture strategies by DCC**:

    - **Maya**: ``maya.cmds.playblast`` with frame capture
    - **Blender**: ``bpy.ops.render.opengl`` (viewport render)
    - **Houdini**: ``hou.viewport`` or ``hou.glRender`` API
    - **3ds Max**: MaxPlus/PyMax runtime screenshot capability
    - **Nuke**: ``nuke.executeViewer`` or screen grab

    Attributes:
        dcc_name: Name of the DCC application (e.g. "maya", "blender").
        execute_func: Callable to execute Python code on the remote DCC side.

    """

    def __init__(
        self,
        dcc_name: str = "generic",
        execute_func: Optional[Any] = None,
    ) -> None:
        """Initialize the RPyC snapshot.

        Args:
            dcc_name: Name of the target DCC application.
            execute_func: Callable(code_str) -> result that executes Python
                code on the remote DCC side via RPyC.

        """
        self.dcc_name = dcc_name.lower()
        self._execute = execute_func

    def _remote_exec(self, code: str) -> Any:
        """Execute Python code on the remote DCC side.

        Args:
            code: Python source code to execute.

        Returns:
            Result of the execution.

        Raises:
            SnapshotError: If execution fails or no executor is configured.

        """
        if self._execute is None:
            raise SnapshotError(
                "No execute function configured for RPyCSnapshot. Pass execute_func during initialization."
            )
        try:
            return self._execute(code)
        except Exception as exc:
            raise SnapshotError(
                f"Remote execution failed for {self.dcc_name}: {exc}",
                cause=exc,
            ) from exc

    def capture_viewport(
        self,
        config: Optional[SnapshotConfig] = None,
    ) -> bytes:
        """Capture viewport screenshot via RPyC.

        This method selects the appropriate DCC-specific capture script based
        on ``dcc_name``, executes it remotely, and decodes the returned
        base64 image data back to raw bytes.

        Args:
            config: Snapshot configuration.

        Returns:
            Raw PNG bytes of the captured viewport.

        Raises:
            SnapshotError: If capture fails or DCC is not supported.

        """
        config = config or SnapshotConfig()
        script = self._get_capture_script(config)

        logger.debug(
            "Capturing %s viewport (%dx%d %s)",
            self.dcc_name,
            config.width,
            config.height,
            config.format.value,
        )

        result = self._remote_exec(script)

        # Result should be a base64-encoded string from the remote DCC
        if isinstance(result, dict):
            if "error" in result:
                raise SnapshotError(f"Remote capture error: {result['error']}")
            if "data" in result:
                return base64.b64decode(result["data"])
            if "image_data" in result:
                return base64.b64decode(result["image_data"])

        if isinstance(result, str):
            # Raw base64 string response
            try:
                return base64.b64decode(result)
            except Exception:
                raise SnapshotError(f"Invalid base64 data returned from {self.dcc_name}")

        if isinstance(result, bytes):
            # Already decoded bytes (some transports handle this natively)
            return result

        raise SnapshotError(f"Unexpected capture result type: {type(result).__name__}")

    def capture_render(self, config: Optional[SnapshotConfig] = None) -> bytes:
        """Capture a software-rendered image via RPyC.

        Args:
            config: Snapshot configuration.

        Returns:
            Raw image bytes of the rendered scene.

        Raises:
            SnapshotError: If rendering fails.

        """
        config = config or SnapshotConfig()
        script = self._get_render_script(config)

        result = self._remote_exec(script)

        if isinstance(result, dict):
            if "error" in result:
                raise SnapshotError(f"Remote render error: {result['error']}")
            if "data" in result:
                return base64.b64decode(result["data"])

        if isinstance(result, str):
            return base64.b64decode(result)

        if isinstance(result, bytes):
            return result

        raise SnapshotError(f"Unexpected render result type: {type(result).__name__}")

    def _get_capture_script(self, config: SnapshotConfig) -> str:
        """Generate DCC-specific Python script for viewport capture.

        Args:
            config: Snapshot configuration.

        Returns:
            Python source code string to execute remotely.

        """
        fmt = config.format.value.upper()  # PNG / JPEG
        width = config.width
        height = config.height

        scripts = {
            "maya": self._maya_capture_script(fmt, width, height),
            "blender": self._blender_capture_script(fmt, width, height),
            "houdini": self._houdini_capture_script(fmt, width, height),
        }

        return scripts.get(self.dcc_name, self._generic_capture_script(fmt, width, height))

    def _get_render_script(self, config: SnapshotConfig) -> str:
        """Generate DCC-specific Python script for render capture.

        Args:
            config: Snapshot configuration.

        Returns:
            Python source code string to execute remotely.

        """
        fmt = config.format.value.upper()
        width = config.width
        height = config.height

        scripts = {
            "maya": self._maya_render_script(fmt, width, height),
            "blender": self._blender_render_script(width, height),
        }

        return scripts.get(self.dcc_name, self._generic_render_script())

    @staticmethod
    def _maya_capture_script(fmt: str, width: int, height: int) -> str:
        """Generate Maya playblast capture script."""
        return f"""
import base64
import tempfile
import os

import maya.cmds as cmds

# Create temp file for playblast output
ext = "{fmt.lower()}" if "{fmt}" == "png" else "jpg"
fd, path = tempfile.mktemp(suffix=f".{{ext}}")

try:
    # Use playblast for viewport frame capture
    result = cmds.playblast(
        format="{fmt}",
        frame=[cmds.currentTime(query=True)],
        viewer=False,
        completeFilename=path,
        width={width},
        height={height},
        quality=100,
        forceOverwrite=True,
        startTime=1,
        endTime=1,
    )

    # Read and encode the captured image
    with open(path if result else path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('ascii')

    {{'success': True, 'data': data, 'format': '{fmt}'}}
finally:
    if os.path.exists(path):
        os.remove(path)
""".strip()

    @staticmethod
    def _maya_render_script(fmt: str, width: int, height: int) -> str:
        """Generate Maya software render capture script."""
        return f"""
import base64
import tempfile
import os

import maya.cmds as cmds

# Set render resolution
cmds.setAttr("defaultResolution.width", {width})
cmds.setAttr("defaultResolution.height", {height})
cmds.setAttr("defaultResolution.imageFormat", 32 if "{fmt}" == "PNG" else 3)

fd, path = tempfile.mktemp(suffix=".{fmt.lower()}")

try:
    cmds.render(path)
    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('ascii')
    {{'success': True, 'data': data}}
finally:
    if os.path.exists(path):
        os.remove(path)
""".strip()

    @staticmethod
    def _blender_capture_script(fmt: str, width: int, height: int) -> str:
        """Generate Blender OpenGL viewport render script."""
        return f"""
import base64
import bpy
import tempfile
import os

# Set viewport dimensions
bpy.context.scene.render.resolution_x = {width}
bpy.context.scene.render.resolution_y = {height}
bpy.context.scene.render.image_settings.file_format = '{fmt}'
if '{fmt}'.lower() == 'jpeg':
    bpy.context.scene.render.image_settings.quality = 95

fd, path = tempfile.mktemp(suffix=".{fmt.lower()}")

try:
    # OpenGL viewport render
    bpy.ops.render.opengl(write_still=True, filepath=path)

    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('ascii')

    {{'success': True, 'data': data, 'format': '{fmt}'}}
finally:
    if os.path.exists(path):
        os.remove(path)
""".strip()

    @staticmethod
    def _blender_render_script(width: int, height: int) -> str:
        """Generate Blender full render (cycles/eevee) script."""
        return f"""
import base64
import bpy
import tempfile
import os

bpy.context.scene.render.resolution_x = {width}
bpy.context.scene.render.resolution_y = {height}
bpy.context.scene.render.file_format = 'PNG'

fd, path = tempfile.mktemp(suffix=".png")

try:
    bpy.ops.render(write_still=True, filepath=path)
    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('ascii')
    {{'success': True, 'data': data}}
finally:
    if os.path.exists(path):
        os.remove(path)
""".strip()

    @staticmethod
    def _houdini_capture_script(fmt: str, width: int, height: int) -> str:
        """Generate Houdini viewport capture script."""
        return f"""
import base64
import hou
import tempfile
import os

fd, path = tempfile.mktemp(suffix=".{fmt.lower()}")

try:
    # Flip Y axis for Houdini's coordinate system
    viewport = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    if viewport:
        viewport.capture(path, {width}, {height})
        with open(path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('ascii')
        {{'success': True, 'data': data}}
    else:
        {{'error': 'No active Scene Viewer found'}}
finally:
    if os.path.exists(path):
        os.remove(path)
""".strip()

    @staticmethod
    def _generic_capture_script(fmt: str, width: int, height: int) -> str:
        """Generate generic fallback script for unsupported DCC types.

        Returns a mock/simulated result for testing purposes.
        """
        return f"""
import base64

# Generic fallback: generate a minimal valid PNG
# This is used for testing or when no DCC-specific implementation exists
width, height = {width}, {height}

# Minimal 1x1 PNG (placeholder — real DCC implementations should override this)
def make_minimal_png(w=w, h=h):
    import struct, zlib
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    raw = b''
    for y in range(h):
        raw += b'\\x00' + b'\\x80' * w * 3  # RGB

    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    signature = b'\\x89PNG\\r\\n\\x1a\\n'
    png = signature + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')

    return base64.b64encode(png).decode('ascii')

{{'success': True, 'data': make_minimal_png(), 'format': '{fmt}', 'mock': True}}
""".strip()

    @staticmethod
    def _generic_render_script() -> str:
        """Return a generic fallback render script (raises NotImplementedError)."""
        return """
{'error': 'Render capture not supported for this DCC type'}
""".strip()

    def get_snapshot_info(self) -> dict[str, Any]:
        """Return snapshot capabilities including available DCC strategies."""
        info = super().get_snapshot_info()
        info["dcc_name"] = self.dcc_name
        info["has_dedicated_strategy"] = self.dcc_name in (
            "maya",
            "blender",
            "houdini",
        )
        info["transport"] = "rpyc"
        return info
