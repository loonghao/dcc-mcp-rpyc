"""Coverage-gap tests for iteration 12.

Covers missing lines in:
- transport/rpyc_transport.py: execute_python / call_function / import_module exception paths
- adapter/base.py: action_paths getter, get_available_actions, get_action_info
- discovery/factory.py (ServiceDiscoveryFactory): strategy creation failure
- utils/decorators.py: with_result_conversion ActionResultModel fallback
- server/dcc.py: _create_server and non-threaded start path
- testing/mock_services.py: exception branches
- client/base.py: discover_service success branch and reconnect-failure branch
"""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# transport/rpyc_transport.py  lines 215-216, 242-243, 263-264
# ─────────────────────────────────────────────────────────────────────────────
class TestRPyCTransportExceptionPaths:
    """Cover the exception branches in execute_python / call_function / import_module."""

    def _connected_transport(self, mock_rpyc, mock_conn):
        from dcc_mcp_ipc.transport.rpyc_transport import RPyCTransport

        mock_rpyc.connect.return_value = mock_conn
        transport = RPyCTransport()
        transport._connect_func = mock_rpyc.connect
        transport.connect()
        return transport

    @patch("dcc_mcp_ipc.transport.rpyc_transport.rpyc")
    def test_execute_python_raises_protocol_error_on_exception(self, mock_rpyc):
        from dcc_mcp_ipc.transport.base import ProtocolError

        mock_conn = MagicMock()
        mock_conn.root.exposed_execute_python.side_effect = RuntimeError("remote crash")
        transport = self._connected_transport(mock_rpyc, mock_conn)

        with pytest.raises(ProtocolError, match="Error executing Python code"):
            transport.execute_python("1 + 1")

    @patch("dcc_mcp_ipc.transport.rpyc_transport.rpyc")
    def test_call_function_raises_protocol_error_on_exception(self, mock_rpyc):
        from dcc_mcp_ipc.transport.base import ProtocolError

        mock_conn = MagicMock()
        mock_conn.root.exposed_call_function.side_effect = RuntimeError("call failed")
        transport = self._connected_transport(mock_rpyc, mock_conn)

        with pytest.raises(ProtocolError, match="Error calling"):
            transport.call_function("os", "getcwd")

    @patch("dcc_mcp_ipc.transport.rpyc_transport.rpyc")
    def test_import_module_raises_protocol_error_on_exception(self, mock_rpyc):
        from dcc_mcp_ipc.transport.base import ProtocolError

        mock_conn = MagicMock()
        mock_conn.root.exposed_get_module.side_effect = ImportError("no such module")
        transport = self._connected_transport(mock_rpyc, mock_conn)

        with pytest.raises(ProtocolError, match="Error importing module"):
            transport.import_module("nonexistent_xyz")


# ─────────────────────────────────────────────────────────────────────────────
# adapter/base.py  lines 95, 127, 139
# ─────────────────────────────────────────────────────────────────────────────
class TestApplicationAdapterBasePaths:
    """Cover action_paths getter, get_available_actions, get_action_info."""

    def _make_adapter(self):
        from dcc_mcp_ipc.adapter.base import ApplicationAdapter
        from dcc_mcp_ipc.client import BaseApplicationClient

        class ConcreteAdapter(ApplicationAdapter):
            def _initialize_client(self) -> None:
                self.client = MagicMock(spec=BaseApplicationClient)

            def _initialize_action_paths(self) -> None:
                self._action_paths = []

            def get_application_info(self):
                return {}

            def execute_action(self, action_name, **kwargs):
                return {}

        with patch("dcc_mcp_ipc.adapter.base.get_action_adapter") as mock_factory:
            mock_aa = MagicMock()
            mock_factory.return_value = mock_aa
            adapter = ConcreteAdapter("test_app")
            adapter.action_adapter = mock_aa
            return adapter

    def test_action_paths_getter(self):
        adapter = self._make_adapter()
        adapter._action_paths = ["/some/path"]
        assert adapter.action_paths == ["/some/path"]

    def test_get_available_actions_delegates(self):
        adapter = self._make_adapter()
        adapter.action_adapter.list_actions.return_value = ["create_sphere", "delete"]
        result = adapter.get_available_actions()
        adapter.action_adapter.list_actions.assert_called_once_with(names_only=True)
        assert result == ["create_sphere", "delete"]

    def test_get_action_info_delegates(self):
        adapter = self._make_adapter()
        adapter.action_adapter.get_action_info.return_value = {"name": "create_sphere", "params": {}}
        result = adapter.get_action_info("create_sphere")
        adapter.action_adapter.get_action_info.assert_called_once_with("create_sphere")
        assert result["name"] == "create_sphere"


# ─────────────────────────────────────────────────────────────────────────────
# discovery/factory.py  lines 84-86 (ServiceDiscoveryFactory.get_strategy)
# ─────────────────────────────────────────────────────────────────────────────
class TestServiceDiscoveryFactoryErrorPath:
    """Cover strategy creation failure branch."""

    def test_get_strategy_exception_returns_none(self):
        from dcc_mcp_ipc.discovery.factory import ServiceDiscoveryFactory

        # Reset singleton so we get a clean state
        ServiceDiscoveryFactory._reset_instance()
        factory = ServiceDiscoveryFactory()

        class BrokenStrategy:
            def __init__(self, **kwargs):
                raise RuntimeError("init failed")

        # Inject the broken strategy class directly
        factory._strategy_classes["broken"] = BrokenStrategy

        result = factory.get_strategy("broken")
        assert result is None

        # Cleanup: reset singleton
        ServiceDiscoveryFactory._reset_instance()


# ─────────────────────────────────────────────────────────────────────────────
# utils/decorators.py  lines 120-123 (with_result_conversion fallback)
# ─────────────────────────────────────────────────────────────────────────────
class TestWithResultConversionFallback:
    """Cover the fallback when ActionResultModel construction fails."""

    def test_returns_raw_result_when_action_result_model_raises(self):
        from dcc_mcp_ipc.utils.decorators import with_result_conversion

        # Return a plain list — not a dict with 'success', not an ActionResultModel
        # The standard-conversion try block will be entered and we force it to raise
        raw = [1, 2, 3]

        @with_result_conversion
        def my_func(self):
            return raw

        # Patch ActionResultModel so the isinstance check still works for the first guard
        # but the constructor call raises when trying to wrap the result
        import dcc_mcp_ipc.utils.decorators as dec_module

        call_count = {"n": 0}

        class FakeARM:
            def __init__(self, *a, **kw):
                call_count["n"] += 1
                raise TypeError("construction failed")

        with patch.object(dec_module, "ActionResultModel", FakeARM):
            result = my_func(None)

        # Should fall back to returning the raw result (lines 122-123)
        assert result == raw


# ─────────────────────────────────────────────────────────────────────────────
# server/dcc.py  line 151 (_create_server) and lines 184-186 (non-threaded start)
# ─────────────────────────────────────────────────────────────────────────────
class TestDCCServerPaths:
    """Cover _create_server call and non-threaded start branch."""

    def _make_server(self):
        from dcc_mcp_ipc.server.dcc import DCCServer

        mock_svc = MagicMock()
        with patch("dcc_mcp_ipc.server.dcc.ZEROCONF_AVAILABLE", False):
            server = DCCServer("maya", service_class=mock_svc, port=0)
        return server, mock_svc

    def test_create_server_calls_create_raw_threaded_server(self):
        server, mock_svc = self._make_server()
        mock_threaded = MagicMock()

        with patch("dcc_mcp_ipc.server.dcc.create_raw_threaded_server", return_value=mock_threaded) as mock_create:
            result = server._create_server()

        mock_create.assert_called_once_with(mock_svc, hostname="0.0.0.0", port=0)
        assert result is mock_threaded

    def test_start_non_threaded_calls_server_start(self):
        """Cover the non-threaded branch (lines 184-186)."""
        server, _ = self._make_server()
        mock_threaded_server = MagicMock()
        mock_threaded_server.port = 12345

        with patch("dcc_mcp_ipc.server.dcc.create_raw_threaded_server", return_value=mock_threaded_server):
            port = server.start(threaded=False)

        mock_threaded_server.start.assert_called_once()
        # server.port is 0 (the config port)
        assert port == 0


# ─────────────────────────────────────────────────────────────────────────────
# testing/mock_services.py  lines 90-91, 213-214, 324-325, 484
# ─────────────────────────────────────────────────────────────────────────────
class TestMockServicesExceptionPaths:
    """Cover exception branches that were previously uncovered."""

    def _make_service(self, dcc_name="test_dcc"):
        """Create MockDCCService without going through RPyC's Slave constructor."""
        from dcc_mcp_ipc.testing.mock_services import MockDCCService

        # Bypass RPyC's Slave.__init__ which requires a stream argument
        svc = MockDCCService.__new__(MockDCCService)
        svc.dcc_name = dcc_name
        # Inject minimal primitives dict if the class uses one
        if not hasattr(svc, "_primitives"):
            svc._primitives = {}
        return svc

    def test_get_environment_info_module_exception_is_swallowed(self):
        """Lines 90-91: except clause in module version enumeration."""
        svc = self._make_service()

        with patch.object(svc, "get_module_version", side_effect=RuntimeError("version error")):
            info = svc.get_environment_info()

        # The exception is swallowed; info should still have the outer structure
        assert "python_version" in info

    def test_call_function_general_exception_returns_error_dict(self):
        """Lines 213-214: general exception in call_function."""
        svc = self._make_service()

        # Patch import_module to raise an unexpected exception (not ImportError/dict)
        with patch.object(svc, "import_module", side_effect=RuntimeError("unexpected")):
            result = svc.call_function("some_module", "some_func")

        assert result["success"] is False
        assert "unexpected" in result["error"]

    def test_create_primitive_exception_branch(self):
        """Lines 324-325: exception caught in the try block → except branch executed."""
        svc = self._make_service()

        # Force an exception inside the try block by making kwargs.get raise.
        # We do this by passing a bad kwargs proxy.  The simplest approach is to
        # make ActionResultModel raise on the *first* call (the success=True wrap),
        # so that the except block on lines 324-331 is entered.
        from dcc_mcp_core import ActionResultModel as RealARM

        call_count = {"n": 0}

        def arm_side_effect(*args, **kwargs):
            call_count["n"] += 1
            # First call: the "unknown type" or success path inside try — raise
            if call_count["n"] == 1:
                raise RuntimeError("forced error")
            # Second call: inside the except block — return normally
            return RealARM(*args, **kwargs)

        with patch("dcc_mcp_ipc.testing.mock_services.ActionResultModel", side_effect=arm_side_effect):
            result = svc.create_primitive("sphere")

        assert result["success"] is False
        assert "forced error" in result.get("error", "")

    def test_exposed_call_action_non_dict_result_wraps_in_action_result(self):
        """Line 484: action returning a non-dict result is wrapped in ActionResultModel."""
        svc = self._make_service()

        # get_scene_info returns a dict with 'success', so test create_primitive returning
        # a result that is a non-success-keyed dict — we mock get_scene_info to return a
        # plain string (non-dict) to hit line 484
        with patch.object(svc, "get_scene_info", return_value="plain string result"):
            result = svc.exposed_call_action("get_scene_info")

        assert result["success"] is True
        assert "result" in result.get("context", {})


# ─────────────────────────────────────────────────────────────────────────────
# client/base.py  lines 114-118 and 479-480
# ─────────────────────────────────────────────────────────────────────────────
class TestClientBasePaths:
    """Cover discover_service success branch and get_client reconnect-failure branch."""

    def test_discover_service_returns_host_port_when_found(self):
        """Lines 114-118: successful file-based service discovery."""
        from dcc_mcp_ipc.client.base import BaseApplicationClient

        client = BaseApplicationClient("maya", host="localhost", port=0)

        mock_service = MagicMock()
        mock_service.port = 18812
        mock_service.host = "localhost"

        with patch("dcc_mcp_ipc.client.base.ServiceRegistry") as mock_reg_cls:
            mock_registry = MagicMock()
            mock_reg_cls.return_value = mock_registry
            mock_registry.get_strategy.return_value = MagicMock()
            mock_registry.discover_services.return_value = [mock_service]

            host, port = client._discover_service()

        assert host == "localhost"
        assert port == 18812

    def test_get_client_reconnect_failure_still_returns_client(self):
        """Lines 479-480: reconnect exception is logged but client is still returned."""
        from dcc_mcp_ipc.client.base import get_client

        mock_client = MagicMock()
        mock_client.is_connected.return_value = False
        mock_client.connect.side_effect = OSError("refused")

        key = ("reconnect_test_app", "localhost", 9999)
        with patch.dict("dcc_mcp_ipc.client.base._clients", {key: mock_client}):
            result = get_client("reconnect_test_app", host="localhost", port=9999)

        assert result is mock_client
