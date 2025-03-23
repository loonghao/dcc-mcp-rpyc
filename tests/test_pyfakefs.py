"""Tests using pyfakefs.

This module demonstrates how to use pyfakefs to test file operations
without touching the real file system.
"""

# Import built-in modules
import os
import time

# Import third-party modules
from pyfakefs.fake_filesystem_unittest import TestCase

# Import local modules
from dcc_mcp_rpyc.discovery import DEFAULT_REGISTRY_PATH
from dcc_mcp_rpyc.discovery import _load_registry_file
from dcc_mcp_rpyc.discovery import _save_registry_file
from dcc_mcp_rpyc.discovery import cleanup_stale_services
from dcc_mcp_rpyc.discovery import discover_services
from dcc_mcp_rpyc.discovery import register_service
from dcc_mcp_rpyc.discovery import unregister_service


class TestWithPyfakefs(TestCase):
    """Tests using pyfakefs."""

    def setUp(self):
        """Set up the fake file system."""
        self.setUpPyfakefs()

        # Create the directory for the registry file
        os.makedirs(os.path.dirname(DEFAULT_REGISTRY_PATH), exist_ok=True)

        # Create a fake registry file
        self.registry_path = os.path.join(os.path.dirname(DEFAULT_REGISTRY_PATH), "test_registry.pkl")

        # Reset the module-level variables in discovery.py
        # Import local modules
        from dcc_mcp_rpyc.discovery import _service_registry

        _service_registry.clear()

    def test_register_service_with_fake_fs(self):
        """Test registering a service with a fake file system."""
        # Register a service
        registry_file = register_service(
            dcc_name="test_dcc", host="localhost", port=12345, registry_path=self.registry_path
        )

        # Verify the registry file exists
        self.assertTrue(os.path.exists(registry_file), "Registry file should exist")

        # Verify the registry file contains the service
        registry = _load_registry_file(registry_file)

        self.assertIn("test_dcc", registry, "Registry should contain the service")
        self.assertEqual(len(registry["test_dcc"]), 1, "Registry should contain one service")
        self.assertEqual(registry["test_dcc"][0]["host"], "localhost", "Service host should be correct")
        self.assertEqual(registry["test_dcc"][0]["port"], 12345, "Service port should be correct")
        self.assertIn("timestamp", registry["test_dcc"][0], "Service should have a timestamp")

    def test_unregister_service_with_fake_fs(self):
        """Test unregistering a service with a fake file system."""
        temp_registry_path = self.registry_path
        # Register a service
        register_service(dcc_name="test_dcc", host="localhost", port=12345, registry_path=temp_registry_path)

        # Unregister the service
        result = unregister_service("test_dcc", registry_path=self.registry_path)
        self.assertTrue(result, "Unregistering the service should succeed")

        # Verify the registry file no longer contains the service
        registry = _load_registry_file(self.registry_path)

        self.assertTrue(
            "test_dcc" not in registry or not registry["test_dcc"], "Registry should not contain the service"
        )

    def test_discover_services_with_fake_fs(self):
        """Test discovering services with a fake file system."""
        # Register services
        register_service(dcc_name="test_dcc1", host="localhost", port=12345, registry_path=self.registry_path)

        register_service(dcc_name="test_dcc2", host="localhost", port=12346, registry_path=self.registry_path)

        # Discover all services
        services = discover_services(registry_path=self.registry_path)
        self.assertEqual(len(services), 2, "Should discover two services")

        # Discover services for a specific DCC
        services = discover_services(dcc_name="test_dcc1", registry_path=self.registry_path)
        self.assertEqual(len(services), 1, "Should discover one service")
        self.assertEqual(services[0]["host"], "localhost", "Service host should be correct")
        self.assertEqual(services[0]["port"], 12345, "Service port should be correct")

    def test_cleanup_stale_services_with_fake_fs(self):
        """Test cleaning up stale services with a fake file system."""
        # Clear any existing registry first
        if os.path.exists(self.registry_path):
            os.remove(self.registry_path)

        # Register a service
        register_service(
            dcc_name="test_dcc",
            host="127.0.0.1",  # Use 127.0.0.1 instead of localhost
            port=12345,
            registry_path=self.registry_path,
        )

        # Verify the service was registered
        registry = _load_registry_file(self.registry_path)
        assert "test_dcc" in registry, "Registry should contain the service"
        assert len(registry["test_dcc"]) == 1, "Registry should contain one service"

        # Modify the timestamp to make the service stale
        registry["test_dcc"][0]["timestamp"] = time.time() - 7200  # 2 hours ago

        # Save the modified registry
        _save_registry_file(registry, self.registry_path)

        # Reset the global registry cache to ensure it reloads from disk
        # Import local modules
        import dcc_mcp_rpyc.discovery as discovery

        discovery._registry_loaded = False
        discovery._service_registry = {}

        # Clean up stale services with a max age of 1 hour
        result = cleanup_stale_services(max_age=3600, registry_path=self.registry_path)
        self.assertTrue(result, "Cleanup should succeed")

        # Verify the service was removed
        registry = _load_registry_file(self.registry_path)
        self.assertTrue(
            "test_dcc" not in registry or not registry["test_dcc"], "Registry should not contain the stale service"
        )
