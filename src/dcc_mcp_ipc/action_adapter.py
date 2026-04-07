"""Action adapter for DCC-MCP-IPC.

This module provides adapters connecting RPyC services with the dcc-mcp-core
Action system (ActionRegistry + ActionDispatcher, Rust/PyO3 backend).
"""

# Import built-in modules
import json
import logging
from typing import Any
from typing import Callable
from typing import Optional
from typing import Union

# Import third-party modules
from dcc_mcp_core import ActionDispatcher
from dcc_mcp_core import ActionRegistry
from dcc_mcp_core import ActionResultModel
from dcc_mcp_core import success_result

# Import local modules
from dcc_mcp_ipc.utils.errors import ActionError
from dcc_mcp_ipc.utils.errors import handle_error

# Configure logging
logger = logging.getLogger(__name__)

# Module-level registry of (name → ActionAdapter) for reuse across callers
_adapters: dict[str, "ActionAdapter"] = {}


class ActionAdapter:
    """Adapter connecting RPyC services with the dcc-mcp-core Action system.

    Wraps an ``ActionRegistry`` + ``ActionDispatcher`` pair and exposes a
    simplified interface for discovering, registering, and calling actions.

    Attributes
    ----------
        name: Logical name for this adapter (e.g. the DCC application name).
        registry: The underlying ``ActionRegistry`` instance.
        dispatcher: The ``ActionDispatcher`` backed by *registry*.
        dcc_name: DCC target used when querying the registry.

    """

    def __init__(self, name: str, dcc_name: str = "python") -> None:
        """Initialise the action adapter.

        Args:
            name: Logical adapter name (used for scoping/logging).
            dcc_name: DCC context passed to registry queries (default: "python").

        """
        self.name = name
        self.dcc_name = dcc_name
        self.registry: ActionRegistry = ActionRegistry()
        self.dispatcher: ActionDispatcher = ActionDispatcher(self.registry)
        logger.debug("Initialised ActionAdapter: %s (dcc=%s)", name, dcc_name)

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------

    def register_action(
        self,
        name: str,
        handler: Callable[..., Any],
        *,
        description: str = "",
        category: str = "",
        tags: Optional[list[str]] = None,
        version: str = "1.0.0",
        input_schema: str = "",
        output_schema: str = "",
        source_file: Optional[str] = None,
    ) -> bool:
        """Register an action handler.

        Args:
            name: Unique action name.
            handler: Python callable invoked when the action is dispatched.
            description: Human-readable description shown in MCP tool listings.
            category: Grouping label (e.g. "scene", "render").
            tags: Optional list of searchable tags.
            version: Semver string (default: "1.0.0").
            input_schema: JSON Schema string for the input parameters.
            output_schema: JSON Schema string for the return value.
            source_file: Optional source file path for tracing.

        Returns:
            True on success.

        Raises:
            ActionError: If registration fails.

        """
        try:
            self.registry.register(
                name,
                description=description,
                category=category,
                tags=tags or [],
                dcc=self.dcc_name,
                version=version,
                input_schema=input_schema,
                output_schema=output_schema,
                source_file=source_file,
            )
            self.dispatcher.register_handler(name, handler)
            logger.debug("Registered action '%s' on adapter '%s'", name, self.name)
            return True
        except Exception as exc:
            logger.error("Error registering action '%s': %s", name, exc)
            raise ActionError(f"Failed to register action '{name}': {exc}", action_name=name, cause=exc) from exc

    def unregister_action(self, name: str) -> bool:
        """Remove a previously registered action handler.

        Args:
            name: Action name to remove.

        Returns:
            True if the handler was found and removed, False otherwise.

        """
        removed = self.dispatcher.remove_handler(name)
        if removed:
            try:
                self.registry.unregister(name, dcc_name=self.dcc_name)
            except Exception:
                pass  # unregister is best-effort; handler removal already succeeded
            logger.debug("Unregistered action '%s' from adapter '%s'", name, self.name)
        return removed

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def search_actions(
        self,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """Search actions by category and/or tags (requires dcc-mcp-core >= 0.12.5).

        Args:
            category: Optional category filter.
            tags: Optional tag list filter.

        Returns:
            List of matching action metadata dicts.

        """
        try:
            return self.registry.search_actions(
                category=category,
                tags=tags,
                dcc_name=self.dcc_name,
            )
        except Exception as exc:
            logger.error("Error searching actions: %s", exc)
            return []

    def register_actions_batch(
        self,
        actions: list[dict[str, Any]],
    ) -> int:
        """Register multiple actions in a single call (requires dcc-mcp-core >= 0.12.6).

        Each entry in *actions* must contain at minimum ``name`` and ``handler``
        keys.  All other keys are forwarded to :meth:`register_action`.

        Args:
            actions: List of action specification dicts.

        Returns:
            Number of successfully registered actions.

        """
        registered = 0
        for spec in actions:
            handler = spec.pop("handler", None)
            name = spec.get("name", "")
            if not handler or not name:
                logger.warning("Skipping action spec missing name or handler: %s", spec)
                continue
            try:
                self.register_action(name, handler, **spec)
                registered += 1
            except Exception as exc:
                logger.warning("Failed to register action '%s': %s", name, exc)
        return registered

    def list_actions(self, names_only: bool = False) -> Union[dict[str, Any], list[str]]:
        """List all registered actions and their metadata.

        Args:
            names_only: When *True* return only action names; otherwise return
                full metadata dictionaries.

        Returns:
            List of names when *names_only* is True, else a dict mapping
            action names to metadata dicts.

        Raises:
            ActionError: If the listing call fails.

        """
        try:
            actions_list = self.registry.list_actions(self.dcc_name)
            if names_only:
                return [a["name"] for a in actions_list]
            return {a["name"]: a for a in actions_list}
        except Exception as exc:
            logger.error("Error listing actions: %s", exc)
            raise ActionError("Error listing actions", action_name="list_actions", cause=exc) from exc

    def get_action_info(self, action_name: str) -> Optional[dict[str, Any]]:
        """Get metadata for a single action.

        Args:
            action_name: The action to look up.

        Returns:
            Metadata dict, or *None* if the action is not registered.

        """
        return self.registry.get_action(action_name, self.dcc_name)

    # ------------------------------------------------------------------
    # Invocation
    # ------------------------------------------------------------------

    def call_action(self, action_name: str, **kwargs: Any) -> ActionResultModel:
        """Dispatch an action by name.

        Parameters are serialised to JSON and forwarded to
        ``ActionDispatcher.dispatch()``.

        Args:
            action_name: Registered action name.
            **kwargs: Key/value parameters for the action.

        Returns:
            ``ActionResultModel`` with the execution result.

        """
        try:
            params_json = json.dumps(kwargs) if kwargs else "null"
            result_dict = self.dispatcher.dispatch(action_name, params_json)

            # dcc-mcp-core 0.12+ dispatch returns {'action': str, 'output': Any, 'validation_skipped': bool}
            if isinstance(result_dict, dict) and "output" in result_dict:
                output = result_dict["output"]
                if isinstance(output, ActionResultModel):
                    return output
                if isinstance(output, dict):
                    return ActionResultModel(
                        success=output.get("success", True),
                        message=output.get("message", f"Executed {action_name}"),
                        error=output.get("error"),
                        context=output.get("context", output),
                    )
                return success_result(
                    message=f"Successfully executed {action_name}",
                    context={"result": output},
                )

            # Legacy / fallback: direct dict result
            if isinstance(result_dict, dict):
                return ActionResultModel(
                    success=result_dict.get("success", True),
                    message=result_dict.get("message", f"Executed {action_name}"),
                    error=result_dict.get("error"),
                    context=result_dict.get("context", result_dict),
                )

            return success_result(
                message=f"Successfully executed {action_name}",
                context={"result": result_dict},
            )

        except Exception as exc:
            logger.error("Error dispatching action '%s': %s", action_name, exc)
            return handle_error(exc, {"action_name": action_name, "kwargs": kwargs})

    # ------------------------------------------------------------------
    # Convenience: call a raw Python callable stored in the dispatcher
    # ------------------------------------------------------------------

    def execute_action(self, action_name: str, **kwargs: Any) -> dict[str, Any]:
        """Execute an action and return a plain dict.

        Thin wrapper over :meth:`call_action` that always returns a serialisable
        ``dict`` (``ActionResultModel.to_dict()``).

        Args:
            action_name: Registered action name.
            **kwargs: Parameters forwarded to the action.

        Returns:
            ``ActionResultModel`` serialised as a dict.

        """
        result = self.call_action(action_name, **kwargs)
        return result.to_dict()


# ---------------------------------------------------------------------------
# Module-level factory
# ---------------------------------------------------------------------------


def get_action_adapter(name: str, dcc_name: str = "python") -> ActionAdapter:
    """Get or create an :class:`ActionAdapter` for the given *name*.

    Adapters are cached by name so the same registry is reused for repeated
    calls with the same adapter name.

    Args:
        name: Logical adapter / DCC application name.
        dcc_name: DCC context for registry queries (default: "python").

    Returns:
        An :class:`ActionAdapter` instance.

    """
    if name not in _adapters:
        _adapters[name] = ActionAdapter(name, dcc_name=dcc_name)
    return _adapters[name]
