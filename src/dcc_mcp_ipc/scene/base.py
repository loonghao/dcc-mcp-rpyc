"""Base classes and data models for the scene information system.

This module defines the abstract interface for querying scene information
across different DCC applications, as well as the standardized data models
for representing objects, hierarchies, materials, cameras, and lights.
"""

# Import built-in modules
from abc import ABC
from abc import abstractmethod
from enum import Enum
from typing import Any

# Import third-party modules
from pydantic import BaseModel
from pydantic import Field

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class TransformMatrix(BaseModel):
    """4x4 transformation matrix for object position/rotation/scale.

    Stored as a flat list of 16 floats in row-major order, compatible with
    Maya, Blender, Unreal, and Unity matrix conventions.
    """

    matrix: list[float] = Field(
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
        ],
        description="4x4 transformation matrix (row-major, 16 floats)",
    )

    @property
    def translation(self) -> tuple[float, float, float]:
        """Extract translation component (tx, ty, tz)."""
        m = self.matrix
        return (m[12], m[13], m[14])

    @property
    def rotation(self) -> tuple[float, float, float]:
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
    def scale(self) -> tuple[float, float, float]:
        """Extract scale component (sx, sy, sz)."""
        # Import built-in modules
        import math

        m = self.matrix
        sx = math.sqrt(m[0] ** 2 + m[1] ** 2 + m[2] ** 2)
        sy = math.sqrt(m[4] ** 2 + m[5] ** 2 + m[6] ** 2)
        sz = math.sqrt(m[8] ** 2 + m[9] ** 2 + m[10] ** 2)
        return (sx, sy, sz)


class ObjectTypeInfo(BaseModel):
    """Information about a single scene object.

    All DCC implementations return this standardized format so that the MCP
    layer can present a uniform interface regardless of the underlying DCC.
    """

    name: str = Field(description="Unique name of the object")
    type: str = Field(description="DCC-specific type (e.g., 'mesh', 'camera', 'light')")
    path: str = Field(default="", description="Full DAG/hierarchy path to the object")
    parent: str = Field(default="", description="Parent object name, empty if root-level")
    children: list[str] = Field(default_factory=list, description="Names of child objects")
    transform: TransformMatrix = Field(
        default_factory=TransformMatrix,
        description="World-space transformation matrix",
    )
    visibility: bool = Field(default=True, description="Whether the object is visible")
    material: str = Field(default="", description="Assigned material name, if any")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="DCC-specific additional attributes",
    )


class SceneHierarchy(BaseModel):
    """Hierarchical representation of scene objects as a tree."""

    root_name: str = Field(description="Name of the root / world node")
    total_objects: int = Field(default=0, description="Total number of objects in tree")
    max_depth: int = Field(default=0, description="Maximum hierarchy depth")
    tree: dict[str, Any] = Field(
        default_factory=dict,
        description="Nested dict representing the object hierarchy",
    )


class MaterialInfo(BaseModel):
    """Information about a material/shader in the scene."""

    name: str = Field(description="Material name")
    type: str = Field(description="Shader type (e.g., 'StandardSurface', 'PrincipledBSDF')")
    assigned_objects: list[str] = Field(
        default_factory=list,
        description="Objects using this material",
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Key material parameters (color, roughness, metalness, etc.)",
    )


class CameraInfo(BaseModel):
    """Information about a camera in the scene."""

    name: str = Field(description="Camera name")
    type: str = Field(default="perspective", description="'perspective' or 'orthographic'")
    focal_length: float = Field(default=35.0, description="Focal length in mm")
    sensor_width: float = Field(default=36.0, description="Sensor/film width in mm")
    sensor_height: float = Field(default=24.0, description="Sensor/film height in mm")
    near_clip: float = Field(default=0.1, description="Near clipping plane")
    far_clip: float = Field(default=10000.0, description="Far clipping plane")
    field_of_view: float = Field(default=54.4, description="Vertical field of view in degrees")
    aspect_ratio: float = Field(default=1.5, description="Aspect ratio (width/height)")
    transform: TransformMatrix = Field(
        default_factory=TransformMatrix,
        description="World-space camera transform",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="DCC-specific camera attributes",
    )


class LightInfo(BaseModel):
    """Information about a light in the scene."""

    name: str = Field(description="Light name")
    type: str = Field(description="Light type: 'directional', 'point', 'spot', 'area', 'ambient'")
    intensity: float = Field(default=1.0, description="Light intensity / strength")
    color: tuple[float, float, float] = Field(
        default=(1.0, 1.0, 1.0),
        description="RGB color as (r, g, b), each 0.0-1.0",
    )
    temperature: float | None = Field(default=None, description="Color temperature in Kelvin")
    transform: TransformMatrix = Field(
        default_factory=TransformMatrix,
        description="World-space light transform",
    )
    enabled: bool = Field(default=True, description="Whether the light is on")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="DCC-specific light attributes (cone angle, decay radius, etc.)",
    )


class SceneInfo(BaseModel):
    """Complete scene information container.

    Aggregates all scene query results into a single serializable structure
    that can be returned to the MCP layer as JSON.
    """

    dcc_type: str = Field(description="DCC application type (e.g., 'maya', 'unreal')")
    scene_name: str = Field(default="", description="Current scene/file name")
    object_count: int = Field(default=0, description="Total number of objects")
    objects: list[ObjectTypeInfo] = Field(
        default_factory=list,
        description="All scene objects matching the filter",
    )
    hierarchy: SceneHierarchy | None = Field(default=None, description="Scene hierarchy tree")
    materials: list[MaterialInfo] = Field(
        default_factory=list,
        description="All materials in the scene",
    )
    cameras: list[CameraInfo] = Field(
        default_factory=list,
        description="All cameras in the scene",
    )
    lights: list[LightInfo] = Field(
        default_factory=list,
        description="All lights in the scene",
    )
    selection: list[str] = Field(
        default_factory=list,
        description="Currently selected object names",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Scene-level metadata (frame range, units, etc.)",
    )


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


class SceneInfoConfig(BaseModel):
    """Configuration for scene info queries."""

    include_transforms: bool = Field(
        default=True,
        description="Include transformation matrices (expensive for large scenes)",
    )
    include_materials: bool = Field(
        default=True,
        description="Include material assignments on objects",
    )
    include_hierarchy: bool = Field(
        default=True,
        description="Build full hierarchy tree",
    )
    include_metadata: bool = Field(
        default=False,
        description="Include DCC-specific metadata attributes",
    )
    max_objects: int = Field(
        default=10000,
        description="Maximum number of objects to return (pagination)",
    )
    page_offset: int = Field(default=0, description="Offset for paginated results")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SceneError(Exception):
    """Base exception for scene information errors."""

    def __init__(self, message: str, dcc_type: str = "", cause: Exception | None = None):
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

    def __init__(self, config: SceneInfoConfig | None = None):
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
    def get_objects(self, filter_: str | SceneQueryFilter = SceneQueryFilter.ALL) -> list[ObjectTypeInfo]:
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
    def get_materials(self) -> list[MaterialInfo]:
        """Get all materials used in the scene.

        Returns:
            List of material info with assigned objects and key properties.

        Raises:
            SceneError: If the query fails.

        """

    @abstractmethod
    def get_cameras(self) -> list[CameraInfo]:
        """Get all cameras in the scene.

        Returns:
            List of camera info with lens settings and transforms.

        Raises:
            SceneError: If the query fails.

        """

    @abstractmethod
    def get_lights(self) -> list[LightInfo]:
        """Get all lights in the scene.

        Returns:
            List of light info with intensity, color, type, etc.

        Raises:
            SceneError: If the query fails.

        """

    @abstractmethod
    def get_selection(self) -> list[str]:
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

    def _get_scene_metadata(self) -> dict[str, Any]:
        """Get DCC-specific scene metadata. Override for custom behavior."""
        return {}
