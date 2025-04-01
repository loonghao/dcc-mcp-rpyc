"""Service discovery strategy integration tests.

This module contains tests for the integration of multiple service discovery strategies.
"""

# Import built-in modules
import os
import tempfile
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.discovery.base import ServiceInfo
from dcc_mcp_rpyc.discovery.file_strategy import FileDiscoveryStrategy
from dcc_mcp_rpyc.discovery.registry import ServiceRegistry


@pytest.fixture
def clean_registry():
    """Ensure the registry is reset before and after each test."""
    ServiceRegistry._reset_instance()
    yield
    ServiceRegistry._reset_instance()


@pytest.fixture
def temp_registry_file():
    """Create a temporary registry file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        f.write(b"{}")
        registry_path = f.name

    yield registry_path

    if os.path.exists(registry_path):
        os.unlink(registry_path)


@pytest.fixture
def sample_service_info():
    """Create a sample service information."""
    return ServiceInfo(
        name="test_service",
        host="127.0.0.1",  # Use a valid IP address instead of hostname
        port=8000,
        dcc_type="maya",
        metadata={"version": "2023"},
    )


def test_multiple_strategies_registration(clean_registry, temp_registry_file, sample_service_info):
    """Test registration of services using multiple strategies."""
    # Setup
    registry = ServiceRegistry()

    # Register file strategy
    with patch("dcc_mcp_rpyc.discovery.factory.ServiceDiscoveryFactory.get_strategy") as mock_get_strategy:
        mock_file_strategy = MagicMock(spec=FileDiscoveryStrategy)
        mock_file_strategy.register_service.return_value = True
        mock_get_strategy.return_value = mock_file_strategy
        registry.ensure_strategy("file", registry_path=temp_registry_file)

    # Mock ZeroConf strategy
    mock_zeroconf_strategy = MagicMock()
    mock_zeroconf_strategy.register_service.return_value = True
    registry.register_strategy("zeroconf", mock_zeroconf_strategy)

    # Use both strategies to register the service
    file_result = registry.register_service("file", sample_service_info)
    zeroconf_result = registry.register_service("zeroconf", sample_service_info)

    # Verify
    assert file_result is True
    assert zeroconf_result is True
    mock_zeroconf_strategy.register_service.assert_called_once_with(sample_service_info)
    mock_file_strategy.register_service.assert_called_once_with(sample_service_info)


def test_multiple_strategies_discovery(clean_registry, temp_registry_file, sample_service_info):
    """Test discovery of services using multiple strategies."""
    # Setup
    registry = ServiceRegistry()

    # Register file strategy
    with patch("dcc_mcp_rpyc.discovery.factory.ServiceDiscoveryFactory.get_strategy") as mock_get_strategy:
        mock_file_strategy = MagicMock(spec=FileDiscoveryStrategy)
        mock_file_strategy.discover_services.return_value = [sample_service_info]
        mock_get_strategy.return_value = mock_file_strategy
        registry.ensure_strategy("file", registry_path=temp_registry_file)

    # Mock ZeroConf strategy
    mock_zeroconf_strategy = MagicMock()
    mock_zeroconf_strategy.discover_services.return_value = [sample_service_info]
    registry.register_strategy("zeroconf", mock_zeroconf_strategy)

    # Use both strategies to discover services
    file_services = registry.discover_services("file")
    zeroconf_services = registry.discover_services("zeroconf")

    # Validate
    assert file_services == [sample_service_info]
    assert zeroconf_services == [sample_service_info]
    mock_zeroconf_strategy.discover_services.assert_called_once()
    mock_file_strategy.discover_services.assert_called_once()


def test_discover_all_services(clean_registry, temp_registry_file, sample_service_info):
    """Test discovery of all services."""
    # Setup
    with patch.object(ServiceRegistry, "discover_services") as mock_discover_services:
        mock_discover_services.return_value = [sample_service_info]

        registry = ServiceRegistry()

        # Execute
        with patch.object(registry, "list_strategies", return_value=["file", "zeroconf"]):
            all_services = []
            for strategy_name in registry.list_strategies():
                services = registry.discover_services(strategy_name)
                all_services.extend(services)

        # Validate
        assert len(all_services) == 2  # 2 services
        assert mock_discover_services.call_count == 2


def test_get_service_from_multiple_strategies(clean_registry, temp_registry_file, sample_service_info):
    """Test getting a service from multiple strategies."""
    # Setup
    with patch.object(ServiceRegistry, "discover_services") as mock_discover_services:
        # Setup return value
        mock_discover_services.return_value = [sample_service_info]

        # Initialize registry
        registry = ServiceRegistry()

        # Execute
        service = registry.discover_services("file", dcc_type="maya")[0]

        # Validate
        assert service is not None
        assert service.name == sample_service_info.name
        assert service.dcc_type == sample_service_info.dcc_type
        mock_discover_services.assert_called_once_with("file", dcc_type="maya")


def test_register_service_with_strategy_helper(clean_registry, temp_registry_file, sample_service_info):
    """Test registering a service with a strategy helper."""
    # Setup
    registry = ServiceRegistry()

    # Execute
    with patch("dcc_mcp_rpyc.discovery.factory.ServiceDiscoveryFactory.get_strategy") as mock_get_strategy:
        mock_file_strategy = MagicMock(spec=FileDiscoveryStrategy)
        mock_file_strategy.register_service.return_value = True
        mock_get_strategy.return_value = mock_file_strategy
        result = registry.register_service_with_strategy("file", sample_service_info, registry_path=temp_registry_file)

    # Validate
    assert result is True
    mock_file_strategy.register_service.assert_called_once_with(sample_service_info)


def test_register_service_with_strategy_helper_unregister(clean_registry, temp_registry_file, sample_service_info):
    """Test unregistering a service using a strategy."""
    # Setup
    registry = ServiceRegistry()

    # Register file strategy
    with patch("dcc_mcp_rpyc.discovery.factory.ServiceDiscoveryFactory.get_strategy") as mock_get_strategy:
        mock_file_strategy = MagicMock(spec=FileDiscoveryStrategy)
        mock_file_strategy.register_service.return_value = True
        mock_file_strategy.unregister_service.return_value = True
        mock_file_strategy.discover_services.return_value = [sample_service_info]
        mock_get_strategy.return_value = mock_file_strategy

        # Register service
        registry.register_service_with_strategy("file", sample_service_info, registry_path=temp_registry_file)

        # Unregister service
        result = registry.register_service_with_strategy("file", sample_service_info, unregister=True)

    # Validate
    assert result is True
    mock_file_strategy.unregister_service.assert_called_once_with(sample_service_info)
