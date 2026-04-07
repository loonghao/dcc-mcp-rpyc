"""Tests for scene/base.py — data models, enums, and BaseSceneInfo ABC.

Covers TransformMatrix, ObjectTypeInfo, SceneHierarchy, MaterialInfo,
CameraInfo, LightInfo, SceneInfo, SceneInfoConfig, SceneQueryFilter,
SceneError, and the BaseSceneInfo abstract interface.
"""

# Import built-in modules
import math

# Import third-party modules
import pytest

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

# =============================================================================
# TransformMatrix Tests
# =============================================================================


class TestTransformMatrix:
    """Tests for the TransformMatrix data model."""

    def test_default_identity_matrix(self) -> None:
        tm = TransformMatrix()
        assert len(tm.matrix) == 16
        # Identity matrix: diagonal is 1.0
        for i in range(4):
            assert tm.matrix[i * 4 + i] == pytest.approx(1.0)

    def test_custom_matrix(self) -> None:
        mat = list(range(16))
        tm = TransformMatrix(matrix=mat)
        assert tm.matrix == list(range(16))

    def test_translation_property(self) -> None:
        tx, ty, tz = 10.0, 20.0, 30.0
        tm = TransformMatrix(
            matrix=[
                1,
                0,
                0,
                0,
                0,
                1,
                0,
                0,
                0,
                0,
                1,
                0,
                tx,
                ty,
                tz,
                1,
            ]
        )
        t = tm.translation
        assert t[0] == pytest.approx(tx)
        assert t[1] == pytest.approx(ty)
        assert t[2] == pytest.approx(tz)

    def test_rotation_property(self) -> None:
        # Simple rotation around Z axis by 45 degrees
        angle_rad = math.radians(45)
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        tm = TransformMatrix(
            matrix=[
                c,
                s,
                0,
                0,
                -s,
                c,
                0,
                0,
                0,
                0,
                1,
                0,
                0,
                0,
                0,
                1,
            ]
        )
        _rx, _ry, rz = tm.rotation
        assert abs(rz) == pytest.approx(45.0, abs=0.5)

    def test_scale_property(self) -> None:
        sx, sy, sz = 2.0, 3.0, 4.0
        tm = TransformMatrix(
            matrix=[
                sx,
                0,
                0,
                0,
                0,
                sy,
                0,
                0,
                0,
                0,
                sz,
                0,
                0,
                0,
                0,
                1,
            ]
        )
        sc = tm.scale
        assert sc[0] == pytest.approx(sx)
        assert sc[1] == pytest.approx(sy)
        assert sc[2] == pytest.approx(sz)

    def test_serialization(self) -> None:
        # Import built-in modules
        from dataclasses import asdict

        tm = TransformMatrix()
        data = asdict(tm)
        assert "matrix" in data
        assert len(data["matrix"]) == 16


# =============================================================================
# ObjectTypeInfo Tests
# =============================================================================


class TestObjectTypeInfo:
    """Tests for the ObjectTypeInfo data model."""

    def test_minimal_creation(self) -> None:
        obj = ObjectTypeInfo(name="cube", type="mesh")
        assert obj.name == "cube"
        assert obj.type == "mesh"
        assert obj.parent == ""
        assert obj.children == []
        assert obj.visibility is True
        assert obj.material == ""

    def test_full_object(self) -> None:
        transform = TransformMatrix()
        obj = ObjectTypeInfo(
            name="pSphere1",
            type="mesh",
            path="|pSphere1",
            parent="|world",
            children=["pSphereShape1"],
            visibility=True,
            material="lambert1",
            transform=transform,
            metadata={"vertex_count": 962},
        )
        assert obj.name == "pSphere1"
        assert obj.material == "lambert1"
        assert obj.metadata["vertex_count"] == 962
        assert isinstance(obj.transform, TransformMatrix)


# =============================================================================
# SceneHierarchy Tests
# =============================================================================


class TestSceneHierarchy:
    """Tests for the SceneHierarchy data model."""

    def test_empty_hierarchy(self) -> None:
        h = SceneHierarchy(root_name="world")
        assert h.root_name == "world"
        assert h.total_objects == 0
        assert h.max_depth == 0
        assert h.tree == {}

    def test_nested_tree(self) -> None:
        tree = {
            "name": "root",
            "children": [
                {"name": "child_a", "children": []},
                {
                    "name": "child_b",
                    "children": [
                        {"name": "grandchild", "children": []},
                    ],
                },
            ],
        }
        h = SceneHierarchy(
            root_name="root",
            total_objects=4,
            max_depth=2,
            tree=tree,
        )
        assert h.total_objects == 4
        assert h.max_depth == 2
        assert len(h.tree["children"]) == 2


# =============================================================================
# MaterialInfo / CameraInfo / LightInfo Tests
# =============================================================================


class TestMaterialInfo:
    """Tests for MaterialInfo."""

    def test_material(self) -> None:
        mat = MaterialInfo(
            name="blinn1SG",
            type="Blinn",
            assigned_objects=["pCube1", "pSphere1"],
            properties={"color": (0.5, 0.5, 0.5), "specular": 0.8},
        )
        assert mat.type == "Blinn"
        assert len(mat.assigned_objects) == 2
        assert mat.properties["color"] == (0.5, 0.5, 0.5)


class TestCameraInfo:
    """Tests for CameraInfo."""

    def test_camera_defaults(self) -> None:
        cam = CameraInfo(name="persp")
        assert cam.focal_length == 35.0
        assert cam.field_of_view == 54.4
        assert cam.near_clip == 0.1
        assert cam.far_clip == 10000.0
        assert cam.type == "perspective"

    def test_orthographic_camera(self) -> None:
        cam = CameraInfo(
            name="top",
            type="orthographic",
            focal_length=0,
            field_of_view=30.0,
            aspect_ratio=1.333,
        )
        assert cam.type == "orthographic"
        assert cam.aspect_ratio == 1.333


class TestLightInfo:
    """Tests for LightInfo."""

    def test_point_light(self) -> None:
        light = LightInfo(
            name="pointLight1",
            type="point",
            intensity=1.5,
            color=(1.0, 0.9, 0.8),
            enabled=True,
        )
        assert light.type == "point"
        assert light.intensity == 1.5
        assert light.color == (1.0, 0.9, 0.8)
        assert light.enabled is True

    def test_directional_light(self) -> None:
        light = LightInfo(
            name="sunLight",
            type="directional",
            intensity=2.0,
            temperature=6500.0,
        )
        assert light.temperature == 6500.0


# =============================================================================
# SceneInfo Tests (aggregate)
# =============================================================================


class TestSceneInfo:
    """Tests for the aggregate SceneInfo container."""

    def test_empty_scene(self) -> None:
        info = SceneInfo(dcc_type="maya")
        assert info.dcc_type == "maya"
        assert info.object_count == 0
        assert info.objects == []
        assert info.selection == []

    def test_populated_scene(self) -> None:
        info = SceneInfo(
            dcc_type="unreal",
            scene_name="MainLevel",
            object_count=42,
            objects=[ObjectTypeInfo(name="StaticMesh_0", type="mesh")],
            cameras=[CameraInfo(name="CameraActor")],
            lights=[LightInfo(name="PointLight_0", type="point")],
            selection=["StaticMesh_0"],
            metadata={"frame_rate": 30},
        )
        assert info.scene_name == "MainLevel"
        assert info.object_count == 42
        assert len(info.cameras) == 1
        assert len(info.lights) == 1
        assert info.metadata["frame_rate"] == 30


# =============================================================================
# SceneInfoConfig & SceneQueryFilter Tests
# =============================================================================


class TestSceneInfoConfig:
    """Tests for SceneInfoConfig."""

    def test_defaults(self) -> None:
        cfg = SceneInfoConfig()
        assert cfg.include_transforms is True
        assert cfg.include_materials is True
        assert cfg.include_hierarchy is True
        assert cfg.max_objects == 10000
        assert cfg.page_offset == 0

    def test_custom_config(self) -> None:
        cfg = SceneInfoConfig(
            include_transforms=False,
            include_metadata=True,
            max_objects=500,
        )
        assert cfg.include_transforms is False
        assert cfg.include_metadata is True
        assert cfg.max_objects == 500


class TestSceneQueryFilter:
    """Tests for SceneQueryFilter enum."""

    def test_all_values(self) -> None:
        expected = [
            "all",
            "meshes",
            "cameras",
            "lights",
            "shapes",
            "joints",
            "visible_only",
            "selected_only",
            "custom",
        ]
        actual = [f.value for f in SceneQueryFilter]
        assert sorted(actual) == sorted(expected)

    def test_string_comparison(self) -> None:
        assert SceneQueryFilter.MESHES == "meshes"
        assert SceneQueryFilter.CAMERAS.value == "cameras"


# =============================================================================
# SceneError Tests
# =============================================================================


class TestSceneError:
    """Tests for SceneError exception."""

    def test_basic_error(self) -> None:
        err = SceneError("something failed")
        assert "something failed" in str(err)
        assert err.dcc_type == ""
        assert err.cause is None

    def test_error_with_dcc_and_cause(self) -> None:
        cause = ValueError("original error")
        err = SceneError("remote call failed", dcc_type="maya", cause=cause)
        assert "[maya]" in str(err)
        assert "remote call failed" in str(err)
        assert err.cause is cause


# =============================================================================
# BaseSceneInfo Abstract Interface Tests
# =============================================================================


def _make_concrete_scene_info(**kwargs) -> BaseSceneInfo:
    """Create a concrete subclass of BaseSceneInfo for testing."""

    class ConcreteSceneInfo(BaseSceneInfo):
        def __init__(self, dcc_type="test_dcc", **kw):
            self._my_dcc_type = dcc_type
            super().__init__(**kw)

        def _dcc_type(self) -> str:
            return self._my_dcc_type

        def get_objects(self, filter_=None):
            return []

        def get_hierarchy(self):
            return SceneHierarchy(root_name="world")

        def get_materials(self):
            return []

        def get_cameras(self):
            return []

        def get_lights(self):
            return []

        def get_selection(self):
            return []

    return ConcreteSceneInfo(**kwargs)


class TestBaseSceneInfo:
    """Tests for the BaseSceneInfo abstract base class behavior."""

    def test_config_default(self) -> None:
        si = _make_concrete_scene_info()
        assert si.config.include_transforms is True
        assert si.config.max_objects == 10000

    def test_config_custom(self) -> None:
        cfg = SceneInfoConfig(include_transforms=False, max_objects=100)
        si = _make_concrete_scene_info(config=cfg)
        assert si.config.include_transforms is False
        assert si.config.max_objects == 100

    def test_get_full_scene_info(self) -> None:
        """Test that get_full_scene_info aggregates all sub-queries."""
        obj = ObjectTypeInfo(name="test_obj", type="mesh")
        cam = CameraInfo(name="cam1")
        light = LightInfo(name="light1", type="point")

        class FullTestScene(BaseSceneInfo):
            def _dcc_type(self):
                return "test"

            def get_objects(self, f=None):
                return [obj]

            def get_hierarchy(self):
                return SceneHierarchy(
                    root_name="world",
                    total_objects=1,
                    tree={"name": "world", "children": [{"name": "test_obj", "children": []}]},
                )

            def get_materials(self):
                return [MaterialInfo(name="mat1", type="Lambert")]

            def get_cameras(self):
                return [cam]

            def get_lights(self):
                return [light]

            def get_selection(self):
                return ["test_obj"]

        si = FullTestScene()
        result = si.get_full_scene_info()

        assert isinstance(result, SceneInfo)
        assert result.dcc_type == "test"
        assert result.object_count == 1
        assert len(result.objects) == 1
        assert result.objects[0].name == "test_obj"
        assert len(result.cameras) == 1
        assert len(result.lights) == 1
        assert result.selection == ["test_obj"]
        assert len(result.materials) == 1
        assert result.hierarchy is not None
        assert result.hierarchy.total_objects == 1

    def test_get_full_scene_info_excludes_optional_when_configured(self) -> None:
        """Test that optional fields are omitted when config disables them."""

        class MinimalScene(BaseSceneInfo):
            def _dcc_type(self):
                return "minimal"

            def get_objects(self, f=None):
                return []

            def get_hierarchy(self):
                raise NotImplementedError

            def get_materials(self):
                raise NotImplementedError

            def get_cameras(self):
                return []

            def get_lights(self):
                return []

            def get_selection(self):
                return []

        cfg = SceneInfoConfig(include_hierarchy=False, include_materials=False)
        si = MinimalScene(config=cfg)
        result = si.get_full_scene_info()

        assert result.hierarchy is None
        assert result.materials == []

    def test_get_full_scene_info_propagates_scene_error(self) -> None:
        """Ensure SceneError from sub-queries propagates unchanged."""

        class FailingScene(BaseSceneInfo):
            def _dcc_type(self):
                return "failing"

            def get_objects(self, f=None):
                raise SceneError("objects fail", dcc_type="failing")

            def get_hierarchy(self): ...
            def get_materials(self): ...
            def get_cameras(self): ...
            def get_lights(self): ...
            def get_selection(self): ...

        si = FailingScene()
        with pytest.raises(SceneError, match="objects fail"):
            si.get_full_scene_info()

    def test_get_full_scene_info_wraps_generic_exception(self) -> None:
        """Generic exceptions should be wrapped as SceneError."""

        class BrokenScene(BaseSceneInfo):
            def _dcc_type(self):
                return "broken"

            def get_objects(self, f=None):
                raise RuntimeError("boom")

            def get_hierarchy(self): ...
            def get_materials(self): ...
            def get_cameras(self): ...
            def get_lights(self): ...
            def get_selection(self): ...

        si = BrokenScene()
        with pytest.raises(SceneError, match="boom"):
            si.get_full_scene_info()

    def test_dcc_type_hook(self) -> None:
        si = _make_concrete_scene_info(dcc_type="houdini")
        assert si._dcc_type() == "houdini"


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Miscellaneous edge case tests."""

    def test_large_transform_values(self) -> None:
        big = [float(i * 1000.0) for i in range(16)]
        tm = TransformMatrix(matrix=big)
        assert tm.matrix == big
        assert len(tm.translation) == 3

    def test_zero_scale_matrix(self) -> None:
        tm = TransformMatrix(
            matrix=[
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                5,
                6,
                7,
                1,
            ]
        )
        sc = tm.scale
        assert sc == (0.0, 0.0, 0.0)

    def test_scene_error_chain(self) -> None:
        inner = RuntimeError("network timeout")
        outer = SceneError("cannot reach DCC", dcc_type="unreal", cause=inner)
        # Python's Exception.__cause__ is only set when using 'raise ... from'
        # Our custom cause attribute stores the original exception
        assert outer.cause is inner

    def test_object_with_empty_children(self) -> None:
        obj = ObjectTypeInfo(name="orphan", type="joint", children=[])
        assert obj.children == []
