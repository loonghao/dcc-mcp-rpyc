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
from dcc_mcp_rpyc.discovery.base import ServiceInfo
from dcc_mcp_rpyc.discovery.file_strategy import FileDiscoveryStrategy


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

    # Check registry file
    with open(temp_registry_file) as f:
        data = json.load(f)
        assert "maya" in data
        assert data["maya"]["name"] == "test_service"
        assert data["maya"]["host"] == "localhost"
        assert data["maya"]["port"] == 8000
        assert "timestamp" in data["maya"]
        assert data["maya"]["metadata"] == {"version": "2023"}


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

    # Check registry file
    with open(temp_registry_file) as f:
        data = json.load(f)
        assert "maya" not in data


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
