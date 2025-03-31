"""Dependency injection utilities for DCC-MCP-RPYC.

This module provides a simple dependency injection container and related utilities
to manage dependencies across the application.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Callable
from typing import Dict
from typing import Type
from typing import TypeVar
from typing import cast

# Configure logging
logger = logging.getLogger(__name__)

# Type variables
T = TypeVar("T")


class Container:
    """A simple dependency injection container.

    This container manages dependencies and their lifecycle, allowing for
    more flexible and testable code. It supports registering factory functions,
    singletons, and instances.

    Attributes
    ----------
        _factories: Dictionary mapping types to factory functions
        _singletons: Dictionary mapping types to singleton instances

    """

    def __init__(self):
        """Initialize the container."""
        self._factories: Dict[Type, Callable[..., Any]] = {}
        self._singletons: Dict[Type, Any] = {}

    def register_factory(self, interface_type: Type[T], factory: Callable[..., T]) -> None:
        """Register a factory function for a type.

        Args:
        ----
            interface_type: The type to register
            factory: A factory function that creates instances of the type

        """
        self._factories[interface_type] = factory
        logger.debug(f"Registered factory for {interface_type.__name__}")

    def register_singleton(self, interface_type: Type[T], factory: Callable[..., T]) -> None:
        """Register a singleton factory for a type.

        The factory will be called once, and the same instance will be returned
        for all subsequent requests.

        Args:
        ----
            interface_type: The type to register
            factory: A factory function that creates instances of the type

        """
        self._factories[interface_type] = factory
        # Mark this factory as a singleton by adding a None entry in the singletons dict
        # The actual instance will be created on first request
        self._singletons[interface_type] = None
        logger.debug(f"Registered singleton factory for {interface_type.__name__}")

    def register_instance(self, interface_type: Type[T], instance: T) -> None:
        """Register an existing instance for a type.

        Args:
        ----
            interface_type: The type to register
            instance: An instance of the type

        """
        self._singletons[interface_type] = instance
        logger.debug(f"Registered instance for {interface_type.__name__}")

    def resolve(self, interface_type: Type[T], *args, **kwargs) -> T:
        """Resolve a type to an instance.

        Args:
        ----
            interface_type: The type to resolve
            *args: Positional arguments to pass to the factory
            **kwargs: Keyword arguments to pass to the factory

        Returns:
        -------
            An instance of the requested type

        Raises:
        ------
            KeyError: If the type is not registered

        """
        # Check if this is a singleton type
        if interface_type in self._singletons:
            # If the singleton hasn't been created yet, create it now
            if self._singletons[interface_type] is None:
                factory = self._factories[interface_type]
                self._singletons[interface_type] = factory(*args, **kwargs)
                logger.debug(f"Created singleton instance of {interface_type.__name__}")

            return cast(T, self._singletons[interface_type])

        # Otherwise, use the factory to create a new instance
        if interface_type in self._factories:
            factory = self._factories[interface_type]
            return factory(*args, **kwargs)

        # If we get here, the type is not registered
        raise KeyError(f"No registration found for {interface_type.__name__}")


# Global container instance
_container = Container()


def get_container() -> Container:
    """Get the global container instance.

    Returns
    -------
        The global container instance

    """
    return _container


def register_factory(interface_type: Type[T], factory: Callable[..., T]) -> None:
    """Register a factory function for a type in the global container.

    Args:
    ----
        interface_type: The type to register
        factory: A factory function that creates instances of the type

    """
    _container.register_factory(interface_type, factory)


def register_singleton(interface_type: Type[T], factory: Callable[..., T]) -> None:
    """Register a singleton factory for a type in the global container.

    Args:
    ----
        interface_type: The type to register
        factory: A factory function that creates instances of the type

    """
    _container.register_singleton(interface_type, factory)


def register_instance(interface_type: Type[T], instance: T) -> None:
    """Register an existing instance for a type in the global container.

    Args:
    ----
        interface_type: The type to register
        instance: An instance of the type

    """
    _container.register_instance(interface_type, instance)


def resolve(interface_type: Type[T], *args, **kwargs) -> T:
    """Resolve a type to an instance from the global container.

    Args:
    ----
        interface_type: The type to resolve
        *args: Positional arguments to pass to the factory
        **kwargs: Keyword arguments to pass to the factory

    Returns:
    -------
        An instance of the requested type

    """
    return _container.resolve(interface_type, *args, **kwargs)
