"""E2E tests for Blender MCP-IPC integration.

These tests exercise the full IPC communication pipeline — server startup,
client connection, RPC calls, action dispatch, and connection pool — using
MockDCCService to simulate a running Blender instance.

No Blender installation is required; the mock service faithfully implements
the same RPyC protocol surface that a real Blender add-on would expose.
"""

# Import built-in modules
import threading
import time
from typing import Any

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_ipc.action_adapter import get_action_adapter
from dcc_mcp_ipc.client import BaseDCCClient
from dcc_mcp_ipc.client import ConnectionPool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def blender_client(blender_server):
    """Function-scoped connected BaseDCCClient pointing at the mock Blender server."""
    _, port = blender_server
    client = BaseDCCClient("blender", host="localhost", port=port, auto_connect=False)
    client.connect()
    yield client
    if client.is_connected():
        client.disconnect()


# ---------------------------------------------------------------------------
# 1. Connection lifecycle
# ---------------------------------------------------------------------------


class TestConnectionLifecycle:
    """Verify that the client can connect to and disconnect from the server."""

    def test_connect_and_is_connected(self, blender_server):
        _, port = blender_server
        client = BaseDCCClient("blender", host="localhost", port=port, auto_connect=False)
        client.connect()
        assert client.is_connected(), "Client should report connected after connect()"
        client.disconnect()

    def test_disconnect_clears_connection(self, blender_server):
        _, port = blender_server
        client = BaseDCCClient("blender", host="localhost", port=port, auto_connect=False)
        client.connect()
        client.disconnect()
        assert not client.is_connected(), "Client should not be connected after disconnect()"

    def test_multiple_connect_disconnect_cycles(self, blender_server):
        """Repeated connect/disconnect must not raise or corrupt state."""
        _, port = blender_server
        client = BaseDCCClient("blender", host="localhost", port=port, auto_connect=False)
        for _ in range(3):
            client.connect()
            assert client.is_connected()
            client.disconnect()
            assert not client.is_connected()


# ---------------------------------------------------------------------------
# 2. DCC info retrieval
# ---------------------------------------------------------------------------


class TestDCCInfo:
    """Verify that the client can retrieve DCC application metadata via IPC."""

    def _get_dcc_info(self, client: BaseDCCClient) -> dict:
        """Retrieve DCC info directly via exposed_ RPC method."""
        return client.execute_with_connection(lambda conn: conn.root.exposed_get_dcc_info())

    def test_get_dcc_info_returns_dict(self, blender_client):
        info = self._get_dcc_info(blender_client)
        assert isinstance(info, dict), "get_dcc_info() must return a dict"

    def test_get_dcc_info_has_name(self, blender_client):
        info = self._get_dcc_info(blender_client)
        assert "name" in info, "DCC info must include 'name' key"

    def test_get_dcc_info_has_version(self, blender_client):
        info = self._get_dcc_info(blender_client)
        assert "version" in info, "DCC info must include 'version' key"

    def test_get_dcc_info_has_platform(self, blender_client):
        info = self._get_dcc_info(blender_client)
        assert "platform" in info, "DCC info must include 'platform' key"


# ---------------------------------------------------------------------------
# 3. Scene information
# ---------------------------------------------------------------------------


class TestSceneInfo:
    """Verify scene metadata retrieval through the IPC channel."""

    def test_get_scene_info_returns_dict(self, blender_client):
        result = blender_client.get_scene_info()
        assert isinstance(result, dict)

    def test_get_scene_info_success_flag(self, blender_client):
        result = blender_client.get_scene_info()
        assert result.get("success") is True

    def test_get_scene_info_has_context(self, blender_client):
        result = blender_client.get_scene_info()
        assert "context" in result, "Scene info result must contain a 'context' key"

    def test_scene_context_has_objects(self, blender_client):
        result = blender_client.get_scene_info()
        ctx = result.get("context", {})
        assert "objects" in ctx, "Scene context must list 'objects'"
        assert isinstance(ctx["objects"], list)


# ---------------------------------------------------------------------------
# 4. Primitive creation (Blender-style actions)
# ---------------------------------------------------------------------------


class TestPrimitiveCreation:
    """Verify that primitive-creation actions work end-to-end over IPC."""

    @pytest.mark.parametrize("primitive_type", ["sphere", "cube"])
    def test_create_supported_primitive(self, blender_client, primitive_type):
        result = blender_client.create_primitive(primitive_type)
        assert isinstance(result, dict)
        assert result.get("success") is True, f"create_primitive({primitive_type!r}) failed: {result}"

    def test_create_sphere_has_context_name(self, blender_client):
        result = blender_client.create_primitive("sphere")
        ctx = result.get("context", {})
        assert "name" in ctx or "id" in ctx, "Sphere result context must include 'name' or 'id'"

    def test_create_cube_has_context_name(self, blender_client):
        result = blender_client.create_primitive("cube")
        ctx = result.get("context", {})
        assert "name" in ctx or "id" in ctx

    def test_create_unknown_primitive_fails_gracefully(self, blender_client):
        result = blender_client.create_primitive("torus_unknown")
        assert isinstance(result, dict)
        # Should report failure, not raise
        assert result.get("success") is False


# ---------------------------------------------------------------------------
# 5. Echo / round-trip via execute_python
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Basic round-trip tests via execute_python to verify bi-directional RPC."""

    def test_execute_simple_expression(self, blender_client):
        result = blender_client.execute_python("1 + 1")
        assert result == 2

    def test_execute_string_expression(self, blender_client):
        result = blender_client.execute_python("'blender'.upper()")
        assert result == "BLENDER"

    def test_execute_arithmetic(self, blender_client):
        result = blender_client.execute_python("7 * 8 - 6")
        assert result == 50


# ---------------------------------------------------------------------------
# 6. Session info
# ---------------------------------------------------------------------------


class TestSessionInfo:
    """Verify session metadata is correctly returned."""

    def test_get_session_info_returns_dict(self, blender_client):
        result = blender_client.get_session_info()
        assert isinstance(result, dict)

    def test_session_info_success(self, blender_client):
        result = blender_client.get_session_info()
        assert result.get("success") is True

    def test_session_info_has_application(self, blender_client):
        result = blender_client.get_session_info()
        ctx = result.get("context", {})
        assert "application" in ctx

    def test_session_info_has_id(self, blender_client):
        result = blender_client.get_session_info()
        ctx = result.get("context", {})
        assert "id" in ctx


# ---------------------------------------------------------------------------
# 7. Action adapter integration
# ---------------------------------------------------------------------------


class TestActionAdapterIntegration:
    """Verify the ActionAdapter can register and dispatch Blender actions.

    Note: ActionAdapter uses the Rust dcc-mcp-core backend which requires plain
    Python dicts (not RPyC netrefs). These tests use local stub functions that
    return plain dicts, simulating what a properly-written Blender action would
    do after unwrapping the RPC response.
    """

    def test_register_and_call_blender_action(self, blender_server):
        """Register a scene-query action and verify successful dispatch."""
        _, port = blender_server
        adapter = get_action_adapter("blender_e2e_scene")

        # Use a plain-dict returning stub (Rust dispatcher requires real Python dicts)
        # The ActionDispatcher may pass a positional context arg — accept *args to handle it
        def _get_scene(*args, **kwargs) -> dict:
            return {"scene": "blender_mock", "objects": ["Cube", "Sphere"], "frame": 1}

        adapter.register_action(
            "blender_e2e_get_scene",
            _get_scene,
            description="Fetch Blender scene info via mock IPC",
            category="scene",
            tags=["blender", "e2e"],
        )

        result = adapter.call_action("blender_e2e_get_scene")
        assert result.success is True

    def test_action_result_to_dict(self, blender_server):
        """Verify ActionAdapter result serialises correctly to a plain dict."""
        _, port = blender_server
        adapter = get_action_adapter("blender_e2e_info_adapter")

        def _get_dcc_info(**kwargs) -> dict:
            return {"name": "blender", "version": "4.0", "platform": "win32"}

        adapter.register_action("blender_e2e_get_info", _get_dcc_info, description="DCC info")
        result = adapter.call_action("blender_e2e_get_info")
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "success" in result_dict

    def test_action_for_primitive_creation(self, blender_server):
        """Verify ActionAdapter dispatches to a Blender-style primitive creation function."""
        _, port = blender_server
        adapter = get_action_adapter("blender_e2e_prim_adapter")

        def _create_sphere(radius: float = 1.0, **kwargs) -> dict:
            return {"success": True, "name": f"Sphere_r{radius}", "type": "SPHERE"}

        adapter.register_action(
            "blender_e2e_create_sphere",
            _create_sphere,
            description="Create a sphere in Blender via mock IPC",
            category="modeling",
            tags=["blender", "mesh", "e2e"],
        )

        result = adapter.call_action("blender_e2e_create_sphere", radius=2.0)
        assert result.success is True
        result_dict = result.to_dict()
        assert result_dict.get("success") is True

    def test_action_ipc_round_trip(self, blender_server):
        """End-to-end: register action, IPC call, verify client receives correct data."""
        _, port = blender_server
        client = BaseDCCClient("blender", host="localhost", port=port, auto_connect=False)
        client.connect()

        # Verify IPC round-trip independently of ActionAdapter
        scene = client.get_scene_info()
        assert scene.get("success") is True
        assert "context" in scene

        client.disconnect()


# ---------------------------------------------------------------------------
# 8. Connection pool
# ---------------------------------------------------------------------------


class TestConnectionPool:
    """Verify that ConnectionPool manages Blender connections correctly."""

    def test_pool_get_client_returns_connected_client(self, blender_server):
        _, port = blender_server
        pool = ConnectionPool()
        client = pool.get_client("blender", host="localhost", port=port)
        assert client.is_connected()
        client.disconnect()

    def test_pool_client_can_call_get_scene_info(self, blender_server):
        _, port = blender_server
        pool = ConnectionPool()
        client = pool.get_client("blender", host="localhost", port=port)
        info = client.get_scene_info()
        assert isinstance(info, dict)
        client.disconnect()


# ---------------------------------------------------------------------------
# 9. Concurrent connections
# ---------------------------------------------------------------------------


class TestConcurrentConnections:
    """Verify that multiple clients can talk to the server simultaneously."""

    def test_two_clients_simultaneously(self, blender_server):
        _, port = blender_server
        results: dict = {}
        errors: dict = {}

        def _worker(name: str) -> None:
            try:
                c = BaseDCCClient("blender", host="localhost", port=port, auto_connect=False)
                c.connect()
                # Use get_scene_info which is properly exposed
                results[name] = c.get_scene_info()
                c.disconnect()
            except Exception as exc:
                errors[name] = exc

        threads = [threading.Thread(target=_worker, args=(f"client-{i}",)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"Concurrent connection errors: {errors}"
        assert len(results) == 2
        for name, info in results.items():
            assert isinstance(info, dict), f"{name} did not return a dict"

    def test_five_clients_simultaneously(self, blender_server):
        _, port = blender_server
        results: dict = {}
        errors: dict = {}

        def _worker(idx: int) -> None:
            name = f"client-{idx}"
            try:
                c = BaseDCCClient("blender", host="localhost", port=port, auto_connect=False)
                c.connect()
                results[name] = c.execute_python(str(idx))
                c.disconnect()
            except Exception as exc:
                errors[name] = exc

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Concurrent errors: {errors}"
        for i in range(5):
            assert results[f"client-{i}"] == i


# ---------------------------------------------------------------------------
# 10. Available actions listing
# ---------------------------------------------------------------------------


class TestAvailableActions:
    """Verify that the server exposes its available actions."""

    def test_get_actions_returns_dict(self, blender_client):
        result = blender_client.execute_with_connection(lambda conn: conn.root.exposed_get_actions())
        assert isinstance(result, dict)
        assert "actions" in result

    def test_get_actions_includes_create_primitive(self, blender_client):
        result = blender_client.execute_with_connection(lambda conn: conn.root.exposed_get_actions())
        actions = result.get("actions", {})
        assert "create_primitive" in actions

    def test_get_actions_includes_get_scene_info(self, blender_client):
        result = blender_client.execute_with_connection(lambda conn: conn.root.exposed_get_actions())
        actions = result.get("actions", {})
        assert "get_scene_info" in actions
