"""Tests for dcc_mcp_ipc.utils.errors module."""

# Import built-in modules
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.utils.errors import ActionError
from dcc_mcp_ipc.utils.errors import ConnectionError
from dcc_mcp_ipc.utils.errors import DCCMCPError
from dcc_mcp_ipc.utils.errors import ExecutionError
from dcc_mcp_ipc.utils.errors import ServiceNotFoundError
from dcc_mcp_ipc.utils.errors import handle_error


class TestDCCMCPError:
    """Tests for the DCCMCPError base exception class."""

    def test_basic_init(self):
        err = DCCMCPError("something went wrong")
        assert err.message == "something went wrong"
        assert err.error_code == "RPYC_ERROR"
        assert err.details == {}
        assert err.cause is None
        assert "RPYC_ERROR" in str(err)
        assert "something went wrong" in str(err)

    def test_init_with_error_code(self):
        err = DCCMCPError("bad", error_code="MY_CODE")
        assert err.error_code == "MY_CODE"
        assert "MY_CODE" in str(err)

    def test_init_with_details(self):
        err = DCCMCPError("bad", details={"key": "value"})
        assert err.details == {"key": "value"}

    def test_init_with_cause(self):
        cause = ValueError("root cause")
        err = DCCMCPError("wrapper", cause=cause)
        assert err.cause is cause
        assert "ValueError" in str(err)
        assert "root cause" in str(err)

    def test_to_dict_minimal(self):
        err = DCCMCPError("minimal error")
        d = err.to_dict()
        assert d["error_code"] == "RPYC_ERROR"
        assert d["message"] == "minimal error"
        assert "details" not in d
        assert "cause" not in d

    def test_to_dict_with_details(self):
        err = DCCMCPError("with details", details={"host": "localhost"})
        d = err.to_dict()
        assert "details" in d
        assert d["details"]["host"] == "localhost"

    def test_to_dict_with_cause(self):
        cause = RuntimeError("boom")
        err = DCCMCPError("caused", cause=cause)
        d = err.to_dict()
        assert "cause" in d
        assert d["cause"]["type"] == "RuntimeError"
        assert d["cause"]["message"] == "boom"
        assert "traceback" in d

    def test_to_action_result_minimal(self):
        err = DCCMCPError("action failed")
        result = err.to_action_result()
        assert result.success is False
        assert result.message == "action failed"

    def test_to_action_result_with_context(self):
        err = DCCMCPError("action failed", details={"code": 42})
        result = err.to_action_result(context={"extra": "info"})
        assert result.success is False
        assert result.context["extra"] == "info"

    def test_is_exception(self):
        err = DCCMCPError("test")
        assert isinstance(err, Exception)

    def test_raise_and_catch(self):
        with pytest.raises(DCCMCPError, match="RPYC_ERROR: test raise"):
            raise DCCMCPError("test raise")


class TestConnectionError:
    """Tests for the ConnectionError exception class."""

    def test_basic_init(self):
        err = ConnectionError("connect failed")
        assert err.message == "connect failed"
        assert err.error_code == "RPYC_CONNECTION_ERROR"

    def test_with_host_port(self):
        err = ConnectionError("refused", host="localhost", port=18812)
        assert err.details["host"] == "localhost"
        assert err.details["port"] == 18812

    def test_with_service_name(self):
        err = ConnectionError("no service", service_name="maya")
        assert err.details["service_name"] == "maya"

    def test_with_cause(self):
        cause = OSError("ECONNREFUSED")
        err = ConnectionError("failed", cause=cause)
        assert err.cause is cause

    def test_is_dcc_mcp_error(self):
        err = ConnectionError("x")
        assert isinstance(err, DCCMCPError)

    def test_to_dict(self):
        err = ConnectionError("bad", host="h", port=9)
        d = err.to_dict()
        assert d["error_code"] == "RPYC_CONNECTION_ERROR"
        assert d["details"]["host"] == "h"
        assert d["details"]["port"] == 9

    def test_partial_details(self):
        # Only port provided (no host), port=0 is falsy so should not be added
        err = ConnectionError("test", port=0)
        assert "port" not in err.details

    def test_nonzero_port_added(self):
        err = ConnectionError("test", port=8080)
        assert err.details["port"] == 8080


class TestServiceNotFoundError:
    """Tests for ServiceNotFoundError."""

    def test_default_message(self):
        err = ServiceNotFoundError("maya")
        assert "maya" in err.message
        assert "not found" in err.message.lower()
        assert err.error_code == "RPYC_SERVICE_NOT_FOUND"

    def test_custom_message(self):
        err = ServiceNotFoundError("blender", message="Blender is offline")
        assert err.message == "Blender is offline"

    def test_with_cause(self):
        cause = TimeoutError("timeout")
        err = ServiceNotFoundError("houdini", cause=cause)
        assert err.cause is cause

    def test_is_connection_error(self):
        err = ServiceNotFoundError("x")
        assert isinstance(err, ConnectionError)
        assert isinstance(err, DCCMCPError)

    def test_to_action_result(self):
        err = ServiceNotFoundError("nuke")
        result = err.to_action_result()
        assert result.success is False


class TestExecutionError:
    """Tests for ExecutionError."""

    def test_basic_init(self):
        err = ExecutionError("exec failed")
        assert err.message == "exec failed"
        assert err.error_code == "RPYC_REMOTE_EXECUTION_ERROR"

    def test_with_all_details(self):
        err = ExecutionError(
            "fail",
            service_name="maya",
            function_name="create_sphere",
            args=[1, 2],
            kwargs={"radius": 5},
            cause=ValueError("bad arg"),
        )
        assert err.details["service_name"] == "maya"
        assert err.details["function_name"] == "create_sphere"
        assert "args" in err.details
        assert "kwargs" in err.details

    def test_is_dcc_mcp_error(self):
        err = ExecutionError("x")
        assert isinstance(err, DCCMCPError)

    def test_empty_details_not_added(self):
        err = ExecutionError("fail")
        assert "service_name" not in err.details
        assert "function_name" not in err.details


class TestActionError:
    """Tests for ActionError."""

    def test_basic_init(self):
        err = ActionError("action failed", action_name="create_cube")
        assert err.message == "action failed"
        assert err.error_code == "RPYC_ACTION_ERROR"
        assert err.details["action_name"] == "create_cube"

    def test_with_args(self):
        err = ActionError("fail", action_name="my_action", args={"x": 1})
        assert "args" in err.details

    def test_without_args(self):
        err = ActionError("fail", action_name="my_action")
        assert "args" not in err.details

    def test_with_cause(self):
        cause = RuntimeError("crash")
        err = ActionError("fail", action_name="x", cause=cause)
        assert err.cause is cause

    def test_is_dcc_mcp_error(self):
        err = ActionError("x", action_name="y")
        assert isinstance(err, DCCMCPError)


class TestHandleError:
    """Tests for the handle_error utility function."""

    def test_generic_exception(self):
        exc = RuntimeError("unexpected failure")
        result = handle_error(exc)
        assert result.success is False
        assert "unexpected failure" in result.message

    def test_generic_exception_with_context(self):
        exc = ValueError("bad value")
        result = handle_error(exc, context={"action": "test_action"})
        assert result.success is False
        assert result.context["action"] == "test_action"
        assert result.context["error_type"] == "ValueError"

    def test_dcc_mcp_error(self):
        err = DCCMCPError("dcc error", error_code="MY_ERR")
        result = handle_error(err)
        assert result.success is False
        assert result.message == "dcc error"

    def test_dcc_mcp_error_with_context(self):
        err = DCCMCPError("dcc error")
        result = handle_error(err, context={"step": "connect"})
        assert result.success is False
        assert result.context["step"] == "connect"

    def test_connection_error_subclass(self):
        err = ConnectionError("conn failed", host="localhost")
        result = handle_error(err)
        assert result.success is False

    def test_service_not_found_error(self):
        err = ServiceNotFoundError("maya")
        result = handle_error(err)
        assert result.success is False

    def test_returns_action_result_model(self):
        # Import third-party modules
        from dcc_mcp_core import ActionResultModel

        exc = Exception("x")
        result = handle_error(exc)
        assert isinstance(result, ActionResultModel)

    def test_context_has_error_type_and_traceback(self):
        exc = TypeError("type mismatch")
        result = handle_error(exc)
        assert "error_type" in result.context
        assert "traceback" in result.context
        assert result.context["error_type"] == "TypeError"
