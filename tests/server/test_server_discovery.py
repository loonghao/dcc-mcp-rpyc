"""Tests for dcc_mcp_ipc.server.discovery module."""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.server.discovery import register_dcc_service
from dcc_mcp_ipc.server.discovery import unregister_dcc_service


class TestRegisterDCCService:
    """Tests for the register_dcc_service function."""

    @patch("dcc_mcp_ipc.server.discovery.ServiceRegistry")
    def test_register_returns_registry_path(self, MockRegistry):
        mock_registry = MagicMock()
        mock_strategy = MagicMock()
        mock_strategy.registry_path = "/tmp/dcc_registry.json"
        mock_registry.get_strategy.return_value = mock_strategy
        MockRegistry.return_value = mock_registry

        result = register_dcc_service("maya", "localhost", 18812)

        assert result == "/tmp/dcc_registry.json"
        mock_registry.register_service_with_strategy.assert_called_once()

    @patch("dcc_mcp_ipc.server.discovery.ServiceRegistry")
    def test_register_creates_correct_service_info(self, MockRegistry):
        # Import local modules
        from dcc_mcp_ipc.server.discovery import ServiceInfo

        mock_registry = MagicMock()
        mock_strategy = MagicMock()
        mock_strategy.registry_path = "/path/to/file"
        mock_registry.get_strategy.return_value = mock_strategy
        MockRegistry.return_value = mock_registry

        register_dcc_service("blender", "192.168.1.1", 9999)

        call_args = mock_registry.register_service_with_strategy.call_args
        # First positional arg should be strategy name "file"
        assert call_args[0][0] == "file"
        # Second positional arg should be a ServiceInfo object
        service_info = call_args[0][1]
        assert service_info.name == "blender"
        assert service_info.host == "192.168.1.1"
        assert service_info.port == 9999


class TestUnregisterDCCService:
    """Tests for the unregister_dcc_service function."""

    @patch("dcc_mcp_ipc.server.discovery.ServiceRegistry")
    def test_unregister_no_services_returns_false(self, MockRegistry):
        mock_registry = MagicMock()
        mock_registry.discover_services.return_value = []
        MockRegistry.return_value = mock_registry

        result = unregister_dcc_service("/some/path")
        assert result is False

    @patch("dcc_mcp_ipc.server.discovery.ServiceRegistry")
    def test_unregister_strategy_error_returns_false(self, MockRegistry):
        mock_registry = MagicMock()
        mock_registry.ensure_strategy.side_effect = ValueError("strategy error")
        MockRegistry.return_value = mock_registry

        result = unregister_dcc_service("/some/path")
        assert result is False

    @patch("dcc_mcp_ipc.server.discovery.ServiceRegistry")
    def test_unregister_success(self, MockRegistry):
        mock_registry = MagicMock()
        mock_service = MagicMock()
        mock_registry.discover_services.return_value = [mock_service]
        mock_registry.unregister_service.return_value = True
        MockRegistry.return_value = mock_registry

        result = unregister_dcc_service("/some/path")
        assert result is True
        mock_registry.unregister_service.assert_called_once_with("file", mock_service)

    @patch("dcc_mcp_ipc.server.discovery.ServiceRegistry")
    def test_unregister_partial_failure(self, MockRegistry):
        mock_registry = MagicMock()
        service1 = MagicMock()
        service2 = MagicMock()
        mock_registry.discover_services.return_value = [service1, service2]
        # First succeeds, second fails
        mock_registry.unregister_service.side_effect = [True, False]
        MockRegistry.return_value = mock_registry

        result = unregister_dcc_service("/some/path")
        assert result is False

    @patch("dcc_mcp_ipc.server.discovery.ServiceRegistry")
    def test_unregister_multiple_services(self, MockRegistry):
        mock_registry = MagicMock()
        services = [MagicMock(), MagicMock(), MagicMock()]
        mock_registry.discover_services.return_value = services
        mock_registry.unregister_service.return_value = True
        MockRegistry.return_value = mock_registry

        result = unregister_dcc_service("/registry")
        assert result is True
        assert mock_registry.unregister_service.call_count == 3
