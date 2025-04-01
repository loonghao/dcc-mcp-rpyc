"""Tests for the base client module.

This module contains tests for the BaseApplicationClient class and related functions.
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.client.base import BaseApplicationClient
from dcc_mcp_rpyc.client.base import close_all_connections
from dcc_mcp_rpyc.client.base import get_client
from dcc_mcp_rpyc.discovery import ServiceInfo


def test_base_client_init():
    """Test basic client initialization."""
    # Disable auto-connect client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    assert client.app_name == "test_app"
    assert client.host == "localhost"
    assert client.port == 8000
    assert client.connection is None


def test_base_client_discover_service():
    """Test service discovery functionality."""
    with patch("dcc_mcp_rpyc.client.base.ServiceRegistry") as mock_registry:
        # Set mock service registry
        mock_registry_instance = MagicMock()
        mock_registry.return_value = mock_registry_instance

        # Set mock strategy
        mock_strategy = MagicMock()
        mock_registry_instance.get_strategy.return_value = mock_strategy

        # Set discover services return value
        mock_registry_instance.discover_services.return_value = [
            ServiceInfo(name="test_app", host="test_host", port=9000, dcc_type="test_app")
        ]

        # Create client and test service discovery
        client = BaseApplicationClient("test_app", auto_connect=False)
        host, port = client._discover_service()

        # Validate result
        assert host == "test_host"
        assert port == 9000
        assert client.host == "test_host"
        assert client.port == 9000


def test_base_client_discover_service_no_services():
    """Test no service discovery."""
    with patch("dcc_mcp_rpyc.client.base.ServiceRegistry") as mock_registry:
        # Set mock strategy
        mock_strategy = MagicMock()
        mock_registry.return_value.get_strategy.return_value = mock_strategy
        mock_registry.return_value.discover_services.return_value = []

        # Create client and test service discovery
        client = BaseApplicationClient("test_app", auto_connect=False)
        host, port = client._discover_service()

        # Validate result
        assert host is None
        assert port is None


def test_base_client_discover_service_exception():
    """Test service discovery exception."""
    with patch("dcc_mcp_rpyc.client.base.ServiceRegistry") as mock_registry:
        # Set mock strategy
        mock_registry.return_value.get_strategy.side_effect = Exception("Test exception")

        # Create client and test service discovery
        client = BaseApplicationClient("test_app", auto_connect=False)
        host, port = client._discover_service()

        # Validate result
        assert host is None
        assert port is None


def test_base_client_connect():
    """Test client connection functionality."""
    # Create mock connection function
    mock_connection = MagicMock()
    mock_connection.ping.return_value = True
    mock_connect_func = MagicMock(return_value=mock_connection)

    # Create client and test connection
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    result = client.connect(rpyc_connect_func=mock_connect_func)

    # Validate result
    assert result is True
    assert client.connection is mock_connection
    mock_connect_func.assert_called_once_with("localhost", 8000, config={"sync_request_timeout": 5.0})


def test_base_client_connect_already_connected():
    """Test client connection when already connected."""
    # Create mock connection
    mock_connection = MagicMock()
    mock_connection.ping.return_value = True

    # Create connected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    client.connection = mock_connection

    # Test connection
    mock_connect_func = MagicMock()
    result = client.connect(rpyc_connect_func=mock_connect_func)

    # Validate result
    assert result is True
    mock_connect_func.assert_not_called()


def test_base_client_connect_no_host_port():
    """Test connection when no host or port is provided."""
    # Create client without host and port
    client = BaseApplicationClient("test_app", None, None, auto_connect=False)

    # Test connection
    mock_connect_func = MagicMock()
    result = client.connect(rpyc_connect_func=mock_connect_func)

    # Validate result
    assert result is False
    mock_connect_func.assert_not_called()


def test_base_client_connect_exception():
    """Test connection when an exception occurs."""
    # Create mock connection function, raise exception
    mock_connect_func = MagicMock(side_effect=Exception("Test exception"))

    # Create client and test connection
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    result = client.connect(rpyc_connect_func=mock_connect_func)

    # Validate result
    assert result is False
    assert client.connection is None


def test_base_client_disconnect():
    """Test client disconnection functionality."""
    # Create mock connection
    mock_connection = MagicMock()

    # Create connected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    client.connection = mock_connection

    # Test disconnection
    result = client.disconnect()

    # Validate result
    assert result is True
    assert client.connection is None
    mock_connection.close.assert_called_once()


def test_base_client_disconnect_not_connected():
    """Test disconnection when client is not connected."""
    # Create unconnected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    client.connection = None

    # Test disconnection
    result = client.disconnect()

    # Validate result
    assert result is True


def test_base_client_disconnect_exception():
    """Test disconnection when an exception occurs."""
    # Create mock connection, raise exception on close
    mock_connection = MagicMock()
    mock_connection.close.side_effect = Exception("Test exception")

    # Create connected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    client.connection = mock_connection

    # Test disconnection
    result = client.disconnect()

    # Validate result
    assert result is False
    assert client.connection is None


def test_base_client_reconnect():
    """Test client reconnection functionality."""
    with patch.object(BaseApplicationClient, "disconnect") as mock_disconnect, patch.object(
        BaseApplicationClient, "connect"
    ) as mock_connect:
        # Set mock method return values
        mock_disconnect.return_value = True
        mock_connect.return_value = True

        # Create client and test reconnection
        client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
        result = client.reconnect()

        # Validate result
        assert result is True
        mock_disconnect.assert_called_once()
        mock_connect.assert_called_once()


def test_base_client_is_connected():
    """Test client connection status check functionality."""
    # Create mock connection
    mock_connection = MagicMock()

    # Create connected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    client.connection = mock_connection

    # Test connection status
    result = client.is_connected()

    # Validate result
    assert result is True
    mock_connection.ping.assert_called_once()


def test_base_client_is_connected_not_connected():
    """Test connection status check functionality when client is not connected."""
    # Create unconnected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    client.connection = None

    # Test connection status
    result = client.is_connected()

    # Validate result
    assert result is False


def test_base_client_is_connected_exception():
    """Test connection status check functionality when an exception occurs."""
    # Create mock connection, raise exception on ping
    mock_connection = MagicMock()
    mock_connection.ping.side_effect = Exception("Test exception")

    # Create connected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    client.connection = mock_connection

    # Test connection status
    result = client.is_connected()

    # Validate result
    assert result is False
    assert client.connection is None


def test_base_client_execute_remote_command():
    """Test client remote command execution functionality."""
    with patch("dcc_mcp_rpyc.client.base._execute_remote_command") as mock_execute:
        # Set mock execution function return value
        mock_execute.return_value = "test_result"

        # Create mock connection
        mock_connection = MagicMock()

        # Create connected client
        client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
        client.connection = mock_connection
        with patch.object(client, "is_connected", return_value=True):
            # Test remote command execution
            result = client.execute_remote_command("test_command", arg1="value1")

            # Validate result
            assert result == "test_result"
            mock_execute.assert_called_once_with(mock_connection, "test_command", arg1="value1")


def test_base_client_execute_remote_command_not_connected():
    """Test remote command execution when client is not connected."""
    # Create unconnected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    with patch.object(client, "is_connected", return_value=False):
        # Test remote command execution
        with pytest.raises(ConnectionError):
            client.execute_remote_command("test_command")


def test_base_client_execute_remote_command_exception():
    """Test remote command execution when an exception occurs."""
    with patch("dcc_mcp_rpyc.client.base._execute_remote_command") as mock_execute:
        # Set mock execution function to raise exception
        mock_execute.side_effect = Exception("Test exception")

        # Create mock connection
        mock_connection = MagicMock()

        # Create connected client
        client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
        client.connection = mock_connection
        with patch.object(client, "is_connected", return_value=True):
            # Test remote command execution
            with pytest.raises(Exception):
                client.execute_remote_command("test_command")


def test_base_client_execute_python():
    """Test client Python code execution functionality."""
    # Create mock connection
    mock_root = MagicMock()
    mock_root.exposed_execute_python.return_value = "test_result"
    mock_connection = MagicMock()
    mock_connection.root = mock_root

    # Create connected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    client.connection = mock_connection
    with patch.object(client, "is_connected", return_value=True):
        # Test Python code execution
        result = client.execute_python("print('test')")

        # Validate result
        assert result == "test_result"
        mock_root.exposed_execute_python.assert_called_once_with("print('test')", {})


def test_base_client_execute_python_with_context():
    """Test client Python code execution with context functionality."""
    # Create mock connection
    mock_root = MagicMock()
    mock_root.exposed_execute_python.return_value = "test_result"
    mock_connection = MagicMock()
    mock_connection.root = mock_root

    # Create connected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    client.connection = mock_connection
    with patch.object(client, "is_connected", return_value=True):
        # Test Python code execution
        context = {"var1": "value1"}
        result = client.execute_python("print('test')", context)

        # Validate result
        assert result == "test_result"
        mock_root.exposed_execute_python.assert_called_once_with("print('test')", context)


def test_base_client_execute_python_not_connected():
    """Test client Python code execution when client is not connected."""
    # Create unconnected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    with patch.object(client, "is_connected", return_value=False):
        # Test Python code execution
        with pytest.raises(ConnectionError):
            client.execute_python("print('test')")


def test_base_client_execute_python_exception():
    """Test client Python code execution when an exception occurs."""
    # Create mock connection
    mock_root = MagicMock()
    mock_root.exposed_execute_python.side_effect = Exception("Test exception")
    mock_connection = MagicMock()
    mock_connection.root = mock_root

    # Create connected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    client.connection = mock_connection
    with patch.object(client, "is_connected", return_value=True):
        # Test Python code execution
        with pytest.raises(Exception):
            client.execute_python("print('test')")


def test_base_client_import_module():
    """Test client module import functionality."""
    # Create mock connection
    mock_root = MagicMock()
    mock_root.exposed_get_module.return_value = "test_module"
    mock_connection = MagicMock()
    mock_connection.root = mock_root

    # Create connected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    client.connection = mock_connection
    with patch.object(client, "is_connected", return_value=True):
        # Test module import
        result = client.import_module("test_module")

        # Validate result
        assert result == "test_module"
        mock_root.exposed_get_module.assert_called_once_with("test_module")


def test_base_client_import_module_not_connected():
    """Test client module import when client is not connected."""
    # Create unconnected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    with patch.object(client, "is_connected", return_value=False):
        # Test module import
        with pytest.raises(ConnectionError):
            client.import_module("test_module")


def test_base_client_import_module_exception():
    """Test client module import when an exception occurs."""
    # Create mock connection
    mock_root = MagicMock()
    mock_root.exposed_get_module.side_effect = Exception("Test exception")
    mock_connection = MagicMock()
    mock_connection.root = mock_root

    # Create connected client
    client = BaseApplicationClient("test_app", "localhost", 8000, auto_connect=False)
    client.connection = mock_connection
    with patch.object(client, "is_connected", return_value=True):
        # Test module import
        with pytest.raises(Exception):
            client.import_module("test_module")


def test_get_client():
    """Test get client function."""
    with patch("dcc_mcp_rpyc.client.base.BaseApplicationClient") as mock_client_class:
        # Set mock client class
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Test getting client
        client = get_client("test_app", "localhost", 8000)

        # Validate result
        assert client is mock_client
        mock_client_class.assert_called_once_with("test_app", "localhost", 8000)


def test_get_client_existing():
    """Test getting existing client."""
    # Create mock client
    mock_client = MagicMock()

    # Use patch to mock _clients dictionary
    key = ("test_app", None, None)
    with patch("dcc_mcp_rpyc.client.base._clients", {key: mock_client}):
        # Test getting client
        client = get_client("test_app")

        # Validate result
        assert client is mock_client


def test_close_all_connections():
    """Test close all connections function."""
    # Create mock clients
    mock_client1 = MagicMock()
    mock_client2 = MagicMock()

    with patch("dcc_mcp_rpyc.client.base._clients", {"app1": mock_client1, "app2": mock_client2}):
        # Test closing all connections
        close_all_connections()

        # Validate results
        mock_client1.disconnect.assert_called_once()
        mock_client2.disconnect.assert_called_once()
