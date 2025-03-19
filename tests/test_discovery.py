"""Tests for the discovery module.

This module contains tests for the service discovery functionality.
"""

# Import built-in modules
import os
import time

# Import local modules
from dcc_mcp_rpyc.discovery import _load_pickle
from dcc_mcp_rpyc.discovery import _save_pickle
from dcc_mcp_rpyc.discovery import cleanup_stale_services
from dcc_mcp_rpyc.discovery import discover_services
from dcc_mcp_rpyc.discovery import find_service_registry_files
from dcc_mcp_rpyc.discovery import register_service
from dcc_mcp_rpyc.discovery import unregister_service


class TestDiscovery:
    """Tests for the discovery module."""

    def test_register_service(self, temp_registry_path: str):
        """Test registering a service.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        # Clear any existing registry first
        if os.path.exists(temp_registry_path):
            os.remove(temp_registry_path)

        # Reset the global registry cache
        # Import local modules
        import dcc_mcp_rpyc.discovery as discovery

        discovery._registry_loaded = False
        discovery._service_registry = {}

        # Register a service
        registry_file = register_service(
            dcc_name="test_dcc",
            host="127.0.0.1",  # Use 127.0.0.1 instead of localhost
            port=12345,
            registry_path=temp_registry_path,
        )

        # Verify the registry file exists
        assert os.path.exists(registry_file), "Registry file should exist"

        # Verify the registry file contains the service
        registry = _load_pickle(registry_file)

        assert "test_dcc" in registry, "Registry should contain the service"
        assert len(registry["test_dcc"]) == 1, "Registry should contain one service"
        assert registry["test_dcc"][0]["host"] == "127.0.0.1", "Service host should be correct"
        assert registry["test_dcc"][0]["port"] == 12345, "Service port should be correct"
        assert "timestamp" in registry["test_dcc"][0], "Service should have a timestamp"

    def test_unregister_service(self, temp_registry_path: str):
        """Test unregistering a service.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        # Clear any existing registry first
        if os.path.exists(temp_registry_path):
            os.remove(temp_registry_path)

        # Reset the global registry cache
        # Import local modules
        import dcc_mcp_rpyc.discovery as discovery

        discovery._registry_loaded = False
        discovery._service_registry = {}

        # Register a service
        registry_file = register_service(
            dcc_name="test_dcc",
            host="127.0.0.1",  # Use 127.0.0.1 instead of localhost
            port=12345,
            registry_path=temp_registry_path,
        )

        # Verify the service was registered
        registry = _load_pickle(registry_file)
        assert "test_dcc" in registry, "Registry should contain the service"

        # Unregister the service
        result = unregister_service("test_dcc", registry_path=temp_registry_path)
        assert result, "Unregistering the service should succeed"

        # Verify the service was unregistered
        registry = _load_pickle(registry_file)
        assert "test_dcc" not in registry or not registry["test_dcc"], "Registry should not contain the service"

        # Reset the global registry cache
        discovery._registry_loaded = False
        discovery._service_registry = {}

    def test_discover_services(self, temp_registry_path: str):
        """Test discovering services.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        # Clear any existing registry first
        if os.path.exists(temp_registry_path):
            os.remove(temp_registry_path)

        # Reset the global registry cache
        # Import local modules
        import dcc_mcp_rpyc.discovery as discovery

        discovery._registry_loaded = False
        discovery._service_registry = {}

        # Register services
        register_service(
            dcc_name="test_dcc1",
            host="127.0.0.1",  # Use 127.0.0.1 instead of localhost
            port=12345,
            registry_path=temp_registry_path,
        )

        register_service(
            dcc_name="test_dcc2",
            host="127.0.0.1",  # Use 127.0.0.1 instead of localhost
            port=12346,
            registry_path=temp_registry_path,
        )

        # Discover all services
        services = discover_services(registry_path=temp_registry_path)
        assert len(services) == 2, "Should discover two services"

        # Discover services for a specific DCC
        services = discover_services(dcc_name="test_dcc1", registry_path=temp_registry_path)
        assert len(services) == 1, "Should discover one service"
        assert services[0]["host"] == "127.0.0.1", "Service host should be correct"
        assert services[0]["port"] == 12345, "Service port should be correct"

        # Reset the global registry cache
        discovery._registry_loaded = False
        discovery._service_registry = {}

    def test_cleanup_stale_services(self, temp_registry_path: str):
        """Test cleaning up stale services.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        # Clear any existing registry first
        if os.path.exists(temp_registry_path):
            os.remove(temp_registry_path)

        # Reset the global registry cache
        # Import local modules
        import dcc_mcp_rpyc.discovery as discovery

        discovery._registry_loaded = False
        discovery._service_registry = {}

        # Register a service
        register_service(
            dcc_name="test_dcc",
            host="127.0.0.1",  # Use 127.0.0.1 instead of localhost
            port=12345,
            registry_path=temp_registry_path,
        )

        # Verify the service was registered
        registry = _load_pickle(temp_registry_path)
        assert "test_dcc" in registry, "Registry should contain the service"
        assert len(registry["test_dcc"]) == 1, "Registry should contain one service"

        # Modify the timestamp to make the service stale
        registry["test_dcc"][0]["timestamp"] = time.time() - 7200  # 2 hours ago

        # Save the modified registry
        _save_pickle(registry, temp_registry_path)

        # Reset the global registry cache to ensure it reloads from disk
        discovery._registry_loaded = False
        discovery._service_registry = {}

        # Clean up stale services with a max age of 1 hour
        result = cleanup_stale_services(max_age=3600, registry_path=temp_registry_path)
        assert result, "Cleaning up stale services should succeed"

        # Verify the service was removed
        registry = _load_pickle(temp_registry_path)
        assert "test_dcc" not in registry or not registry["test_dcc"], "Registry should not contain the stale service"

        # Reset the global registry cache
        discovery._registry_loaded = False
        discovery._service_registry = {}

    def test_load_and_save_registry(self, temp_registry_path: str):
        """Test loading and saving the registry.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        # Clear any existing registry first
        if os.path.exists(temp_registry_path):
            os.remove(temp_registry_path)

        # Reset the global registry cache
        # Import local modules
        import dcc_mcp_rpyc.discovery as discovery

        discovery._registry_loaded = False
        discovery._service_registry = {}

        # Create a registry
        registry = {
            "test_dcc": [
                {
                    "host": "127.0.0.1",  # Use 127.0.0.1 instead of localhost
                    "port": 12345,
                    "timestamp": time.time(),
                }
            ]
        }

        # Save the registry
        _save_pickle(registry, temp_registry_path)

        # Load the registry
        loaded_registry = _load_pickle(temp_registry_path)

        # Verify the registry was loaded correctly
        assert "test_dcc" in loaded_registry, "Registry should contain the service"
        assert len(loaded_registry["test_dcc"]) == 1, "Registry should contain one service"
        assert loaded_registry["test_dcc"][0]["host"] == "127.0.0.1", "Service host should be correct"
        assert loaded_registry["test_dcc"][0]["port"] == 12345, "Service port should be correct"

        # Reset the global registry cache
        discovery._registry_loaded = False
        discovery._service_registry = {}

    def test_find_service_registry_files(self, temp_registry_path: str):
        """Test finding service registry files.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        # Clear any existing registry first
        if os.path.exists(temp_registry_path):
            os.remove(temp_registry_path)

        # Reset the global registry cache
        # Import local modules
        import dcc_mcp_rpyc.discovery as discovery

        discovery._registry_loaded = False
        discovery._service_registry = {}

        # Register a service
        register_service(
            dcc_name="test_dcc",
            host="127.0.0.1",  # Use 127.0.0.1 instead of localhost
            port=12345,
            registry_path=temp_registry_path,
        )

        # Verify the registry file exists
        assert os.path.exists(temp_registry_path), "Registry file should exist"

        # Load the registry directly to verify it contains the DCC
        registry = _load_pickle(temp_registry_path)
        assert "test_dcc" in registry, "Registry should contain the service"

        # Find registry files for a specific DCC using direct path
        files = find_service_registry_files(dcc_name="test_dcc", registry_path=temp_registry_path)
        assert len(files) > 0, "Should find the registry file when specifying exact path"

        # Reset the global registry cache
        discovery._registry_loaded = False
        discovery._service_registry = {}
