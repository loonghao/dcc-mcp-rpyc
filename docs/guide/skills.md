# Skills System

The Skills System enables **zero-code MCP tool registration**. Instead of writing Python boilerplate to register an action, you drop a `SKILL.md` file into a directory and the `SkillManager` auto-registers it.

## Directory Structure

```
my_skills/
├── create_sphere/
│   ├── SKILL.md          # Skill definition (frontmatter)
│   └── run.py            # Executed when the skill is invoked
├── render_scene/
│   ├── SKILL.md
│   └── run.py
└── export_fbx/
    ├── SKILL.md
    └── run.py
```

## SKILL.md Format

```markdown
---
name: create_sphere
description: Create a sphere primitive at the specified position
category: modeling
tags:
  - primitive
  - mesh
  - geometry
parameters:
  radius:
    type: float
    default: 1.0
    description: Sphere radius in scene units
  name:
    type: string
    default: sphere1
    description: Name for the new object
  position:
    type: list
    default: [0, 0, 0]
    description: World-space position [x, y, z]
---

## Create Sphere

Creates a polygonal sphere at the given position.
```

## run.py

The `run.py` script is executed with the skill's parameters injected into its local scope:

```python
# Parameters from SKILL.md are available as local variables:
# radius, name, position

import maya.cmds as cmds

cmds.polySphere(r=radius, name=name)
cmds.move(*position, name)

result = {
    "success": True,
    "name": name,
    "position": position,
}
# `result` is automatically captured and returned
```

## Using SkillManager

```python
from dcc_mcp_ipc.skills import SkillManager
from dcc_mcp_ipc.action_adapter import get_action_adapter

adapter = get_action_adapter("maya")
mgr = SkillManager(adapter=adapter, dcc_name="maya")

# Register all skills from one or more directories
mgr.load_paths([
    "./my_skills",
    "/pipeline/shared_skills",
])

# Enable hot-reload (watches for SKILL.md changes)
mgr.start_watching()

# Skills are now callable via the action adapter
result = adapter.call_action("create_sphere", radius=2.0, name="bigSphere")
print(result.success)
```

## Hot-reload

When `start_watching()` is called, a `SkillWatcher` monitors the loaded paths for file system events:

- **Add / modify** `SKILL.md` → skill is re-registered
- **Delete** `SKILL.md` → skill is unregistered
- Changes take effect without restarting the DCC application

To stop watching:

```python
mgr.stop_watching()
```

## Environment Variable Configuration

You can configure skill paths via an environment variable instead of hardcoding:

```bash
export DCC_MCP_SKILL_PATHS=/pipeline/skills:/home/user/my_skills
```

```python
mgr = SkillManager(adapter=adapter, dcc_name="maya")
mgr.load_from_env()  # reads DCC_MCP_SKILL_PATHS
```

## Listing Loaded Skills

```python
for skill in mgr.list_skills():
    print(skill.name, skill.path)
```
