# SkillManager

`SkillManager` automates action registration from `SKILL.md` files. It wraps `SkillScanner` (filesystem scanning) and `SkillWatcher` (hot-reload via OS file events).

## Import

```python
from dcc_mcp_ipc.skills import SkillManager
```

## Constructor

```python
mgr = SkillManager(
    adapter: ActionAdapter,
    dcc_name: str,
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `adapter` | `ActionAdapter` | The adapter to register discovered skills into |
| `dcc_name` | `str` | DCC name used when executing skill scripts |

## Methods

### `load_paths`

```python
mgr.load_paths(paths: list[str]) -> None
```

Scan the given directories for `SKILL.md` files and register them as actions.

### `load_from_env`

```python
mgr.load_from_env(env_var: str = "DCC_MCP_SKILL_PATHS") -> None
```

Read colon/semicolon-delimited paths from an environment variable and call `load_paths`.

### `start_watching`

```python
mgr.start_watching() -> None
```

Start `SkillWatcher` to monitor loaded paths for file changes. Changes are debounced and trigger automatic re-registration.

### `stop_watching`

```python
mgr.stop_watching() -> None
```

Stop the file watcher.

### `list_skills`

```python
skills = mgr.list_skills() -> list[SkillInfo]
```

Return metadata for all currently registered skills.

### `reload`

```python
mgr.reload() -> None
```

Manually trigger a re-scan and re-registration of all loaded paths.

## SkillInfo

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Skill name (from `SKILL.md` frontmatter) |
| `path` | `str` | Absolute path to the skill directory |
| `description` | `str` | Skill description |
| `category` | `str` | Skill category |
| `tags` | `list[str]` | Tags |
