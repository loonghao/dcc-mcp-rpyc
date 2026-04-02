"""Tests for the transport base module."""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.transport.base import BaseTransport
from dcc_mcp_ipc.transport.base import ConnectionError
from dcc_mcp_ipc.transport.base import ProtocolError
from dcc_mcp_ipc.transport.base import TimeoutError
from dcc_mcp_ipc.transport.base import TransportConfig
from dcc_mcp_ipc.transport.base import TransportError
from dcc_mcp_ipc.transport.base import TransportState


class ConcreteTransport(BaseTransport):
    """Concrete implementation for testing the abstract base class."""

    def __init__(self, config=None):
        super().__init__(config)
        self.connect_called = False
        self.disconnect_called = False
        self.health_check_result = True
        self.execute_result = {"success": True}

    def connect(self):
        self.connect_called = True
        self._state = TransportState.CONNECTED

    def disconnect(self):
        self.disconnect_called = True
        self._state = TransportState.DISCONNECTED

    def health_check(self):
        return self.health_check_result

    def execute(self, action, params=None, timeout=None):
        return self.execute_result


class TestTransportConfig:
    """Tests for TransportConfig."""

    def test_default_config(self):
        config = TransportConfig()
        assert config.host == "localhost"
        assert config.port == 0
        assert config.timeout == 30.0
        assert config.retry_count == 3
        assert config.retry_delay == 1.0
        assert config.metadata == {}

    def test_custom_config(self):
        config = TransportConfig(
            host="192.168.1.100",
            port=18812,
            timeout=10.0,
            retry_count=5,
            metadata={"protocol": "rpyc"},
        )
        assert config.host == "192.168.1.100"
        assert config.port == 18812
        assert config.timeout == 10.0
        assert config.retry_count == 5
        assert config.metadata == {"protocol": "rpyc"}


class TestTransportState:
    """Tests for TransportState enum."""

    def test_states_exist(self):
        assert TransportState.DISCONNECTED == "disconnected"
        assert TransportState.CONNECTING == "connecting"
        assert TransportState.CONNECTED == "connected"
        assert TransportState.ERROR == "error"


class TestTransportError:
    """Tests for transport error hierarchy."""

    def test_transport_error(self):
        err = TransportError("something failed")
        assert str(err) == "something failed"
        assert err.cause is None

    def test_transport_error_with_cause(self):
        cause = RuntimeError("root cause")
        err = TransportError("something failed", cause=cause)
        assert err.cause is cause

    def test_connection_error(self):
        err = ConnectionError("connection refused")
        assert isinstance(err, TransportError)

    def test_timeout_error(self):
        err = TimeoutError("timed out")
        assert isinstance(err, TransportError)

    def test_protocol_error(self):
        err = ProtocolError("invalid response")
        assert isinstance(err, TransportError)


class TestBaseTransport:
    """Tests for BaseTransport abstract class (via ConcreteTransport)."""

    def test_init_default_config(self):
        transport = ConcreteTransport()
        assert transport.config.host == "localhost"
        assert transport.state == TransportState.DISCONNECTED
        assert not transport.is_connected

    def test_init_custom_config(self):
        config = TransportConfig(host="10.0.0.1", port=9999)
        transport = ConcreteTransport(config)
        assert transport.config.host == "10.0.0.1"
        assert transport.config.port == 9999

    def test_connect(self):
        transport = ConcreteTransport()
        transport.connect()
        assert transport.connect_called
        assert transport.state == TransportState.CONNECTED
        assert transport.is_connected

    def test_disconnect(self):
        transport = ConcreteTransport()
        transport.connect()
        transport.disconnect()
        assert transport.disconnect_called
        assert transport.state == TransportState.DISCONNECTED
        assert not transport.is_connected

    def test_reconnect(self):
        transport = ConcreteTransport()
        transport.connect()
        transport.reconnect()
        assert transport.disconnect_called
        assert transport.connect_called

    def test_execute(self):
        transport = ConcreteTransport()
        result = transport.execute("test_action", {"key": "value"})
        assert result == {"success": True}

    def test_execute_python_calls_execute(self):
        transport = ConcreteTransport()
        transport.execute_result = {"success": True, "result": "42"}
        result = transport.execute_python("print(42)")
        assert result == {"success": True, "result": "42"}

    def test_call_function_calls_execute(self):
        transport = ConcreteTransport()
        transport.execute_result = {"success": True, "result": [1, 2, 3]}
        result = transport.call_function("os.path", "join", "/tmp", "test")
        assert result == {"success": True, "result": [1, 2, 3]}

    def test_context_manager(self):
        transport = ConcreteTransport()
        with transport as t:
            assert t is transport
            assert t.connect_called
            assert t.state == TransportState.CONNECTED
        assert transport.disconnect_called

    def test_repr(self):
        transport = ConcreteTransport()
        r = repr(transport)
        assert "ConcreteTransport" in r
        assert "localhost" in r
        assert "disconnected" in r

    def test_health_check(self):
        transport = ConcreteTransport()
        assert transport.health_check() is True
        transport.health_check_result = False
        assert transport.health_check() is False
