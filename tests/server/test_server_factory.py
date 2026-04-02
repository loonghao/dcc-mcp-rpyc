"""Tests for dcc_mcp_ipc.server.factory module."""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest
import rpyc

# Import local modules
from dcc_mcp_ipc.server.factory import cleanup_server
from dcc_mcp_ipc.server.factory import create_dcc_server
from dcc_mcp_ipc.server.factory import create_service_factory
from dcc_mcp_ipc.server.factory import create_shared_service_instance


class TestCreateDCCServer:
    """Tests for the create_dcc_server factory function."""

    @patch("dcc_mcp_ipc.server.factory.create_raw_threaded_server")
    @patch("dcc_mcp_ipc.server.factory.DCCServer")
    def test_create_basic(self, MockDCCServer, mock_raw):
        from dcc_mcp_ipc.server.base import BaseRPyCService

        mock_threaded = MagicMock()
        mock_raw.return_value = mock_threaded
        mock_dcc = MagicMock()
        MockDCCServer.return_value = mock_dcc

        result = create_dcc_server("maya", BaseRPyCService)

        assert result is mock_dcc
        mock_raw.assert_called_once()
        MockDCCServer.assert_called_once()

    @patch("dcc_mcp_ipc.server.factory.create_raw_threaded_server")
    @patch("dcc_mcp_ipc.server.factory.DCCServer")
    def test_create_with_custom_port(self, MockDCCServer, mock_raw):
        from dcc_mcp_ipc.server.base import BaseRPyCService

        mock_raw.return_value = MagicMock()
        mock_dcc = MagicMock()
        MockDCCServer.return_value = mock_dcc

        result = create_dcc_server("blender", BaseRPyCService, host="0.0.0.0", port=18813)

        call_kwargs = MockDCCServer.call_args[1]
        assert call_kwargs["host"] == "0.0.0.0"
        assert call_kwargs["port"] == 18813

    @patch("dcc_mcp_ipc.server.factory.create_raw_threaded_server")
    @patch("dcc_mcp_ipc.server.factory.DCCServer")
    def test_create_with_registry_path(self, MockDCCServer, mock_raw):
        from dcc_mcp_ipc.server.base import BaseRPyCService

        mock_raw.return_value = MagicMock()
        mock_dcc = MagicMock()
        MockDCCServer.return_value = mock_dcc

        create_dcc_server("maya", BaseRPyCService, registry_path="/tmp/reg.json")

        call_kwargs = MockDCCServer.call_args[1]
        assert call_kwargs["registry_path"] == "/tmp/reg.json"


class TestCleanupServer:
    """Tests for the cleanup_server function."""

    def test_cleanup_none_server(self):
        result = cleanup_server(None, None)
        assert result is True

    def test_cleanup_with_server(self):
        mock_server = MagicMock()
        result = cleanup_server(mock_server, None)
        assert result is True
        mock_server.close.assert_called_once()

    def test_cleanup_server_close_fails(self):
        mock_server = MagicMock()
        mock_server.close.side_effect = RuntimeError("close error")
        result = cleanup_server(mock_server, None)
        assert result is False

    def test_cleanup_with_custom_closer(self):
        mock_server = MagicMock()
        mock_closer = MagicMock()
        result = cleanup_server(mock_server, None, server_closer=mock_closer)
        assert result is True
        mock_closer.assert_called_once_with(mock_server)
        mock_server.close.assert_not_called()

    @patch("dcc_mcp_ipc.server.factory.unregister_dcc_service")
    def test_cleanup_with_registry_file(self, mock_unreg):
        mock_unreg.return_value = True
        result = cleanup_server(None, "/tmp/registry.json", timeout=1.0)
        assert result is True

    @patch("dcc_mcp_ipc.server.factory.unregister_dcc_service")
    def test_cleanup_registry_unregister_timeout(self, mock_unreg):
        import time

        def slow_unreg(*args):
            time.sleep(5)

        mock_unreg.side_effect = slow_unreg
        result = cleanup_server(None, "/tmp/registry.json", timeout=0.1)
        assert result is False  # timeout

    @patch("dcc_mcp_ipc.server.factory.unregister_dcc_service")
    def test_cleanup_both_server_and_registry(self, mock_unreg):
        mock_unreg.return_value = True
        mock_server = MagicMock()
        result = cleanup_server(mock_server, "/tmp/reg.json", timeout=2.0)
        assert result is True
        mock_server.close.assert_called_once()


class TestCreateServiceFactory:
    """Tests for the create_service_factory function."""

    def test_factory_creates_instance(self):
        class MyService(rpyc.Service):
            def __init__(self, value=0):
                self.value = value

        factory = create_service_factory(MyService, value=42)
        instance = factory()
        assert isinstance(instance, MyService)
        assert instance.value == 42

    def test_factory_callable(self):
        factory = create_service_factory(rpyc.Service)
        assert callable(factory)

    def test_factory_name_set(self):
        factory = create_service_factory(rpyc.Service)
        assert "Service" in factory.__name__

    def test_factory_with_conn_arg(self):
        class MyService(rpyc.Service):
            pass

        factory = create_service_factory(MyService)
        instance = factory(conn=None)
        assert isinstance(instance, MyService)

    def test_factory_error_propagates(self):
        class BadService(rpyc.Service):
            def __init__(self):
                raise ValueError("cannot create")

        factory = create_service_factory(BadService)
        with pytest.raises(ValueError, match="cannot create"):
            factory()

    def test_factory_creates_new_instance_each_call(self):
        class MyService(rpyc.Service):
            pass

        factory = create_service_factory(MyService)
        a = factory()
        b = factory()
        assert a is not b


class TestCreateSharedServiceInstance:
    """Tests for the create_shared_service_instance function."""

    def test_returns_callable(self):
        factory = create_shared_service_instance(rpyc.Service)
        assert callable(factory)

    def test_shared_instance_same_object(self):
        class MyService(rpyc.Service):
            pass

        factory = create_shared_service_instance(MyService)
        a = factory()
        b = factory()
        assert a is b  # Same instance every time

    def test_factory_name_set(self):
        factory = create_shared_service_instance(rpyc.Service)
        assert "Service" in factory.__name__

    def test_factory_accepts_conn_arg(self):
        class MyService(rpyc.Service):
            pass

        factory = create_shared_service_instance(MyService)
        instance = factory(conn=None)
        assert isinstance(instance, MyService)

    def test_creation_error_propagates(self):
        class BadService(rpyc.Service):
            def __init__(self):
                raise TypeError("bad init")

        with pytest.raises(TypeError, match="bad init"):
            create_shared_service_instance(BadService)
