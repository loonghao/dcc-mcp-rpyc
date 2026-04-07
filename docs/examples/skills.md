# Skills Example

This example shows a complete zero-code MCP skill setup for Maya.

## Directory Structure

```
pipeline_skills/
├── create_sphere/
│   ├── SKILL.md
│   └── run.py
├── render_frame/
│   ├── SKILL.md
│   └── run.py
└── export_selection/
    ├── SKILL.md
    └── run.py
```

## create_sphere/SKILL.md

```markdown
---
name: create_sphere
description: Create a polygonal sphere in Maya at the specified position
category: modeling
tags:
  - primitive
  - mesh
parameters:
  radius:
    type: float
    default: 1.0
    description: Sphere radius in Maya units
  name:
    type: string
    default: pSphere1
    description: Name for the created object
  subdivisions_axis:
    type: int
    default: 20
    description: Number of subdivisions around the axis
  subdivisions_height:
    type: int
    default: 20
    description: Number of subdivisions along the height
---

Creates a polygon sphere with the specified parameters.
```

## create_sphere/run.py

```python
# Parameters injected from SKILL.md: radius, name, subdivisions_axis, subdivisions_height
import maya.cmds as cmds

transforms = cmds.polySphere(
    r=radius,
    n=name,
    sx=subdivisions_axis,
    sy=subdivisions_height,
)[0]

result = {
    "success": True,
    "name": transforms,
    "radius": radius,
}
```

## render_frame/SKILL.md

```markdown
---
name: render_frame
description: Render the current frame in Maya using the active renderer
category: rendering
tags:
  - render
  - output
parameters:
  output_path:
    type: string
    default: ""
    description: Output file path (empty = use render settings)
  width:
    type: int
    default: 0
    description: Override render width (0 = use render settings)
  height:
    type: int
    default: 0
    description: Override render height (0 = use render settings)
---
```

## render_frame/run.py

```python
import maya.cmds as cmds

if width > 0:
    cmds.setAttr("defaultResolution.width", width)
if height > 0:
    cmds.setAttr("defaultResolution.height", height)

cmds.render(batch=True)

result = {
    "success": True,
    "frame": cmds.currentTime(query=True),
    "output_path": cmds.renderSettings(firstImageName=True)[0],
}
```

## Registering Skills

```python
from dcc_mcp_ipc.skills import SkillManager
from dcc_mcp_ipc.action_adapter import get_action_adapter

adapter = get_action_adapter("maya")
mgr = SkillManager(adapter=adapter, dcc_name="maya")

mgr.load_paths(["./pipeline_skills"])
mgr.start_watching()

# Now usable as MCP tools
result = adapter.call_action("create_sphere", radius=3.0, name="bigSphere")
print(result.success)

result = adapter.call_action("render_frame", width=1920, height=1080)
print(result.to_dict())
```
