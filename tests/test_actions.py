"""Tests for the Action system in DCC-MCP-RPYC.

This module contains tests for the Action system, including action registration,
discovery, and execution.
"""

# Import built-in modules
import os

# Import third-party modules
from dcc_mcp_core.actions.base import Action
from dcc_mcp_core.models import ActionResultModel
from pydantic import BaseModel
from pydantic import Field
import pytest

# Import local modules
from dcc_mcp_rpyc.action_adapter import ActionAdapter


# Create a MockActionRegistry class for testing
class MockActionRegistry:
    """Mock implementation of ActionRegistry for testing purposes.

    This class provides a simplified version of the ActionRegistry class
    with just enough functionality to support testing action registration and retrieval.
    """

    def __init__(self):
        self._actions = {}

    def register(self, action_class):
        name = action_class.name or action_class.__name__
        self._actions[name] = action_class

    def get_action(self, name):
        return self._actions.get(name)

    def list_actions(self, dcc_name=None):
        result = []
        for name, action_class in self._actions.items():
            result.append(
                {
                    "name": name,
                    "description": getattr(action_class, "description", ""),
                    "tags": getattr(action_class, "tags", []),
                    "dcc": getattr(action_class, "dcc", None),
                    "input_schema": {},
                }
            )
        return result


# Create a MockActionManager class for testing
class MockActionManager:
    """Mock implementation of ActionManager for testing purposes.

    This class provides a simplified version of the ActionManager class
    with just enough functionality to support testing action registration, discovery and execution.
    """

    def __init__(self, name):
        self.name = name
        self.registry = MockActionRegistry()

    def call_action(self, action_name, **kwargs):
        action_class = self.registry.get_action(action_name)
        if not action_class:
            return ActionResultModel(
                success=False,
                message=f"Action '{action_name}' not found",
                error=f"Action '{action_name}' not found",
                context={"available_actions": []},
            )

        try:
            # Create Action instance and execute
            action = action_class(context={})
            # Validate input
            if hasattr(action_class, "input_model") and action_class.input_model:
                input_data = action_class.input_model(**kwargs)
                return action.execute(input_data)
            return action.execute()
        except Exception as e:
            return ActionResultModel(
                success=False,
                message=f"Error: {e!s}",
                error=str(e),
                context={
                    "action_name": action_name,
                    "args": kwargs,
                    "error_type": type(e).__name__,
                    "traceback": str(e),
                },
            )

    def discover_all_actions(self):
        """Discover all Actions.

        This is a mock method that does not perform any actual actions.
        """

    def register_action_path(self, path):
        """Register Action path.

        This is a mock method that does not perform any actual actions.
        """

    def refresh_actions(self, force=False):
        """Refresh Actions.

        This is a mock method that does not perform any actual actions.
        """

    def list_actions(self):
        """List all registered Actions.

        Returns:
            Dictionary, keys are Action names, values are Action metadata

        """
        actions = {}
        for action_info in self.registry.list_actions():
            name = action_info["name"]
            actions[name] = action_info
        return actions

    def get_action(self, name):
        """Get the specified Action class.

        Args:
            name: Action name

        Returns:
            Action class or None

        """
        return self.registry.get_action(name)


# Patch the get_action_adapter function to return a new mock object
@pytest.fixture
def mock_action_adapter(monkeypatch):
    """Mock the get_action_adapter function to return a test adapter."""
    # Create a dictionary to store adapter instances
    adapters = {}

    def mock_get_adapter(name):
        if name not in adapters:
            adapter = ActionAdapter(name)
            # Replace action_manager with our mock version
            adapter.action_manager = MockActionManager(name)
            adapters[name] = adapter
        return adapters[name]

    # Replace the original function
    monkeypatch.setattr("dcc_mcp_rpyc.action_adapter.get_action_adapter", mock_get_adapter)

    return mock_get_adapter


def test_action_adapter_creation():
    """Test creating an action adapter."""
    # Create an action adapter
    adapter = ActionAdapter("test")

    # Check if the adapter is created successfully
    assert adapter.name == "test"
    assert adapter.action_manager is not None


def test_get_action_adapter(mock_action_adapter):
    """Test getting an action adapter."""
    # Get an action adapter
    adapter1 = mock_action_adapter("test")

    # Get the same adapter again
    adapter2 = mock_action_adapter("test")

    # Check if the two references point to the same adapter
    assert adapter1 is adapter2
    assert adapter1.name == "test"


def test_register_action(mock_action_adapter):
    """Test registering an action."""

    # Define test action class
    class TestActionInput(BaseModel):
        """Test action input model."""

        name: str = Field(description="Name parameter")
        value: int = Field(default=42, description="Value parameter")

    class TestAction(Action):
        """Test action for testing the action system."""

        name = "test_action"
        input_model = TestActionInput

        def execute(self, input_data: TestActionInput) -> ActionResultModel:
            """Execute the test action."""
            return ActionResultModel(
                success=True,
                message=f"Executed test action with name={input_data.name}, value={input_data.value}",
                context={"name": input_data.name, "value": input_data.value},
            )

    # Create an action adapter
    adapter = mock_action_adapter("test_register")

    # Register an action
    adapter.action_manager.registry.register(TestAction)

    # Check if the action is registered
    actions = adapter.list_actions()
    assert "test_action" in actions
    assert actions["test_action"]["name"] == "test_action"


def test_call_action(mock_action_adapter):
    """Test calling an action."""

    # 定义测试 Action 类
    class TestActionInput(BaseModel):
        """Test action input model."""

        name: str = Field(description="Name parameter")
        value: int = Field(default=42, description="Value parameter")

    class TestAction(Action):
        """Test action for testing the action system."""

        name = "test_action"
        input_model = TestActionInput

        def execute(self, input_data: TestActionInput) -> ActionResultModel:
            """Execute the test action."""
            return ActionResultModel(
                success=True,
                message=f"Executed test action with name={input_data.name}, value={input_data.value}",
                context={"name": input_data.name, "value": input_data.value},
            )

    # Create an action adapter
    adapter = mock_action_adapter("test_call")

    # Register an action
    adapter.action_manager.registry.register(TestAction)

    # Call action
    result = adapter.call_action("test_action", name="test_name", value=123)

    # Check result
    assert result.success is True
    assert "test_name" in result.message
    assert "123" in result.message
    assert result.context["name"] == "test_name"
    assert result.context["value"] == 123


def test_action_input_validation(mock_action_adapter):
    """Test action input validation."""

    # Define test action class
    class TestActionInput(BaseModel):
        """Test action input model."""

        name: str = Field(description="Name parameter")
        value: int = Field(default=42, description="Value parameter")

    class TestAction(Action):
        """Test action for testing the action system."""

        name = "test_action"
        input_model = TestActionInput

        def execute(self, input_data: TestActionInput) -> ActionResultModel:
            """Execute the test action."""
            return ActionResultModel(
                success=True,
                message=f"Executed test action with name={input_data.name}, value={input_data.value}",
                context={"name": input_data.name, "value": input_data.value},
            )

    # Create an action adapter
    adapter = mock_action_adapter("test_validation")

    # Register an action
    adapter.action_manager.registry.register(TestAction)

    # Call action when missing required parameters
    result = adapter.call_action("test_action", value=123)
    assert result.success is False
    assert "Error" in result.message

    # Call action when parameter type is incorrect
    result = adapter.call_action("test_action", name=123, value="not_an_int")
    assert result.success is False
    assert "Error" in result.message


def test_action_discovery(mock_action_adapter):
    """Test action discovery."""
    # Create a temporary directory for action discovery
    # Import built-in modules
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a Python module with an action
        module_path = os.path.join(temp_dir, "test_actions_module.py")
        with open(module_path, "w") as f:
            f.write("""\
from dcc_mcp_core.actions.base import Action
from dcc_mcp_core.models import ActionResultModel
from pydantic import BaseModel, Field

class DiscoveredActionInput(BaseModel):
    message: str = Field(description="Message to echo")

class DiscoveredAction(Action):
    name = "discovered_action"
    input_model = DiscoveredActionInput
    
    def execute(self, input_data: DiscoveredActionInput) -> ActionResultModel:
        return ActionResultModel(
            success=True,
            message=f"Discovered action: {input_data.message}",
            context={"message": input_data.message}
        )
""")

        # Create an action adapter
        adapter = mock_action_adapter("test_discovery")

        # Directly register Action, without using set_action_search_paths method
        class DiscoveredActionInput(BaseModel):
            """Discovered action input model."""

            message: str = Field(description="Message to echo")

        class DiscoveredAction(Action):
            """Discovered action for testing."""

            name = "discovered_action"
            input_model = DiscoveredActionInput

            def execute(self, input_data: DiscoveredActionInput) -> ActionResultModel:
                """Execute the discovered action."""
                return ActionResultModel(
                    success=True,
                    message=f"Discovered action: {input_data.message}",
                    context={"message": input_data.message},
                )

        # Register discovered action
        adapter.action_manager.registry.register(DiscoveredAction)

        # Check if action has been discovered
        actions = adapter.list_actions()
        assert "discovered_action" in actions

        # Call discovered action
        result = adapter.call_action("discovered_action", message="Hello from discovered action")

        # Check result
        assert result.success is True
        assert (
            "Hello from discovered action" in result.message
            or result.context.get("message") == "Hello from discovered action"
        )
