"""Tests for the Skills integration module (dcc_mcp_ipc.skills).

All dcc-mcp-core Rust classes are mocked so the suite runs without the
compiled extension.
"""

# Import built-in modules
import os
import tempfile
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.action_adapter import ActionAdapter
from dcc_mcp_ipc.skills.scanner import SkillManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_metadata(name="my_skill", description="A skill", scripts=None, skill_path="/skills/my_skill"):
    meta = MagicMock()
    meta.name = name
    meta.description = description
    meta.dcc = "python"
    meta.tags = ["test"]
    meta.version = "1.0.0"
    meta.scripts = scripts or ["run.py"]
    meta.skill_path = skill_path
    meta.depends = []
    return meta


# ---------------------------------------------------------------------------
# SkillManager unit tests
# ---------------------------------------------------------------------------

class TestSkillManagerInit:

    def test_creates_default_adapter(self):
        with patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mgr = SkillManager(dcc_name="maya")
        assert mgr.dcc_name == "maya"
        assert isinstance(mgr.adapter, ActionAdapter)

    def test_accepts_external_adapter(self):
        adapter = ActionAdapter("external", dcc_name="houdini")
        with patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mgr = SkillManager(adapter=adapter, dcc_name="houdini")
        assert mgr.adapter is adapter


class TestSkillManagerLoadPaths:

    @pytest.fixture
    def mock_scanner(self):
        with patch("dcc_mcp_ipc.skills.scanner.SkillScanner") as cls:
            scanner = MagicMock()
            cls.return_value = scanner
            yield scanner

    def test_load_paths_registers_skills(self, mock_scanner):
        meta = _make_metadata("echo_skill")
        mock_scanner.scan.return_value = ["/skills/echo_skill"]

        with patch("dcc_mcp_ipc.skills.scanner.parse_skill_md", return_value=meta):
            adapter = ActionAdapter("test_load")
            with patch.object(adapter, "register_action") as mock_reg:
                mgr = SkillManager(adapter=adapter)
                mgr._scanner = mock_scanner
                mgr.load_paths(["/skills"])

                mock_reg.assert_called_once_with(
                    "echo_skill",
                    mock_reg.call_args[0][1],
                    description="A skill",
                    category="skill",
                    tags=["test"],
                    version="1.0.0",
                    source_file=os.path.join("/skills/echo_skill", "SKILL.md"),
                )

    def test_load_paths_returns_names(self, mock_scanner):
        meta = _make_metadata("skill_a")
        mock_scanner.scan.return_value = ["/skills/skill_a"]

        with patch("dcc_mcp_ipc.skills.scanner.parse_skill_md", return_value=meta):
            mgr = SkillManager()
            mgr._scanner = mock_scanner
            names = mgr.load_paths(["/skills"])

        assert "skill_a" in names

    def test_load_paths_skips_missing_metadata(self, mock_scanner):
        mock_scanner.scan.return_value = ["/skills/broken"]

        with patch("dcc_mcp_ipc.skills.scanner.parse_skill_md", return_value=None):
            mgr = SkillManager()
            mgr._scanner = mock_scanner
            names = mgr.load_paths(["/skills"])

        assert names == []

    def test_load_env_paths_empty(self, mock_scanner):
        """No env var → no paths loaded."""
        mgr = SkillManager()
        mgr._scanner = mock_scanner
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DCC_MCP_SKILL_PATHS", None)
            names = mgr.load_env_paths()
        assert names == []

    def test_load_env_paths_from_env(self, mock_scanner):
        meta = _make_metadata("env_skill")
        mock_scanner.scan.return_value = ["/env/env_skill"]

        with patch("dcc_mcp_ipc.skills.scanner.parse_skill_md", return_value=meta), \
             patch.dict(os.environ, {"DCC_MCP_SKILL_PATHS": "/env"}):
            mgr = SkillManager()
            mgr._scanner = mock_scanner
            names = mgr.load_env_paths()

        assert "env_skill" in names


class TestSkillManagerPipeline:

    def test_load_full_pipeline(self):
        meta = _make_metadata("pipe_skill")
        with patch("dcc_mcp_ipc.skills.scanner.scan_and_load_lenient") as mock_scan, \
             patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mock_scan.return_value = ([meta], [])
            adapter = ActionAdapter("pipeline_test")
            with patch.object(adapter, "register_action"):
                mgr = SkillManager(adapter=adapter)
                names = mgr.load_full_pipeline()

        assert "pipe_skill" in names

    def test_load_full_pipeline_with_errors(self):
        """Partial failures are logged but don't abort the load."""
        meta = _make_metadata("good_skill")
        with patch("dcc_mcp_ipc.skills.scanner.scan_and_load_lenient") as mock_scan, \
             patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mock_scan.return_value = ([meta], ["bad/skill/path"])
            adapter = ActionAdapter("partial_test")
            with patch.object(adapter, "register_action"):
                mgr = SkillManager(adapter=adapter)
                names = mgr.load_full_pipeline()

        assert "good_skill" in names


class TestSkillManagerWatcher:

    def test_start_watching_creates_watcher(self):
        with patch("dcc_mcp_ipc.skills.scanner.SkillWatcher") as mock_cls, \
             patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mock_watcher = MagicMock()
            mock_cls.return_value = mock_watcher

            mgr = SkillManager()
            mgr._skill_paths = ["/skills"]
            mgr.start_watching(debounce_ms=200)

            mock_cls.assert_called_once_with(debounce_ms=200)
            mock_watcher.watch.assert_called_once_with("/skills")
            assert mgr._watcher is mock_watcher

    def test_start_watching_idempotent(self):
        with patch("dcc_mcp_ipc.skills.scanner.SkillWatcher") as mock_cls, \
             patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mgr = SkillManager()
            mgr._watcher = MagicMock()  # already watching
            mgr.start_watching()
            mock_cls.assert_not_called()

    def test_stop_watching_cleans_up(self):
        with patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mock_watcher = MagicMock()
            mgr = SkillManager()
            mgr._skill_paths = ["/skills"]
            mgr._watcher = mock_watcher

            mgr.stop_watching()

            mock_watcher.unwatch.assert_called_once_with("/skills")
            assert mgr._watcher is None

    def test_reload_via_watcher(self):
        meta = _make_metadata("hot_skill")
        with patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mock_watcher = MagicMock()
            mock_watcher.skills.return_value = [meta]

            adapter = ActionAdapter("reload_test")
            with patch.object(adapter, "register_action"):
                mgr = SkillManager(adapter=adapter)
                mgr._watcher = mock_watcher
                names = mgr.reload()

        mock_watcher.reload.assert_called_once()
        assert "hot_skill" in names


class TestSkillManagerIntrospection:

    def test_list_skills_empty(self):
        with patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mgr = SkillManager()
        assert mgr.list_skills() == []

    def test_get_skill_none_when_missing(self):
        with patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mgr = SkillManager()
        assert mgr.get_skill("unknown") is None

    def test_get_skill_after_register(self):
        meta = _make_metadata("known_skill")
        with patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            adapter = ActionAdapter("introspect_test")
            with patch.object(adapter, "register_action"):
                mgr = SkillManager(adapter=adapter)
                mgr._register_skill(meta)

        assert mgr.get_skill("known_skill") is meta


class TestSkillHandlerExecution:
    """Tests for the skill handler closure created by _build_handler."""

    def test_handler_executes_script(self):
        """Handler runs a script that sets `result`."""
        with tempfile.TemporaryDirectory() as tmpdir:
            script = os.path.join(tmpdir, "run.py")
            with open(script, "w") as f:
                f.write("result = skill_path + '/done'\n")

            meta = _make_metadata(
                name="runner",
                scripts=["run.py"],
                skill_path=tmpdir,
            )

            with patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
                mgr = SkillManager()
            handler = mgr._build_handler(meta)
            result = handler()

        assert result["success"] is True

    def test_handler_reports_missing_script(self):
        meta = _make_metadata(
            name="missing",
            scripts=["nonexistent.py"],
            skill_path="/no/such/dir",
        )
        with patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
            mgr = SkillManager()
        handler = mgr._build_handler(meta)
        result = handler()
        # Missing script is warned but doesn't crash — returns success with empty results
        assert result["success"] is True

    def test_handler_reports_script_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script = os.path.join(tmpdir, "bad.py")
            with open(script, "w") as f:
                f.write("raise ValueError('intentional')\n")

            meta = _make_metadata(
                name="bad_runner",
                scripts=["bad.py"],
                skill_path=tmpdir,
            )

            with patch("dcc_mcp_ipc.skills.scanner.SkillScanner"):
                mgr = SkillManager()
            handler = mgr._build_handler(meta)
            result = handler()

        assert result["success"] is False
        assert "intentional" in result["error"]
