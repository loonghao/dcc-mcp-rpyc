"""Tests for the client module.

This module contains tests for the BaseDCCClient and ConnectionPool classes.
"""

# Import built-in modules
import time
from typing import Tuple

# Import local modules
from dcc_mcp_rpyc.client import BaseDCCClient
from dcc_mcp_rpyc.client import ConnectionPool
from dcc_mcp_rpyc.client import close_all_connections
from dcc_mcp_rpyc.client import create_client
from dcc_mcp_rpyc.client import get_client
from dcc_mcp_rpyc.discovery import register_service
from dcc_mcp_rpyc.server import DCCServer


class TestBaseDCCClient:
    """Tests for the BaseDCCClient class."""

    def test_client_connect(self, dcc_rpyc_server: Tuple[DCCServer, int], temp_registry_path: str):
        """Test client connection.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server
            temp_registry_path: Fixture providing a temporary registry file path

        """
        _, port = dcc_rpyc_server
        client = None

        try:
            # Register the service
            register_service("test_dcc", "127.0.0.1", port, registry_path=temp_registry_path)

            # Create a client with explicit host and port
            client = BaseDCCClient("test_dcc", host="127.0.0.1", port=port, connection_timeout=5.0)

            # Test connection with retry
            max_retries = 3
            retry_delay = 0.5
            for i in range(max_retries):
                try:
                    assert client.is_connected(), "Client should be connected"
                    break
                except AssertionError:
                    if i == max_retries - 1:
                        raise
                    time.sleep(retry_delay)

            # Test client properties
            assert client.dcc_name == "test_dcc", "Client should have the correct DCC name"
            assert client.host == "127.0.0.1", "Client should have the correct host"
            assert client.port == port, "Client should have the correct port"

            # Test client methods
            result = client.call("echo", "test")
            assert result == "test", "Echo should return the input"

            result = client.call("add", 1, 2)
            assert result == 3, "Add should return the sum"
        finally:
            # Clean up
            if client and client.is_connected():
                client.disconnect()

    def test_client_auto_discovery(self, dcc_rpyc_server: Tuple[DCCServer, int], temp_registry_path: str):
        """Test client auto-discovery.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server
            temp_registry_path: Fixture providing a temporary registry file path

        """
        _, port = dcc_rpyc_server
        client = None

        try:
            # Register the service
            register_service("test_dcc", "127.0.0.1", port, registry_path=temp_registry_path)

            # Create a client with auto-discovery
            client = BaseDCCClient(
                dcc_name="test_dcc",
                host=None,  # Force auto-discovery
                port=None,  # Force auto-discovery
                registry_path=temp_registry_path,
                connection_timeout=5.0,
            )

            # Test connection with retry
            max_retries = 3
            retry_delay = 0.5
            for i in range(max_retries):
                try:
                    assert client.is_connected(), "Client should be connected"
                    break
                except AssertionError:
                    if i == max_retries - 1:
                        raise
                    time.sleep(retry_delay)
                    client.connect()

            # Verify the client found the correct service
            assert client.host == "127.0.0.1", "Client should have found the correct host"
            assert client.port == port, "Client should have found the correct port"

            # Test client methods
            result = client.echo("test")
            assert result == "test", "Echo should return the input"
        finally:
            # Clean up
            if client and client.is_connected():
                client.disconnect()

    def test_client_reconnect(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test client reconnection.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        _, port = dcc_rpyc_server
        client = None

        try:
            # Create a client
            client = BaseDCCClient("test_dcc", host="localhost", port=port, connection_timeout=5.0)

            # Test initial connection
            assert client.is_connected(), "Client should be connected"

            # Disconnect
            client.disconnect()
            assert not client.is_connected(), "Client should be disconnected"

            # Reconnect
            client.connect()

            # Test connection with retry
            max_retries = 3
            retry_delay = 0.5
            for i in range(max_retries):
                try:
                    assert client.is_connected(), "Client should be reconnected"
                    break
                except AssertionError:
                    if i == max_retries - 1:
                        raise
                    time.sleep(retry_delay)
                    client.connect()

            # Test client methods after reconnection
            result = client.echo("test_reconnect")
            assert result == "test_reconnect", "Echo should return the input after reconnection"
        finally:
            # Clean up
            if client and client.is_connected():
                client.disconnect()

    def test_client_with_context(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test client with context manager.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        _, port = dcc_rpyc_server

        # Test client as context manager
        with BaseDCCClient(
            "test_dcc", host="localhost", port=port, auto_connect=True, connection_timeout=5.0
        ) as client:
            # Test connection
            assert client.is_connected(), "Client should be connected inside context"

            # Test client methods
            result = client.echo("test_context")
            assert result == "test_context", "Echo should return the input inside context"

        # Verify the client was disconnected after the context
        assert not client.is_connected(), "Client should be disconnected after context"


class TestConnectionPool:
    """Tests for the ConnectionPool class."""

    def test_connection_pool(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test connection pool.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        _, port = dcc_rpyc_server
        pool = None

        try:
            # Create a connection pool
            pool = ConnectionPool()

            # Get a client from the pool
            client = pool.get_client("test_dcc", host="localhost", port=port, connection_timeout=5.0)
            assert client.is_connected(), "Client should be connected"

            # Test client methods
            result = client.echo("test_pool")
            assert result == "test_pool", "Echo should return the input"

            # Release the client back to the pool
            pool.release_client(client)

            # Get the same client again
            client2 = pool.get_client("test_dcc", host="localhost", port=port)
            assert client2 is client, "Should get the same client instance from the pool"
            assert client2.is_connected(), "Client should still be connected"
        finally:
            # Clean up
            if pool:
                pool.close_all()

    def test_global_connection_pool(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test global connection pool.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        _, port = dcc_rpyc_server

        try:
            # Get a client from the global pool
            client = get_client("test_dcc", host="localhost", port=port, connection_timeout=5.0)
            assert client.is_connected(), "Client should be connected"

            # Test client methods
            result = client.echo("test_global_pool")
            assert result == "test_global_pool", "Echo should return the input"
        finally:
            # Clean up
            close_all_connections()

    def test_create_client_function(self, dcc_rpyc_server: Tuple[DCCServer, int]):
        """Test the create_client function.

        Args:
        ----
            dcc_rpyc_server: Fixture providing a DCC RPYC server

        """
        _, port = dcc_rpyc_server
        client = None

        try:
            # Create a client
            client = create_client(dcc_name="test_dcc", host="localhost", port=port, connection_timeout=5.0)

            # Test connection
            assert client.is_connected(), "Client should be connected"

            # Test client methods
            result = client.echo("test_create_client")
            assert result == "test_create_client", "Echo should return the input"
        finally:
            # Clean up
            if client and client.is_connected():
                client.disconnect()
