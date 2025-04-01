"""Tests for the service registry module.

This module contains tests for the ServiceRegistry class.
"""

# Import built-in modules
from unittest.mock import MagicMock

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.discovery.base import ServiceInfo
from dcc_mcp_rpyc.discovery.registry import ServiceRegistry


@pytest.fixture
def clean_registry():
    """Fixture to ensure a clean registry for each test."""
    ServiceRegistry._reset_instance()
    yield
    ServiceRegistry._reset_instance()


@pytest.fixture
def mock_strategy():
    """Fixture to create a mock strategy."""
    strategy = MagicMock()
    strategy.discover_services.return_value = []
    strategy.register_service.return_value = True
    strategy.unregister_service.return_value = True
    return strategy


@pytest.fixture
def sample_service_info():
    """Fixture to create a sample service info."""
    return ServiceInfo(name="test_service", host="localhost", port=8000, dcc_type="maya", metadata={"version": "2023"})


def test_registry_singleton(clean_registry):
    """Test that ServiceRegistry follows the singleton pattern."""
    registry1 = ServiceRegistry()
    registry2 = ServiceRegistry()
    assert registry1 is registry2


def test_register_strategy(clean_registry, mock_strategy):
    """Test registering a strategy."""
    registry = ServiceRegistry()
    registry.register_strategy("test", mock_strategy)
    assert registry.get_strategy("test") is mock_strategy
    assert "test" in registry.list_strategies()


def test_discover_services(clean_registry, mock_strategy, sample_service_info):
    """Test discovering services."""
    # Setup
    registry = ServiceRegistry()
    registry.register_strategy("test", mock_strategy)
    mock_strategy.discover_services.return_value = [sample_service_info]

    # Execute
    services = registry.discover_services("test")

    # Verify
    assert len(services) == 1
    assert services[0] == sample_service_info
    mock_strategy.discover_services.assert_called_once_with(None)


def test_discover_services_with_type(clean_registry, mock_strategy, sample_service_info):
    """Test discovering services with a specific type."""
    # Setup
    registry = ServiceRegistry()
    registry.register_strategy("test", mock_strategy)
    mock_strategy.discover_services.return_value = [sample_service_info]

    # Execute
    services = registry.discover_services("test", "maya")

    # Verify
    assert len(services) == 1
    assert services[0] == sample_service_info
    mock_strategy.discover_services.assert_called_once_with("maya")


def test_discover_services_strategy_not_found(clean_registry):
    """Test discovering services with a non-existent strategy."""
    registry = ServiceRegistry()
    with pytest.raises(ValueError):
        registry.discover_services("non_existent")


def test_register_service(clean_registry, mock_strategy, sample_service_info):
    """Test registering a service."""
    # Setup
    registry = ServiceRegistry()
    registry.register_strategy("test", mock_strategy)

    # Execute
    success = registry.register_service("test", sample_service_info)

    # Verify
    assert success is True
    mock_strategy.register_service.assert_called_once_with(sample_service_info)


def test_register_service_strategy_not_found(clean_registry, sample_service_info):
    """Test registering a service with a non-existent strategy."""
    registry = ServiceRegistry()
    with pytest.raises(ValueError):
        registry.register_service("non_existent", sample_service_info)


def test_unregister_service(clean_registry, mock_strategy, sample_service_info):
    """Test unregistering a service."""
    # Setup
    registry = ServiceRegistry()
    registry.register_strategy("test", mock_strategy)
    registry.register_service("test", sample_service_info)

    # Execute
    success = registry.unregister_service("test", sample_service_info)

    # Verify
    assert success is True
    mock_strategy.unregister_service.assert_called_once_with(sample_service_info)


def test_unregister_service_strategy_not_found(clean_registry, sample_service_info):
    """Test unregistering a service with a non-existent strategy."""
    registry = ServiceRegistry()
    with pytest.raises(ValueError):
        registry.unregister_service("non_existent", sample_service_info)


def test_get_service(clean_registry, mock_strategy, sample_service_info):
    """Test getting a service by DCC type and name."""
    # Setup
    registry = ServiceRegistry()
    registry.register_strategy("test", mock_strategy)
    mock_strategy.discover_services.return_value = [sample_service_info]
    registry.discover_services("test")

    # Execute
    service = registry.get_service("maya", "test_service")

    # Verify
    assert service == sample_service_info


def test_get_service_by_dcc_type_only(clean_registry, mock_strategy, sample_service_info):
    """Test getting a service by DCC type only."""
    # Setup
    registry = ServiceRegistry()
    registry.register_strategy("test", mock_strategy)
    mock_strategy.discover_services.return_value = [sample_service_info]
    registry.discover_services("test")

    # Execute
    service = registry.get_service("maya")

    # Verify
    assert service == sample_service_info


def test_get_service_not_found(clean_registry):
    """Test getting a non-existent service."""
    registry = ServiceRegistry()
    service = registry.get_service("non_existent")
    assert service is None


def test_list_services(clean_registry, mock_strategy, sample_service_info):
    """Test listing all services."""
    # Setup
    registry = ServiceRegistry()
    registry.register_strategy("test", mock_strategy)
    mock_strategy.discover_services.return_value = [sample_service_info]
    registry.discover_services("test")

    # Execute
    services = registry.list_services()

    # Verify
    assert len(services) == 1
    assert services[0] == sample_service_info


def test_list_services_by_dcc_type(clean_registry, mock_strategy, sample_service_info):
    """Test listing services filtered by DCC type."""
    # Setup
    registry = ServiceRegistry()
    registry.register_strategy("test", mock_strategy)
    mock_strategy.discover_services.return_value = [sample_service_info]
    registry.discover_services("test")

    # Execute
    services = registry.list_services("maya")

    # Verify
    assert len(services) == 1
    assert services[0] == sample_service_info

    # Test with non-existent DCC type
    services = registry.list_services("non_existent")
    assert len(services) == 0
