"""Tests for dcc_mcp_ipc.utils.rpyc_utils module."""

# Import built-in modules
from unittest.mock import MagicMock

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.utils.rpyc_utils import deliver_parameters
from dcc_mcp_ipc.utils.rpyc_utils import execute_remote_command


class TestDeliverParameters:
    """Tests for the deliver_parameters function."""

    def test_empty_dict(self):
        result = deliver_parameters({})
        assert result == {}

    def test_simple_values(self):
        params = {"a": 1, "b": "hello", "c": [1, 2, 3]}
        result = deliver_parameters(params)
        assert result == params

    def test_nested_dict(self):
        params = {"nested": {"x": 1, "y": 2}}
        result = deliver_parameters(params)
        assert result["nested"] == {"x": 1, "y": 2}

    def test_none_values(self):
        params = {"key": None}
        result = deliver_parameters(params)
        assert result["key"] is None

    def test_returns_new_dict(self):
        params = {"a": 1}
        result = deliver_parameters(params)
        # Should return a new dict (not the same object)
        assert result is not params
        assert result == params

    def test_all_types(self):
        params = {
            "int": 42,
            "float": 3.14,
            "str": "text",
            "bool": True,
            "list": [1, 2],
            "dict": {"k": "v"},
            "none": None,
        }
        result = deliver_parameters(params)
        assert len(result) == len(params)
        for key in params:
            assert result[key] == params[key]


class TestExecuteRemoteCommand:
    """Tests for the execute_remote_command function."""

    def test_basic_call(self):
        mock_conn = MagicMock()
        mock_conn.exposed_ping.return_value = "pong"

        result = execute_remote_command(mock_conn, "exposed_ping")
        assert result == "pong"
        mock_conn.exposed_ping.assert_called_once()

    def test_call_with_args(self):
        mock_conn = MagicMock()
        mock_conn.exposed_add.return_value = 5

        result = execute_remote_command(mock_conn, "exposed_add", 2, 3)
        assert result == 5
        mock_conn.exposed_add.assert_called_once_with(2, 3)

    def test_call_with_kwargs(self):
        mock_conn = MagicMock()
        mock_conn.exposed_create.return_value = {"id": "obj1"}

        result = execute_remote_command(mock_conn, "exposed_create", name="sphere", radius=1.0)
        assert result == {"id": "obj1"}
        mock_conn.exposed_create.assert_called_once_with(name="sphere", radius=1.0)

    def test_call_with_args_and_kwargs(self):
        mock_conn = MagicMock()
        mock_conn.my_cmd.return_value = "ok"

        result = execute_remote_command(mock_conn, "my_cmd", 1, 2, extra="x")
        assert result == "ok"
        mock_conn.my_cmd.assert_called_once_with(1, 2, extra="x")

    def test_command_not_found_raises(self):
        """If the command doesn't exist on the connection, AttributeError is raised."""
        conn = object()  # plain object, no attributes
        with pytest.raises(AttributeError):
            execute_remote_command(conn, "nonexistent_command")

    def test_command_raises_propagates(self):
        mock_conn = MagicMock()
        mock_conn.bad_cmd.side_effect = RuntimeError("remote crash")

        with pytest.raises(RuntimeError, match="remote crash"):
            execute_remote_command(mock_conn, "bad_cmd")
