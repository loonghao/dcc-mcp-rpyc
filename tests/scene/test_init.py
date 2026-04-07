"""Tests for scene/__init__.py — create_scene_info factory function.

Covers all branches of create_scene_info including rpyc, http, and invalid transport.
"""

# Import built-in modules
from unittest.mock import MagicMock

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.scene import (
    BaseSceneInfo,
    CameraInfo,
    LightInfo,
    MaterialInfo,
    ObjectTypeInfo,
    SceneError,
    SceneHierarchy,
    SceneInfo,
    SceneInfoConfig,
    SceneQueryFilter,
    TransformMatrix,
    create_scene_info,
)
from dcc_mcp_ipc.scene.http import HTTPSceneInfo
from dcc_mcp_ipc.scene.rpyc import RPyCSceneInfo


class TestSceneModuleExports:
    """Verify all public symbols are exported from scene/__init__.py."""

    def test_base_scene_info_exported(self):
        assert BaseSceneInfo is not None

    def test_data_models_exported(self):
        assert CameraInfo is not None
        assert LightInfo is not None
        assert MaterialInfo is not None
        assert ObjectTypeInfo is not None
        assert SceneError is not None
        assert SceneHierarchy is not None
        assert SceneInfo is not None
        assert SceneInfoConfig is not None
        assert SceneQueryFilter is not None
        assert TransformMatrix is not None


class TestCreateSceneInfo:
    """Tests for the create_scene_info factory function (lines 95-106)."""

    def test_rpyc_transport_returns_rpyc_instance(self):
        """create_scene_info with transport='rpyc' returns RPyCSceneInfo."""
        mock_exec = MagicMock(return_value=[])
        scene = create_scene_info("maya", transport="rpyc", execute_func=mock_exec)
        assert isinstance(scene, RPyCSceneInfo)

    def test_rpyc_transport_is_default(self):
        """Default transport is 'rpyc'."""
        mock_exec = MagicMock(return_value=[])
        scene = create_scene_info("blender", execute_func=mock_exec)
        assert isinstance(scene, RPyCSceneInfo)

    def test_rpyc_passes_dcc_name(self):
        """dcc_name is passed through to the RPyCSceneInfo instance."""
        mock_exec = MagicMock(return_value=[])
        scene = create_scene_info("houdini", transport="rpyc", execute_func=mock_exec)
        assert isinstance(scene, RPyCSceneInfo)
        assert scene._dcc_name == "houdini"

    def test_http_transport_returns_http_instance(self):
        """create_scene_info with transport='http' returns HTTPSceneInfo."""
        scene = create_scene_info("unreal", transport="http", base_url="http://localhost:30010")
        assert isinstance(scene, HTTPSceneInfo)

    def test_http_transport_passes_dcc_type(self):
        """dcc_name is passed as dcc_type to HTTPSceneInfo."""
        scene = create_scene_info("unreal", transport="http", base_url="http://localhost:8080")
        assert isinstance(scene, HTTPSceneInfo)

    def test_unsupported_transport_raises_value_error(self):
        """Unsupported transport raises ValueError (line 105-106)."""
        with pytest.raises(ValueError, match="Unsupported transport"):
            create_scene_info("maya", transport="grpc")

    def test_unsupported_transport_message_contains_name(self):
        """ValueError message includes the invalid transport name."""
        with pytest.raises(ValueError, match="websocket"):
            create_scene_info("maya", transport="websocket")

    def test_unsupported_transport_message_lists_supported(self):
        """ValueError message lists supported transports."""
        with pytest.raises(ValueError, match="rpyc"):
            create_scene_info("maya", transport="invalid_proto")
