"""Tests for the client pool module.

This module contains tests for the ClientRegistry and ConnectionPool classes.
"""

# Import built-in modules
import time
from unittest.mock import MagicMock
from unittest.mock import patch

# Import local modules
from dcc_mcp_ipc.client.dcc import BaseDCCClient
from dcc_mcp_ipc.client.pool import ClientRegistry
from dcc_mcp_ipc.client.pool import ConnectionPool
from dcc_mcp_ipc.client.pool import close_all_connections
from dcc_mcp_ipc.client.pool import close_client
from dcc_mcp_ipc.client.pool import get_client


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


def test_connection_pool_close_client_disconnect_error():
    """Test closing client when disconnect raises an exception."""
    # Create mock client that raises on disconnect
    mock_client = MagicMock(spec=BaseDCCClient)
    mock_client.disconnect.side_effect = RuntimeError("disconnect error")

    # Create connection pool and add client
    pool = ConnectionPool()
    pool.pool[("test_dcc", "localhost", 8000)] = (mock_client, time.time())

    # Close client should not raise, returns False
    result = pool.close_client("test_dcc", "localhost", 8000)

    assert result is False
    # Client was removed from pool despite error? No - check implementation
    # Actually looking at the code: except returns False without del, so key remains


def test_connection_pool_close_all_with_errors():
    """Test closing all connections when some raise exceptions."""
    mock_client1 = MagicMock(spec=BaseDCCClient)
    mock_client2 = MagicMock(spec=BaseDCCClient)
    mock_client2.disconnect.side_effect = RuntimeError("error")

    pool = ConnectionPool()
    pool.pool[("dcc1", "localhost", 8000)] = (mock_client1, time.time())
    pool.pool[("dcc2", "localhost", 8001)] = (mock_client2, time.time())

    pool.close_all_connections()

    assert pool.pool == {}
    mock_client1.disconnect.assert_called_once()
    mock_client2.disconnect.assert_called_once()


def test_connection_pool_get_client_with_client_class():
    """Test get_client using client_class parameter."""
    mock_client = MagicMock(spec=BaseDCCClient)
    mock_client.is_connected.return_value = True

    with patch.object(BaseDCCClient, "__init__", return_value=None):
        BaseDCCClient.is_connected = lambda self: True  # type: ignore[attr-defined]

        pool = ConnectionPool()
        pool.get_client(
            "test_dcc",
            "localhost",
            8000,
            auto_connect=False,
            client_class=type(
                "MockClient",
                (object,),
                {
                    "__init__": lambda s, **kw: None,
                    "is_connected": lambda s: True,
                },
            ),
        )
        assert ("test_dcc", "localhost", 8000) in pool.pool


def test_connection_pool_get_client_zeroconf_discovery():
    """Test get_client using ZeroConf discovery when host/port is None."""
    mock_factory = MagicMock(return_value=MagicMock(spec=BaseDCCClient))

    pool = ConnectionPool()

    with patch.object(pool, "_cleanup_idle_connections"):
        with patch("dcc_mcp_ipc.client.pool.ZeroConfDiscoveryStrategy") as MockZC:
            mock_zc = MagicMock()
            MockZC.return_value = mock_zc

            # Import local modules
            from dcc_mcp_ipc.discovery import ServiceInfo

            mock_service = ServiceInfo(name="test_maya", host="192.168.1.100", port=9000, dcc_type="maya")
            mock_zc.discover_services.return_value = [mock_service]

            pool.get_client("maya", use_zeroconf=True, client_factory=mock_factory)

            mock_zc.discover_services.assert_called_once_with("maya")
            mock_factory.assert_called_once()


def test_connection_pool_cleanup_not_triggered_yet():
    """Test that cleanup is skipped if cleanup_interval hasn't elapsed."""
    mock_client = MagicMock(spec=BaseDCCClient)
    mock_client.is_connected.return_value = True

    pool = ConnectionPool(cleanup_interval=60.0)
    current_time = time.time()
    pool.pool[("dcc1", "h", 8000)] = (mock_client, current_time)
    pool.last_cleanup = current_time - 10.0  # Only 10s ago, less than 60s interval

    with patch("time.time", return_value=current_time):
        pool.get_client("dcc1", "h", 8000, client_factory=MagicMock(return_value=mock_client))

    # Client should still be in pool (not cleaned up as idle)
    assert ("dcc1", "h", 8000) in pool.pool


def test_connection_pool_key_case_insensitive():
    """Test that connection keys are case-insensitive for dcc_name."""
    mock_client = MagicMock(spec=BaseDCCClient)
    mock_client.is_connected.return_value = True
    mock_factory = MagicMock(return_value=mock_client)

    pool = ConnectionPool()

    pool.get_client("Maya", "localhost", 8000, client_factory=mock_factory)

    # Should find the same client using lowercase key
    assert ("maya", "localhost", 8000) in pool.pool


# Test global functions
def test_global_get_client():
    """Test global get client function."""
    # Create mock connection pool
    mock_pool = MagicMock(spec=ConnectionPool)
    mock_client = MagicMock(spec=BaseDCCClient)
    mock_pool.get_client.return_value = mock_client

    # Replace global connection pool
    with patch("dcc_mcp_ipc.client.pool._connection_pool", mock_pool):
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
    with patch("dcc_mcp_ipc.client.pool._connection_pool", mock_pool):
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
    with patch("dcc_mcp_ipc.client.pool._connection_pool", mock_pool):
        # Close all connections
        close_all_connections()

    # Validate result
    mock_pool.close_all_connections.assert_called_once()
