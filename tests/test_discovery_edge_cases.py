"""Tests for edge cases in the discovery module.

This module contains tests for edge cases and error handling in the discovery module
that are currently lacking coverage.
"""

# Import built-in modules
import json
import time
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.discovery import discover_services
from dcc_mcp_rpyc.discovery import get_latest_service
from dcc_mcp_rpyc.discovery import load_registry
from dcc_mcp_rpyc.discovery import register_service
from dcc_mcp_rpyc.discovery import save_registry
from dcc_mcp_rpyc.discovery import unregister_service


@pytest.fixture
def temp_registry_path(tmp_path):
    """Fixture providing a temporary registry file path.

    Args:
    ----
        tmp_path: pytest fixture providing a temporary directory

    Returns:
    -------
        Path to a temporary registry file

    """
    registry_file = tmp_path / "test_registry.json"
    # Create an empty registry file
    registry_file.write_text("{}")
    return str(registry_file)


class TestDiscoveryEdgeCases:
    """Tests for edge cases in the discovery module."""

    def test_register_service_custom_path(self, temp_registry_path):
        """Test register_service with custom path.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        # Test with custom path
        with patch("dcc_mcp_rpyc.discovery._registry_loaded", False):
            with patch("dcc_mcp_rpyc.discovery.load_registry"):
                with patch("dcc_mcp_rpyc.discovery.save_registry", return_value=True):
                    result = register_service("test_dcc", "127.0.0.1", 12345, registry_path=temp_registry_path)
                    assert result == temp_registry_path

    def test_register_service_default_path(self):
        """Test register_service with default path."""
        # Test with default path (should create a unique path)
        with patch("dcc_mcp_rpyc.discovery._registry_loaded", False):
            with patch("dcc_mcp_rpyc.discovery.load_registry"):
                with patch("dcc_mcp_rpyc.discovery.save_registry", return_value=True):
                    with patch("os.getpid", return_value=12345):
                        with patch("os.path.dirname", return_value="/path/to/registry"):
                            with patch("os.makedirs") as mock_makedirs:
                                result = register_service("test_dcc", "127.0.0.1", 12345)
                                assert "test_dcc" in result
                                assert "12345" in result
                                mock_makedirs.assert_called_once_with("/path/to/registry", exist_ok=True)

    def test_register_service_save_failure(self):
        """Test register_service with save failure."""
        # Test with save failure
        with patch("dcc_mcp_rpyc.discovery._registry_loaded", False):
            with patch("dcc_mcp_rpyc.discovery.load_registry"):
                with patch("dcc_mcp_rpyc.discovery.save_registry", return_value=False):
                    result = register_service("test_dcc", "127.0.0.1", 12345, registry_path="/path/to/registry")
                    assert result == ""

    def test_unregister_service_nonexistent_file(self):
        """Test unregister_service with non-existent file."""
        # Test with non-existent file
        with patch("os.path.exists", return_value=False):
            result = unregister_service("test_dcc", registry_path="/nonexistent/path")
            assert result is True  # Nothing to unregister

    def test_unregister_service_existing(self, temp_registry_path):
        """Test unregister_service with existing service.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        # Create a registry with a service
        registry = {"test_dcc": [{"host": "127.0.0.1", "port": 12345, "timestamp": time.time()}]}
        with open(temp_registry_path, "w") as f:
            json.dump(registry, f)

        # Unregister the service
        result = unregister_service("test_dcc", registry_path=temp_registry_path)
        assert result is True

        # Verify the service was unregistered (set to empty list, not removed)
        with open(temp_registry_path) as f:
            registry = json.load(f)
            assert "test_dcc" in registry
            assert registry["test_dcc"] == []

    def test_unregister_service_exception(self):
        """Test unregister_service with exception."""
        # Create a mock loader that raises an exception
        mock_loader = MagicMock(side_effect=Exception("Test error"))

        # Test with custom registry loader that raises an exception
        with patch("os.path.exists", return_value=True):
            result = unregister_service("test_dcc", registry_path="/path/to/registry", registry_loader=mock_loader)
            assert result is False
            mock_loader.assert_called_once_with("/path/to/registry")

    def test_discover_services_empty(self, temp_registry_path):
        """Test discover_services with empty registry.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        # Discover services in empty registry
        with patch("dcc_mcp_rpyc.discovery.find_service_registry_files", return_value=[temp_registry_path]):
            result = discover_services(registry_path=temp_registry_path)
            assert result == []

    def test_discover_services_filter_stale(self):
        """Test discover_services filtering stale services."""
        # Create a registry with fresh and stale services
        registry = {
            "fresh_dcc": [
                {
                    "host": "127.0.0.1",
                    "port": 12345,
                    "timestamp": 900,  # Fresh timestamp
                }
            ],
            "stale_dcc": [
                {
                    "host": "127.0.0.1",
                    "port": 12346,
                    "timestamp": 0,  # Very old timestamp
                }
            ],
        }

        # Mock loading registry
        with patch("dcc_mcp_rpyc.discovery._load_registry_file", return_value=registry):
            with patch("dcc_mcp_rpyc.discovery.find_service_registry_files", return_value=["/path/to/registry"]):
                with patch("time.time", return_value=1000):  # Current time
                    result = discover_services(max_age=200)
                    # Result should be a list of dictionaries with 'dcc' field added
                    assert len(result) == 1
                    assert result[0]["dcc"] == "fresh_dcc"
                    assert result[0]["host"] == "127.0.0.1"
                    assert result[0]["port"] == 12345

    def test_discover_services_specific_dcc(self):
        """Test discover_services for a specific DCC."""
        # Create a registry with multiple services
        registry = {
            "dcc1": [
                {
                    "host": "127.0.0.1",
                    "port": 12345,
                    "timestamp": time.time(),
                }
            ],
            "dcc2": [
                {
                    "host": "127.0.0.1",
                    "port": 12346,
                    "timestamp": time.time(),
                }
            ],
        }

        # Mock loading registry
        with patch("dcc_mcp_rpyc.discovery._load_registry_file", return_value=registry):
            with patch("dcc_mcp_rpyc.discovery.find_service_registry_files", return_value=["/path/to/registry"]):
                result = discover_services("dcc1")
                assert len(result) == 1
                assert result[0]["dcc"] == "dcc1"

    def test_discover_services_multiple_files(self):
        """Test discover_services with multiple registry files."""
        # Create two registry files with different services
        registry1 = {"dcc1": [{"host": "127.0.0.1", "port": 12345, "timestamp": time.time()}]}
        registry2 = {"dcc2": [{"host": "127.0.0.1", "port": 12346, "timestamp": time.time()}]}

        # Create mock functions for dependency injection
        mock_registry_loader = MagicMock(side_effect=[registry1, registry2])
        mock_files_finder = MagicMock(return_value=["/path/to/registry1", "/path/to/registry2"])

        # Test discover_services with custom loader and finder
        result = discover_services(registry_loader=mock_registry_loader, registry_files_finder=mock_files_finder)

        # Verify the results
        assert len(result) == 2
        assert {s["dcc"] for s in result} == {"dcc1", "dcc2"}

        # Verify the mock functions were called correctly
        mock_files_finder.assert_called_once_with(None)
        assert mock_registry_loader.call_count == 2
        mock_registry_loader.assert_any_call("/path/to/registry1")
        mock_registry_loader.assert_any_call("/path/to/registry2")

    def test_get_latest_service_empty(self):
        """Test get_latest_service with empty list."""
        result = get_latest_service([])
        assert result == {}

    def test_get_latest_service_multiple(self):
        """Test get_latest_service with multiple services."""
        services = [
            {"host": "127.0.0.1", "port": 12345, "timestamp": 100},
            {"host": "127.0.0.1", "port": 12346, "timestamp": 200},  # Latest
            {"host": "127.0.0.1", "port": 12347, "timestamp": 150},
        ]
        result = get_latest_service(services)
        assert result["port"] == 12346
        assert result["timestamp"] == 200

    def test_load_save_registry(self, temp_registry_path):
        """Test load_registry and save_registry functions.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        # Test load_registry
        # Import local modules
        import dcc_mcp_rpyc.discovery

        with patch.object(dcc_mcp_rpyc.discovery, "_registry_loaded", False):
            with patch.object(dcc_mcp_rpyc.discovery, "_service_registry", {}):
                # Write test data to registry file
                test_data = {"test_dcc": [{"host": "127.0.0.1", "port": 12345, "timestamp": time.time()}]}
                with open(temp_registry_path, "w") as f:
                    json.dump(test_data, f)

                # Load the registry
                result = load_registry(temp_registry_path)
                assert result is True
                assert dcc_mcp_rpyc.discovery._service_registry == test_data
                assert dcc_mcp_rpyc.discovery._registry_loaded is True

        # Test save_registry
        with patch.object(dcc_mcp_rpyc.discovery, "_service_registry", test_data):
            result = save_registry(temp_registry_path)
            assert result is True

            # Verify the saved data
            with open(temp_registry_path) as f:
                saved_data = json.load(f)
                assert saved_data == test_data
