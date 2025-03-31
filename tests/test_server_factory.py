"""Tests for the server factory functions.

This module contains tests for the service factory functions in the server.py module.
"""

# Import built-in modules
from unittest import mock

# Import local modules
from dcc_mcp_rpyc.server import BaseRPyCService
from dcc_mcp_rpyc.server import create_service_factory
from dcc_mcp_rpyc.server import create_shared_service_instance


class TestBaseRPyCService:
    """Tests for the BaseRPyCService class."""

    def test_init(self):
        """Test initialization of BaseRPyCService."""
        # Create a service instance
        service = BaseRPyCService()
        # Just verify it can be instantiated without errors
        assert isinstance(service, BaseRPyCService)

    def test_on_connect(self):
        """Test on_connect method with mocked connection."""
        # Create a service instance
        service = BaseRPyCService()

        # Create a mock connection with proper structure
        conn = mock.MagicMock()
        conn._channel = mock.MagicMock()
        conn._channel.stream = mock.MagicMock()
        conn._channel.stream.sock = mock.MagicMock()
        conn._channel.stream.sock.getpeername = mock.MagicMock(return_value=("127.0.0.1", 12345))

        # Call on_connect - it should log the connection but not raise exceptions
        service.on_connect(conn)

    def test_on_disconnect(self):
        """Test on_disconnect method with mocked connection."""
        # Create a service instance
        service = BaseRPyCService()

        # Create a mock connection
        conn = mock.MagicMock()

        # Call on_disconnect - it should log the disconnection but not raise exceptions
        service.on_disconnect(conn)


class TestServiceFactoryFunctions:
    """Tests for the service factory functions."""

    def test_create_service_factory(self):
        """Test create_service_factory function."""
        # Create a service factory
        factory = create_service_factory(BaseRPyCService)

        # Verify the factory is callable
        assert callable(factory)

        # Create a mock connection
        conn = mock.MagicMock()

        # Create a service instance using the factory
        service_instance = factory(conn)

        # Verify the service instance was created correctly
        assert isinstance(service_instance, BaseRPyCService)

    def test_create_shared_service_instance(self):
        """Test create_shared_service_instance function."""
        # Create a shared service instance
        shared_instance = create_shared_service_instance(BaseRPyCService)

        # Verify the shared instance is callable
        assert callable(shared_instance)

        # Create mock connections
        conn1 = mock.MagicMock()
        conn2 = mock.MagicMock()

        # Create service instances using the shared instance
        service_instance1 = shared_instance(conn1)
        service_instance2 = shared_instance(conn2)

        # Verify the service instances are the same object
        assert service_instance1 is service_instance2

        # Verify the service instance was created correctly
        assert isinstance(service_instance1, BaseRPyCService)
