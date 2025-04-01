"""Factory for creating service discovery strategies.

This module provides a factory for creating and managing different service discovery strategies.
"""

# Import built-in modules
import logging
from typing import Dict
from typing import Optional

# Import local modules
from dcc_mcp_rpyc.discovery.base import ServiceDiscoveryStrategy
from dcc_mcp_rpyc.discovery.file_strategy import FileDiscoveryStrategy
from dcc_mcp_rpyc.discovery.zeroconf_strategy import ZEROCONF_AVAILABLE
from dcc_mcp_rpyc.discovery.zeroconf_strategy import ZeroConfDiscoveryStrategy

# Configure logging
logger = logging.getLogger(__name__)


class ServiceDiscoveryFactory:
    """Factory for creating service discovery strategies.

    This class follows the singleton pattern to ensure a single factory instance
    is used throughout the application.
    """

    _instance = None
    _logger = logging.getLogger(__name__)

    def __new__(cls):
        """Ensure only one instance of ServiceDiscoveryFactory exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._strategies = {}
            cls._instance._strategy_classes = {
                "file": FileDiscoveryStrategy,
                "zeroconf": ZeroConfDiscoveryStrategy if ZEROCONF_AVAILABLE else None,
            }
            cls._logger.debug("Created new ServiceDiscoveryFactory instance")
        return cls._instance

    @classmethod
    def _reset_instance(cls):
        """Reset the singleton instance.

        This method is primarily used for testing purposes.
        """
        cls._instance = None
        cls._logger.debug("Reset ServiceDiscoveryFactory singleton instance")

    def get_strategy(self, strategy_type: str, **kwargs) -> Optional[ServiceDiscoveryStrategy]:
        """Get a service discovery strategy instance.

        Args:
            strategy_type: Type of strategy to get ('file' or 'zeroconf')
            **kwargs: Additional arguments to pass to the strategy constructor

        Returns:
            The strategy instance or None if not available

        Raises:
            ValueError: If the strategy type is not supported

        """
        # Check if strategy type is supported
        if strategy_type not in self._strategy_classes:
            raise ValueError(f"Strategy type '{strategy_type}' is not supported")

        # Check if strategy class is available
        strategy_class = self._strategy_classes[strategy_type]
        if strategy_class is None:
            logger.warning(f"Strategy type '{strategy_type}' is not available")
            return None

        # Check if strategy instance already exists
        if strategy_type in self._strategies:
            return self._strategies[strategy_type]

        # Create new strategy instance
        try:
            strategy = strategy_class(**kwargs)
            self._strategies[strategy_type] = strategy
            return strategy
        except Exception as e:
            logger.error(f"Error creating strategy '{strategy_type}': {e}")
            return None

    def list_available_strategies(self) -> Dict[str, bool]:
        """List all available strategy types.

        Returns:
            Dictionary mapping strategy types to availability status

        """
        return {
            strategy_type: strategy_class is not None
            for strategy_type, strategy_class in self._strategy_classes.items()
        }
