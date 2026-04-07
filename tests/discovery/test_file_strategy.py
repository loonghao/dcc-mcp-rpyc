"""Tests for the file-based service discovery strategy.

This module contains tests for the FileDiscoveryStrategy class.
"""

# Import built-in modules
import json
import os
import tempfile
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.discovery.base import ServiceInfo
from dcc_mcp_ipc.discovery.file_strategy import FileDiscoveryStrategy


@pytest.fixture
def temp_registry_file():
    """Fixture to create a temporary registry file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        f.write(b"{}")
        registry_path = f.name

    yield registry_path

    # Clean up
    if os.path.exists(registry_path):
        os.unlink(registry_path)


@pytest.fixture
def sample_service_info():
    """Fixture to create a sample service info."""
    return ServiceInfo(name="test_service", host="localhost", port=8000, dcc_type="maya", metadata={"version": "2023"})


def test_init_with_custom_path(temp_registry_file):
    """Test initializing with a custom registry path."""
    strategy = FileDiscoveryStrategy(registry_path=temp_registry_file)
    assert strategy.registry_path == temp_registry_file


def test_register_service(temp_registry_file, sample_service_info):
    """Test registering a service."""
    # Setup
    strategy = FileDiscoveryStrategy(registry_path=temp_registry_file)

    # Execute
    success = strategy.register_service(sample_service_info)

    # Verify
    assert success is True

    # Check registry file - key is now dcc_type:host:port
    with open(temp_registry_file) as f:
        data = json.load(f)
        key = "maya:localhost:8000"
        assert key in data
        assert data[key]["name"] == "test_service"
        assert data[key]["host"] == "localhost"
        assert data[key]["port"] == 8000
        assert data[key]["dcc_type"] == "maya"
        assert "timestamp" in data[key]
        assert data[key]["metadata"] == {"version": "2023"}


def test_discover_services(temp_registry_file, sample_service_info):
    """Test discovering services."""
    # Setup
    strategy = FileDiscoveryStrategy(registry_path=temp_registry_file)
    strategy.register_service(sample_service_info)

    # Execute
    services = strategy.discover_services()

    # Verify
    assert len(services) == 1
    assert services[0].name == "test_service"
    assert services[0].host == "localhost"
    assert services[0].port == 8000
    assert services[0].dcc_type == "maya"
    assert services[0].metadata == {"version": "2023"}


def test_discover_services_with_type(temp_registry_file, sample_service_info):
    """Test discovering services with a specific type."""
    # Setup
    strategy = FileDiscoveryStrategy(registry_path=temp_registry_file)
    strategy.register_service(sample_service_info)

    # Execute
    services = strategy.discover_services("maya")

    # Verify
    assert len(services) == 1
    assert services[0].name == "test_service"

    # Test with non-existent type
    services = strategy.discover_services("non_existent")
    assert len(services) == 0


def test_unregister_service(temp_registry_file, sample_service_info):
    """Test unregistering a service."""
    # Setup
    strategy = FileDiscoveryStrategy(registry_path=temp_registry_file)
    strategy.register_service(sample_service_info)

    # Execute
    success = strategy.unregister_service(sample_service_info)

    # Verify
    assert success is True

    # Check registry file - composite key should be gone
    with open(temp_registry_file) as f:
        data = json.load(f)
        assert "maya:localhost:8000" not in data


def test_unregister_non_existent_service(temp_registry_file, sample_service_info):
    """Test unregistering a non-existent service."""
    # Setup
    strategy = FileDiscoveryStrategy(registry_path=temp_registry_file)

    # Execute
    success = strategy.unregister_service(sample_service_info)

    # Verify
    assert success is False


@patch("time.time")
def test_discover_stale_services(mock_time, temp_registry_file, sample_service_info):
    """Test discovering stale services."""
    # Setup
    strategy = FileDiscoveryStrategy(registry_path=temp_registry_file)

    # Set current time
    mock_time.return_value = 1000

    # Register service
    strategy.register_service(sample_service_info)

    # Set time to 2 hours later
    mock_time.return_value = 1000 + 7200  # 2 hours = 7200 seconds

    # Execute
    services = strategy.discover_services()

    # Verify
    assert len(services) == 0  # Service should be considered stale


def test_register_multiple_instances_same_dcc_type(temp_registry_file):
    """Test registering multiple instances of the same DCC type.

    This is the core regression test for the multi-instance bug where
    the second instance would overwrite the first when using dcc_type
    as the only registry key.
    """
    strategy = FileDiscoveryStrategy(registry_path=temp_registry_file)

    maya_instance_1 = ServiceInfo(
        name="maya-2024-shot010",
        host="127.0.0.1",
        port=18812,
        dcc_type="maya",
        metadata={"scene": "shot_010.ma", "version": "2024"},
    )
    maya_instance_2 = ServiceInfo(
        name="maya-2024-shot020",
        host="127.0.0.1",
        port=18813,
        dcc_type="maya",
        metadata={"scene": "shot_020.ma", "version": "2024"},
    )

    # Register both instances
    assert strategy.register_service(maya_instance_1) is True
    assert strategy.register_service(maya_instance_2) is True

    # Both should be discoverable
    services = strategy.discover_services("maya")
    assert len(services) == 2

    # Verify distinct instances
    ports = {s.port for s in services}
    assert ports == {18812, 18813}

    names = {s.name for s in services}
    assert names == {"maya-2024-shot010", "maya-2024-shot020"}

    # Check registry file has both keys
    with open(temp_registry_file) as f:
        data = json.load(f)
        assert "maya:127.0.0.1:18812" in data
        assert "maya:127.0.0.1:18813" in data


def test_register_mixed_dcc_types(temp_registry_file):
    """Test registering instances of different DCC types."""
    strategy = FileDiscoveryStrategy(registry_path=temp_registry_file)

    maya = ServiceInfo(name="maya-2024", host="127.0.0.1", port=18812, dcc_type="maya")
    houdini = ServiceInfo(name="houdini-20", host="127.0.0.1", port=18820, dcc_type="houdini")
    blender = ServiceInfo(name="blender-4", host="127.0.0.1", port=18830, dcc_type="blender")

    for svc in [maya, houdini, blender]:
        assert strategy.register_service(svc) is True

    # Discover all
    all_services = strategy.discover_services()
    assert len(all_services) == 3

    # Filter by type
    maya_services = strategy.discover_services("maya")
    assert len(maya_services) == 1
    assert maya_services[0].port == 18812

    houdini_services = strategy.discover_services("houdini")
    assert len(houdini_services) == 1
    assert houdini_services[0].port == 18820


def test_unregister_specific_instance(temp_registry_file):
    """Test unregistering one instance without affecting others of the same type."""
    strategy = FileDiscoveryStrategy(registry_path=temp_registry_file)

    maya1 = ServiceInfo(name="maya-1", host="127.0.0.1", port=18812, dcc_type="maya")
    maya2 = ServiceInfo(name="maya-2", host="127.0.0.1", port=18813, dcc_type="maya")

    strategy.register_service(maya1)
    strategy.register_service(maya2)

    # Unregister only instance 1
    assert strategy.unregister_service(maya1) is True

    # Instance 2 should still be discoverable
    services = strategy.discover_services("maya")
    assert len(services) == 1
    assert services[0].port == 18813
    assert services[0].name == "maya-2"


def test_backward_compat_legacy_registry_format(temp_registry_file):
    """Test backward compatibility with legacy registry format (dcc_type as key)."""
    # Import built-in modules
    import time as time_mod

    # Write legacy format directly
    legacy_data = {
        "maya": {
            "name": "legacy-maya",
            "host": "127.0.0.1",
            "port": 18812,
            "timestamp": time_mod.time(),
            "metadata": {},
        },
    }
    with open(temp_registry_file, "w") as f:
        json.dump(legacy_data, f)

    # Strategy should still discover legacy entries
    strategy = FileDiscoveryStrategy(registry_path=temp_registry_file)
    services = strategy.discover_services("maya")
    assert len(services) == 1
    assert services[0].name == "legacy-maya"
    assert services[0].dcc_type == "maya"


def test_make_service_key():
    """Test the composite key generation."""
    info = ServiceInfo(name="test", host="192.168.1.10", port=9999, dcc_type="houdini")
    key = FileDiscoveryStrategy._make_service_key(info)
    assert key == "houdini:192.168.1.10:9999"


class TestFileStrategyErrorPaths:
    """Tests covering exception/error branches in FileDiscoveryStrategy."""

    def test_get_default_config_dir_exception_fallback_nt(self, monkeypatch):
        """_get_default_config_dir() falls back to APPDATA when get_config_dir raises (lines 30-38)."""
        import os
        import tempfile

        # Import local modules
        import dcc_mcp_ipc.discovery.file_strategy as mod

        tmp = tempfile.mkdtemp()
        monkeypatch.setenv("APPDATA", tmp)
        monkeypatch.setattr("os.name", "nt")

        with patch("dcc_mcp_ipc.discovery.file_strategy.get_config_dir", side_effect=RuntimeError("unavailable")):
            result = mod._get_default_config_dir()

        assert result.startswith(tmp)
        assert os.path.isdir(result)

    def test_get_default_config_dir_exception_fallback_posix(self, monkeypatch):
        """_get_default_config_dir() falls back to XDG_CONFIG_HOME on non-Windows (lines 35-38)."""
        import os
        import tempfile

        # Import local modules
        import dcc_mcp_ipc.discovery.file_strategy as mod

        tmp = tempfile.mkdtemp()
        monkeypatch.setattr("os.name", "posix")
        monkeypatch.setenv("XDG_CONFIG_HOME", tmp)

        with patch("dcc_mcp_ipc.discovery.file_strategy.get_config_dir", side_effect=RuntimeError("unavailable")):
            result = mod._get_default_config_dir()

        assert result.startswith(tmp)

    def test_load_registry_json_error(self, tmp_path):
        """_load_registry() logs error when file contains invalid JSON (lines 71-72)."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("NOT_JSON")
        strategy = FileDiscoveryStrategy(registry_path=str(bad_file))
        # Should not raise; _services remains empty
        assert strategy._services == {}

    def test_save_registry_permission_error(self, tmp_path):
        """_save_registry() logs error on write failure (lines 83-84)."""
        registry_file = tmp_path / "registry.json"
        registry_file.write_text("{}")
        strategy = FileDiscoveryStrategy(registry_path=str(registry_file))
        service = ServiceInfo(name="test", host="localhost", port=8001, dcc_type="maya")
        strategy._services["key"] = {"host": "h"}

        with patch("builtins.open", side_effect=PermissionError("read-only")):
            strategy._save_registry()  # must not raise

    def test_discover_invalid_service_data_skipped(self, tmp_path):
        """Non-dict service entry is skipped with warning (lines 103-104)."""
        import json as json_mod
        import time

        registry_file = tmp_path / "registry.json"
        data = {
            "invalid_entry": "not_a_dict",  # triggers line 103
            "maya:localhost:9001": {
                "name": "maya-ok",
                "host": "localhost",
                "port": 9001,
                "dcc_type": "maya",
                "timestamp": time.time(),
                "metadata": {},
            },
        }
        registry_file.write_text(json_mod.dumps(data))
        strategy = FileDiscoveryStrategy(registry_path=str(registry_file))
        services = strategy.discover_services()
        assert len(services) == 1
        assert services[0].name == "maya-ok"

    def test_discover_service_info_creation_error(self, tmp_path):
        """ServiceInfo construction error is caught per entry (lines 129-130)."""
        import json as json_mod
        import time

        registry_file = tmp_path / "registry.json"
        data = {
            "maya:localhost:9002": {
                "name": "maya-test",
                "host": "localhost",
                "port": 9002,
                "dcc_type": "maya",
                "timestamp": time.time(),
                "metadata": {},
            },
        }
        registry_file.write_text(json_mod.dumps(data))
        strategy = FileDiscoveryStrategy(registry_path=str(registry_file))

        # Simulate ServiceInfo constructor raising
        with patch("dcc_mcp_ipc.discovery.file_strategy.ServiceInfo", side_effect=ValueError("bad data")):
            services = strategy.discover_services()

        assert services == []

    def test_register_service_exception(self, tmp_path):
        """register_service() logs error and returns False on exception (lines 187-189)."""
        registry_file = tmp_path / "registry.json"
        registry_file.write_text("{}")
        strategy = FileDiscoveryStrategy(registry_path=str(registry_file))
        service = ServiceInfo(name="s", host="h", port=1, dcc_type="t")

        with patch.object(strategy, "_save_registry", side_effect=RuntimeError("disk full")):
            result = strategy.register_service(service)

        assert result is False

    def test_unregister_legacy_dcc_type_key(self, tmp_path):
        """unregister_service() falls back to legacy dcc_type key (line 212)."""
        import json as json_mod
        import time

        registry_file = tmp_path / "registry.json"
        # Store with legacy key (just dcc_type, no host:port)
        data = {
            "maya": {
                "name": "legacy-maya",
                "host": "127.0.0.1",
                "port": 18812,
                "dcc_type": "maya",
                "timestamp": time.time(),
                "metadata": {},
            }
        }
        registry_file.write_text(json_mod.dumps(data))
        strategy = FileDiscoveryStrategy(registry_path=str(registry_file))

        # unregister using the new-format ServiceInfo; composite key won't match legacy key
        service = ServiceInfo(name="legacy-maya", host="127.0.0.1", port=18812, dcc_type="maya")
        result = strategy.unregister_service(service)

        assert result is True  # Should have found and removed the legacy key

    def test_unregister_service_exception(self, tmp_path):
        """unregister_service() logs error and returns False on exception (lines 228-230)."""
        registry_file = tmp_path / "registry.json"
        registry_file.write_text("{}")
        strategy = FileDiscoveryStrategy(registry_path=str(registry_file))
        service = ServiceInfo(name="s", host="h", port=1, dcc_type="t")

        with patch.object(strategy, "_load_registry", side_effect=RuntimeError("fs error")):
            result = strategy.unregister_service(service)

        assert result is False
