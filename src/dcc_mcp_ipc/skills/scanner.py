"""Skills discovery and registration for DCC-MCP-IPC.

Bridges the dcc-mcp-core Rust Skills system with the IPC action layer so that
zero-code ``SKILL.md``-based scripts are automatically exposed as MCP tools
through the ``ActionAdapter``.

Typical usage
-------------
Inside a DCC plugin or server startup::

    from dcc_mcp_ipc.skills import SkillManager

    manager = SkillManager(dcc_name="maya")
    manager.load_paths(["/path/to/skills"])
    # All discovered skills are now callable via action_adapter.call_action(name)

    manager.start_watching()   # hot-reload on file change
"""

# Import built-in modules
import logging
import os
from typing import Any
from typing import Callable
from typing import Optional

# Import third-party modules
from dcc_mcp_core import SkillMetadata
from dcc_mcp_core import SkillScanner
from dcc_mcp_core import SkillWatcher
from dcc_mcp_core import parse_skill_md
from dcc_mcp_core import scan_and_load_lenient

# Import local modules
from dcc_mcp_ipc.action_adapter import ActionAdapter

logger = logging.getLogger(__name__)


class SkillManager:
    """Discovers, loads, and hot-reloads DCC Skills as MCP tools.

    Each discovered Skill is registered as an action in the provided
    :class:`~dcc_mcp_ipc.action_adapter.ActionAdapter`, making it callable
    through the standard ``call_action`` / ``dispatch`` pipeline.

    Attributes
    ----------
        dcc_name: DCC context used when scanning and registering actions.
        adapter: The :class:`ActionAdapter` skills are registered into.
        watcher: The :class:`SkillWatcher` used for hot-reload (after
            :meth:`start_watching`).

    """

    def __init__(
        self,
        adapter: Optional[ActionAdapter] = None,
        dcc_name: str = "python",
    ) -> None:
        """Initialise the skill manager.

        Args:
            adapter: :class:`ActionAdapter` to register skills into.  When
                *None* a new adapter is created with ``name="skills"``.
            dcc_name: DCC context for registry queries (default: "python").

        """
        self.dcc_name = dcc_name
        self.adapter = adapter or ActionAdapter("skills", dcc_name=dcc_name)
        self._scanner = SkillScanner()
        self._watcher: Optional[SkillWatcher] = None
        self._skill_paths: list[str] = []
        self._registered_skills: dict[str, SkillMetadata] = {}

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_paths(
        self,
        paths: list[str],
        *,
        force_refresh: bool = False,
    ) -> list[str]:
        """Scan *paths* for Skills and register them as actions.

        Args:
            paths: List of directory paths to scan.
            force_refresh: Re-scan even if already cached.

        Returns:
            List of registered skill names.

        """
        self._skill_paths = list(paths)
        skill_dirs = self._scanner.scan(
            extra_paths=paths,
            dcc_name=self.dcc_name,
            force_refresh=force_refresh,
        )

        registered: list[str] = []
        for skill_dir in skill_dirs:
            metadata = parse_skill_md(skill_dir)
            if metadata is None:
                logger.debug("No SKILL.md found in %s, skipping", skill_dir)
                continue
            self._register_skill(metadata)
            registered.append(metadata.name)

        logger.info(
            "SkillManager: registered %d skills from %d paths",
            len(registered),
            len(paths),
        )
        return registered

    def load_env_paths(self) -> list[str]:
        """Load skills from :envvar:`DCC_MCP_SKILL_PATHS` environment variable.

        Returns:
            List of registered skill names.

        """
        skill_paths_env = os.environ.get("DCC_MCP_SKILL_PATHS", "")
        if not skill_paths_env:
            logger.debug("DCC_MCP_SKILL_PATHS not set, no env-based skills loaded")
            return []

        paths = [p.strip() for p in skill_paths_env.split(os.pathsep) if p.strip()]
        return self.load_paths(paths)

    def load_full_pipeline(self, extra_paths: Optional[list[str]] = None) -> list[str]:
        """Run the full scan-and-load pipeline (includes dependency resolution).

        Args:
            extra_paths: Additional directories beyond the default skill paths.

        Returns:
            List of registered skill names.

        """
        skills, errors = scan_and_load_lenient(
            extra_paths=(self._skill_paths + (extra_paths or [])) or None,
            dcc_name=self.dcc_name,
        )
        if errors:
            logger.warning("SkillManager: %d skills failed to load: %s", len(errors), errors)

        registered: list[str] = []
        for metadata in skills:
            self._register_skill(metadata)
            registered.append(metadata.name)

        logger.info("SkillManager (pipeline): registered %d skills", len(registered))
        return registered

    # ------------------------------------------------------------------
    # Hot-reload
    # ------------------------------------------------------------------

    def start_watching(self, debounce_ms: int = 300) -> None:
        """Start a :class:`SkillWatcher` for hot-reload of skill directories.

        Args:
            debounce_ms: Debounce interval in milliseconds (default: 300).

        """
        if self._watcher is not None:
            logger.debug("SkillWatcher already running")
            return

        self._watcher = SkillWatcher(debounce_ms=debounce_ms)
        for path in self._skill_paths:
            self._watcher.watch(path)
            logger.debug("SkillWatcher: watching %s", path)

        logger.info("SkillWatcher started, watching %d paths", len(self._skill_paths))

    def stop_watching(self) -> None:
        """Stop the hot-reload watcher."""
        if self._watcher is not None:
            for path in self._skill_paths:
                self._watcher.unwatch(path)
            self._watcher = None
            logger.info("SkillWatcher stopped")

    def reload(self) -> list[str]:
        """Force-reload all watched skills and re-register them.

        Returns:
            List of re-registered skill names.

        """
        if self._watcher is None:
            return self.load_paths(self._skill_paths, force_refresh=True)

        self._watcher.reload()
        skills = self._watcher.skills()
        registered: list[str] = []
        for metadata in skills:
            self._register_skill(metadata)
            registered.append(metadata.name)

        logger.info("SkillManager: reloaded %d skills", len(registered))
        return registered

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_skills(self) -> list[SkillMetadata]:
        """Return metadata for all currently registered skills."""
        return list(self._registered_skills.values())

    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        """Look up skill metadata by name.

        Args:
            name: Skill name (from ``SKILL.md``).

        Returns:
            :class:`SkillMetadata` or *None* if not found.

        """
        return self._registered_skills.get(name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_handler(self, metadata: SkillMetadata) -> Callable[..., Any]:
        """Create a callable handler that executes the skill's scripts.

        The handler is a closure over *metadata*.  It builds a small
        execution context (``skill_path``, ``dcc``, extra kwargs) and
        evaluates or imports the skill scripts sequentially.

        Args:
            metadata: :class:`SkillMetadata` describing the skill.

        Returns:
            A Python callable suitable for
            :meth:`~dcc_mcp_ipc.action_adapter.ActionAdapter.register_action`.

        """

        def _handler(**kwargs: Any) -> dict[str, Any]:
            ctx: dict[str, Any] = {
                "skill_path": metadata.skill_path,
                "dcc": metadata.dcc,
                **kwargs,
            }
            results: list[Any] = []

            for script_rel in metadata.scripts:
                script_path = os.path.join(metadata.skill_path, script_rel)
                if not os.path.isfile(script_path):
                    logger.warning("Skill '%s': script not found: %s", metadata.name, script_path)
                    continue
                try:
                    with open(script_path, encoding="utf-8") as fh:
                        code = fh.read()
                    local_ctx: dict[str, Any] = dict(ctx)
                    exec(compile(code, script_path, "exec"), {}, local_ctx)
                    results.append(local_ctx.get("result"))
                except Exception as exc:
                    logger.error("Skill '%s' script '%s' failed: %s", metadata.name, script_path, exc)
                    return {
                        "success": False,
                        "message": f"Skill '{metadata.name}' script failed: {exc}",
                        "error": str(exc),
                    }

            return {
                "success": True,
                "message": f"Skill '{metadata.name}' executed successfully",
                "context": {"results": results},
            }

        _handler.__name__ = metadata.name
        _handler.__doc__ = metadata.description or f"Run skill '{metadata.name}'"
        return _handler

    def _register_skill(self, metadata: SkillMetadata) -> None:
        """Register a single skill into the action adapter.

        Args:
            metadata: Parsed :class:`SkillMetadata`.

        """
        handler = self._build_handler(metadata)
        try:
            self.adapter.register_action(
                metadata.name,
                handler,
                description=metadata.description,
                category="skill",
                tags=metadata.tags,
                version=metadata.version,
                source_file=os.path.join(metadata.skill_path, "SKILL.md"),
            )
            self._registered_skills[metadata.name] = metadata
            logger.debug("Registered skill action: '%s'", metadata.name)
        except Exception as exc:
            logger.warning("Failed to register skill '%s': %s", metadata.name, exc)
