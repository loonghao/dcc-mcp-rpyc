"""Tests for the HTTP transport implementation."""

# Import built-in modules
import http.client
import json
import socket
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_rpyc.transport.base import ConnectionError
from dcc_mcp_rpyc.transport.base import ProtocolError
from dcc_mcp_rpyc.transport.base import TimeoutError
from dcc_mcp_rpyc.transport.base import TransportState
from dcc_mcp_rpyc.transport.http import HTTPTransport
from dcc_mcp_rpyc.transport.http import HTTPTransportConfig


class TestHTTPTransportConfig:
    """Tests for HTTPTransportConfig."""

    def test_default_config(self):
        config = HTTPTransportConfig()
        assert config.base_path == ""
        assert config.use_ssl is False
        assert "Content-Type" in config.headers
        assert config.action_endpoint == "/api/v1/action/{action}"

    def test_unreal_config(self):
        config = HTTPTransportConfig(
            host="localhost",
            port=30010,
            base_path="/remote",
            action_endpoint="/object/call",
        )
        assert config.port == 30010
        assert config.base_path == "/remote"


class TestHTTPTransport:
    """Tests for HTTPTransport."""

    def _make_mock_response(self, status=200, body=None):
        """Create a mock HTTP response."""
        mock_response = MagicMock()
        mock_response.status = status
        if body is None:
            body = {"success": True}
        mock_response.read.return_value = json.dumps(body).encode("utf-8")
        return mock_response

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_connect_success(self, MockHTTPConn):
        mock_conn = MagicMock()
        MockHTTPConn.return_value = mock_conn

        config = HTTPTransportConfig(host="localhost", port=30010)
        transport = HTTPTransport(config)
        transport.connect()

        assert transport.state == TransportState.CONNECTED
        assert transport.is_connected
        MockHTTPConn.assert_called_once_with("localhost", 30010, timeout=30.0)
        mock_conn.connect.assert_called_once()

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPSConnection")
    def test_connect_ssl(self, MockHTTPSConn):
        mock_conn = MagicMock()
        MockHTTPSConn.return_value = mock_conn

        config = HTTPTransportConfig(host="secure.host", port=443, use_ssl=True)
        transport = HTTPTransport(config)
        transport.connect()

        assert transport.state == TransportState.CONNECTED
        MockHTTPSConn.assert_called_once()

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_connect_failure(self, MockHTTPConn):
        mock_conn = MagicMock()
        mock_conn.connect.side_effect = OSError("Connection refused")
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig(host="bad", port=1))

        with pytest.raises(ConnectionError, match="Failed to connect"):
            transport.connect()
        assert transport.state == TransportState.ERROR

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_connect_already_connected(self, MockHTTPConn):
        mock_conn = MagicMock()
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig(host="localhost", port=80))
        transport.connect()
        transport.connect()  # should be no-op
        assert MockHTTPConn.call_count == 1

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_disconnect(self, MockHTTPConn):
        mock_conn = MagicMock()
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig())
        transport.connect()
        transport.disconnect()

        assert transport.state == TransportState.DISCONNECTED
        mock_conn.close.assert_called_once()

    def test_disconnect_when_not_connected(self):
        transport = HTTPTransport()
        transport.disconnect()  # should not raise
        assert transport.state == TransportState.DISCONNECTED

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_health_check_success(self, MockHTTPConn):
        mock_conn = MagicMock()
        mock_response = self._make_mock_response(200)
        mock_conn.getresponse.return_value = mock_response
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig())
        transport.connect()
        assert transport.health_check() is True

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_health_check_failure(self, MockHTTPConn):
        mock_conn = MagicMock()
        mock_conn.getresponse.side_effect = OSError("no route")
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig())
        transport.connect()
        assert transport.health_check() is False

    def test_health_check_not_connected(self):
        transport = HTTPTransport()
        assert transport.health_check() is False

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_execute_success(self, MockHTTPConn):
        mock_conn = MagicMock()
        mock_response = self._make_mock_response(200, {"success": True, "data": "ok"})
        mock_conn.getresponse.return_value = mock_response
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig())
        transport.connect()

        result = transport.execute("get_scene_info", {"filter": "mesh"})
        assert result == {"success": True, "data": "ok"}

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_execute_http_error(self, MockHTTPConn):
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.read.return_value = b"Internal Server Error"
        mock_conn.getresponse.return_value = mock_response
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig())
        transport.connect()

        with pytest.raises(ProtocolError, match="HTTP 500"):
            transport.execute("bad_action")

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_execute_timeout(self, MockHTTPConn):
        mock_conn = MagicMock()
        mock_conn.getresponse.side_effect = socket.timeout("timed out")
        # Also mock request to allow it to proceed
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig())
        transport.connect()

        with pytest.raises(TimeoutError, match="timed out"):
            transport.execute("slow_action")

    def test_execute_not_connected(self):
        transport = HTTPTransport()
        with pytest.raises(ConnectionError, match="Not connected"):
            transport.execute("test")

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_execute_empty_response(self, MockHTTPConn):
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b""
        mock_conn.getresponse.return_value = mock_response
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig())
        transport.connect()

        result = transport.execute("no_content_action")
        assert result == {"success": True}

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_execute_non_json_response(self, MockHTTPConn):
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"plain text response"
        mock_conn.getresponse.return_value = mock_response
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig())
        transport.connect()

        result = transport.execute("text_action")
        assert result == {"success": True, "result": "plain text response"}

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_execute_connection_broken(self, MockHTTPConn):
        mock_conn = MagicMock()
        mock_conn.request.side_effect = BrokenPipeError("pipe broken")
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig())
        transport.connect()

        with pytest.raises(ConnectionError, match="HTTP request failed"):
            transport.execute("action")
        assert transport.state == TransportState.ERROR

    # ── Unreal Engine Remote Control Shortcuts ────────────────────────

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_call_remote_object(self, MockHTTPConn):
        mock_conn = MagicMock()
        mock_response = self._make_mock_response(200, {"ReturnValue": True})
        mock_conn.getresponse.return_value = mock_response
        MockHTTPConn.return_value = mock_conn

        config = HTTPTransportConfig(host="localhost", port=30010)
        transport = HTTPTransport(config)
        transport.connect()

        result = transport.call_remote_object(
            "/Game/MyActor",
            "SetActorLocation",
            {"NewLocation": {"X": 0, "Y": 0, "Z": 100}},
        )
        assert result == {"ReturnValue": True}

        # Verify the request body
        call_args = mock_conn.request.call_args
        body = json.loads(call_args[1]["body"] if "body" in call_args[1] else call_args[0][2])
        assert body["objectPath"] == "/Game/MyActor"
        assert body["functionName"] == "SetActorLocation"
        assert "parameters" in body

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_get_remote_property(self, MockHTTPConn):
        mock_conn = MagicMock()
        mock_response = self._make_mock_response(200, {"propertyValue": {"X": 1.0}})
        mock_conn.getresponse.return_value = mock_response
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig(port=30010))
        transport.connect()

        result = transport.get_remote_property("/Game/MyActor", "ActorLocation")
        assert result == {"propertyValue": {"X": 1.0}}

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_set_remote_property(self, MockHTTPConn):
        mock_conn = MagicMock()
        mock_response = self._make_mock_response(200, {"success": True})
        mock_conn.getresponse.return_value = mock_response
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig(port=30010))
        transport.connect()

        result = transport.set_remote_property("/Game/MyActor", "ActorLabel", "NewName")
        assert result["success"] is True

    @patch("dcc_mcp_rpyc.transport.http.http.client.HTTPConnection")
    def test_call_remote_object_no_params(self, MockHTTPConn):
        mock_conn = MagicMock()
        mock_response = self._make_mock_response(200, {"result": "ok"})
        mock_conn.getresponse.return_value = mock_response
        MockHTTPConn.return_value = mock_conn

        transport = HTTPTransport(HTTPTransportConfig(port=30010))
        transport.connect()

        result = transport.call_remote_object("/Game/Actor", "GetName")
        assert result == {"result": "ok"}

        # Verify no "parameters" key in body when params is None
        call_args = mock_conn.request.call_args
        body = json.loads(call_args[1]["body"] if "body" in call_args[1] else call_args[0][2])
        assert "parameters" not in body
