"""HTTP transport implementation for scene information queries.

Supports Unreal Engine Remote Control API and Unity HTTP-based communication.
Uses ``requests`` as an optional dependency — falls back gracefully when unavailable.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Union

# Import third-party modules (optional)
try:
    # Import third-party modules
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Import local modules
from dcc_mcp_ipc.scene.base import BaseSceneInfo
from dcc_mcp_ipc.scene.base import CameraInfo
from dcc_mcp_ipc.scene.base import LightInfo
from dcc_mcp_ipc.scene.base import MaterialInfo
from dcc_mcp_ipc.scene.base import ObjectTypeInfo
from dcc_mcp_ipc.scene.base import SceneError
from dcc_mcp_ipc.scene.base import SceneHierarchy
from dcc_mcp_ipc.scene.base import SceneQueryFilter
from dcc_mcp_ipc.scene.base import TransformMatrix

# Configure logging
logger = logging.getLogger(__name__)


class HTTPSceneInfo(BaseSceneInfo):
    """HTTP-based scene info implementation for Unreal Engine and Unity.

    Communicates with the DCC's HTTP endpoint (e.g., Unreal Remote Control API
    on port 30010, or Unity's custom HTTP listener).

    Usage::

        http_scene = HTTPSceneInfo(base_url="http://localhost:30010", dcc_type="unreal")
        objects = http_scene.get_objects()
    """

    def __init__(
        self,
        dcc_type: str = "unreal",
        base_url: str = "http://localhost:30010",
        timeout: float = 30.0,
        session=None,
        config=None,
    ):
        """Initialize the HTTP scene info client.

        Args:
            dcc_type: DCC type ("unreal" or "unity").
            base_url: Base URL of the HTTP endpoint.
            timeout: HTTP request timeout in seconds.
            session: Optional ``requests.Session`` for connection reuse.
            config: Optional SceneInfoConfig.

        """
        super().__init__(config=config)
        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "The 'requests' package is required for HTTPSceneInfo. Install it with: pip install requests"
            )

        self._dcc_type_val = dcc_type.lower()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = session or requests.Session()

    # ---- Abstract implementations ------------------------------------------

    def _dcc_type(self) -> str:
        return self._dcc_type_val

    def _get_scene_name(self) -> str:
        """Get current level/scene name."""
        if self._dcc_type_val == "unreal":
            try:
                resp = self._request(
                    "post",
                    "/remote/object/call",
                    json={
                        "objectPath": "/Game/Editors/PIE/GameInstance",
                        "functionName": "GetCurrentLevelName",
                        "parameters": {"generateReturnValue": True},
                    },
                )
                data = resp.json() if isinstance(resp, requests.Response) else resp
                return str(data.get("ReturnValue", ""))
            except Exception:
                pass
        return ""

    def get_objects(self, filter_: Union[str, SceneQueryFilter] = SceneQueryFilter.ALL) -> list[ObjectTypeInfo]:
        """Get scene objects via HTTP."""
        if self._dcc_type_val == "unreal":
            return self._unreal_get_objects(filter_)
        elif self._dcc_type_val == "unity":
            return self._unity_get_objects(filter_)
        raise SceneError(f"Unsupported DCC type for HTTP: {self._dcc_type_val}", dcc_type=self._dcc_type)

    def get_hierarchy(self) -> SceneHierarchy:
        """Get scene hierarchy."""
        objects = self.get_objects()
        return HTTPSceneInfo._build_hierarchy_from_objects(objects)

    def get_materials(self) -> list[MaterialInfo]:
        """Get materials."""
        if self._dcc_type_val == "unreal":
            return self._unreal_get_materials()
        return []

    def get_cameras(self) -> list[CameraInfo]:
        """Get cameras."""
        if self._dcc_type_val == "unreal":
            return self._unreal_get_cameras()
        return []

    def get_lights(self) -> list[LightInfo]:
        """Get lights."""
        if self._dcc_type_val == "unreal":
            return self._unreal_get_lights()
        return []

    def get_selection(self) -> list[str]:
        """Get selected actors."""
        if self._dcc_type_val == "unreal":
            try:
                resp = self._request(
                    "post",
                    "/remote/object/call",
                    json={
                        "objectPath": "/Game/Editors/PIE/GameInstance",
                        "functionName": "GetSelectedActors",
                        "parameters": {"generateReturnValue": True},
                    },
                )
                data = resp.json() if isinstance(resp, requests.Response) else resp
                actors = data.get("ReturnValue", [])
                return [a.get("Name", "") for a in actors] if isinstance(actors, list) else []
            except Exception:
                pass
        return []

    def _get_scene_metadata(self) -> dict[str, Any]:
        """Get scene metadata."""
        meta = {}
        try:
            if self._dcc_type_val == "unreal":
                # Query level info
                resp = self._request(
                    "post",
                    "/remote/object/call",
                    json={
                        "objectPath": "/Game/Editors/PIE/GameInstance",
                        "functionName": "GetLevelName",
                        "parameters": {"generateReturnValue": True},
                    },
                )
                data = resp.json() if isinstance(resp, requests.Response) else resp
                meta["level"] = data.get("ReturnValue", "")
        except Exception:
            pass
        return meta

    def health_check(self) -> bool:
        """Check if the HTTP endpoint is reachable.

        Returns:
            True if the server responds successfully.

        """
        try:
            resp = self._session.get(
                f"{self._base_url}/remote/object/call",
                timeout=min(self._timeout, 5.0),
            )
            return resp.status_code < 500
        except Exception:
            return False

    # ---- Unreal-specific helpers -------------------------------------------

    def _unreal_get_objects(self, filter_) -> list[ObjectTypeInfo]:
        """Get actors from Unreal Engine via Remote Control API."""
        actor_classes = self._map_filter_to_unreal_classes(filter_)
        all_objects = []

        for cls_path in actor_classes:
            try:
                resp = self._request(
                    "post",
                    "/remote/object/call",
                    json={
                        "objectPath": "/Game/Editors/PIE/GameInstance",
                        "functionName": "GetActorsOfClass",
                        "parameters": {
                            "ActorClassPath": cls_path,
                            "generateReturnValue": True,
                        },
                    },
                )

                if isinstance(resp, requests.Response):
                    data = resp.json()
                else:
                    data = resp

                actors = data.get("ReturnValue", [])
                if not isinstance(actors, list):
                    continue

                for actor in actors:
                    name = actor.get("Name", "")
                    path = actor.get("OuterPath", "")

                    # Try to get transform (use default if unavailable)
                    _transform = self._unreal_get_actor_transform(path)
                    transform = _transform if _transform is not None else TransformMatrix()

                    all_objects.append(
                        ObjectTypeInfo(
                            name=name,
                            type=self._extract_unreal_type(cls_path),
                            path=path,
                            parent="",  # UE doesn't expose parent easily
                            children=[],
                            visibility=True,
                            material="",
                            transform=transform,
                            metadata={"actor_class": cls_path},
                        )
                    )

                    if len(all_objects) >= self.config.max_objects:
                        break

            except Exception as e:
                logger.debug(f"Failed to query class {cls_path}: {e}")

        return all_objects[: self.config.max_objects]

    def _unreal_get_materials(self) -> list[MaterialInfo]:
        """Get materials from Unreal Engine."""
        try:
            resp = self._request(
                "post",
                "/remote/object/call",
                json={
                    "objectPath": "/Game/Editors/PIE/GameInstance",
                    "functionName": "GetMaterialsInUse",
                    "parameters": {"generateReturnValue": True},
                },
            )
            data = resp.json() if isinstance(resp, requests.Response) else resp
            mats = data.get("ReturnValue", [])
            results = []
            for m in mats if isinstance(mats, list) else []:
                results.append(
                    MaterialInfo(
                        name=m.get("Name", "Unknown"),
                        type=m.get("MaterialType", "M"),
                        assigned_objects=[],
                        properties={"base_color": m.get("BaseColor")},
                    )
                )
            return results
        except Exception as e:
            logger.debug(f"Failed to query materials: {e}")
            return []

    def _unreal_get_cameras(self) -> list[CameraInfo]:
        """Get cameras from Unreal Engine."""
        cameras = self._unreal_get_objects(SceneQueryFilter.CAMERAS)
        results = []
        for cam_obj in cameras:
            try:
                # Query camera-specific properties
                resp = self._request(
                    "post",
                    "/remote/object/property",
                    json={
                        "objectPath": cam_obj.path,
                        "propertyName": "CurrentPlaytimeCameraSettings_FOV",
                    },
                )
                fov = 90.0
                if isinstance(resp, requests.Response):
                    prop_data = resp.json()
                    fov = float(prop_data.get("PropertyValue", 90.0))

                results.append(
                    CameraInfo(
                        name=cam_obj.name,
                        type="perspective",
                        focal_length=24.0,  # UE uses FOV instead
                        field_of_view=fov,
                        aspect_ratio=16.0 / 9.0,
                        transform=cam_obj.transform,
                        metadata={"actor_class": cam_obj.metadata.get("actor_class", "")},
                    )
                )
            except Exception:
                results.append(
                    CameraInfo(
                        name=cam_obj.name,
                        type="perspective",
                        field_of_view=90.0,
                        transform=cam_obj.transform,
                    )
                )
        return results

    def _unreal_get_lights(self) -> list[LightInfo]:
        """Get lights from Unreal Engine."""
        all_light_types = [
            ("point", "/Script/Engine.PointLightComponent"),
            ("spot", "/Script/Engine.SpotLightComponent"),
            ("directional", "/Script/Engine.DirectionalLightComponent"),
            ("area", "/Script/Engine.RectLightComponent"),
        ]
        lights = []
        for light_type, cls in all_light_types:
            try:
                resp = self._request(
                    "post",
                    "/remote/object/call",
                    json={
                        "objectPath": "/Game/Editors/PIE/GameInstance",
                        "functionName": "GetComponentsOfClass",
                        "parameters": {
                            "ComponentClassPath": cls,
                            "generateReturnValue": True,
                        },
                    },
                )
                data = resp.json() if isinstance(resp, requests.Response) else resp
                components = data.get("ReturnValue", [])
                if not isinstance(components, list):
                    continue

                for comp in components:
                    comp_path = comp.get("OuterPath", "")
                    name = comp.get("Name", "")

                    # Get intensity
                    intensity = 1.0
                    color_val = (1.0, 1.0, 1.0)
                    try:
                        int_resp = self._request(
                            "post",
                            "/remote/object/property",
                            json={
                                "objectPath": comp_path,
                                "propertyName": "Intensity",
                            },
                        )
                        int_data = int_resp.json() if isinstance(int_resp, requests.Response) else int_resp
                        intensity = float(int_data.get("PropertyValue", 1.0))

                        col_resp = self._request(
                            "post",
                            "/remote/object/property",
                            json={
                                "objectPath": comp_path,
                                "propertyName": "LightColor",
                            },
                        )
                        col_data = col_resp.json() if isinstance(col_resp, requests.Response) else col_resp
                        c = col_data.get("PropertyValue", {"R": 1.0, "G": 1.0, "B": 1.0})
                        color_val = (c.get("R", 1.0), c.get("G", 1.0), c.get("B", 1.0))
                    except Exception:
                        pass

                    lights.append(
                        LightInfo(
                            name=name,
                            type=light_type,
                            intensity=intensity,
                            color=color_val,
                            enabled=True,
                            metadata={"component_path": comp_path},
                        )
                    )

            except Exception as e:
                logger.debug(f"Failed to query {light_type} lights: {e}")

        return lights

    def _unreal_get_actor_transform(self, actor_path: str) -> "TransformMatrix | None":
        """Query the world transform of an Unreal actor."""
        if not self.config.include_transforms:
            return None
        try:
            resp = self._request(
                "post",
                "/remote/object/call",
                json={
                    "objectPath": actor_path,
                    "functionName": "K2_GetActorLocation",
                    "parameters": {"generateReturnValue": True},
                },
            )
            data = resp.json() if isinstance(resp, requests.Response) else resp
            loc = data.get("ReturnValue", {})
            x = loc.get("X", 0.0)
            y = loc.get("Y", 0.0)
            z = loc.get("Z", 0.0)
            # Build identity matrix with translation
            matrix = [
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
                x,
                y,
                z,
                1,
            ]
            return TransformMatrix(matrix=matrix)
        except Exception:
            return None

    # ---- Unity helpers (stub) ----------------------------------------------

    def _unity_get_objects(self, filter_) -> list[ObjectTypeInfo]:
        """Get GameObjects from Unity (placeholder).

        Unity would use its own HTTP endpoint format (e.g., C# HttpListener).
        This stub returns an empty list until Unity integration is implemented.
        """
        logger.info("Unity HTTP scene query not yet fully implemented")
        return []

    # ---- Generic helpers ---------------------------------------------------

    @staticmethod
    def _map_filter_to_unreal_classes(filter_) -> list[str]:
        """Map a SceneQueryFilter to Unreal Actor classes."""
        if isinstance(filter_, SceneQueryFilter):
            filter_ = filter_.value
        mapping = {
            "all": [
                "/Script/Engine.StaticMeshActor",
                "/Script/Engine.CameraActor",
                "/Script/Engine.PointLightComponent",
                "/Script/Engine.SpotLightComponent",
                "/Script/Engine.DirectionalLightComponent",
            ],
            "meshes": ["/Script/Engine.StaticMeshActor"],
            "cameras": ["/Script/Engine.CameraActor"],
            "lights": [
                "/Script/Engine.PointLightComponent",
                "/Script/Engine.SpotLightComponent",
                "/Script/Engine.DirectionalLightComponent",
                "/Script/Engine.RectLightComponent",
            ],
        }
        return mapping.get(str(filter_), mapping.get("all", []))

    @staticmethod
    def _extract_unreal_type(class_path: str) -> str:
        """Extract readable type from Unreal class path."""
        parts = class_path.rsplit(".", 1)
        return parts[-1] if parts else class_path

    @staticmethod
    def _build_hierarchy_from_objects(objects: list[ObjectTypeInfo]) -> SceneHierarchy:
        """Build hierarchy from flat object list (same logic as RPyC version)."""
        if not objects:
            return SceneHierarchy(root_name="world", total_objects=0, max_depth=0, tree={})

        children_map: dict[str, list] = {}
        roots = []
        max_depth = 0

        for obj in objects:
            name = obj.name
            parent = obj.parent
            depth = len(obj.path.split("/")) if obj.path else 1
            max_depth = max(max_depth, depth)

            if not parent:
                roots.append(name)

            if parent not in children_map:
                children_map[parent] = []
            children_map[parent].append(name)

        def build_node(n: str) -> dict:
            kids = children_map.get(n, [])
            return {"name": n, "children": [build_node(c) for c in kids]}

        return SceneHierarchy(
            root_name="world",
            total_objects=len(objects),
            max_depth=max_depth,
            tree={"name": "world", "children": [build_node(r) for r in roots]},
        )

    # ---- HTTP request helper ----------------------------------------------

    def _request(self, method: str, path: str, **kwargs) -> Any:
        """Send an HTTP request to the DCC endpoint."""
        url = f"{self._base_url}{path}"
        kwargs.setdefault("timeout", self._timeout)
        try:
            response = getattr(self._session, method)(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.ConnectionError as e:
            raise SceneError(
                f"Cannot connect to {url}: {e}",
                dcc_type=self._dcc_type_val,
                cause=e,
            )
        except requests.exceptions.Timeout as e:
            raise SceneError(
                f"Request to {url} timed out",
                dcc_type=self._dcc_type_val,
                cause=e,
            )
        except requests.exceptions.HTTPError as e:
            raise SceneError(
                f"HTTP error from {url}: {e.response.status_code}",
                dcc_type=self._dcc_type_val,
                cause=e,
            )
