"""Tests for the asynchronous client classes.

This module contains tests for the asynchronous client classes in client/async_base.py
and client/async_dcc.py.
"""

# Import built-in modules
import unittest.mock as mock

# Import third-party modules
import pytest
import rpyc

# Import local modules
from dcc_mcp_ipc.client.async_base import AsyncBaseApplicationClient
from dcc_mcp_ipc.client.async_dcc import AsyncBaseDCCClient
from dcc_mcp_ipc.utils.errors import ConnectionError


# Mock RPyC connection for testing
class MockConnection:
    """Mock RPyC connection for testing."""

    def __init__(self, closed=False):
        self.closed = closed
        self.root = mock.MagicMock()

    def close(self):
        """Close the connection."""
        self.closed = True


@pytest.fixture
def mock_rpyc_connect(monkeypatch):
    """Mock rpyc.connect to return a mock connection."""
    mock_connect = mock.MagicMock(return_value=MockConnection())
    monkeypatch.setattr(rpyc, "connect", mock_connect)
    return mock_connect


@pytest.mark.asyncio
async def test_async_client_connect(mock_rpyc_connect):
    """Test connecting to a server asynchronously."""
    # Create a client
    client = AsyncBaseApplicationClient("localhost", 18812)

    # Connect to the server
    await client.connect()

    # Check that rpyc.connect was called with the correct arguments
    mock_rpyc_connect.assert_called_once_with(
        "localhost",
        18812,
        config={"sync_request_timeout": 30},
        service=None,
        keepalive=True,
    )

    # Check that the client is connected
    assert client.is_connected() is True


@pytest.mark.asyncio
async def test_async_client_connect_failure(monkeypatch):
    """Test handling connection failures."""

    # Mock rpyc.connect to raise an exception
    def mock_connect(*args, **kwargs):
        raise ConnectionRefusedError("Connection refused")

    monkeypatch.setattr(rpyc, "connect", mock_connect)

    # Create a client with a single connection attempt
    client = AsyncBaseApplicationClient("localhost", 18812, connection_attempts=1, connection_retry_delay=0.1)

    # Try to connect to the server
    with pytest.raises(ConnectionError):
        await client.connect()

    # Check that the client is not connected
    assert client.is_connected() is False


@pytest.mark.asyncio
async def test_async_client_close():
    """Test closing the connection."""
    # Create a client with a mock connection
    client = AsyncBaseApplicationClient("localhost", 18812)
    client.connection = MockConnection()

    # Close the connection
    client.close()

    # Check that the connection is closed
    assert client.connection is None
    assert client.is_connected() is False


@pytest.mark.asyncio
async def test_async_client_execute_python(mock_rpyc_connect):
    """Test executing Python code asynchronously."""
    # Create a client
    client = AsyncBaseApplicationClient("localhost", 18812)

    # Connect to the server
    await client.connect()

    # Mock the root.execute_python method
    client.connection.root.exposed_execute_python = mock.MagicMock(return_value=42)

    # Execute Python code
    result = await client.execute_python("2 + 2")

    # Check that the method was called with the correct arguments
    client.connection.root.exposed_execute_python.assert_called_once_with("2 + 2", {})

    # Check the result
    assert result == 42


@pytest.mark.asyncio
async def test_async_client_get_application_info(mock_rpyc_connect):
    """Test getting application info asynchronously."""
    # Create a client
    client = AsyncBaseApplicationClient("localhost", 18812)

    # Connect to the server
    await client.connect()

    # Mock the root.get_application_info method
    client.connection.root.get_application_info = mock.MagicMock(return_value={"name": "test_app", "version": "1.0.0"})

    # Get application info
    result = await client.get_application_info()

    # Check that the method was called
    client.connection.root.get_application_info.assert_called_once()

    # Check the result
    assert result == {"name": "test_app", "version": "1.0.0"}


@pytest.mark.asyncio
async def test_async_client_call_action(mock_rpyc_connect):
    """Test calling an action asynchronously."""
    # Create a client
    client = AsyncBaseApplicationClient("localhost", 18812)

    # Connect to the server
    await client.connect()

    # Mock the root.call_action method
    client.connection.root.exposed_call_action = mock.MagicMock(return_value={"result": "success"})

    # Call an action
    result = await client.call_action("test_action", arg1="value1", arg2="value2")

    # Check that the method was called with the correct arguments
    client.connection.root.exposed_call_action.assert_called_once_with("test_action", arg1="value1", arg2="value2")

    # Check the result
    assert result == {"result": "success"}


@pytest.mark.asyncio
async def test_async_dcc_client_get_dcc_info(mock_rpyc_connect):
    """Test getting DCC info asynchronously."""
    # Create a client
    client = AsyncBaseDCCClient("localhost", 18812, "test_dcc")

    # Connect to the server
    await client.connect()

    # Mock the root.get_dcc_info method
    client.connection.root.get_dcc_info = mock.MagicMock(return_value={"name": "test_dcc", "version": "1.0.0"})

    # Get DCC info
    result = await client.get_dcc_info()

    # Check that the method was called
    client.connection.root.get_dcc_info.assert_called_once()

    # Check the result
    assert result == {"name": "test_dcc", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Coverage improvement: uncovered paths in async_base.py (target: 79% -> 88%+)
# Missing lines: 78, 108, 143-145, 153-154, 169, 229-232, 257-260,
#                277-280, 344
# ---------------------------------------------------------------------------


class TestAsyncBaseDefaultConfig:
    """Tests for __init__ default config injection (line 78)."""

    def test_default_sync_request_timeout_set(self):
        """When no config provided, sync_request_timeout defaults to 30."""
        client = AsyncBaseApplicationClient("localhost", 18812)
        assert client.config["sync_request_timeout"] == 30

    def test_custom_config_preserved(self):
        """When custom config provided, it is not overwritten."""
        custom_config = {"sync_request_timeout": 60, "custom_key": "value"}
        client = AsyncBaseApplicationClient("localhost", 18812, config=custom_config)
        assert client.config["sync_request_timeout"] == 60
        assert client.config["custom_key"] == "value"

    def test_partial_config_gets_default_timeout(self):
        """When config missing sync_request_timeout only, default is added."""
        client = AsyncBaseApplicationClient("localhost", 18812, config={"allow_public_attrs": True})
        assert client.config["sync_request_timeout"] == 30
        assert client.config["allow_public_attrs"] is True


class TestAsyncBaseConnectPaths:
    """Tests for connect() edge cases (lines 108, 143-145)."""

    @pytest.mark.asyncio
    async def test_connect_already_connected_returns_true(self):
        """connect() returns True immediately if already connected (line 108)."""
        client = AsyncBaseApplicationClient("localhost", 18812)
        client.connection = MockConnection()
        result = await client.connect()
        assert result is True

    @pytest.mark.asyncio
    async def test_connect_retries_with_delay(self):
        """Connect fails first attempt, succeeds on second (line 143-145)."""
        call_count = 0

        def _failing_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionRefusedError("not ready yet")
            return MockConnection()

        with mock.patch("rpyc.connect", side_effect=_failing_then_success):
            client = AsyncBaseApplicationClient("localhost", 18812, connection_attempts=2, connection_retry_delay=0.01)
            result = await client.connect()
            assert result is True
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_connect_all_attempts_fail_raises_connection_error(self):
        """All connection attempts exhausted raises ConnectionError."""
        with mock.patch("rpyc.connect", side_effect=ConnectionRefusedError("refused")):
            client = AsyncBaseApplicationClient("localhost", 18812, connection_attempts=3, connection_retry_delay=0.01)
            with pytest.raises(ConnectionError, match="Failed to connect"):
                await client.connect()


class TestAsyncBaseCloseEdgeCases:
    """Tests for close() error path (lines 153-154)."""

    def test_close_handles_close_exception(self):
        """close() handles exception when closing the connection gracefully."""

        class FailingCloseConnection:
            closed = False

            def close(self):
                raise OSError("close failed unexpectedly")

        client = AsyncBaseApplicationClient("localhost", 18812)
        client.connection = FailingCloseConnection()
        # Should not raise despite close() failing
        client.close()
        assert client.connection is None


class TestAsyncBaseEnsureConnected:
    """Test for ensure_connected (line 169)."""

    @pytest.mark.asyncio
    async def test_ensure_connected_calls_connect_when_disconnected(self):
        """ensure_connected calls connect() when not connected."""
        client = AsyncBaseApplicationClient("localhost", 18812)
        connect_called = False

        async def _tracking_connect():
            nonlocal connect_called
            connect_called = True
            client.connection = MockConnection()
            return True

        client.connect = _tracking_connect
        await client.ensure_connected()
        assert connect_called is True

    @pytest.mark.asyncio
    async def test_ensure_connected_noop_when_connected(self):
        """ensure_connected does nothing when already connected."""
        client = AsyncBaseApplicationClient("localhost", 18812)
        client.connection = MockConnection()
        connect_called = False

        async def _tracking_connect():
            nonlocal connect_called
            connect_called = True
            return True

        client.connect = _tracking_connect
        await client.ensure_connected()
        assert connect_called is False


class TestAsyncBaseRemoteMethodCoverage:
    """Cover remaining remote method stubs.

    Covers get_environment_info, call_function, list_actions (lines 229-232, 257-260, 277-280).
    """

    @pytest.mark.asyncio
    async def test_get_environment_info(self, mock_rpyc_connect):
        """get_environment_info delegates to root.get_environment_info()."""
        client = AsyncBaseApplicationClient("localhost", 18812)
        await client.connect()

        client.connection.root.get_environment_info = mock.MagicMock(
            return_value={"python": "3.12", "platform": "linux"}
        )
        result = await client.get_environment_info()
        assert result == {"python": "3.12", "platform": "linux"}
        client.connection.root.get_environment_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_function(self, mock_rpyc_connect):
        """call_function delegates to root.exposed_call_function()."""
        client = AsyncBaseApplicationClient("localhost", 18812)
        await client.connect()

        client.connection.root.exposed_call_function = mock.MagicMock(return_value="func_result")
        result = await client.call_function("math_module", "add", 1, 2)
        assert result == "func_result"
        client.connection.root.exposed_call_function.assert_called_once_with("math_module", "add", 1, 2)

    @pytest.mark.asyncio
    async def test_list_actions(self, mock_rpyc_connect):
        """list_actions delegates to root.exposed_list_actions()."""
        client = AsyncBaseApplicationClient("localhost", 18812)
        await client.connect()

        expected = {"action_a": {"desc": "A"}, "action_b": {"desc": "B"}}
        client.connection.root.exposed_list_actions = mock.MagicMock(return_value=expected)
        result = await client.list_actions()
        assert result == expected
        client.connection.root.exposed_list_actions.assert_called_once()


class TestGetAsyncClientFactory:
    """Test get_async_client factory function (line 344)."""

    @pytest.mark.asyncio
    async def test_get_async_client_returns_client_instance(self):
        """Factory creates an AsyncBaseApplicationClient with given params."""
        # Import local modules
        from dcc_mcp_ipc.client.async_base import get_async_client

        client = await get_async_client(
            host="myhost",
            port=9999,
            service_name="dcc_service",
            connection_attempts=5,
            connection_timeout=10.0,
            connection_retry_delay=2.0,
        )

        assert isinstance(client, AsyncBaseApplicationClient)
        assert client.host == "myhost"
        assert client.port == 9999
        assert client.service_name == "dcc_service"
        assert client.connection_attempts == 5
        assert client.connection_timeout == 10.0
        assert client.connection_retry_delay == 2.0


class TestAsyncBaseIsConnected:
    """Test is_connected() edge cases (covers line 93)."""

    def test_is_connected_false_when_connection_none(self):
        """is_connected returns False when no connection exists."""
        client = AsyncBaseApplicationClient("localhost", 18812)
        assert client.is_connected() is False

    def test_is_connected_false_when_connection_closed(self):
        """is_connected returns False when connection is closed."""
        client = AsyncBaseApplicationClient("localhost", 18812)
        client.connection = MockConnection(closed=True)
        assert client.is_connected() is False
