"""Tests for the dependency injection container.

This module contains tests for the dependency injection container in utils/di.py.
"""

# Import built-in modules
import unittest

# Import local modules
from dcc_mcp_rpyc.utils.di import Container
from dcc_mcp_rpyc.utils.di import get_container
from dcc_mcp_rpyc.utils.di import register_factory
from dcc_mcp_rpyc.utils.di import register_instance
from dcc_mcp_rpyc.utils.di import register_singleton
from dcc_mcp_rpyc.utils.di import resolve


class TestContainer(unittest.TestCase):
    """Tests for the Container class."""

    def setUp(self):
        """Set up the test environment."""
        self.container = Container()

    def test_register_factory(self):
        """Test registering a factory function."""

        # Define a simple class
        class TestClass:
            def __init__(self, value=None):
                self.value = value

        # Register a factory function
        self.container.register_factory(TestClass, lambda value=None: TestClass(value))

        # Resolve the type
        instance1 = self.container.resolve(TestClass)
        instance2 = self.container.resolve(TestClass, value="test")

        # Check that we got different instances
        self.assertIsInstance(instance1, TestClass)
        self.assertIsInstance(instance2, TestClass)
        self.assertIsNot(instance1, instance2)
        self.assertIsNone(instance1.value)
        self.assertEqual(instance2.value, "test")

    def test_register_singleton(self):
        """Test registering a singleton factory function."""

        # Define a simple class
        class TestClass:
            def __init__(self, value=None):
                self.value = value

        # Register a singleton factory function
        self.container.register_singleton(TestClass, lambda value=None: TestClass(value))

        # Resolve the type multiple times
        instance1 = self.container.resolve(TestClass)
        instance2 = self.container.resolve(TestClass)

        # Check that we got the same instance
        self.assertIsInstance(instance1, TestClass)
        self.assertIsInstance(instance2, TestClass)
        self.assertIs(instance1, instance2)

        # Check that arguments to resolve are ignored for singletons after first resolution
        instance3 = self.container.resolve(TestClass, value="test")
        self.assertIs(instance1, instance3)
        self.assertIsNone(instance3.value)  # Value is still None because it's the same instance

    def test_register_instance(self):
        """Test registering an existing instance."""

        # Define a simple class
        class TestClass:
            def __init__(self, value=None):
                self.value = value

        # Create an instance
        original = TestClass("original")

        # Register the instance
        self.container.register_instance(TestClass, original)

        # Resolve the type
        instance = self.container.resolve(TestClass)

        # Check that we got the same instance
        self.assertIsInstance(instance, TestClass)
        self.assertIs(instance, original)
        self.assertEqual(instance.value, "original")

    def test_resolve_unregistered(self):
        """Test resolving an unregistered type."""

        # Define a simple class
        class TestClass:
            pass

        # Try to resolve the unregistered type
        with self.assertRaises(KeyError):
            self.container.resolve(TestClass)


def test_global_container():
    """Test the global container functions."""

    # Define a simple class
    class TestClass:
        def __init__(self, value=None):
            self.value = value

    # Get the global container
    get_container()

    # Register a factory function
    register_factory(TestClass, lambda value=None: TestClass(value))

    # Resolve the type
    instance1 = resolve(TestClass)
    instance2 = resolve(TestClass, value="test")

    # Check that we got different instances
    assert isinstance(instance1, TestClass)
    assert isinstance(instance2, TestClass)
    assert instance1 is not instance2
    assert instance1.value is None
    assert instance2.value == "test"


def test_global_singleton():
    """Test the global singleton registration."""

    # Define a simple class
    class TestClass:
        def __init__(self, value=None):
            self.value = value

    # Register a singleton factory function
    register_singleton(TestClass, lambda value=None: TestClass(value))

    # Resolve the type multiple times
    instance1 = resolve(TestClass)
    instance2 = resolve(TestClass)

    # Check that we got the same instance
    assert isinstance(instance1, TestClass)
    assert isinstance(instance2, TestClass)
    assert instance1 is instance2


def test_global_instance():
    """Test the global instance registration."""

    # Define a simple class
    class TestClass:
        def __init__(self, value=None):
            self.value = value

    # Create an instance
    original = TestClass("original")

    # Register the instance
    register_instance(TestClass, original)

    # Resolve the type
    instance = resolve(TestClass)

    # Check that we got the same instance
    assert isinstance(instance, TestClass)
    assert instance is original
    assert instance.value == "original"


def test_complex_dependency_chain():
    """Test a more complex dependency chain."""

    # Define some classes with dependencies
    class Database:
        def __init__(self, connection_string):
            self.connection_string = connection_string

    class Repository:
        def __init__(self, database):
            self.database = database

    class Service:
        def __init__(self, repository, logger=None):
            self.repository = repository
            self.logger = logger

    # Register the dependencies
    container = Container()
    container.register_singleton(Database, lambda: Database("test_connection"))
    container.register_factory(Repository, lambda: Repository(container.resolve(Database)))
    container.register_factory(Service, lambda logger=None: Service(container.resolve(Repository), logger))

    # Resolve the service
    service = container.resolve(Service)
    service_with_logger = container.resolve(Service, logger="test_logger")

    # Check the dependency chain
    assert isinstance(service, Service)
    assert isinstance(service.repository, Repository)
    assert isinstance(service.repository.database, Database)
    assert service.repository.database.connection_string == "test_connection"
    assert service.logger is None

    # Check that we got a new service instance with the logger
    assert isinstance(service_with_logger, Service)
    assert service_with_logger is not service
    assert service_with_logger.logger == "test_logger"

    # But they should share the same database instance
    assert service_with_logger.repository.database is service.repository.database
