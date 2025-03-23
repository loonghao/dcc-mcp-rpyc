"""Tests for server module functions and decorators.

This module contains tests for the functions and decorators in the server module
that are currently lacking coverage.
"""

# Import built-in modules
from typing import Any
from typing import Dict
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest
from rpyc.utils.server import ThreadedServer

# Import local modules
from dcc_mcp_rpyc.server import BaseRPyCService
from dcc_mcp_rpyc.server import DCCRPyCService
from dcc_mcp_rpyc.server import DCCServer
from dcc_mcp_rpyc.server import cleanup_server
from dcc_mcp_rpyc.server import create_dcc_server
from dcc_mcp_rpyc.server import create_raw_threaded_server
from dcc_mcp_rpyc.server import register_dcc_service
from dcc_mcp_rpyc.server import unregister_dcc_service


# Create a concrete implementation of DCCRPyCService for testing
class TestDCCService(DCCRPyCService):
    """Test implementation of DCCRPyCService."""

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current scene.

        Returns
        -------
            Dict with scene information

        """
        return {"scene": "test_scene", "objects": ["obj1", "obj2"]}

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session.

        Returns
        -------
            Dict with session information

        """
        return {"session": "test_session", "user": "test_user"}

    def test_function(self) -> str:
        """Test function for decorator testing.

        Returns
        -------
            Test result

        """
        return "test_result"

    def test_dict_function(self) -> Dict[str, Any]:
        """Test function returning a dict for decorator testing.

        Returns
        -------
            Test result dict

        """
        return {"result": "test_dict_result"}

    def test_model_function(self) -> Dict[str, Any]:
        """Test function returning a model-like dict for decorator testing.

        Returns
        -------
            Test model-like dict

        """

        # Simulate a model with a dict method
        class FakeModel:
            def dict(self):
                return {"model_result": "test_model_result"}

        return FakeModel()

    def test_error_function(self) -> None:
        """Test function that raises an error for decorator testing.

        Raises
        ------
            ValueError: Always raised for testing

        """
        raise ValueError("Test error")


@pytest.fixture
def test_dcc_service():
    """Fixture to provide a TestDCCService instance."""
    return TestDCCService()


class TestServerFunctions:
    """Tests for server module functions."""

    def test_with_scene_info_decorator(self, test_dcc_service):
        """Test the with_scene_info decorator."""
        # Use fixture to get TestDCCService instance
        service = test_dcc_service

        # Test with simple return value
        decorated_func = DCCRPyCService.with_scene_info(TestDCCService.test_function)
        result = decorated_func(service)

        assert "result" in result
        assert result["result"] == "test_result"
        assert "scene_info" in result
        assert result["scene_info"] == service.get_scene_info()

        # Test with dict return value
        decorated_func = DCCRPyCService.with_scene_info(TestDCCService.test_dict_function)
        result = decorated_func(service)

        assert "result" in result
        assert result["result"] == "test_dict_result"
        assert "scene_info" in result

        # Test with model-like return value
        decorated_func = DCCRPyCService.with_scene_info(TestDCCService.test_model_function)
        result = decorated_func(service)

        assert "model_result" in result
        assert result["model_result"] == "test_model_result"
        assert "scene_info" in result

        # Test with error
        decorated_func = DCCRPyCService.with_scene_info(TestDCCService.test_error_function)
        with pytest.raises(ValueError):
            decorated_func(service)

    def test_with_session_info_decorator(self, test_dcc_service):
        """Test the with_session_info decorator."""
        # Use fixture to get TestDCCService instance
        service = test_dcc_service

        # Test with simple return value
        decorated_func = DCCRPyCService.with_session_info(TestDCCService.test_function)
        result = decorated_func(service)

        assert "result" in result
        assert result["result"] == "test_result"
        assert "session_info" in result
        assert result["session_info"] == service.get_session_info()

        # Test with dict return value
        decorated_func = DCCRPyCService.with_session_info(TestDCCService.test_dict_function)
        result = decorated_func(service)

        assert "result" in result
        assert result["result"] == "test_dict_result"
        assert "session_info" in result

        # Test with model-like return value
        decorated_func = DCCRPyCService.with_session_info(TestDCCService.test_model_function)
        result = decorated_func(service)

        assert "model_result" in result
        assert result["model_result"] == "test_model_result"
        assert "session_info" in result

        # Test with error
        decorated_func = DCCRPyCService.with_session_info(TestDCCService.test_error_function)
        with pytest.raises(ValueError):
            decorated_func(service)

    def test_create_raw_threaded_server(self):
        """Test the create_raw_threaded_server function."""
        with patch("dcc_mcp_rpyc.server.ThreadedServer") as mock_server:
            # Test with default parameters
            _ = create_raw_threaded_server(BaseRPyCService)
            mock_server.assert_called_once()
            args, kwargs = mock_server.call_args
            assert args[0] == BaseRPyCService  # service

            # Reset mock
            mock_server.reset_mock()

            # Test with custom parameters
            _ = create_raw_threaded_server(
                BaseRPyCService,
                hostname="127.0.0.1",
                port=12345,
                protocol_config={"allow_all_attrs": True},
                timeout=30.0,
            )
            mock_server.assert_called_once()
            args, kwargs = mock_server.call_args
            assert args[0] == BaseRPyCService  # service
            assert kwargs["hostname"] == "127.0.0.1"
            assert kwargs["port"] == 12345
            assert "allow_all_attrs" in kwargs["protocol_config"]

    def test_create_dcc_server(self):
        """Test the create_dcc_server function."""
        with patch("dcc_mcp_rpyc.server.DCCServer") as mock_dcc_server:
            # Test with default parameters
            _ = create_dcc_server("test_dcc")
            mock_dcc_server.assert_called_once()
            assert mock_dcc_server.call_args[0][0] == "test_dcc"

            # Reset mock
            mock_dcc_server.reset_mock()

            # Test with custom parameters
            _ = create_dcc_server(
                "test_dcc",
                service_class=TestDCCService,
                host="127.0.0.1",
                port=12345,
            )
            mock_dcc_server.assert_called_once()
            args, kwargs = mock_dcc_server.call_args
            assert args[0] == "test_dcc"  # dcc_name is first position argument
            assert kwargs["service_class"] == TestDCCService
            assert kwargs["host"] == "127.0.0.1"
            assert kwargs["port"] == 12345

    def test_register_dcc_service(self, temp_registry_path):
        """Test the register_dcc_service function.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        with patch("dcc_mcp_rpyc.server.discovery.register_service") as mock_register:
            mock_register.return_value = temp_registry_path

            # Test registration
            result = register_dcc_service("test_dcc", "127.0.0.1", 12345)

            mock_register.assert_called_once()
            call_args = mock_register.call_args[0]
            assert call_args[0] == "test_dcc"
            assert call_args[1] == "127.0.0.1"
            assert call_args[2] == 12345

            assert result == temp_registry_path

    def test_unregister_dcc_service(self, temp_registry_path):
        """Test the unregister_dcc_service function.

        Args:
        ----
            temp_registry_path: Fixture providing a temporary registry file path

        """
        with patch("dcc_mcp_rpyc.server.discovery.unregister_service") as mock_unregister, patch(
            "dcc_mcp_rpyc.server.os.path.exists"
        ) as mock_exists, patch("dcc_mcp_rpyc.server._load_registry_file") as mock_load:
            mock_unregister.return_value = True
            mock_exists.return_value = True
            mock_load.return_value = {"test_dcc": {"host": "localhost", "port": 12345}}

            # Test with registry file path
            result = unregister_dcc_service(registry_file=temp_registry_path)

            mock_exists.assert_called_once_with(temp_registry_path)
            mock_load.assert_called_once_with(temp_registry_path)
            mock_unregister.assert_called_once_with("test_dcc", registry_path=None)
            assert result is True

            # Reset mock objects
            mock_unregister.reset_mock()
            mock_exists.reset_mock()
            mock_load.reset_mock()

            result = unregister_dcc_service()

            mock_unregister.assert_called_once_with("unknown_dcc", registry_path=None)
            assert result is True

    def test_cleanup_server(self):
        """Test the cleanup_server function."""
        # Create mock server
        mock_server = MagicMock(spec=ThreadedServer)
        mock_server.clients = []

        # Test with server and registry file
        with patch("dcc_mcp_rpyc.server.unregister_dcc_service") as mock_unregister, patch(
            "threading.Thread"
        ) as mock_thread:
            mock_unregister.return_value = True
            mock_thread_instance = MagicMock()
            mock_thread_instance.is_alive.return_value = False
            mock_thread.return_value = mock_thread_instance

            result = cleanup_server(mock_server, "test_registry_file.json")

            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
            mock_thread_instance.join.assert_called_once()
            mock_unregister.assert_called_once_with("test_registry_file.json")
            assert result is True

        # Test with server but no registry file
        mock_server.reset_mock()
        with patch("threading.Thread") as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread_instance.is_alive.return_value = False
            mock_thread.return_value = mock_thread_instance

            result = cleanup_server(mock_server, None)

            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
            mock_thread_instance.join.assert_called_once()
            assert result is True

        # Test with no server but registry file
        with patch("dcc_mcp_rpyc.server.unregister_dcc_service") as mock_unregister:
            mock_unregister.return_value = True

            result = cleanup_server(None, "test_registry_file.json")

            mock_unregister.assert_called_once_with("test_registry_file.json")
            assert result is True

        # Test with no server and no registry file
        result = cleanup_server(None, None)

        assert result is True

        # Test with server close raising exception using custom server_closer
        mock_server = MagicMock(spec=ThreadedServer)
        mock_closer = MagicMock(side_effect=Exception("Test error"))

        result = cleanup_server(mock_server, None, server_closer=mock_closer)

        mock_closer.assert_called_once_with(mock_server)
        assert result is False


class TestDCCServerClass:
    """Tests for the DCCServer class."""

    def test_dcc_server_init(self):
        """Test the DCCServer initialization."""
        # Test with default parameters
        server = DCCServer("test_dcc")
        assert server.dcc_name == "test_dcc"
        assert server.service_class == BaseRPyCService
        assert server.host == "localhost"
        assert server.port == 0
        assert server.server is None
        assert server.running is False
        assert server.registry_file is None

        # Test with custom parameters
        server = DCCServer(
            "test_dcc",
            service_class=TestDCCService,
            host="127.0.0.1",
            port=12345,
        )
        assert server.dcc_name == "test_dcc"
        assert server.service_class == TestDCCService
        assert server.host == "127.0.0.1"
        assert server.port == 12345

    def test_dcc_server_start(self):
        """Test the DCCServer start method."""
        with patch("dcc_mcp_rpyc.server.create_raw_threaded_server") as mock_create:
            mock_server = MagicMock()
            mock_server.port = 12345
            mock_create.return_value = mock_server

            # Create server
            server = DCCServer("test_dcc")

            with patch("dcc_mcp_rpyc.server.register_dcc_service") as mock_register:
                mock_register.return_value = "test_registry_file.json"

                # Call start method
                result = server.start(threaded=True)

                mock_create.assert_called_once()
                mock_register.assert_called_once_with(dcc_name="test_dcc", host="localhost", port=12345)
                assert server.registry_file == "test_registry_file.json"
                assert result == 12345
                assert server.running is True

    def test_dcc_server_stop(self):
        """Test the DCCServer stop method."""
        with patch("dcc_mcp_rpyc.server.create_raw_threaded_server") as mock_create:
            mock_server = MagicMock()
            mock_create.return_value = mock_server

            # Create server
            server = DCCServer("test_dcc")
            server.server = mock_server
            server.running = True
            server.registry_file = "test_registry_file.json"

            with patch("dcc_mcp_rpyc.server.unregister_dcc_service") as mock_unregister, patch(
                "os.path.exists"
            ) as mock_exists:
                mock_unregister.return_value = True
                mock_exists.return_value = True  # Mock file exists

                # Call stop method
                result = server.stop()

                mock_unregister.assert_called_once_with(registry_file="test_registry_file.json")
                mock_server.close.assert_called_once()
                assert result is True
                assert server.running is False
                assert server.registry_file is None
                assert server.server is None

    def test_dcc_server_is_running(self):
        """Test the DCCServer is_running method."""
        with patch("dcc_mcp_rpyc.server.create_raw_threaded_server") as mock_create:
            mock_server = MagicMock()
            mock_create.return_value = mock_server

            # Create server
            server = DCCServer("test_dcc")

            # Test not running
            assert not server.is_running()

            server.running = True
            server.server = mock_server  # Set server attribute
            assert server.is_running()
