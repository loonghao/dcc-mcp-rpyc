"""Tests for the service discovery factory.

This module contains tests for the ServiceDiscoveryFactory class.
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.discovery.factory import ServiceDiscoveryFactory
from dcc_mcp_rpyc.discovery.file_strategy import FileDiscoveryStrategy


@pytest.fixture
def clean_factory():
    """Fixture to ensure a clean factory for each test."""
    ServiceDiscoveryFactory._reset_instance()
    yield
    ServiceDiscoveryFactory._reset_instance()


def test_factory_singleton(clean_factory):
    """Test that ServiceDiscoveryFactory follows the singleton pattern."""
    factory1 = ServiceDiscoveryFactory()
    factory2 = ServiceDiscoveryFactory()
    assert factory1 is factory2


def test_get_file_strategy(clean_factory):
    """Test getting a file discovery strategy."""
    factory = ServiceDiscoveryFactory()
    strategy = factory.get_strategy("file")
    assert isinstance(strategy, FileDiscoveryStrategy)

    # Test caching
    strategy2 = factory.get_strategy("file")
    assert strategy is strategy2


@patch("dcc_mcp_rpyc.discovery.factory.ZEROCONF_AVAILABLE", True)
@patch("dcc_mcp_rpyc.discovery.factory.ZeroConfDiscoveryStrategy")
def test_get_zeroconf_strategy(mock_zeroconf_strategy, clean_factory):
    """Test getting a ZeroConf discovery strategy."""
    # Setup
    mock_instance = MagicMock()
    mock_zeroconf_strategy.return_value = mock_instance

    # Execute
    factory = ServiceDiscoveryFactory()
    strategy = factory.get_strategy("zeroconf")

    # Verify
    assert strategy is mock_instance
    mock_zeroconf_strategy.assert_called_once()

    # Test caching
    strategy2 = factory.get_strategy("zeroconf")
    assert strategy is strategy2
    assert mock_zeroconf_strategy.call_count == 1  # Should not be called again


@patch("dcc_mcp_rpyc.discovery.factory.ZEROCONF_AVAILABLE", False)
def test_get_unavailable_zeroconf_strategy(clean_factory):
    """Test getting an unavailable ZeroConf discovery strategy."""
    factory = ServiceDiscoveryFactory()
    strategy = factory.get_strategy("zeroconf")
    assert strategy is None


def test_get_invalid_strategy(clean_factory):
    """Test getting an invalid strategy type."""
    factory = ServiceDiscoveryFactory()
    with pytest.raises(ValueError):
        factory.get_strategy("invalid")


def test_list_available_strategies(clean_factory):
    """Test listing available strategies."""
    factory = ServiceDiscoveryFactory()
    strategies = factory.list_available_strategies()
    assert "file" in strategies
    assert strategies["file"] is True  # File strategy should always be available
    assert "zeroconf" in strategies  # ZeroConf availability depends on the environment
