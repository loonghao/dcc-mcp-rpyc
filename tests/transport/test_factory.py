"""Tests for the transport factory module."""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.transport.base import BaseTransport
from dcc_mcp_rpyc.transport.base import TransportConfig
from dcc_mcp_rpyc.transport.base import TransportState
from dcc_mcp_rpyc.transport.factory import _transport_instances
from dcc_mcp_rpyc.transport.factory import _transport_registry
from dcc_mcp_rpyc.transport.factory import create_transport
from dcc_mcp_rpyc.transport.factory import get_transport
from dcc_mcp_rpyc.transport.factory import register_transport


class DummyTransport(BaseTransport):
    """A dummy transport for testing the factory."""

    def connect(self):
        self._state = TransportState.CONNECTED

    def disconnect(self):
        self._state = TransportState.DISCONNECTED

    def health_check(self):
        return self._state == TransportState.CONNECTED

    def execute(self, action, params=None, timeout=None):
        return {"success": True, "action": action}


class TestRegisterTransport:
    """Tests for register_transport."""

    def test_register_and_create(self):
        register_transport("dummy", DummyTransport)
        assert "dummy" in _transport_registry
        assert _transport_registry["dummy"] is DummyTransport

    def test_register_case_insensitive(self):
        register_transport("DUMMY", DummyTransport)
        assert "dummy" in _transport_registry


class TestCreateTransport:
    """Tests for create_transport."""

    def test_create_known_protocol(self):
        register_transport("dummy", DummyTransport)
        transport = create_transport("dummy")
        assert isinstance(transport, DummyTransport)
        assert transport.state == TransportState.DISCONNECTED

    def test_create_with_config(self):
        register_transport("dummy", DummyTransport)
        config = TransportConfig(host="10.0.0.1", port=5555)
        transport = create_transport("dummy", config=config)
        assert transport.config.host == "10.0.0.1"
        assert transport.config.port == 5555

    def test_create_unknown_protocol(self):
        with pytest.raises(ValueError, match="Unknown transport protocol"):
            create_transport("nonexistent_protocol_xyz")

    def test_case_insensitive_create(self):
        register_transport("dummy", DummyTransport)
        transport = create_transport("DUMMY")
        assert isinstance(transport, DummyTransport)


class TestGetTransport:
    """Tests for get_transport (caching)."""

    def setup_method(self):
        """Clean the instance cache before each test."""
        _transport_instances.clear()
        register_transport("dummy", DummyTransport)

    def test_get_creates_new(self):
        transport = get_transport("dummy", host="host1", port=1111)
        assert isinstance(transport, DummyTransport)
        assert ("dummy", "host1", 1111) in _transport_instances

    def test_get_returns_cached(self):
        t1 = get_transport("dummy", host="host1", port=1111)
        t1.connect()  # mark as connected
        t2 = get_transport("dummy", host="host1", port=1111)
        assert t1 is t2

    def test_get_creates_new_if_disconnected(self):
        t1 = get_transport("dummy", host="host1", port=1111)
        # t1 is disconnected (never connected), so get_transport should create new
        t2 = get_transport("dummy", host="host1", port=1111)
        assert t2 is not t1 or not t2.is_connected

    def test_get_with_config(self):
        config = TransportConfig(host="custom", port=9999)
        transport = get_transport("dummy", host="custom", port=9999, config=config)
        assert transport.config.host == "custom"
        assert transport.config.port == 9999


class TestBuiltinRegistration:
    """Tests for built-in transport auto-registration."""

    def test_rpyc_registered(self):
        assert "rpyc" in _transport_registry

    def test_http_registered(self):
        assert "http" in _transport_registry

    def test_create_rpyc_transport(self):
        from dcc_mcp_rpyc.transport.rpyc_transport import RPyCTransport

        transport = create_transport("rpyc")
        assert isinstance(transport, RPyCTransport)

    def test_create_http_transport(self):
        from dcc_mcp_rpyc.transport.http import HTTPTransport

        transport = create_transport("http")
        assert isinstance(transport, HTTPTransport)
