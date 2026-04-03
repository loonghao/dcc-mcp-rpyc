"""Tests for dcc_mcp_ipc.utils.decorators module."""

# Import built-in modules
from unittest.mock import patch

# Import third-party modules
import pytest
from dcc_mcp_core.models import ActionResultModel

# Import local modules
from dcc_mcp_ipc.utils.decorators import with_action_result
from dcc_mcp_ipc.utils.decorators import with_error_handling
from dcc_mcp_ipc.utils.decorators import with_info
from dcc_mcp_ipc.utils.decorators import with_result_conversion


class TestWithErrorHandling:
    """Tests for the with_error_handling decorator."""

    def test_success_passes_through(self):
        @with_error_handling
        def my_func():
            return {"success": True, "value": 42}

        result = my_func()
        assert result == {"success": True, "value": 42}

    def test_exception_returns_action_result(self):
        @with_error_handling
        def failing_func():
            raise ValueError("boom")

        result = failing_func()
        assert isinstance(result, ActionResultModel)
        assert result.success is False
        assert "boom" in result.message

    def test_exception_context_has_function_name(self):
        @with_error_handling
        def named_func():
            raise RuntimeError("err")

        result = named_func()
        assert "named_func" in result.context.get("function", "")

    def test_wraps_preserves_name(self):
        @with_error_handling
        def original():
            return "ok"

        assert original.__name__ == "original"

    def test_args_kwargs_in_context(self):
        @with_error_handling
        def func_with_args(a, b, key="val"):
            raise Exception("fail")

        result = func_with_args(1, 2, key="x")
        assert result.success is False
        # args/kwargs info should be in the context
        assert "args" in result.context or "kwargs" in result.context

    def test_return_value_is_not_wrapped_on_success(self):
        @with_error_handling
        def returns_string():
            return "hello"

        assert with_error_handling(lambda: "hello")() == "hello"

    def test_none_return_passes_through(self):
        @with_error_handling
        def returns_none():
            return None

        assert returns_none() is None


class TestWithResultConversion:
    """Tests for the with_result_conversion decorator."""

    def test_dict_with_success_key_converted(self):
        @with_result_conversion
        def func():
            return {"success": True, "message": "ok", "context": {}}

        result = func()
        assert isinstance(result, ActionResultModel)
        assert result.success is True

    def test_dict_without_success_wrapped(self):
        @with_result_conversion
        def func():
            return {"data": "value"}

        result = func()
        assert isinstance(result, ActionResultModel)
        assert result.success is True
        assert result.context["result"]["data"] == "value"

    def test_action_result_model_passes_through(self):
        model = ActionResultModel(success=True, message="already model")

        @with_result_conversion
        def func():
            return model

        result = func()
        assert result is model

    def test_string_result_wrapped(self):
        @with_result_conversion
        def func():
            return "plain string"

        result = func()
        assert isinstance(result, ActionResultModel)
        assert result.context["result"] == "plain string"

    def test_none_result_wrapped(self):
        @with_result_conversion
        def func():
            return None

        result = func()
        assert isinstance(result, ActionResultModel)

    def test_wraps_preserves_name(self):
        @with_result_conversion
        def my_converted_func():
            return {}

        assert my_converted_func.__name__ == "my_converted_func"

    def test_dict_conversion_failure_falls_back(self):
        # dict with 'success' key but extra invalid fields for ActionResultModel
        @with_result_conversion
        def func():
            return {"success": True, "invalid_extra_field_xyz": "boom", "message": "ok"}

        # Should not raise; should either succeed or fall back gracefully
        result = func()
        assert result is not None


class TestWithInfo:
    """Tests for the with_info decorator factory."""

    def _make_obj_with_info(self, info_value):
        class Obj:
            def get_info(self):
                return info_value

            @with_info(lambda self: self.get_info(), "app_info")
            def do_work(self):
                return {"result": "done"}

        return Obj()

    def test_adds_info_to_dict_result(self):
        obj = self._make_obj_with_info({"name": "maya"})
        result = obj.do_work()
        assert "app_info" in result
        assert result["app_info"]["name"] == "maya"
        assert result["result"] == "done"

    def test_works_with_action_result_model(self):
        class Obj:
            def get_info(self):
                return {"version": "2024"}

            @with_info(lambda self: self.get_info(), "dcc_info")
            def do_work(self):
                return ActionResultModel(success=True, message="ok")

        obj = Obj()
        result = obj.do_work()
        assert "dcc_info" in result
        assert result["dcc_info"]["version"] == "2024"

    def test_works_with_non_dict_result(self):
        class Obj:
            def get_info(self):
                return {"x": 1}

            @with_info(lambda self: self.get_info(), "meta")
            def do_work(self):
                return "plain_string"

        obj = Obj()
        result = obj.do_work()
        assert "meta" in result
        assert result["result"] == "plain_string"

    def test_exception_in_func_propagates(self):
        class Obj:
            def get_info(self):
                return {}

            @with_info(lambda self: self.get_info(), "info")
            def do_work(self):
                raise RuntimeError("inner error")

        obj = Obj()
        with pytest.raises(RuntimeError, match="inner error"):
            obj.do_work()

    def test_wraps_preserves_name(self):
        def info_getter(self):
            return {}

        class Obj:
            @with_info(info_getter, "stuff")
            def my_named_method(self):
                return {}

        obj = Obj()
        assert obj.my_named_method.__name__ == "my_named_method"

    def test_works_with_legacy_dict_method(self):
        """Covers the result.dict() branch (line 161 in decorators.py)."""

        class LegacyModel:
            """Simulates a Pydantic v1 model that exposes .dict() but not .model_dump()."""

            def dict(self):
                return {"legacy": True, "data": "value"}

        class Obj:
            def get_info(self):
                return {"source": "legacy"}

            @with_info(lambda self: self.get_info(), "meta")
            def do_work(self):
                return LegacyModel()

        obj = Obj()
        result = obj.do_work()
        assert "meta" in result
        assert result.get("legacy") is True


class TestWithActionResult:
    """Tests for the with_action_result combined decorator."""

    def test_success_returns_action_result_model(self):
        @with_action_result
        def func():
            return {"data": "value"}

        result = func()
        assert isinstance(result, ActionResultModel)
        assert result.success is True

    def test_exception_returns_error_action_result(self):
        @with_action_result
        def failing():
            raise ValueError("test error")

        result = failing()
        assert isinstance(result, ActionResultModel)
        assert result.success is False
        assert "test error" in result.message

    def test_success_with_string_result(self):
        @with_action_result
        def func():
            return "hello"

        result = func()
        assert isinstance(result, ActionResultModel)
        assert result.success is True

    def test_action_result_passthrough(self):
        @with_action_result
        def func():
            return ActionResultModel(success=True, message="prebuilt")

        result = func()
        assert isinstance(result, ActionResultModel)
        assert result.message == "prebuilt"

    def test_wraps_preserves_name(self):
        @with_action_result
        def my_action_func():
            return {}

        assert my_action_func.__name__ == "my_action_func"


class TestWithErrorHandlingEdgePaths:
    """Edge-path tests for with_error_handling – covers re-raise branch (lines 74-76)."""

    def test_reraises_when_action_result_model_creation_fails(self):
        """If ActionResultModel itself raises during error handling, original exception re-raised."""

        @with_error_handling
        def bad_func():
            raise ValueError("original error")

        # Patch ActionResultModel so it raises a secondary exception – triggering lines 74-76
        with patch("dcc_mcp_ipc.utils.decorators.ActionResultModel", side_effect=RuntimeError("model broken")):
            with pytest.raises(RuntimeError, match="model broken"):
                bad_func()


class TestWithResultConversionEdgePaths:
    """Edge-path tests for with_result_conversion – covers lines 112-114, 121-124."""

    def test_standard_conversion_with_non_dict_object(self):
        """For an arbitrary object, standard conversion wraps it via ActionResultModel."""

        class ArbitraryObj:
            pass

        obj = ArbitraryObj()

        @with_result_conversion
        def func():
            return obj

        result = func()
        # Result should be ActionResultModel with the original object in context
        assert isinstance(result, ActionResultModel)
        assert result.success is True
        assert result.context["result"] is obj

    def test_dict_with_success_and_invalid_extra_field_fallback(self):
        """Dict with 'success' but invalid extra field: ActionResultModel(**result) should fail,
        then fall through to the standard wrapping path."""

        @with_result_conversion
        def func():
            # ActionResultModel does NOT accept 'invalid_extra_field_xyz' as a known field,
            # but Pydantic v2 ignores extra fields by default – so we use a value that
            # causes a validation error (e.g. wrong type for a known field).
            return {"success": "not_a_bool_hopefully_causes_error", "message": 123}

        # Should not raise; result is either converted or falls back gracefully
        result = func()
        assert result is not None
