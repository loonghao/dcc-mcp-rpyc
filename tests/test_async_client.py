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
from dcc_mcp_rpyc.client.async_base import AsyncBaseApplicationClient
from dcc_mcp_rpyc.client.async_dcc import AsyncBaseDCCClient
from dcc_mcp_rpyc.utils.errors import ConnectionError


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
