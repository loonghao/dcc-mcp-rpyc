"""Tests for the client pool module.

This module contains tests for the ClientRegistry and ConnectionPool classes.
"""

# Import built-in modules
import time
from unittest.mock import MagicMock
from unittest.mock import patch

# Import local modules
from dcc_mcp_rpyc.client.dcc import BaseDCCClient
from dcc_mcp_rpyc.client.pool import ClientRegistry
from dcc_mcp_rpyc.client.pool import ConnectionPool
from dcc_mcp_rpyc.client.pool import close_all_connections
from dcc_mcp_rpyc.client.pool import close_client
from dcc_mcp_rpyc.client.pool import get_client


def test_client_registry_register():
    """Test client registry registration."""
    # Clear registry for testing
    ClientRegistry._registry = {}

    # Create mock client class
    mock_client_class = MagicMock(spec=BaseDCCClient)

    # Register client class
    ClientRegistry.register("test_dcc", mock_client_class)

    # Validate registration
    assert "test_dcc" in ClientRegistry._registry
    assert ClientRegistry._registry["test_dcc"] is mock_client_class


def test_client_registry_get_client_class():
    """Test getting client class."""
    # Clear registry for testing
    ClientRegistry._registry = {}

    # Create mock client class
    mock_client_class = MagicMock(spec=BaseDCCClient)

    # Register client class
    ClientRegistry.register("test_dcc", mock_client_class)

    # Get client class
    client_class = ClientRegistry.get_client_class("test_dcc")

    # Validate result
    assert client_class is mock_client_class


def test_client_registry_get_client_class_not_found():
    """Test getting non-existent client class."""
    # Clear registry for testing
    ClientRegistry._registry = {}

    # Get non-existent client class
    client_class = ClientRegistry.get_client_class("non_existent_dcc")

    # Validate result
    assert client_class is BaseDCCClient


def test_client_registry_get_client_class_default():
    """Test getting client class with default value."""
    # Clear registry for testing
    ClientRegistry._registry = {}

    # Get non-existent client class
    client_class = ClientRegistry.get_client_class("non_existent_dcc")

    # Validate result
    assert client_class is BaseDCCClient


# Test ConnectionPool class
def test_connection_pool_init():
    """Test connection pool initialization."""
    # Create connection pool
    pool = ConnectionPool(max_idle_time=300.0, cleanup_interval=60.0)

    # Validate initialization result
    assert pool.pool == {}
    assert pool.max_idle_time == 300.0
    assert pool.cleanup_interval == 60.0
    assert pool.last_cleanup <= time.time()


def test_connection_pool_get_client():
    """Test getting client from connection pool."""
    # Create mock client
    mock_client = MagicMock(spec=BaseDCCClient)
    mock_client.is_connected.return_value = True

    # Create mock client factory function
    mock_factory = MagicMock(return_value=mock_client)

    # Create connection pool
    pool = ConnectionPool()

    # Get client from connection pool, using client_factory parameter
    client = pool.get_client("test_dcc", "localhost", 8000, client_factory=mock_factory)

    # Validate result
    assert client is mock_client
    assert ("test_dcc", "localhost", 8000) in pool.pool
    assert pool.pool[("test_dcc", "localhost", 8000)][0] is mock_client
    mock_factory.assert_called_once_with(
        dcc_name="test_dcc",
        host="localhost",
        port=8000,
        auto_connect=True,
        connection_timeout=5.0,
        registry_path=None,
        use_zeroconf=False,
    )


def test_connection_pool_get_client_existing():
    """Test getting existing client from connection pool."""
    # Create mock client
    mock_client = MagicMock(spec=BaseDCCClient)
    mock_client.is_connected.return_value = True

    # Create connection pool and add client
    pool = ConnectionPool()
    pool.pool[("test_dcc", "localhost", 8000)] = (mock_client, time.time())

    # Create mock client factory function
    mock_factory = MagicMock()

    # Get client from connection pool, using client_factory parameter
    client = pool.get_client("test_dcc", "localhost", 8000, client_factory=mock_factory)

    # Validate result
    assert client is mock_client
    mock_factory.assert_not_called()


def test_connection_pool_get_client_existing_not_connected():
    """Test getting existing client from connection pool that is not connected."""
    # Create mock client
    mock_client = MagicMock(spec=BaseDCCClient)
    mock_client.is_connected.return_value = False
    mock_client.connect.return_value = True

    # Create connection pool and add client
    pool = ConnectionPool()
    pool.pool[("test_dcc", "localhost", 8000)] = (mock_client, time.time())

    # Create mock client factory function
    mock_factory = MagicMock()

    # Get client from connection pool, using client_factory parameter
    client = pool.get_client("test_dcc", "localhost", 8000, client_factory=mock_factory)

    # Validate result
    assert client is mock_client
    mock_client.connect.assert_called_once()
    mock_factory.assert_not_called()


def test_connection_pool_get_client_existing_reconnect_failed():
    """Test getting existing client from connection pool that is not connected."""
    # Create mock client
    mock_client = MagicMock(spec=BaseDCCClient)
    mock_client.is_connected.return_value = False
    mock_client.connect.return_value = False

    # Create connection pool and add client
    pool = ConnectionPool()
    pool.pool[("test_dcc", "localhost", 8000)] = (mock_client, time.time())

    # Create mock client factory function
    mock_factory = MagicMock()

    # Get client from connection pool, using client_factory parameter
    client = pool.get_client("test_dcc", "localhost", 8000, client_factory=mock_factory)

    # Validate result
    # According to ConnectionPool.get_client behavior, when reconnect fails, the original client should be returned
    assert client is mock_client
    mock_client.connect.assert_called_once()
    # Factory function should not be called, because client already exists
    mock_factory.assert_not_called()


def test_connection_pool_close_client():
    """Test closing client from connection pool."""
    # Create mock client
    mock_client = MagicMock(spec=BaseDCCClient)

    # Create connection pool and add client
    pool = ConnectionPool()
    pool.pool[("test_dcc", "localhost", 8000)] = (mock_client, time.time())

    # Close client
    result = pool.close_client("test_dcc", "localhost", 8000)

    # Validate result
    assert result is True
    assert ("test_dcc", "localhost", 8000) not in pool.pool
    mock_client.disconnect.assert_called_once()


def test_connection_pool_close_client_not_found():
    """Test closing client from connection pool that does not exist."""
    # Create connection pool
    pool = ConnectionPool()

    # Close non-existent client
    result = pool.close_client("test_dcc", "localhost", 8000)

    # Validate result
    assert result is False


def test_connection_pool_close_all_connections():
    """Test closing all clients from connection pool."""
    # Create mock clients
    mock_client1 = MagicMock(spec=BaseDCCClient)
    mock_client2 = MagicMock(spec=BaseDCCClient)

    # Create connection pool and add clients
    pool = ConnectionPool()
    pool.pool[("test_dcc1", "localhost", 8000)] = (mock_client1, time.time())
    pool.pool[("test_dcc2", "localhost", 8001)] = (mock_client2, time.time())

    # Close all clients
    pool.close_all_connections()

    # Validate result
    assert pool.pool == {}
    mock_client1.disconnect.assert_called_once()
    mock_client2.disconnect.assert_called_once()


def test_connection_pool_cleanup_idle_connections():
    """Test cleaning up idle connections."""
    # Create mock clients
    mock_client1 = MagicMock(spec=BaseDCCClient)
    mock_client2 = MagicMock(spec=BaseDCCClient)

    # Create connection pool and add clients
    pool = ConnectionPool(max_idle_time=1.0, cleanup_interval=0.5)

    # Add a new client and an old client
    current_time = time.time()
    pool.pool[("test_dcc1", "localhost", 8000)] = (mock_client1, current_time)
    pool.pool[("test_dcc2", "localhost", 8001)] = (mock_client2, current_time - 2.0)  # 超过最大空闲时间

    # Set last cleanup time to long ago, ensuring cleanup will be triggered
    pool.last_cleanup = current_time - 1.0  # 超过清理间隔

    # Get client, trigger cleanup
    with patch("time.time", return_value=current_time):
        # Get a client, trigger cleanup
        pool.get_client("test_dcc1", "localhost", 8000)

    # Validate result
    assert ("test_dcc1", "localhost", 8000) in pool.pool  # New client still in pool
    assert ("test_dcc2", "localhost", 8001) not in pool.pool  # Old client has been cleaned up
    mock_client2.disconnect.assert_called_once()


# Test global functions
def test_global_get_client():
    """Test global get client function."""
    # Create mock connection pool
    mock_pool = MagicMock(spec=ConnectionPool)
    mock_client = MagicMock(spec=BaseDCCClient)
    mock_pool.get_client.return_value = mock_client

    # Replace global connection pool
    with patch("dcc_mcp_rpyc.client.pool._connection_pool", mock_pool):
        # Get client
        client = get_client("test_dcc", "localhost", 8000)

    # Validate result
    assert client is mock_client
    mock_pool.get_client.assert_called_once_with(
        dcc_name="test_dcc",
        host="localhost",
        port=8000,
        auto_connect=True,
        connection_timeout=5.0,
        registry_path=None,
        client_class=None,
        client_factory=None,
        use_zeroconf=False,
    )


def test_global_close_client():
    """Test global close client function."""
    # Create mock connection pool
    mock_pool = MagicMock(spec=ConnectionPool)
    mock_pool.close_client.return_value = True

    # Replace global connection pool
    with patch("dcc_mcp_rpyc.client.pool._connection_pool", mock_pool):
        # Close client
        result = close_client("test_dcc", "localhost", 8000)

    # Validate result
    assert result is True
    mock_pool.close_client.assert_called_once_with("test_dcc", "localhost", 8000)


def test_global_close_all_connections():
    """Test global close all connections function."""
    # Create mock connection pool
    mock_pool = MagicMock(spec=ConnectionPool)

    # Replace global connection pool
    with patch("dcc_mcp_rpyc.client.pool._connection_pool", mock_pool):
        # Close all connections
        close_all_connections()

    # Validate result
    mock_pool.close_all_connections.assert_called_once()
