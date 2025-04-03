"""Tests for connection pool and service discovery.

This module tests the connection pool and service discovery functionality.
"""

# Import built-in modules
import os
import time
import unittest
from unittest import mock

# Import local modules
from dcc_mcp_rpyc.client.pool import ConnectionPool
from dcc_mcp_rpyc.discovery import ServiceInfo
from dcc_mcp_rpyc.discovery import ServiceRegistry
from dcc_mcp_rpyc.discovery.file_strategy import FileDiscoveryStrategy


class TestConnectionPool(unittest.TestCase):
    """Tests for connection pool functionality."""

    def setUp(self):
        """Set up test environment."""
        # Reset the ServiceRegistry singleton
        ServiceRegistry._reset_instance()
        
        # Create a test registry file
        self.registry_path = os.path.join(os.path.dirname(__file__), "test_registry.json")
        if os.path.exists(self.registry_path):
            os.remove(self.registry_path)
            
        # Create a connection pool
        self.pool = ConnectionPool(max_idle_time=1.0, cleanup_interval=0.5)
        
    def tearDown(self):
        """Clean up test environment."""
        # Remove test registry file
        if os.path.exists(self.registry_path):
            os.remove(self.registry_path)
            
    def test_registry_version_compatibility(self):
        """Test registry file version compatibility."""
        # Create a file discovery strategy
        strategy = FileDiscoveryStrategy(registry_path=self.registry_path)
        
        # Register a service
        service_info = ServiceInfo(
            name="test-service",
            host="localhost",
            port=12345,
            dcc_type="test",
            metadata={"version": "1.0.0"},
        )
        self.assertTrue(strategy.register_service(service_info))
        
        # Verify registry file exists
        self.assertTrue(os.path.exists(self.registry_path))
        
        # Create a new strategy to load the registry file
        strategy2 = FileDiscoveryStrategy(registry_path=self.registry_path)
        
        # Discover services
        services = strategy2.discover_services("test")
        
        # Verify service was discovered
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0].name, "test-service")
        self.assertEqual(services[0].host, "localhost")
        self.assertEqual(services[0].port, 12345)
        self.assertEqual(services[0].dcc_type, "test")
        self.assertEqual(services[0].metadata["version"], "1.0.0")
        
    def test_connection_pool_cleanup(self):
        """Test connection pool cleanup."""
        # Mock client with is_connected and close methods
        mock_client = mock.MagicMock()
        mock_client.is_connected.return_value = True
        mock_client.ping.return_value = True
        
        # Add client to pool
        self.pool.pool[("test", "localhost", 12345)] = (mock_client, time.time())
        
        # Verify client is in pool
        self.assertEqual(len(self.pool.pool), 1)
        
        # Wait for cleanup interval
        time.sleep(1.5)  # Wait longer than max_idle_time
        
        # Trigger cleanup
        self.pool.cleanup_idle_connections()
        
        # Verify client was removed from pool
        self.assertEqual(len(self.pool.pool), 0)
        
        # Verify close was called
        mock_client.close.assert_called_once()
        
    def test_client_validation(self):
        """Test client validation."""
        # Mock client with is_connected method that returns False
        mock_client = mock.MagicMock()
        mock_client.is_connected.return_value = False
        
        # Check if client is valid
        self.assertFalse(self.pool._is_client_valid(mock_client))
        
        # Mock client with is_connected method that returns True
        mock_client = mock.MagicMock()
        mock_client.is_connected.return_value = True
        mock_client.ping.return_value = True
        
        # Check if client is valid
        self.assertTrue(self.pool._is_client_valid(mock_client))
        
        # Mock client with is_connected method that returns True but ping raises exception
        mock_client = mock.MagicMock()
        mock_client.is_connected.return_value = True
        mock_client.ping.side_effect = Exception("Test exception")
        
        # Check if client is valid
        self.assertFalse(self.pool._is_client_valid(mock_client))
        
    def test_service_registry_caching(self):
        """Test service registry caching."""
        # Create registry
        registry = ServiceRegistry()
        
        # Create and register strategy
        strategy = FileDiscoveryStrategy(registry_path=self.registry_path)
        registry.register_strategy("file", strategy)
        
        # Register a service
        service_info = ServiceInfo(
            name="test-service",
            host="localhost",
            port=12345,
            dcc_type="test",
            metadata={"version": "1.0.0"},
        )
        registry.register_service("file", service_info)
        
        # Get available DCC instances with refresh=True
        instances1 = registry.get_available_dcc_instances(refresh=True)
        
        # Verify instances
        self.assertIn("test", instances1)
        self.assertEqual(len(instances1["test"]), 1)
        self.assertEqual(instances1["test"][0]["name"], "test-service")
        
        # Register another service
        service_info2 = ServiceInfo(
            name="test-service-2",
            host="localhost",
            port=12346,
            dcc_type="test",
            metadata={"version": "2.0.0"},
        )
        registry.register_service("file", service_info2)
        
        # Get available DCC instances with refresh=False (should use cache)
        instances2 = registry.get_available_dcc_instances(refresh=False)
        
        # Verify instances (should be same as before)
        self.assertEqual(instances1, instances2)
        
        # Get available DCC instances with refresh=True
        instances3 = registry.get_available_dcc_instances(refresh=True)
        
        # Verify instances (should include new service)
        self.assertIn("test", instances3)
        self.assertEqual(len(instances3["test"]), 2)
        

if __name__ == "__main__":
    unittest.main()
