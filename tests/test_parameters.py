"""Tests for the parameters module.

This module tests the parameter processing functionality specific to RPyC.
"""

# Import built-in modules
import unittest
from unittest import mock

# Import third-party modules
import pytest
import rpyc

# Import local modules
from dcc_mcp_rpyc.parameters import deliver_parameters
from dcc_mcp_rpyc.parameters import execute_remote_command
from dcc_mcp_rpyc.parameters import process_rpyc_parameters


class TestDeliverParameters:
    """Test the deliver_parameters function."""

    def test_deliver_basic_types(self):
        """Test delivering basic types."""
        # Test with basic types
        params = {
            "int_value": 42,
            "float_value": 3.14,
            "str_value": "hello",
            "bool_value": True,
            "none_value": None,
        }
        result = deliver_parameters(params)
        assert result == params

    def test_deliver_with_mock_netref(self):
        """Test delivering a mock NetRef."""
        # Create a mock NetRef
        mock_netref = mock.MagicMock(spec=rpyc.core.netref.BaseNetref)
        mock_netref.__class__.__name__ = "NetrefClass"

        # Set up the mock to return a specific value when delivered
        with mock.patch("rpyc.utils.classic.deliver", return_value=True):
            params = {"netref_value": mock_netref}
            result = deliver_parameters(params)
            assert result["netref_value"] is True


class TestProcessRPyCParameters:
    """Test the process_rpyc_parameters function."""

    def test_process_dict_params(self):
        """Test processing dictionary parameters."""
        params = {
            "int_value": 42,
            "float_value": 3.14,
            "str_value": "hello",
            "bool_value": True,
            "none_value": None,
        }
        result = process_rpyc_parameters(params)
        assert result == params

    def test_process_string_params(self):
        """Test processing string parameters."""
        params_str = '{"int_value": 42, "bool_value": true}'
        result = process_rpyc_parameters(params_str)
        assert result == {"int_value": 42, "bool_value": True}


class TestExecuteRemoteCommand:
    """Test the execute_remote_command function."""

    def test_execute_command(self):
        """Test executing a command."""
        # Create a mock connection
        mock_connection = mock.MagicMock()
        mock_cmd = mock.MagicMock()
        mock_connection.__getattr__.return_value = mock_cmd

        # Execute a command
        execute_remote_command(mock_connection, "test_command", 1, 2, key1="value1", key2=True)

        # Check that the command was called with the right arguments
        mock_connection.__getattr__.assert_called_once_with("test_command")
        mock_cmd.assert_called_once()
        args, kwargs = mock_cmd.call_args
        assert args == (1, 2)
        assert kwargs == {"key1": "value1", "key2": True}

    def test_execute_command_with_netref(self):
        """Test executing a command with a NetRef argument."""
        # Create a mock connection and command
        mock_connection = mock.MagicMock()
        mock_cmd = mock.MagicMock()
        mock_connection.__getattr__.return_value = mock_cmd

        # Create a mock NetRef
        mock_netref = mock.MagicMock(spec=rpyc.core.netref.BaseNetref)
        mock_netref.__class__.__name__ = "NetrefClass"

        # Set up the mock to return a specific value when delivered
        with mock.patch("rpyc.utils.classic.deliver", return_value=True):
            # Execute a command with a NetRef argument
            execute_remote_command(mock_connection, "test_command", mock_netref, key=mock_netref)

            # Check that the command was called with the delivered values
            mock_cmd.assert_called_once()
            args, kwargs = mock_cmd.call_args
            assert args == (True,)
            assert kwargs == {"key": True}
