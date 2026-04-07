"""RPyC transport implementation for scene information queries.

Supports Maya, Blender, Houdini, and any DCC with an RPyC server that exposes
standard scene query methods (``get_scene_info``, ``execute_python``, etc.).
"""

# Import built-in modules
import logging
from typing import Any

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

# ---------------------------------------------------------------------------
# DCC-specific script templates for RPyC execute_python path
# ---------------------------------------------------------------------------

_DCC_SCRIPTS: dict[str, dict[str, str]] = {
    "maya": {
        "get_objects": """
import maya.cmds as cmds
filter_type = {filter}
if filter_type == 'all':
    objects = cmds.ls(dag=True, long=True)
elif filter_type == 'meshes':
    objects = cmds.ls(type='mesh', long=True)
elif filter_type == 'cameras':
    objects = cmds.ls(type='camera', long=True)
elif filter_type == 'lights':
    lights = cmds.ls(type=['directionalLight', 'pointLight', 'spotLight', 'areaLight'], long=True)
    # Also get transform shapes for light transforms
    objects = cmds.listRelatives(lights, parent=True, fullPath=True) or []
elif filter_type == 'joints':
    objects = cmds.ls(type='joint', long=True)
elif filter_type == 'visible_only':
    all_objs = cmds.ls(dag=True, long=True, visible=True)
    objects = [o for o in all_objs if cmds.getAttr(o + '.visibility')]
else:
    objects = cmds.ls(dag=True, long=True)

result = []
for obj in objects:
    try:
        obj_type = cmds.objectType(obj)
        parent = cmds.listRelatives(obj, parent=True, fullPath=True)
        children = cmds.listRelatives(obj, children=True, fullPath=True) or []
        mat = cmds.listConnections(obj, type='shadingEngine', destination=False)
        shader = None
        if mat:
            shader = cmds.listConnections(mat[0], type=['lambert', 'phong', 'phongE',
                'blinn', 'surfaceShader', 'aiStandardSurface', 'StandardSurface'], source=True)
        vis = True
        if cmds.attributeQuery('visibility', node=obj, exists=True):
            vis = cmds.getAttr(obj + '.visibility')
        # Get world matrix
        from maya.api import OpenMaya as om
        sel_list = om.MSelectionList()
        try:
            sel_list.add(obj)
            dag_path = om.MDagPath.getAPathTo(sel_list.getDependNode(0))
            fn_tfm = om.MFnTransform(dag_path)
            m = fn_tfm.transformationMatrix().asMatrix()
            matrix = [m(i // 4, i % 4) for i in range(16)]
        except Exception:
            matrix = None
        result.append({{
            'name': obj.split('|')[-1],
            'type': obj_type,
            'path': obj,
            'parent': parent[0] if parent else '',
            'children': [c.split('|')[-1] for c in children],
            'visibility': vis,
            'material': shader[0] if shader else '',
            'transform_matrix': matrix,
            'metadata': {{}}
        }})
    except Exception as e:
        pass  # Skip problematic objects
result
""",
        "get_hierarchy": """
import maya.cmds as cmds
all_objects = cmds.ls(dag=True, long=True) or []

def build_tree(node_name):
    children = cmds.listRelatives(node_name, children=True, fullPath=True) or []
    return {{
        'name': node_name,
        'children': [build_tree(c) for c in children]
    }}

tree = build_tree('|')
{{
    'root_name': '|',
    'total_objects': len(all_objects),
    'max_depth': len(max([o.split('|') for o in all_objects], key=len)) if all_objects else 0,
    'tree': tree
}}
""",
        "get_materials": """
import maya.cmds as cmds
shading_engines = cmds.ls(type='shadingEngine') or []
materials = []
for se in shading_engines:
    if se == 'initialShadingGroup' or se == 'initialParticleSE':
        continue
    shaders = cmds.listConnections(se, source=True, destination=False,
        type=['lambert','phong','phongE','blinn','surfaceShader',
               'aiStandardSurface','StandardSurface']) or []
    connected = cmds.sets(se, query=True) or []
    props = {{}}
    if shaders:
        sg = shaders[0]
        attrs = ['color', 'diffuse', 'specularColor', 'roughness']
        for a in attrs:
            try:
                val = cmds.getAttr(sg + '.' + a)
                props[a] = list(val) if hasattr(val, '__iter__') else float(val)
            except Exception:
                pass
    materials.append({{
        'name': shaders[0].split(':')[-1] if shaders else se,
        'type': cmds.objectType(shaders[0]) if shaders else 'unknown',
        'assigned_objects': [c.split('|')[-1] for c in connected],
        'properties': props
    }})
materials
""",
        "get_cameras": """
import maya.cmds as cmds
cam_transforms = cmds.ls(type='camera', long=True) or []
cam_shapes = cmds.listRelatives(cam_transforms, shapes=True, fullPath=True) or []
cameras = []
for tfm, shp in zip(cam_transforms, cam_shapes):
    try:
        fl = cmds.getAttr(shp + '.focalLength') if cmds.attributeQuery('focalLength', node=shp, exists=True) else 35.0
        fov = cmds.getAttr(shp + '.horizontalFieldOfView') if cmds.attributeQuery('horizontalFieldOfView', node=shp, exists=True) else 54.4
        near = cmds.getAttr(shp + '.nearClipPlane') if cmds.attributeQuery('nearClipPlane', node=shp, exists=True) else 0.1
        far = cmds.getAttr(shp + '.farClipPlane') if cmds.attributeQuery('farClipPlane', node=shp, exists=True) else 10000.0
        cameras.append({{
            'name': tfm.split('|')[-1],
            'type': cmds.camera(shp, orthographic=True, q=True) and 'orthographic' or 'perspective',
            'focal_length': float(fl),
            'field_of_view': float(fov),
            'near_clip': float(near),
            'far_clip': float(far),
            'aspect_ratio': cmds.getAttr(shp + '.aspectRatio') if cmds.attributeQuery('aspectRatio', node=shp, exists=True) else 1.5,
            'sensor_width': cmds.getAttr(shp + '.horizontalFilmAperture') * 25.4 if cmds.attributeQuery('horizontalFilmAperture', node=shp, exists=True) else 36.0,
            'sensor_height': cmds.getAttr(shp + '.verticalFilmAperture') * 25.4 if cmds.attributeQuery('verticalFilmAperture', node=shp, exists=True) else 24.0,
            'metadata': {{}}
        }})
    except Exception:
        pass
cameras
""",
        "get_lights": """
import maya.cmds as cmds
light_types = [
    ('directionalLight', 'directional'), ('pointLight', 'point'),
    ('spotLight', 'spot'), ('areaLight', 'area'),
]
lights = []
for lt, display_type in light_types:
    nodes = cmds.ltos(cmds.ls(type=lt, long=True) or []) or []
    for n in nodes:
        try:
            intensity = cmds.getAttr(n + '.intensity') if cmds.attributeQuery('intensity', node=n, exists=True) else 1.0
            col = cmds.getAttr(n + '.color') or (1,1,1)
            enabled = not cmds.getAttr(n + '.visibility') if cmds.attributeQuery('visibility', node=n, exists=True) else True
            lights.append({{
                'name': n.split('|')[-1],
                'type': display_type,
                'intensity': float(intensity),
                'color': tuple(col),
                'enabled': bool(enabled),
                'metadata': {{
                    'cone_angle': float(cmds.getAttr(n + '.coneAngle')) if display_type == 'spot' and cmds.attributeQuery('coneAngle', node=n, exists=True) else None,
                    'decay_rate': cmds.getAttr(n + '.decayRate', asString=True) if cmds.attributeQuery('decayRate', node=n, exists=True) else None
                }}
            }})
        except Exception:
            pass
lights
""",
        "get_selection": """
import maya.cmds as cmds
cmds.ls(selection=True, long=True) or []
""",
    },
    "blender": {
        "get_objects": """
import bpy
filter_type = '{filter}'
data = bpy.data
result = []
for obj in data.objects:
    if filter_type != 'all':
        type_map = {{
            'meshes': 'MESH', 'cameras': 'CAMERA', 'lights': 'LIGHT',
            'curves': 'CURVE', 'surfaces': 'SURFACE', 'armatures': 'ARMATURE'
        }}
        if filter_type in type_map:
            if obj.type != type_map[filter_type]:
                continue
        elif filter_type == 'visible_only':
            if not obj.visible_viewport:
                continue
    mat_names = [m.name for m in obj.data.materials if m] if obj.data else []
    result.append({{
        'name': obj.name,
        'type': obj.type.lower(),
        'path': obj.name_full if hasattr(obj, 'name_full') else obj.name,
        'parent': obj.parent.name if obj.parent else '',
        'children': [c.name for c in obj.children],
        'visibility': obj.visible_viewport,
        'material': mat_names[0] if mat_names else '',
        'transform_matrix': list(obj.matrix_world.transposed()) if self.config.include_transforms else None,
        'metadata': {{}}
    }})
result
""",
        "get_hierarchy": """
import bpy
def build_tree(parent):
    children = [obj for obj in bpy.data.objects if obj.parent == parent]
    return {{
        'name': parent.name if parent else 'World',
        'children': [build_tree(c) for c in children]
    }}
roots = [o for o in bpy.data.objects if o.parent is None]
{{
    'root_name': 'World',
    'total_objects': len(bpy.data.objects),
    'max_depth': max([len(o.name.split('|')) for o in bpy.data.objects]) if bpy.data.objects else 0,
    'tree': {{'name': 'World', 'children': [build_tree(r) for r in roots]}}
}}
""",
        "get_materials": """
import bpy
materials = []
for mat in bpy.data.materials:
    props = {{}}
    if mat.use_nodes and mat.node_tree:
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                base_col = node.inputs.get('Base Color')
                if base_col is not None:
                    props['base_color'] = list(base_col.default_value)[:3]
                rough = node.inputs.get('Roughness')
                if rough is not None:
                    props['roughness'] = rough.default_value
                metal = node.inputs.get('Metallic')
                if metal is not None:
                    props['metallic'] = metal.default_value
    assigned = [o.name for o in bpy.data.objects if mat in (o.data.materials if o.data else [])]
    materials.append({{
        'name': mat.name,
        'type': 'PrincipledBSDF' if mat.use_nodes else 'Unknown',
        'assigned_objects': assigned,
        'properties': props
    }})
materials
""",
        "get_cameras": """
import bpy
cameras = []
for obj in bpy.data.objects:
    if obj.type != 'CAMERA':
        continue
    cam = obj.data
    lenses = getattr(cam, 'lens', 35.0)
    sensor_w = getattr(cam, 'sensor_width', 36.0)
    sensor_h = getattr(cam, 'sensor_height', 20.0)
    import math
    fov = 2.0 * math.degrees(math.atan2(sensor_w / 2.0, lenses))
    cameras.append({{
        'name': obj.name,
        'type': 'perspective' if cam.type == 'PERSP' else 'orthographic',
        'focal_length': lenses,
        'field_of_view': fov,
        'near_clip': getattr(cam, 'clip_start', 0.1),
        'far_clip': getattr(cam, 'clip_end', 1000.0),
        'aspect_ratio': cam.sensor_width / cam.sensor_height if cam.sensor_height > 0 else 16/9,
        'sensor_width': sensor_w,
        'sensor_height': sensor_h,
        'metadata': {{}}
    }})
cameras
""",
        "get_lights": """
import bpy
lights = []
light_map = {{'POINT':'point', 'SUN':'directional', 'SPOT':'spot', 'AREA':'area'}}
for obj in bpy.data.objects:
    if obj.type != 'LIGHT':
        continue
    light = obj.data
    col = light.color if hasattr(light, 'color') else (1,1,1)
    energy = light.energy if hasattr(light, 'energy') else 1.0
    meta = {{}}
    if light.type == 'SPOT':
        meta['cone_angle'] = math.degrees(getattr(light, 'spot_size', math.pi/4)) / 2
        meta['blend'] = getattr(light, 'spot_blend', 0.5)
    elif light.type == 'AREA':
        meta['size_x'] = getattr(light, 'size', 1.0)
        meta['size_y'] = getattr(light, 'size_y', 1.0)
    lights.append({{
        'name': obj.name,
        'type': light_map.get(light.type, light.type.lower()),
        'intensity': energy,
        'color': (col.r if hasattr(col,'r') else col[0], col.g if hasattr(col,'g') else col[1], col.b if hasattr(col,'b') else col[2]),
        'enabled': not obj.hide_render,
        'metadata': meta
    }})
lights
""",
        "get_selection": """
import bpy
[obj.name for obj in bpy.context.selected_objects]
""",
    },
}


class RPyCSceneInfo(BaseSceneInfo):
    """RPyC-based scene info implementation.

    Queries the remote DCC process via an ``execute_func`` callable (typically
    ``connection.root.execute_python``). Falls back to ``conn.root.get_scene_info``
    if the server provides it.
    """

    def __init__(
        self,
        dcc_name: str = "maya",
        execute_func=None,
        config=None,
        connection=None,
    ):
        """Initialize the RPyC scene info client.

        Args:
            dcc_name: Target DCC identifier ("maya", "blender", "houdini").
            execute_func: Callable that executes Python code remotely.
            config: Optional SceneInfoConfig.
            connection: Optional RPyC connection (alternative to execute_func).

        """
        super().__init__(config=config)
        self._dcc_name = dcc_name.lower()
        self._execute_func = execute_func
        self._connection = connection

    def _get_exec_func(self):
        """Resolve the execution function."""
        func = self._execute_func
        if func is None and self._connection is not None:
            root = getattr(self._connection, 'root', None)
            if root is not None:
                if hasattr(root, 'exposed_execute_python'):
                    func = root.exposed_execute_python
                elif hasattr(root, 'execute_python'):
                    func = root.execute_python
        if func is None:
            raise SceneError(
                "No execute function provided and no valid connection available",
                dcc_type=self._dcc_name,
            )
        return func

    def _exec(self, code: str) -> Any:
        """Execute code on the remote DCC and return the result."""
        func = self._get_exec_func()
        try:
            result = func(code)
            return result
        except Exception as e:
            raise SceneError(
                f"Remote execution failed: {e}",
                dcc_type=self._dcc_name,
                cause=e,
            )

    # ---- Abstract implementations ------------------------------------------

    def _dcc_type(self) -> str:
        return self._dcc_name

    def _get_scene_name(self) -> str:
        """Get scene name via RPyC."""
        try:
            if self._dcc_name == "maya":
                return self._exec("import maya.cmds as cmds; cmds.file(query=True, sceneName=True)")
            elif self._dcc_name == "blender":
                return self._exec("import bpy; bpy.path.display_name_from_filepath(bpy.data.filepath)")
        except SceneError:
            pass
        return ""

    def get_objects(self, filter_: str | SceneQueryFilter = SceneQueryFilter.ALL) -> list[ObjectTypeInfo]:
        """Get objects by executing DCC-specific script or using generic API."""
        # Try DCC-specific optimized script first
        scripts = _DCC_SCRIPTS.get(self._dcc_name, {})
        script_key = "get_objects"
        if isinstance(filter_, SceneQueryFilter):
            filter_str = filter_.value
        else:
            filter_str = str(filter_)

        if script_key in scripts:
            try:
                template = scripts[script_key]
                code = template.format(filter=filter_str, include_transforms=str(self.config.include_transforms))
                raw_list = self._exec(code)
                if isinstance(raw_list, list):
                    return [self._parse_object(raw) for raw in raw_list]
            except (SceneError, KeyError, TypeError):
                logger.debug("DCC-specific object query failed, falling back to generic")

        # Fallback to generic get_scene_info on the server
        return self._generic_get_objects(filter_str)

    def get_hierarchy(self) -> SceneHierarchy:
        """Get hierarchy via DCC-specific script or generic fallback."""
        scripts = _DCC_SCRIPTS.get(self._dcc_name, {})
        script = scripts.get("get_hierarchy")
        if script:
            try:
                raw = self._exec(script)
                if isinstance(raw, dict):
                    return SceneHierarchy(**raw)
            except (SceneError, TypeError):
                logger.debug("DCC-specific hierarchy query failed, falling back")

        # Build hierarchy from objects
        objects = self.get_objects()
        return self._build_hierarchy_from_objects(objects)

    def get_materials(self) -> list[MaterialInfo]:
        """Get materials via DCC-specific script or generic fallback."""
        scripts = _DCC_SCRIPTS.get(self._dcc_name, {})
        script = scripts.get("get_materials")
        if script:
            try:
                raw = self._exec(script)
                if isinstance(raw, list):
                    return [MaterialInfo(**item) for item in raw]
            except (SceneError, TypeError):
                logger.debug("DCC-specific material query failed, falling back")
        return []

    def get_cameras(self) -> list[CameraInfo]:
        """Get cameras via DCC-specific script or generic fallback."""
        scripts = _DCC_SCRIPTS.get(self._dcc_name, {})
        script = scripts.get("get_cameras")
        if script:
            try:
                raw = self._exec(script)
                if isinstance(raw, list):
                    return [CameraInfo(**item) for item in raw]
            except (SceneError, TypeError):
                logger.debug("DCC-specific camera query failed, falling back")
        return []

    def get_lights(self) -> list[LightInfo]:
        """Get lights via DCC-specific script or generic fallback."""
        scripts = _DCC_SCRIPTS.get(self._dcc_name, {})
        script = scripts.get("get_lights")
        if script:
            try:
                raw = self._exec(script)
                if isinstance(raw, list):
                    return [LightInfo(**item) for item in raw]
            except (SceneError, TypeError):
                logger.debug("DCC-specific light query failed, falling back")
        return []

    def get_selection(self) -> list[str]:
        """Get selection via DCC-specific script or generic fallback."""
        scripts = _DCC_SCRIPTS.get(self._dcc_name, {})
        script = scripts.get("get_selection")
        if script:
            try:
                raw = self._exec(script)
                if isinstance(raw, (list, tuple)):
                    return list(raw)
            except (SceneError, TypeError):
                logger.debug("DCC-specific selection query failed, falling back")

        # Generic fallback via get_scene_info
        try:
            func = self._get_exec_func()
            info = func("return get_selection()" if self._dcc_name == "python" else "")
            if isinstance(info, (list, tuple)):
                return list(info)
        except Exception:
            pass
        return []

    def _get_scene_metadata(self) -> dict[str, Any]:
        """Get DCC-specific metadata."""
        meta = {}
        try:
            if self._dcc_name == "maya":
                start = self._exec(
                    "import maya.cmds as cmds; "
                    "cmds.playbackOptions(q=True, minTime=True), "
                    "cmds.playbackOptions(q=True, maxTime=True)"
                )
                meta["frame_range"] = list(start) if hasattr(start, "__iter__") else (1, 120)
                meta["current_frame"] = self._exec("import maya.cmds as cmds; cmds.currentTime(q=True)")
                meta["units"] = self._exec("import maya.cmds as cmds; cmds.currentUnit(q=True, linear=True)")
            elif self._dcc_name == "blender":
                meta["frame_start"] = self._exec("import bpy; bpy.context.scene.frame_start")
                meta["frame_end"] = self._exec("import bpy; bpy.context.scene.frame_end")
                meta["current_frame"] = self._exec("import bpy; bpy.context.scene.frame_current")
        except (SceneError, AttributeError):
            pass
        return meta

    # ---- Internal helpers --------------------------------------------------

    @staticmethod
    def _parse_object(raw: dict) -> ObjectTypeInfo:
        """Convert a raw dict from remote into ObjectTypeInfo."""
        transform_data = raw.pop("transform_matrix", None)
        transform = TransformMatrix(matrix=transform_data) if transform_data else TransformMatrix()

        metadata = raw.pop("metadata", {})

        return ObjectTypeInfo(
            name=raw.get("name", ""),
            type=raw.get("type", "unknown"),
            path=raw.get("path", ""),
            parent=raw.get("parent", ""),
            children=raw.get("children", []),
            visibility=raw.get("visibility", True),
            material=raw.get("material", ""),
            transform=transform,
            metadata=metadata,
        )

    def _generic_get_objects(self, filter_str: str) -> list[ObjectTypeInfo]:
        """Fallback: call get_scene_info() on the remote server."""
        func = self._get_exec_func()
        try:
            info = func("return get_scene_info()")
            if isinstance(info, dict):
                objects = info.get("objects", [])
                return [self._parse_object(o) for o in objects]
        except Exception as e:
            logger.warning(f"Generic object query failed: {e}")
        return []

    @staticmethod
    def _build_hierarchy_from_objects(objects: list[ObjectTypeInfo]) -> SceneHierarchy:
        """Build a hierarchy tree from a flat list of objects."""
        if not objects:
            return SceneHierarchy(root_name="world", total_objects=0, max_depth=0, tree={})

        children_map: dict[str, list] = {}
        roots = []
        max_depth = 0

        for obj in objects:
            name = obj.name
            parent = obj.parent
            depth = len(obj.path.split("|")) if obj.path else 1
            max_depth = max(max_depth, depth)

            if not parent:
                roots.append(name)

            if parent not in children_map:
                children_map[parent] = []
            children_map[parent].append(name)

        def build_node(name: str) -> dict:
            kids = children_map.get(name, [])
            return {"name": name, "children": [build_node(c) for c in kids]}

        root_node = {"name": "world", "children": [build_node(r) for r in roots]}
        return SceneHierarchy(
            root_name="world",
            total_objects=len(objects),
            max_depth=max_depth,
            tree=root_node,
        )
