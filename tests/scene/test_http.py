"""Tests for scene/http.py — HTTPSceneInfo implementation.

All tests use mock HTTP responses; no real DCC needed.
Tests are skipped if ``requests`` is not installed.
"""

import json
import pytest

# Skip entire module if requests unavailable
try:
    import requests
    from unittest.mock import MagicMock, patch, PropertyMock

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    MagicMock = type(None)  # placeholder for type hints below


pytestmark = pytest.mark.skipif(
    not REQUESTS_AVAILABLE,
    reason="requests library not installed",
)


if REQUESTS_AVAILABLE:
    from dcc_mcp_ipc.scene.base import (
        CameraInfo,
        LightInfo,
        MaterialInfo,
        ObjectTypeInfo,
        SceneError,
        SceneHierarchy,
        SceneInfoConfig,
        SceneQueryFilter,
        TransformMatrix,
    )
    from dcc_mcp_ipc.scene.http import HTTPSceneInfo, _UNREAL_ACTOR_CLASSES


# =============================================================================
# Fixtures (only defined when requests available)
# =============================================================================

if REQUESTS_AVAILABLE:

    @pytest.fixture
    def mock_session():
        """Return a mocked requests.Session."""
        session = MagicMock(spec=requests.Session)
        return session

    @pytest.fixture
    def http_scene(mock_session) -> HTTPSceneInfo:
        """Create an HTTPSceneInfo with a mocked session."""
        return HTTPSceneInfo(
            dcc_type="unreal",
            base_url="http://localhost:30010",
            timeout=10.0,
            session=mock_session,
        )

    def _make_response(data: dict | list, status_code: int = 200) -> MagicMock:
        """Create a mock HTTP response."""
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = data if isinstance(data, (dict, list)) else {}
        resp.raise_for_status = MagicMock()
        return resp


    # =============================================================================
    # Initialization Tests
    # =============================================================================

    class TestHTTPSceneInfoInit:
        """Tests for HTTPSceneInfo initialization."""

        def test_basic_init(self) -> None:
            si = HTTPSceneInfo(dcc_type="unreal", base_url="http://localhost:30010")
            assert si._dcc_type == "unreal"
            assert si._base_url == "http://localhost:30010"
            assert si._timeout == 30.0

        def test_custom_timeout_and_session(self, mock_session) -> None:
            si = HTTPSceneInfo(
                dcc_type="unity",
                base_url="http://localhost:8080",
                timeout=5.0,
                session=mock_session,
            )
            assert si._timeout == 5.0
            assert si._session is mock_session

        def test_base_url_trailing_slash_stripped(self) -> None:
            si = HTTPSceneInfo(dcc_type="unreal", base_url="http://localhost:30010/")
            assert si._base_url == "http://localhost:30010"

        def test_no_requests_raises(self) -> None:
            """If requests is truly missing, should raise ImportError."""
            with patch.dict("sys.modules", {"requests": None}):
                with patch("dcc_mcp_ipc.scene.http.REQUESTS_AVAILABLE", False):
                    with pytest.raises(ImportError, match="requests"):
                        from dcc_mcp_ipc.scene.http import HTTPSceneInfo as HS
                        HS(dcc_type="unreal")

    # =============================================================================
    # health_check Tests
    # =============================================================================

    class TestHealthCheck:
        """Tests for health_check()."""

        def test_healthy_response(self, http_scene, mock_session) -> None:
            mock_session.get.return_value = _make_response({}, 200)
            assert http_scene.health_check() is True

        def test_server_error_returns_false(self, http_scene, mock_session) -> None:
            mock_session.get.return_value = _make_response({}, 500)
            assert http_scene.health_check() is False

        def test_connection_error_returns_false(self, http_scene, mock_session) -> None:
            mock_session.get.side_effect = requests.ConnectionError("refused")
            assert http_scene.health_check() is False

    # =============================================================================
    # get_objects Tests (Unreal)
    # =============================================================================

    class TestHTTPGetObjects:
        """Tests for HTTPSceneInfo.get_objects() with Unreal RC API."""

        def test_unreal_get_actors(self, http_scene, mock_session) -> None:
            mock_session.post.return_value = _make_response({
                "ReturnValue": [
                    {"Name": "StaticMesh_0", "OuterPath": "/Game/Maps/Main.StaticMesh_0"},
                    {"Name": "StaticMesh_1", "OuterPath": "/Game/Maps/Main.StaticMesh_1"},
                ]
            })
            objects = http_scene.get_objects()
            assert len(objects) == 2
            assert objects[0].name == "StaticMesh_0"
            assert objects[0].type == "StaticMeshActor"

        def test_unreal_filter_cameras(self, http_scene, mock_session) -> None:
            mock_session.post.return_value = _make_response({
                "ReturnValue": [{"Name": "CameraActor", "OuterPath": "/Game/Cameras.CameraActor"}]
            })
            cameras = http_scene.get_objects(SceneQueryFilter.CAMERAS)
            assert len(cameras) == 1
            assert cameras[0].name == "CameraActor"

        def test_unreal_empty_result(self, http_scene, mock_session) -> None:
            mock_session.post.return_value = _make_response({"ReturnValue": []})
            objects = http_scene.get_objects()
            assert objects == []

        def test_unexpected_response_format(self, http_scene, mock_session) -> None:
            mock_session.post.return_value = _make_response({"error": "bad"})
            objects = http_scene.get_objects()
            assert objects == []

        def test_max_objects_limit(self, http_scene, mock_session) -> None:
            many_actors = [{"Name": f"Actor_{i}", "OuterPath": f"/Game/A.Actor_{i}"} for i in range(100)]
            mock_session.post.return_value = _make_response({"ReturnValue": many_actors})

            cfg = SceneInfoConfig(max_objects=5)
            limited_scene = HTTPSceneInfo(
                dcc_type="unreal",
                base_url="http://localhost:30010",
                config=cfg,
                session=mock_session,
            )
            objects = limited_scene.get_objects()
            assert len(objects) <= 5

        def test_unreal_transform_included(self, http_scene, mock_session) -> None:
            actor_resp = _make_response({
                "ReturnValue": [{"Name": "Cube", "OuterPath": "/Game/Cube"}]
            })
            transform_resp = _make_response({
                "ReturnValue": {"X": 10.0, "Y": 20.0, "Z": 30.0}
            })
            mock_session.post.side_effect = [actor_resp, transform_resp]

            objects = http_scene.get_objects()
            assert len(objects) == 1
            tm = objects[0].transform
            assert tm.translation[0] == 10.0

        def test_unreal_transform_skipped_when_disabled(self, mock_session) -> None:
            cfg = SceneInfoConfig(include_transforms=False)
            scene = HTTPSceneInfo(
                dcc_type="unreal",
                base_url="http://localhost:30010",
                config=cfg,
                session=mock_session,
            )
            mock_session.post.return_value = _make_response({
                "ReturnValue": [{"Name": "Cube", "OuterPath": "/Game/Cube"}]
            })
            objects = scene.get_objects()
            assert objects[0].transform.matrix == TransformMatrix().matrix

        def test_unsupported_dcc_raises(self) -> None:
            si = HTTPSceneInfo(dcc_type="unsupported_dcc")
            with pytest.raises(SceneError, match="Unsupported DCC"):
                si.get_objects()

        def test_http_connection_error_wrapped(self, http_scene, mock_session) -> None:
            mock_session.post.side_effect = requests.ConnectionError("connection refused")
            with pytest.raises(SceneError, match="Cannot connect") as exc_info:
                http_scene.get_objects()
            assert exc_info.value.cause is not None

        def test_http_timeout_error_wrapped(self, http_scene, mock_session) -> None:
            mock_session.post.side_effect = requests.Timeout("request timed out")
            with pytest.raises(SceneError, match="timed out") as exc_info:
                http_scene.get_objects()
            assert exc_info.value.cause is not None

        def test_http_server_error_wrapped(self, http_scene, mock_session) -> None:
            bad_resp = MagicMock()
            bad_resp.status_code = 503
            bad_resp.raise_for_status.side_effect = requests.HTTPError(response=bad_resp)
            mock_session.post.return_value = bad_resp
            with pytest.raises(SceneError, match="HTTP error") as exc_info:
                http_scene.get_objects()
            assert exc_info.value.cause is not None

    # =============================================================================
    # get_hierarchy / get_materials / get_cameras / get_lights / get_selection Tests
    # =============================================================================

    class TestHTTPOtherQueries:
        """Tests for hierarchy, materials, cameras, lights, selection."""

        def test_get_hierarchy_from_objects(self, http_scene, mock_session) -> None:
            mock_session.post.return_value = _make_response({
                "ReturnValue": [
                    {"Name": "Parent", "OuterPath": "/Game/Parent"},
                    {"Name": "Child", "OuterPath": "/Game/Parent/Child"},
                ]
            })
            h = http_scene.get_hierarchy()
            assert isinstance(h, SceneHierarchy)
            assert h.total_objects == 2

        def test_get_materials(self, http_scene, mock_session) -> None:
            mock_session.post.return_value = _make_response({
                "ReturnValue": [{
                    "Name": "M_Brick",
                    "MaterialType": "M",
                    "BaseColor": {"R": 0.8, "G": 0.3, "B": 0.1},
                }]
            })
            mats = http_scene.get_materials()
            assert len(mats) == 1
            assert mats[0].name == "M_Brick"
            assert mats[0].type == "M"

        def test_get_cameras_with_fov(self, http_scene, mock_session) -> None:
            actor_resp = _make_response({
                "ReturnValue": [{"Name": "Cam", "OuterPath": "/Game/Cam"}]
            })
            fov_resp = _make_response({"PropertyValue": 90.0})
            mock_session.post.side_effect = [actor_resp, fov_resp]

            cams = http_scene.get_cameras()
            assert len(cams) == 1
            assert cams[0].field_of_view == 90.0

        def test_get_lights_point(self, http_scene, mock_session) -> None:
            comp_resp = _make_response({
                "ReturnValue": [{"Name": "PLight", "OuterPath": "/Game/PLight"}]
            })
            int_resp = _make_response({"PropertyValue": 1.5})
            col_resp = _make_response({"PropertyValue": {"R": 1.0, "G": 1.0, "B": 0.9}})
            mock_session.post.side_effect = [comp_resp, int_resp, col_resp]

            lights = http_scene.get_lights()
            assert len(lights) == 1
            assert lights[0].type == "point"
            assert lights[0].intensity == 1.5
            assert lights[0].color == (1.0, 1.0, 0.9)

        def test_get_lights_multiple_types(self, mock_session) -> None:
            """Test that all light types are queried."""
            scene = HTTPSceneInfo(
                dcc_type="unreal",
                base_url="http://localhost:30010",
                session=mock_session,
            )

            # Each light class returns empty + point returns one light
            responses = []
            for _ in range(8):  # 4 types x 2 queries each
                responses.append(_make_response({"ReturnValue": []}))
            # Insert one point light response
            responses[2] = _make_response({"ReturnValue": [{"Name": "PointLight1", "OuterPath": "/Game/PL1"}]})
            responses[3] = _make_response({"PropertyValue": 2.0})  # intensity
            responses[4] = _make_response({"PropertyValue": {"R": 1, "G": 1, "B": 1}})  # color

            mock_session.post.side_effect = responses
            lights = scene.get_lights()
            # At least the point light should be returned
            assert any(l.type == "point" for l in lights)

        def test_get_selection(self, http_scene, mock_session) -> None:
            mock_session.post.return_value = _make_response({
                "ReturnValue": [
                    {"Name": "SelectedCube", "OuterPath": "/Game/Cube"},
                    {"Name": "SelectedSphere", "OuterPath": "/Game/Sphere"},
                ]
            })
            sel = http_scene.get_selection()
            assert sel == ["SelectedCube", "SelectedSphere"]

        def test_get_materials_fallback_on_error(self, http_scene, mock_session) -> None:
            mock_session.post.side_effect = Exception("materials endpoint error")
            mats = http_scene.get_materials()
            assert mats == []

        def test_get_cameras_fallback_on_error(self, http_scene, mock_session) -> None:
            mock_session.post.side_effect = Exception("camera query fail")
            cams = http_scene.get_cameras()
            assert cams == []

        def test_lights_fallback_on_error(self, http_scene, mock_session) -> None:
            mock_session.post.side_effect = Exception("light query fail")
            lights = http_scene.get_lights()
            assert lights == []

        def test_selection_fallback_on_error(self, http_scene, mock_session) -> None:
            mock_session.post.side_effect = Exception("selection fail")
            sel = http_scene.get_selection()
            assert sel == []

    # =============================================================================
    # _get_scene_name / _get_scene_metadata Tests
    # =============================================================================

    class TestHTTPMetadata:
        """Tests for HTTP-based metadata queries."""

        def test_unreal_level_name(self, http_scene, mock_session) -> None:
            mock_session.post.return_value = _make_response({"ReturnValue": "/Game/Maps/MainLevel"})
            name = http_scene._get_scene_name()
            assert name == "/Game/Maps/MainLevel"

        def test_unreal_metadata(self, http_scene, mock_session) -> None:
            mock_session.post.return_value = _make_response({"ReturnValue": "MainLevel"})
            meta = http_scene._get_scene_metadata()
            assert "level" in meta

        def test_metadata_graceful_failure(self, http_scene, mock_session) -> None:
            mock_session.post.side_effect = Exception("metadata unavailable")
            meta = http_scene._get_scene_metadata()
            assert meta == {}

    # =============================================================================
    # Unity stub Tests
    # =============================================================================

    class TestUnityStub:
        """Tests that Unity path returns empty and logs info."""

        def test_unity_get_objects_returns_empty(self, mock_session) -> None:
            si = HTTPSceneInfo(dcc_type="unity", base_url="http://localhost:8080", session=mock_session)
            objects = si.get_objects()
            assert objects == []

    # =============================================================================
    # URL Mapping & Helper Tests
    # =============================================================================

    class TestURLMapping:
        """Tests for filter-to-class mapping and URL building."""

        def test_all_maps_to_multiple_classes(self) -> None:
            classes = HTTPSceneInfo._map_filter_to_unreal_classes(SceneQueryFilter.ALL)
            assert len(classes) >= 3
            assert any("StaticMesh" in c for c in classes)
            assert any("Camera" in c for c in classes)

        def test_meshes_maps_only_meshes(self) -> None:
            classes = HTTPSceneInfo._map_filter_to_unreal_classes(SceneQueryFilter.MESHES)
            assert all("StaticMesh" in c for c in classes)

        def test_extract_unreal_type(self) -> None:
            assert "StaticMeshActor" in HTTPSceneInfo._extract_unreal_type("/Script/Engine.StaticMeshActor")

        def test_build_hierarchy_from_objects(self) -> None:
            objs = [
                ObjectTypeInfo(name="Root", type="group", parent="", path="/Root"),
                ObjectTypeInfo(name="A", type="mesh", parent="Root", path="/Root/A"),
                ObjectTypeInfo(name="B", type="mesh", parent="A", path="/Root/A/B"),
            ]
            h = HTTPSceneInfo._build_hierarchy_from_objects(objs)
            assert h.total_objects == 3
            assert h.max_depth >= 2

        def test_build_hierarchy_empty(self) -> None:
            h = HTTPSceneInfo._build_hierarchy_from_objects([])
            assert h.total_objects == 0

    # =============================================================================
    # Request Method Tests
    # =============================================================================

    class TestRequestMethod:
        """Tests for internal _request method."""

        def test_post_success(self, http_scene, mock_session) -> None:
            mock_session.post.return_value = _make_response({"ok": True}, 200)
            result = http_scene._request("post", "/test/path", json={"key": "val"})
            mock_session.post.assert_called_once()

        def test_post_connection_error(self, http_scene, mock_session) -> None:
            mock_session.post.side_effect = requests.ConnectionError("down")
            with pytest.raises(SceneError, match="Cannot connect"):
                http_scene._request("post", "/test")

        def test_post_timeout(self, http_scene, mock_session) -> None:
            mock_session.post.side_effect = requests.Timeout()
            with pytest.raises(SceneError, match="timed out"):
                http_scene._request("post", "/test")

        def test_post_http_error(self, http_scene, mock_session) -> None:
            err_resp = MagicMock(status_code=404)
            err_resp.raise_for_status.side_effect = requests.HTTPError(response=err_resp)
            mock_session.post.return_value = err_resp
            with pytest.raises(SceneError, match="HTTP error"):
                http_scene._request("post", "/notfound")

    # =============================================================================
    # Full Integration Test via get_full_scene_info
    # =============================================================================

    class TestHTTPFullSceneInfo:
        """Integration test for get_full_scene_info over HTTP."""

        def test_aggregation(self, mock_session) -> None:
            def side_effect(*args, **kwargs):
                url = args[0] if args else kwargs.get("url", "")
                data = json.dumps(kwargs.get("json", {})) if "json" in kwargs else ""

                if "/property" in url or ("functionName" in data and "FOV" in data):
                    return _make_response({"PropertyValue": 75.0})

                return _make_response({
                    "ReturnValue": (
                        [{"Name": "SM_Cube", "OuterPath": "/Game/Cube"}]
                        if "ActorsOfClass" in data or "ComponentsOfClass" not in data
                        else []
                    ) if "call" in url
                    else []
                })

            mock_session.post.side_effect = side_effect

            si = HTTPSceneInfo(
                dcc_type="unreal",
                base_url="http://localhost:30010",
                timeout=5.0,
                session=mock_session,
            )
            result = si.get_full_scene_info()
            assert isinstance(result, SceneInfo)
            assert result.dcc_type == "unreal"
            assert len(result.objects) > 0
