"""Tests for the ServiceRegistry class helper methods.

This module contains tests for the helper methods of the ServiceRegistry class.
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.discovery.base import ServiceInfo
from dcc_mcp_rpyc.discovery.file_strategy import FileDiscoveryStrategy
from dcc_mcp_rpyc.discovery.registry import ServiceRegistry
from dcc_mcp_rpyc.discovery.zeroconf_strategy import ZEROCONF_AVAILABLE
from dcc_mcp_rpyc.discovery.zeroconf_strategy import ZeroConfDiscoveryStrategy


@pytest.fixture
def clean_registry():
    """Fixture to ensure a clean registry for each test."""
    ServiceRegistry._reset_instance()
    yield
    ServiceRegistry._reset_instance()


@pytest.fixture
def sample_service_info():
    """Fixture to create a sample service info."""
    return ServiceInfo(name="test_service", host="localhost", port=8000, dcc_type="maya", metadata={"version": "2023"})


def test_ensure_strategy_file(clean_registry):
    """Test ensuring a file strategy exists."""
    # Setup
    registry = ServiceRegistry()

    # Execute
    strategy = registry.ensure_strategy("file")

    # Verify
    assert isinstance(strategy, FileDiscoveryStrategy)
    assert registry.get_strategy("file") is strategy


@pytest.mark.skipif(not ZEROCONF_AVAILABLE, reason="ZeroConf is not available")
def test_ensure_strategy_zeroconf(clean_registry):
    """Test ensuring a ZeroConf strategy exists."""
    # Setup
    registry = ServiceRegistry()

    # Execute
    strategy = registry.ensure_strategy("zeroconf")

    # Verify
    assert isinstance(strategy, ZeroConfDiscoveryStrategy)
    assert registry.get_strategy("zeroconf") is strategy


def test_ensure_strategy_with_kwargs(clean_registry):
    """Test ensuring a strategy exists with keyword arguments."""
    # Setup
    registry = ServiceRegistry()

    # Execute
    with patch("dcc_mcp_rpyc.discovery.factory.ServiceDiscoveryFactory.get_strategy") as mock_get_strategy:
        mock_strategy = MagicMock(spec=FileDiscoveryStrategy)
        mock_get_strategy.return_value = mock_strategy
        strategy = registry.ensure_strategy("file", registry_path="/tmp/test.json")

    # Verify
    assert strategy is mock_strategy


def test_ensure_strategy_invalid_type(clean_registry):
    """Test ensuring an invalid strategy type."""
    # Setup
    registry = ServiceRegistry()

    # Execute and verify
    with pytest.raises(ValueError):
        registry.ensure_strategy("invalid")


def test_register_service_with_strategy(clean_registry, sample_service_info):
    """Test registering a service with a strategy."""
    # Setup
    registry = ServiceRegistry()
    mock_strategy = MagicMock()
    mock_strategy.register_service.return_value = True
    registry.register_strategy("mock", mock_strategy)

    # Execute
    result = registry.register_service_with_strategy("mock", sample_service_info)

    # Verify
    assert result is True
    mock_strategy.register_service.assert_called_once_with(sample_service_info)


def test_register_service_with_strategy_ensure(clean_registry, sample_service_info):
    """Test registering a service with a strategy, ensuring the strategy exists."""
    # Setup
    registry = ServiceRegistry()

    # Mock register_service method
    with patch.object(ServiceRegistry, "register_service") as mock_register_service:
        mock_register_service.return_value = True

        # Mock ensure_strategy method
        with patch.object(ServiceRegistry, "ensure_strategy") as mock_ensure_strategy:
            mock_strategy = MagicMock()
            mock_ensure_strategy.return_value = mock_strategy

            # Execute
            result = registry.register_service_with_strategy("file", sample_service_info)

    # Verify
    assert result is True
    mock_ensure_strategy.assert_called_once()
    mock_register_service.assert_called_once()


def test_register_service_with_strategy_unregister(clean_registry, sample_service_info):
    """Test unregistering a service with a strategy."""
    # Setup
    registry = ServiceRegistry()
    mock_strategy = MagicMock()
    mock_strategy.unregister_service.return_value = True
    registry.register_strategy("mock", mock_strategy)

    # Execute
    result = registry.register_service_with_strategy("mock", sample_service_info, unregister=True)

    # Verify
    assert result is True
    mock_strategy.unregister_service.assert_called_once_with(sample_service_info)


def test_register_service_with_strategy_failure(clean_registry, sample_service_info):
    """Test registering a service with a strategy that fails."""
    # Setup
    registry = ServiceRegistry()
    mock_strategy = MagicMock()
    mock_strategy.register_service.return_value = False
    registry.register_strategy("mock", mock_strategy)

    # Execute
    result = registry.register_service_with_strategy("mock", sample_service_info)

    # Verify
    assert result is False
    mock_strategy.register_service.assert_called_once_with(sample_service_info)
