"""Tests for specific methods in the DCCAdapter class.

This module contains tests for the methods that are currently lacking coverage
in the DCCAdapter class.
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
from dcc_mcp_core.models import ActionResultModel

# Import local modules
from dcc_mcp_rpyc.adapter import DCCAdapter


# Create a concrete implementation of DCCAdapter for testing specific methods
class MethodTestDCCAdapter(DCCAdapter):
    """Test implementation of DCCAdapter for testing specific methods."""

    def __init__(self, dcc_name: str = "test_dcc"):
        """Initialize the MethodTestDCCAdapter.

        Args:
        ----
            dcc_name: Name of the DCC application

        """
        # Initialize attributes before calling parent constructor
        self.mock_client = MagicMock()
        self.mock_client.is_connected.return_value = True
        self.mock_client.root = MagicMock()

        # Call parent constructor
        super().__init__(dcc_name)

    def _initialize_client(self) -> None:
        """Initialize the client for communicating with the DCC application."""
        self.client = self.mock_client

    def _initialize_action_paths(self) -> None:
        """Initialize the paths to search for actions."""
        self.action_paths = ["test/actions/path"]


class TestAdapterMethods:
    """Tests for specific methods in the DCCAdapter class."""

    def test_create_action_manager(self):
        """Test the _create_action_manager method."""
        adapter = MethodTestDCCAdapter()

        # Test with successful import from dcc_mcp_core
        mock_creator = MagicMock()
        mock_manager = MagicMock()
        mock_creator.return_value = mock_manager

        result = adapter._create_action_manager("test_dcc", action_manager_creator=mock_creator)

        assert result == mock_manager
        mock_creator.assert_called_once_with("test_dcc")

        # Test with ImportError, using dependency injection instead of side_effect
        mock_creator = MagicMock(side_effect=ImportError())
        mock_fallback = MagicMock()
        mock_manager = MagicMock()
        mock_fallback.return_value = mock_manager

        result = adapter._create_action_manager(
            "test_dcc", action_manager_creator=mock_creator, fallback_manager_getter=mock_fallback
        )

        assert result == mock_manager
        mock_creator.assert_called_once_with("test_dcc")
        mock_fallback.assert_called_once_with("test_dcc")

    def test_get_action_manager(self):
        """Test the _get_action_manager method."""
        adapter = MethodTestDCCAdapter()

        # Test with successful import from dcc_mcp_core
        mock_getter = MagicMock()
        mock_manager = MagicMock()
        mock_getter.return_value = mock_manager

        result = adapter._get_action_manager("test_dcc", action_manager_getter=mock_getter)

        assert result == mock_manager
        mock_getter.assert_called_once_with("test_dcc")

        # Test with ImportError
        mock_getter = MagicMock(side_effect=ImportError())

        result = adapter._get_action_manager("test_dcc", action_manager_getter=mock_getter)

        assert result is None
        mock_getter.assert_called_once_with("test_dcc")

    def test_call_action_function(self):
        """Test the _call_action_function method."""
        adapter = MethodTestDCCAdapter()

        # Set up mock action manager
        mock_manager = MagicMock()
        adapter.action_manager = mock_manager

        # Test with action manager having call_function method
        mock_manager.call_function.return_value = {"result": "success"}

        result = adapter._call_action_function(
            "test_dcc", "test_action", "test_function", {"context": "data"}, "arg1", kwarg1="value1"
        )

        mock_manager.call_function.assert_called_once_with(
            "test_action", "test_function", {"context": "data"}, "arg1", kwarg1="value1"
        )
        assert result == {"result": "success"}

        # Test with action manager not having call_function method
        delattr(mock_manager, "call_function")
        adapter.client.root.call_action_function.return_value = {"result": "success"}

        result = adapter._call_action_function(
            "test_dcc", "test_action", "test_function", {"context": "data"}, "arg1", kwarg1="value1"
        )

        adapter.client.root.call_action_function.assert_called_once_with(
            "test_action", "test_function", {"context": "data"}, "arg1", kwarg1="value1"
        )
        assert result == {"result": "success"}

        # Test with action manager being None
        adapter.action_manager = None
        adapter.client.root.call_action_function.reset_mock()
        adapter.client.root.call_action_function.return_value = {"result": "success"}

        result = adapter._call_action_function(
            "test_dcc", "test_action", "test_function", {"context": "data"}, "arg1", kwarg1="value1"
        )

        # Should have created a new action manager
        assert adapter.action_manager is not None

        # Test with exception
        adapter.action_manager = mock_manager
        mock_manager.call_function = MagicMock(side_effect=ValueError("Test error"))

        result = adapter._call_action_function(
            "test_dcc", "test_action", "test_function", {"context": "data"}, "arg1", kwarg1="value1"
        )

        assert result.get("success") is False
        assert "Test error" in result.get("error", "")

    def test_call_action_function_wrapper(self):
        """Test the call_action_function method (wrapper)."""
        adapter = MethodTestDCCAdapter()

        # Test with successful execution
        with patch.object(adapter, "_call_action_function") as mock_call:
            # Return a dict that looks like an ActionResultModel
            mock_call.return_value = {"success": True, "message": "Success message", "context": {"data": "value"}}

            with patch.object(adapter, "get_session_info") as mock_session:
                mock_session.return_value = {"success": True, "context": {"session": "info"}}

                result = adapter.call_action_function(
                    "test_action", "test_function", {"context": "data"}, "arg1", kwarg1="value1"
                )

                mock_call.assert_called_once_with(
                    adapter.dcc_name, "test_action", "test_function", {"context": "data"}, "arg1", kwarg1="value1"
                )

                assert result.get("success") is True
                assert result.get("message") == "Success message"
                assert "function_result" in result.get("context", {})
                assert "session_info" in result.get("context", {})

        # Test with ActionResultModel return value
        with patch.object(adapter, "_call_action_function") as mock_call:
            # Return an ActionResultModel
            action_result = ActionResultModel(
                success=True, message="Model success", prompt="Next steps", context={"model": "data"}
            )
            mock_call.return_value = action_result

            with patch.object(adapter, "get_session_info") as mock_session:
                mock_session.return_value = {"success": True, "context": {"session": "info"}}

                result = adapter.call_action_function(
                    "test_action", "test_function", {"context": "data"}, "arg1", kwarg1="value1"
                )

                assert result.get("success") is True
                assert result.get("message") == "Model success"
                assert result.get("prompt") == "Next steps"
                assert "function_result" in result.get("context", {})
                assert "session_info" in result.get("context", {})

        # Test with non-dict, non-ActionResultModel return value
        with patch.object(adapter, "_call_action_function") as mock_call:
            # Return a simple value
            mock_call.return_value = "simple string result"

            with patch.object(adapter, "get_session_info") as mock_session:
                mock_session.return_value = {"success": True, "context": {"session": "info"}}

                result = adapter.call_action_function(
                    "test_action", "test_function", {"context": "data"}, "arg1", kwarg1="value1"
                )

                assert result.get("success") is True
                assert "Successfully executed test_action.test_function" == result.get("message", "")
                assert "function_result" in result.get("context", {})
                assert "raw_result" in result.get("context", {}).get("function_result", {})

        # Test with exception
        with patch.object(adapter, "ensure_connected", side_effect=ValueError("Connection error")):
            result = adapter.call_action_function(
                "test_action", "test_function", {"context": "data"}, "arg1", kwarg1="value1"
            )

            assert result.get("success") is False
            assert "Failed to execute" in result.get("message", "")
            assert "Connection error" in result.get("error", "")
