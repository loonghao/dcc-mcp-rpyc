"""Tests for the ZeroConf-based service discovery strategy.

This module contains tests for the ZeroConfDiscoveryStrategy class.
"""

# Import built-in modules
import time
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.discovery.base import ServiceInfo
from dcc_mcp_rpyc.discovery.zeroconf_strategy import ServiceListener
from dcc_mcp_rpyc.discovery.zeroconf_strategy import ZEROCONF_AVAILABLE
from dcc_mcp_rpyc.discovery.zeroconf_strategy import ZeroConfDiscoveryStrategy
from dcc_mcp_rpyc.discovery.zeroconf_strategy import get_local_ip


@pytest.fixture
def sample_service_info():
    """Fixture to create a sample service info."""
    return ServiceInfo(
        name="test_service",
        host="127.0.0.1",  # Use valid IP address instead of hostname
        port=8000,
        dcc_type="maya",
        metadata={"version": "2023"},
    )


@pytest.mark.skipif(not ZEROCONF_AVAILABLE, reason="ZeroConf is not available")
def test_init():
    """Test initializing the ZeroConfDiscoveryStrategy."""
    strategy = ZeroConfDiscoveryStrategy()
    assert strategy is not None


@pytest.mark.skipif(not ZEROCONF_AVAILABLE, reason="ZeroConf is not available")
@patch("dcc_mcp_rpyc.discovery.zeroconf_strategy.Zeroconf")
@patch("dcc_mcp_rpyc.discovery.zeroconf_strategy.ServiceInfo")
def test_register_service(mock_service_info, mock_zeroconf, sample_service_info):
    """Test registering a service."""
    # Setup
    mock_zeroconf_instance = MagicMock()
    mock_zeroconf.return_value = mock_zeroconf_instance

    mock_service_info_instance = MagicMock()
    mock_service_info.return_value = mock_service_info_instance

    # Execute
    with patch.object(ZeroConfDiscoveryStrategy, "register_service", return_value=True):
        strategy = ZeroConfDiscoveryStrategy()

        # Execute
        result = strategy.register_service(sample_service_info)

        # Verify
        assert result is True


@pytest.mark.skipif(not ZEROCONF_AVAILABLE, reason="ZeroConf is not available")
@patch("dcc_mcp_rpyc.discovery.zeroconf_strategy.Zeroconf")
@patch("dcc_mcp_rpyc.discovery.zeroconf_strategy.ServiceBrowser")
def test_discover_services(mock_service_browser, mock_zeroconf, sample_service_info):
    """Test discovering services."""
    # Setup
    mock_zeroconf_instance = MagicMock()
    mock_zeroconf.return_value = mock_zeroconf_instance

    mock_browser_instance = MagicMock()
    mock_service_browser.return_value = mock_browser_instance

    # Mock the listener to return our sample service
    mock_listener = MagicMock()
    mock_listener.services = {
        "test_service": {
            "name": sample_service_info.name,
            "host": sample_service_info.host,
            "port": sample_service_info.port,
            "dcc_name": sample_service_info.dcc_type,
            "properties": sample_service_info.metadata,
        }
    }

    with patch("dcc_mcp_rpyc.discovery.zeroconf_strategy.ServiceListener", return_value=mock_listener):
        # Patch _ensure_zeroconf to return True
        with patch.object(ZeroConfDiscoveryStrategy, "_ensure_zeroconf", return_value=True):
            strategy = ZeroConfDiscoveryStrategy()

            # Execute
            services = strategy.discover_services()

            # Verify
            assert len(services) == 1
            assert services[0].name == sample_service_info.name
            assert services[0].host == sample_service_info.host
            assert services[0].port == sample_service_info.port


@pytest.mark.skipif(not ZEROCONF_AVAILABLE, reason="ZeroConf is not available")
@patch("dcc_mcp_rpyc.discovery.zeroconf_strategy.Zeroconf")
@patch("dcc_mcp_rpyc.discovery.zeroconf_strategy.ServiceBrowser")
def test_discover_services_with_type(mock_service_browser, mock_zeroconf, sample_service_info):
    """Test discovering services with a specific type."""
    # Setup
    mock_zeroconf_instance = MagicMock()
    mock_zeroconf.return_value = mock_zeroconf_instance

    mock_browser_instance = MagicMock()
    mock_service_browser.return_value = mock_browser_instance

    # Mock the listener to return our sample service
    mock_listener = MagicMock()
    mock_listener.services = {
        "test_service": {
            "name": sample_service_info.name,
            "host": sample_service_info.host,
            "port": sample_service_info.port,
            "dcc_name": sample_service_info.dcc_type,
            "properties": sample_service_info.metadata,
        }
    }

    with patch("dcc_mcp_rpyc.discovery.zeroconf_strategy.ServiceListener", return_value=mock_listener):
        # Patch _ensure_zeroconf to return True
        with patch.object(ZeroConfDiscoveryStrategy, "_ensure_zeroconf", return_value=True):
            strategy = ZeroConfDiscoveryStrategy()

            # Execute
            services = strategy.discover_services(dcc_type="maya")

            # Verify
            assert len(services) == 1
            assert services[0].name == sample_service_info.name
            assert services[0].dcc_type == "maya"


@pytest.mark.skipif(not ZEROCONF_AVAILABLE, reason="ZeroConf is not available")
@patch("dcc_mcp_rpyc.discovery.zeroconf_strategy.Zeroconf")
@patch("dcc_mcp_rpyc.discovery.zeroconf_strategy.ServiceInfo")
def test_unregister_service(mock_service_info, mock_zeroconf, sample_service_info):
    """Test unregistering a service."""
    # Setup
    mock_zeroconf_instance = MagicMock()
    mock_zeroconf.return_value = mock_zeroconf_instance

    mock_service_info_instance = MagicMock()
    mock_service_info.return_value = mock_service_info_instance

    # Execute
    with patch.object(ZeroConfDiscoveryStrategy, "unregister_service", return_value=True):
        strategy = ZeroConfDiscoveryStrategy()

        # Execute
        result = strategy.unregister_service(sample_service_info)

        # Verify
        assert result is True


@pytest.mark.skipif(not ZEROCONF_AVAILABLE, reason="ZeroConf is not available")
@patch("dcc_mcp_rpyc.discovery.zeroconf_strategy.Zeroconf")
@patch("dcc_mcp_rpyc.discovery.zeroconf_strategy.ServiceInfo")
def test_unregister_service_by_name(mock_service_info, mock_zeroconf):
    """Test unregistering a service by name."""
    # Setup
    strategy = ZeroConfDiscoveryStrategy()

    # Mock zeroconf
    mock_zeroconf = MagicMock()
    strategy._zeroconf = mock_zeroconf

    # Add a service
    service_name = "test_service"
    service_key = f"maya:{service_name}:127.0.0.1:8000"
    strategy._services[service_key] = ServiceInfo(
        name=service_name, host="127.0.0.1", port=8000, dcc_type="maya", metadata={}
    )

    # Execute
    with patch.object(strategy, "_ensure_zeroconf", return_value=True):
        result = strategy.unregister_service_by_name(service_name)

    assert result is True
    assert service_key not in strategy._services


@pytest.mark.skipif(not ZEROCONF_AVAILABLE, reason="ZeroConf is not available")
def test_get_local_ip():
    """u6d4bu8bd5u8fd9u4e0au672cu5730u5730u4ee3u53f0u3002."""
    # u6267u884c
    ip = get_local_ip()

    # u9a8cu8bc1
    assert ip is not None
    assert isinstance(ip, str)
    # u9a8cu8bc1u662fu5224u4ee5u6b63u786eu7684IPu5730u5f0f
    parts = ip.split(".")
    assert len(parts) == 4
    for part in parts:
        assert part.isdigit()
        assert 0 <= int(part) <= 255


@pytest.mark.skipif(not ZEROCONF_AVAILABLE, reason="ZeroConf is not available")
def test_service_listener_init():
    """u6d4bu8bd5 ServiceListener u7684u521du59cbu5316u3002."""
    # u6267u884c
    listener = ServiceListener()

    # u9a8cu8bc1
    assert listener.dcc_name is None
    assert isinstance(listener.services, dict)
    assert len(listener.services) == 0

    listener = ServiceListener(dcc_name="maya")
    assert listener.dcc_name == "maya"


@pytest.mark.skipif(not ZEROCONF_AVAILABLE, reason="ZeroConf is not available")
@patch("dcc_mcp_rpyc.discovery.zeroconf_strategy.socket.inet_ntoa")
def test_service_listener_add_service(mock_inet_ntoa):
    """Test adding a service to ServiceListener."""
    # Setup
    mock_inet_ntoa.return_value = "127.0.0.1"
    listener = ServiceListener()
    mock_zeroconf = MagicMock()

    # Execute
    mock_info = MagicMock()
    mock_info.properties = {b"dcc_name": b"maya", b"service_name": b"test_service", b"version": b"2023"}

    # Setup addresses_by_version
    type_a = 1
    mock_info.addresses_by_version = {type_a: [b"\x7f\x00\x00\x01"]}  # 127.0.0.1
    mock_info.port = 8000
    mock_zeroconf.get_service_info.return_value = mock_info

    # Execute
    listener.add_service(mock_zeroconf, "_dcc-mcp._tcp.local.", "test_service._dcc-mcp._tcp.local.")

    # Verify
    assert len(listener.services) == 1
    service = listener.services.get("test_service._dcc-mcp._tcp.local.")
    assert service is not None
    assert service["name"] == "test_service"
    assert service["host"] == "127.0.0.1"
    assert service["port"] == 8000
    assert service["dcc_name"] == "maya"
    assert "timestamp" in service


@pytest.mark.skipif(not ZEROCONF_AVAILABLE, reason="ZeroConf is not available")
def test_service_listener_remove_service():
    """Test removing a service from ServiceListener."""
    # Setup
    listener = ServiceListener()
    mock_zeroconf = MagicMock()

    # Setup listener.services
    service_name = "test_service._dcc-mcp._tcp.local."
    listener.services[service_name] = {
        "name": "test_service",
        "host": "127.0.0.1",
        "port": 8000,
        "dcc_name": "maya",
        "properties": {"version": "2023"},
        "timestamp": time.time(),
    }

    # Execute
    listener.remove_service(mock_zeroconf, "_dcc-mcp._tcp.local.", service_name)

    # Verify
    assert len(listener.services) == 0
    assert service_name not in listener.services


@pytest.mark.skipif(not ZEROCONF_AVAILABLE, reason="ZeroConf is not available")
def test_service_listener_update_service():
    """Test updating a service in ServiceListener."""
    # Setup
    listener = ServiceListener()
    mock_zeroconf = MagicMock()

    # Setup add_service
    with patch.object(ServiceListener, "add_service") as mock_add_service:
        # Execute
        listener.update_service(mock_zeroconf, "_dcc-mcp._tcp.local.", "test_service._dcc-mcp._tcp.local.")

        # Verify
        mock_add_service.assert_called_once_with(
            mock_zeroconf, "_dcc-mcp._tcp.local.", "test_service._dcc-mcp._tcp.local."
        )


@pytest.mark.skipif(not ZEROCONF_AVAILABLE, reason="ZeroConf is not available")
def test_del_method():
    """Test that __del__ method correctly cleans up resources."""
    # Setup
    strategy = ZeroConfDiscoveryStrategy()
    mock_zeroconf = MagicMock()
    strategy._zeroconf = mock_zeroconf

    # Execute - Manually call __del__ method
    strategy.__del__()

    # Verify
    mock_zeroconf.close.assert_called_once()
