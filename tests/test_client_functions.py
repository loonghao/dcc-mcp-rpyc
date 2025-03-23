"""Tests for client module functions and classes.

This module contains tests for the functions and classes in the client module
that are currently lacking coverage.
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.client import BaseDCCClient
from dcc_mcp_rpyc.client import ClientRegistry
from dcc_mcp_rpyc.client import ConnectionPool


class TestConnectionPool:
    """Tests for the ConnectionPool class."""

    def test_connection_pool_init(self):
        """Test the ConnectionPool initialization."""
        # Test with default parameters
        pool = ConnectionPool()
        assert hasattr(pool, "pool")
        assert len(pool.pool) == 0

    def test_connection_pool_get_client(self):
        """Test the get_client method."""
        pool = ConnectionPool()

        # Create a mock client that will be returned by create_client
        mock_client = MagicMock()
        mock_client.host = "127.0.0.1"
        mock_client.port = 12345
        mock_client.is_connected.return_value = True

        # Test getting a new client
        with patch("dcc_mcp_rpyc.client.create_client", return_value=mock_client) as mock_create_client:
            client = pool.get_client("test_dcc", "127.0.0.1", 12345)

            # Verify create_client was called correctly
            mock_create_client.assert_called_once()
            call_args = mock_create_client.call_args[0]
            assert call_args[0] == "test_dcc"
            assert call_args[1] == "127.0.0.1"
            assert call_args[2] == 12345
            assert call_args[3] is True  # auto_connect
            assert call_args[4] == 5.0  # timeout

            # Verify client was returned and added to pool
            assert client == mock_client
            assert len(pool.pool) == 1
            assert ("test_dcc", "127.0.0.1", 12345) in pool.pool
            assert pool.pool[("test_dcc", "127.0.0.1", 12345)] == mock_client

        # Test getting an existing client
        # Reset the pool to ensure test consistency
        pool = ConnectionPool()
        pool.pool[("test_dcc", "127.0.0.1", 12345)] = mock_client

        with patch("dcc_mcp_rpyc.client.create_client", return_value=MagicMock()) as mock_create_client:
            # The second call should use the pooled client and not call create_client
            client = pool.get_client("test_dcc", "127.0.0.1", 12345)

            # Verify create_client was not called
            mock_create_client.assert_not_called()

            # Verify the pooled client was returned
            assert client == mock_client
            assert len(pool.pool) == 1

        # Test using custom client factory
        pool = ConnectionPool()
        mock_factory = MagicMock(return_value=mock_client)

        client = pool.get_client("test_dcc", "127.0.0.1", 12345, client_factory=mock_factory)

        # Verify factory was called correctly
        mock_factory.assert_called_once()
        call_args = mock_factory.call_args[0]
        assert call_args[0] == "test_dcc"
        assert call_args[1] == "127.0.0.1"
        assert call_args[2] == 12345

        # Verify client was returned and added to pool
        assert client == mock_client
        assert len(pool.pool) == 1
        assert ("test_dcc", "127.0.0.1", 12345) in pool.pool
        assert pool.pool[("test_dcc", "127.0.0.1", 12345)] == mock_client

    def test_connection_pool_release_client(self):
        """Test the release_client method."""
        pool = ConnectionPool()

        # Add a client to the pool
        with patch("dcc_mcp_rpyc.client.create_client") as mock_create_client:
            mock_client = MagicMock()
            mock_client.dcc_name = "test_dcc"
            mock_client.host = "127.0.0.1"
            mock_client.port = 12345
            mock_create_client.return_value = mock_client

            client = pool.get_client("test_dcc", "127.0.0.1", 12345)
            assert len(pool.pool) == 1

        # Release the client
        pool.release_client(client)

        # The client should still be in the pool
        assert len(pool.pool) == 1
        key = ("test_dcc", "127.0.0.1", 12345)
        assert key in pool.pool

    def test_connection_pool_close_all(self):
        """Test the close_all method."""
        pool = ConnectionPool()

        # 创建自定义的客户端工厂函数
        mock_client1 = MagicMock()
        mock_client1.dcc_name = "test_dcc1"
        mock_client1.host = "127.0.0.1"
        mock_client1.port = 12345

        mock_client2 = MagicMock()
        mock_client2.dcc_name = "test_dcc2"
        mock_client2.host = "127.0.0.1"
        mock_client2.port = 12346

        # 使用列表来跟踪调用次数
        clients = [mock_client1, mock_client2]
        call_count = 0

        def custom_client_factory(*args, **kwargs):
            nonlocal call_count
            client = clients[call_count]
            call_count += 1
            return client

        # 使用依赖注入而不是 patch
        pool.get_client("test_dcc1", "127.0.0.1", 12345, client_factory=custom_client_factory)
        pool.get_client("test_dcc2", "127.0.0.1", 12346, client_factory=custom_client_factory)
        assert len(pool.pool) == 2

        # 关闭所有客户端
        pool.close_all()

        mock_client1.disconnect.assert_called_once()
        mock_client2.disconnect.assert_called_once()
        assert len(pool.pool) == 0


class TestClientRegistry:
    """Tests for the ClientRegistry class."""

    def test_client_registry_init(self):
        """Test the ClientRegistry initialization."""
        # The registry is a class with a class variable _registry
        assert hasattr(ClientRegistry, "_registry")
        assert isinstance(ClientRegistry._registry, dict)

    def test_client_registry_register(self):
        """Test the register method."""
        # Clear registry before test
        ClientRegistry._registry = {}

        # Create a mock client class
        mock_client_class = MagicMock()
        mock_client_class.__name__ = "MockClient"

        # Register the client class
        ClientRegistry.register("test_dcc", mock_client_class)

        assert "test_dcc" in ClientRegistry._registry
        assert ClientRegistry._registry["test_dcc"] == mock_client_class

    def test_client_registry_get_client_class(self):
        """Test the get_client_class method."""
        # Clear registry before test
        ClientRegistry._registry = {}

        # Create a mock client class
        mock_client_class = MagicMock()
        mock_client_class.__name__ = "MockClient"

        # Register the client class
        ClientRegistry.register("test_dcc", mock_client_class)

        # Get the client class
        result = ClientRegistry.get_client_class("test_dcc")
        assert result == mock_client_class

        # Get a non-existent client class (should return BaseDCCClient)
        result = ClientRegistry.get_client_class("non_existent")
        assert result == BaseDCCClient


class TestBaseDCCClient:
    """Tests for the BaseDCCClient class."""

    def test_base_dcc_client_init(self):
        """Test the BaseDCCClient initialization."""
        # Test with default parameters
        with patch("dcc_mcp_rpyc.client.BaseDCCClient._discover_service"):
            client = BaseDCCClient("test_dcc", auto_connect=False)
            assert client.dcc_name == "test_dcc"
            assert client.host is None
            assert client.port is None
            assert client.connection is None
            assert client.connection_timeout == 5.0
            assert client.registry_path is None

        # Test with custom parameters
        with patch("dcc_mcp_rpyc.client.BaseDCCClient._discover_service"):
            client = BaseDCCClient(
                "test_dcc",
                "127.0.0.1",
                12345,
                False,
                10.0,
                "/path/to/registry",
            )
            assert client.dcc_name == "test_dcc"
            assert client.host == "127.0.0.1"
            assert client.port == 12345
            assert client.connection is None
            assert client.connection_timeout == 10.0
            assert client.registry_path == "/path/to/registry"

    def test_base_dcc_client_connect(self):
        """Test the connect method."""
        client = BaseDCCClient("test_dcc", "127.0.0.1", 12345, False)

        # Test successful connection
        # u521bu5efau4e00u4e2au6a21u62dfu7684u8fdeu63a5u51fdu6570
        mock_connect = MagicMock()
        # Create a mock connection that will pass the is_connected check
        mock_conn = MagicMock()
        # Make ping() return None to simulate successful ping
        mock_conn.ping.return_value = None
        mock_connect.return_value = mock_conn

        # u5148u6a21u62df is_connected u8fd4u56de Falseuff0cu7136u540eu518du8fd4u56de True
        is_connected_mock = MagicMock()
        is_connected_mock.side_effect = [
            False,
            True,
        ]  # u7b2cu4e00u6b21u8c03u7528u8fd4u56de Falseuff0cu7b2cu4e8cu6b21u8c03u7528u8fd4u56de True

        with patch.object(client, "is_connected", is_connected_mock):
            # Call connect with our mock_connect function
            result = client.connect(rpyc_connect_func=mock_connect)

            # Verify our mock_connect was called correctly
            mock_connect.assert_called_once_with("127.0.0.1", 12345, config={"sync_request_timeout": 5.0})
            # Verify is_connected was called twice
            assert is_connected_mock.call_count == 2
            # Verify connection was successful
            assert result is True
            assert client.connection == mock_conn

        # Test connection failure
        mock_connect_error = MagicMock(side_effect=Exception("Connection error"))

        # u91cdu7f6e client u5e76u786eu4fdd is_connected u8fd4u56de False
        client.connection = None
        with patch.object(client, "is_connected", return_value=False):
            result = client.connect(rpyc_connect_func=mock_connect_error)

            # Verify connect function was called
            mock_connect_error.assert_called_once()
            # Verify connection failed
            assert result is False
            assert client.connection is None

    def test_base_dcc_client_disconnect(self):
        """Test the disconnect method."""
        client = BaseDCCClient("test_dcc", "127.0.0.1", 12345, False)

        # Test disconnection when not connected
        result = client.disconnect()
        assert result is True

        # Test successful disconnection
        with patch("rpyc.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            client.connect()

            result = client.disconnect()

            mock_conn.close.assert_called_once()
            assert result is True
            assert client.connection is None

        # Test disconnection failure
        with patch("rpyc.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_conn.close.side_effect = Exception("Disconnection error")
            mock_connect.return_value = mock_conn
            client.connect()

            result = client.disconnect()

            mock_conn.close.assert_called_once()
            assert result is False
            assert client.connection is None

    def test_base_dcc_client_is_connected(self):
        """Test the is_connected method."""
        client = BaseDCCClient("test_dcc", "127.0.0.1", 12345, False)

        # Test when not connected
        assert client.is_connected() is False

        # Test when connected
        with patch("rpyc.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            client.connect()

            # Test successful ping
            assert client.is_connected() is True

            # Test failed ping
            mock_conn.ping.side_effect = Exception("Ping error")
            assert client.is_connected() is False

    def test_base_dcc_client_ensure_connected(self):
        """Test the ensure_connected method."""
        client = BaseDCCClient("test_dcc", "127.0.0.1", 12345, False)

        # Test when already connected
        with patch.object(client, "is_connected", return_value=True):
            with patch.object(client, "connect") as mock_connect:
                client.ensure_connected()
                mock_connect.assert_not_called()

        # Test when not connected but reconnect succeeds
        with patch.object(client, "is_connected", return_value=False):
            with patch.object(client, "connect", return_value=True) as mock_connect:
                client.ensure_connected()
                mock_connect.assert_called_once()

        # Test when not connected and reconnect fails
        with patch.object(client, "is_connected", return_value=False):
            with patch.object(client, "connect", return_value=False) as mock_connect:
                with pytest.raises(ConnectionError):
                    client.ensure_connected()
                mock_connect.assert_called_once()

    def test_base_dcc_client_context_manager(self):
        """Test the BaseDCCClient as a context manager."""
        client = BaseDCCClient("test_dcc", "127.0.0.1", 12345, False)

        # Test context manager
        with patch.object(client, "disconnect") as mock_disconnect:
            with client:
                pass
            mock_disconnect.assert_called_once()
