"""Base classes and data models for the scene information system.

This module defines the abstract interface for querying scene information
across different DCC applications, as well as the standardized data models
for representing objects, hierarchies, materials, cameras, and lights.
"""

# Import built-in modules
from abc import ABC
from abc import abstractmethod
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import Optional

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class TransformMatrix:
    """4x4 transformation matrix for object position/rotation/scale.

    Stored as a flat list of 16 floats in row-major order, compatible with
    Maya, Blender, Unreal, and Unity matrix conventions.
    """

    matrix: list = field(
        default_factory=lambda: [
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
        ]
    )

    @property
    def translation(self) -> tuple:
        """Extract translation component (tx, ty, tz)."""
        m = self.matrix
        return (m[12], m[13], m[14])

    @property
    def rotation(self) -> tuple:
        """Extract Euler rotation (rx, ry, rz) in degrees."""
        # Import built-in modules
        import math

        m = self.matrix
        sy = math.sqrt(m[0] ** 2 + m[1] ** 2)
        if sy > 1e-6:
            rx = math.atan2(m[9], m[10])
            ry = math.atan2(-m[8], sy)
            rz = math.atan2(m[4], m[0])
        else:
            rx = math.atan2(-m[5], m[1])
            ry = math.atan2(-m[8], sy)
            rz = 0.0
        return (math.degrees(rx), math.degrees(ry), math.degrees(rz))

    @property
    def scale(self) -> tuple:
        """Extract scale component (sx, sy, sz)."""
        # Import built-in modules
        import math

        m = self.matrix
        sx = math.sqrt(m[0] ** 2 + m[1] ** 2 + m[2] ** 2)
        sy = math.sqrt(m[4] ** 2 + m[5] ** 2 + m[6] ** 2)
        sz = math.sqrt(m[8] ** 2 + m[9] ** 2 + m[10] ** 2)
        return (sx, sy, sz)

    def model_dump(self) -> dict:
        """Return a dict representation (dataclasses compatibility shim)."""
        return asdict(self)


@dataclass
class ObjectTypeInfo:
    """Information about a single scene object.

    All DCC implementations return this standardized format so that the MCP
    layer can present a uniform interface regardless of the underlying DCC.
    """

    name: str = ""
    type: str = ""
    path: str = ""
    parent: str = ""
    children: list = field(default_factory=list)
    transform: TransformMatrix = field(default_factory=TransformMatrix)
    visibility: bool = True
    material: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class SceneHierarchy:
    """Hierarchical representation of scene objects as a tree."""

    root_name: str = ""
    total_objects: int = 0
    max_depth: int = 0
    tree: dict = field(default_factory=dict)


@dataclass
class MaterialInfo:
    """Information about a material/shader in the scene."""

    name: str = ""
    type: str = ""
    assigned_objects: list = field(default_factory=list)
    properties: dict = field(default_factory=dict)


@dataclass
class CameraInfo:
    """Information about a camera in the scene."""

    name: str = ""
    type: str = "perspective"
    focal_length: float = 35.0
    sensor_width: float = 36.0
    sensor_height: float = 24.0
    near_clip: float = 0.1
    far_clip: float = 10000.0
    field_of_view: float = 54.4
    aspect_ratio: float = 1.5
    transform: TransformMatrix = field(default_factory=TransformMatrix)
    metadata: dict = field(default_factory=dict)


@dataclass
class LightInfo:
    """Information about a light in the scene."""

    name: str = ""
    type: str = ""
    intensity: float = 1.0
    color: tuple = (1.0, 1.0, 1.0)
    temperature: Optional[float] = None
    transform: TransformMatrix = field(default_factory=TransformMatrix)
    enabled: bool = True
    metadata: dict = field(default_factory=dict)


@dataclass
class SceneInfo:
    """Complete scene information container.

    Aggregates all scene query results into a single serializable structure
    that can be returned to the MCP layer as JSON.
    """

    dcc_type: str = ""
    scene_name: str = ""
    object_count: int = 0
    objects: list = field(default_factory=list)
    hierarchy: Optional[SceneHierarchy] = None
    materials: list = field(default_factory=list)
    cameras: list = field(default_factory=list)
    lights: list = field(default_factory=list)
    selection: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Configuration & Enums
# ---------------------------------------------------------------------------


class SceneQueryFilter(str, Enum):
    """Predefined filter types for object queries."""

    ALL = "all"
    MESHES = "meshes"
    CAMERAS = "cameras"
    LIGHTS = "lights"
    SHAPES = "shapes"
    JOINTS = "joints"
    VISIBLE_ONLY = "visible_only"
    SELECTED_ONLY = "selected_only"
    CUSTOM = "custom"


@dataclass
class SceneInfoConfig:
    """Configuration for scene info queries."""

    include_transforms: bool = True
    include_materials: bool = True
    include_hierarchy: bool = True
    include_metadata: bool = False
    max_objects: int = 10000
    page_offset: int = 0


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SceneError(Exception):
    """Base exception for scene information errors."""

    def __init__(self, message: str, dcc_type: str = "", cause: Optional[Exception] = None):
        self.dcc_type = dcc_type
        self.cause = cause
        super().__init__(f"[{dcc_type}] {message}" if dcc_type else message)


# ---------------------------------------------------------------------------
# Abstract Interface
# ---------------------------------------------------------------------------


class BaseSceneInfo(ABC):
    """Abstract base class for DCC scene information queries.

    All DCC-specific implementations must inherit from this class and
    implement all abstract methods. The goal is to provide a unified
    interface so that upper-layer code (MCP tools) does not need to know
    which DCC it is communicating with.
    """

    def __init__(self, config: Optional[SceneInfoConfig] = None):
        """Initialize with optional configuration.

        Args:
            config: Query configuration options.

        """
        self._config = config or SceneInfoConfig()

    @property
    def config(self) -> SceneInfoConfig:
        """Return current query configuration."""
        return self._config

    # ---- Core query methods (all abstract) --------------------------------

    @abstractmethod
    def get_objects(self, filter_: Any = SceneQueryFilter.ALL) -> list:
        """Get scene objects matching the given filter.

        Args:
            filter_: Object type filter (meshes, cameras, lights, etc.).

        Returns:
            List of standardized object info dicts.

        Raises:
            SceneError: If the query fails.

        """

    @abstractmethod
    def get_hierarchy(self) -> SceneHierarchy:
        """Get the complete scene hierarchy as a tree.

        Returns:
            A SceneHierarchy containing the nested object tree.

        Raises:
            SceneError: If building the hierarchy fails.

        """

    @abstractmethod
    def get_materials(self) -> list:
        """Get all materials used in the scene.

        Returns:
            List of material info with assigned objects and key properties.

        Raises:
            SceneError: If the query fails.

        """

    @abstractmethod
    def get_cameras(self) -> list:
        """Get all cameras in the scene.

        Returns:
            List of camera info with lens settings and transforms.

        Raises:
            SceneError: If the query fails.

        """

    @abstractmethod
    def get_lights(self) -> list:
        """Get all lights in the scene.

        Returns:
            List of light info with intensity, color, type, etc.

        Raises:
            SceneError: If the query fails.

        """

    @abstractmethod
    def get_selection(self) -> list:
        """Get currently selected object names.

        Returns:
            List of selected object name strings.

        Raises:
            SceneError: If the query fails.

        """

    # ---- Convenience methods (default implementations) ---------------------

    def get_full_scene_info(self) -> SceneInfo:
        """Aggregate all scene information into a single result.

        This is the primary method called by MCP tools like ``dcc_get_scene_info``.
        It calls each individual query method and combines the results.

        Returns:
            A complete SceneInfo object.

        Raises:
            SceneError: If any critical query fails.

        """
        try:
            return SceneInfo(
                dcc_type=self._dcc_type(),
                scene_name=self._get_scene_name(),
                objects=self.get_objects(),
                hierarchy=self.get_hierarchy() if self.config.include_hierarchy else None,
                materials=self.get_materials() if self.config.include_materials else [],
                cameras=self.get_cameras(),
                lights=self.get_lights(),
                selection=self.get_selection(),
                metadata=self._get_scene_metadata(),
            )
        except SceneError:
            raise
        except Exception as e:
            raise SceneError(
                f"Failed to gather full scene info: {e}",
                dcc_type=self._dcc_type(),
                cause=e,
            )

    # ---- Subclass hooks ---------------------------------------------------

    @abstractmethod
    def _dcc_type(self) -> str:
        """Return the DCC type identifier string (e.g., 'maya', 'unreal')."""

    def _get_scene_name(self) -> str:
        """Get the current scene/file name. Override for custom behavior."""
        return ""

    def _get_scene_metadata(self) -> dict:
        """Get DCC-specific scene metadata. Override for custom behavior."""
        return {}
