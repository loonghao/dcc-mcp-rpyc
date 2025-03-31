"""Basic tests for the server module.

This module contains basic tests for the server.py module.
"""

# Import built-in modules
from unittest import mock

# Import third-party modules
import rpyc
from rpyc.core import service

# Import local modules
from dcc_mcp_rpyc.server import BaseRPyCService
from dcc_mcp_rpyc.server import DCCServer
from dcc_mcp_rpyc.server import create_service_factory
from dcc_mcp_rpyc.server import create_shared_service_instance


class TestBaseRPyCService:
    """Tests for the BaseRPyCService class."""

    def test_init(self):
        """Test initialization of BaseRPyCService."""
        # Create a service instance
        service_instance = BaseRPyCService()
        # Just verify it can be instantiated without errors
        assert isinstance(service_instance, BaseRPyCService)
        # Verify it inherits from rpyc.SlaveService
        assert isinstance(service_instance, rpyc.SlaveService)


class TestDCCServerClass:
    """Tests for the DCCServer class."""

    def test_init(self):
        """Test initialization of DCCServer."""
        # Create a server instance
        server = DCCServer(
            dcc_name="test_dcc",
            service_class=BaseRPyCService,  # Use the class directly, not an instance
            host="127.0.0.1",
            port=12345,
        )

        # Verify the server was initialized correctly
        assert server.dcc_name == "test_dcc"
        assert issubclass(server.service_class, service.Service)
        assert server.host == "127.0.0.1"
        assert server.port == 12345
        assert server.server is None
        assert not server.running
        # Check that server.lock is a lock object, not specifically an RLock
        assert hasattr(server.lock, "acquire")
        assert hasattr(server.lock, "release")
        assert server.registry_file is None
        assert isinstance(server.clients, list)


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
