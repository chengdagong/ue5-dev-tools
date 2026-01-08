"""
Unit tests for UE5RemoteExecution class.

Tests the core socket-based communication with UE5 editor using mocks.
"""

import pytest
import json
import socket
from unittest.mock import Mock, patch, MagicMock, call

from ue5_remote.executor import UE5RemoteExecution


class TestUE5RemoteExecutionInit:
    """Test UE5RemoteExecution initialization."""

    def test_default_initialization(self):
        """Test default values on initialization."""
        executor = UE5RemoteExecution()

        assert executor.multicast_group == ("239.0.0.1", 6766)
        assert executor.multicast_bind_address == "0.0.0.0"
        assert executor.project_name == ""
        assert executor.unreal_node_id is None
        assert executor.mcast_sock is None
        assert executor.cmd_sock is None
        assert executor.cmd_connection is None

    def test_custom_initialization(self):
        """Test custom values on initialization."""
        executor = UE5RemoteExecution(
            multicast_group=("239.0.0.2", 7000),
            multicast_bind_address="127.0.0.1",
            project_name="MyProject"
        )

        assert executor.multicast_group == ("239.0.0.2", 7000)
        assert executor.multicast_bind_address == "127.0.0.1"
        assert executor.project_name == "MyProject"

    def test_exec_types_constants(self):
        """Test ExecTypes constants are defined correctly."""
        assert UE5RemoteExecution.ExecTypes.EXECUTE_FILE == "ExecuteFile"
        assert UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT == "ExecuteStatement"
        assert UE5RemoteExecution.ExecTypes.EVALUATE_STATEMENT == "EvaluateStatement"

    def test_protocol_constants(self):
        """Test protocol constants are defined correctly."""
        assert UE5RemoteExecution.MAGIC == "ue_py"
        assert UE5RemoteExecution.PROTOCOL_VERSION == 1
        assert UE5RemoteExecution.SOCKET_TIMEOUT == 0.5
        assert UE5RemoteExecution.BUFFER_SIZE == 2_097_152


class TestCreateMulticastSocket:
    """Test multicast socket creation and configuration."""

    @patch('socket.socket')
    def test_socket_creation(self, mock_socket_class):
        """Test socket is created with correct parameters."""
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        executor = UE5RemoteExecution()
        sock = executor._create_multicast_socket()

        # Verify socket constructor was called correctly
        mock_socket_class.assert_called_once_with(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP
        )

    @patch('socket.socket')
    def test_socket_options(self, mock_socket_class):
        """Test socket options are set correctly."""
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        executor = UE5RemoteExecution()
        sock = executor._create_multicast_socket()

        # Verify timeout is set
        mock_sock.settimeout.assert_called_with(0.5)

        # Verify multicast options
        setsockopt_calls = mock_sock.setsockopt.call_args_list

        # Check TTL was set
        ttl_call = call(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 0)
        assert ttl_call in setsockopt_calls

        # Check loopback was enabled
        loop_call = call(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        assert loop_call in setsockopt_calls

        # Check reuse addr was set
        reuse_call = call(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        assert reuse_call in setsockopt_calls

    @patch('socket.socket')
    def test_socket_bind(self, mock_socket_class):
        """Test socket binds to correct address."""
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        executor = UE5RemoteExecution(
            multicast_group=("239.0.0.1", 6766),
            multicast_bind_address="0.0.0.0"
        )
        sock = executor._create_multicast_socket()

        mock_sock.bind.assert_called_once_with(("0.0.0.0", 6766))

    @patch('socket.socket')
    @patch('socket.inet_aton')
    def test_multicast_membership(self, mock_inet_aton, mock_socket_class):
        """Test multicast group membership is added."""
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        # Mock inet_aton to return predictable bytes
        mock_inet_aton.side_effect = lambda addr: {
            "239.0.0.1": b'\xef\x00\x00\x01',
            "0.0.0.0": b'\x00\x00\x00\x00'
        }[addr]

        executor = UE5RemoteExecution()
        sock = executor._create_multicast_socket()

        # Verify membership request
        expected_mreq = b'\xef\x00\x00\x01\x00\x00\x00\x00'
        membership_call = call(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, expected_mreq)
        assert membership_call in mock_sock.setsockopt.call_args_list


class TestFindUnrealInstance:
    """Test UE5 instance discovery via multicast."""

    @patch.object(UE5RemoteExecution, '_create_multicast_socket')
    @patch.object(UE5RemoteExecution, '_send_message')
    @patch.object(UE5RemoteExecution, '_receive_all_messages')
    def test_find_instance_success(self, mock_receive_all, mock_send, mock_create_socket):
        """Test successful UE5 instance discovery."""
        mock_sock = MagicMock()
        mock_create_socket.return_value = mock_sock

        pong_response = {
            "type": "pong",
            "source": "ue5_node_abc",
            "data": {
                "project_name": "TestProject",
                "engine_version": "5.4.0"
            }
        }
        mock_receive_all.return_value = [pong_response]  # Returns list

        executor = UE5RemoteExecution()
        result = executor.find_unreal_instance()

        assert result is True
        assert executor.unreal_node_id == "ue5_node_abc"
        assert executor.mcast_sock is mock_sock

        # Verify ping was sent
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        ping_msg = call_args[1]
        assert ping_msg["type"] == "ping"
        assert ping_msg["magic"] == "ue_py"

    @patch.object(UE5RemoteExecution, '_create_multicast_socket')
    @patch.object(UE5RemoteExecution, '_send_message')
    @patch.object(UE5RemoteExecution, '_receive_all_messages')
    def test_find_instance_timeout(self, mock_receive_all, mock_send, mock_create_socket):
        """Test timeout when no UE5 instance responds."""
        mock_sock = MagicMock()
        mock_create_socket.return_value = mock_sock
        mock_receive_all.return_value = []  # No response (empty list)

        executor = UE5RemoteExecution()
        result = executor.find_unreal_instance()

        assert result is False
        assert executor.unreal_node_id is None

    @patch.object(UE5RemoteExecution, '_create_multicast_socket')
    def test_find_instance_socket_error(self, mock_create_socket):
        """Test handling of socket creation error."""
        mock_create_socket.side_effect = OSError("Network error")

        executor = UE5RemoteExecution()
        result = executor.find_unreal_instance()

        assert result is False


class TestReceiveMessages:
    """Test message receiving and parsing."""

    def test_receive_valid_json(self):
        """Test receiving and parsing valid JSON message."""
        mock_sock = MagicMock()

        pong_data = json.dumps({
            "type": "pong",
            "source": "ue5_node",
            "data": {"project_name": "Test"}
        }).encode()

        mock_sock.recvfrom.side_effect = [
            (pong_data, ("127.0.0.1", 6766)),
            socket.timeout()  # End loop
        ]

        executor = UE5RemoteExecution()
        result = executor._receive_messages(mock_sock, "ping")

        assert result is not None
        assert result["type"] == "pong"
        assert result["source"] == "ue5_node"

    def test_receive_ignores_echo(self):
        """Test that received messages of same type (echo) are ignored."""
        mock_sock = MagicMock()

        # First message is echo (same type as what we sent)
        ping_echo = json.dumps({"type": "ping", "source": "self"}).encode()
        # Second message is actual response
        pong_data = json.dumps({"type": "pong", "source": "ue5"}).encode()

        mock_sock.recvfrom.side_effect = [
            (ping_echo, ("127.0.0.1", 6766)),
            (pong_data, ("127.0.0.1", 6766)),
            socket.timeout()
        ]

        executor = UE5RemoteExecution()
        result = executor._receive_messages(mock_sock, "ping")

        assert result is not None
        assert result["type"] == "pong"

    def test_receive_filters_by_project_name(self):
        """Test that messages are filtered by project name."""
        mock_sock = MagicMock()

        # First response: wrong project
        wrong_project = json.dumps({
            "type": "pong",
            "source": "node1",
            "data": {"project_name": "OtherProject"}
        }).encode()

        # Second response: correct project
        correct_project = json.dumps({
            "type": "pong",
            "source": "node2",
            "data": {"project_name": "TestProject"}
        }).encode()

        mock_sock.recvfrom.side_effect = [
            (wrong_project, ("127.0.0.1", 6766)),
            (correct_project, ("127.0.0.1", 6766)),
            socket.timeout()
        ]

        executor = UE5RemoteExecution(project_name="TestProject")
        result = executor._receive_messages(mock_sock, "ping")

        assert result is not None
        assert result["source"] == "node2"

    def test_receive_timeout(self):
        """Test timeout returns None."""
        mock_sock = MagicMock()
        mock_sock.recvfrom.side_effect = socket.timeout()

        executor = UE5RemoteExecution()
        result = executor._receive_messages(mock_sock, "ping")

        assert result is None

    def test_receive_handles_incomplete_json(self):
        """Test handling of incomplete JSON data (fragmented packets)."""
        mock_sock = MagicMock()

        # Simulate fragmented JSON
        part1 = b'{"type": "pong", '
        part2 = b'"source": "ue5"}'

        mock_sock.recvfrom.side_effect = [
            (part1, ("127.0.0.1", 6766)),
            (part2, ("127.0.0.1", 6766)),
            socket.timeout()
        ]

        executor = UE5RemoteExecution()
        result = executor._receive_messages(mock_sock, "ping")

        assert result is not None
        assert result["type"] == "pong"


class TestOpenConnection:
    """Test command connection opening."""

    @patch('socket.socket')
    def test_open_connection_without_node_id(self, mock_socket_class):
        """Test error when trying to open connection without finding UE5 first."""
        executor = UE5RemoteExecution()
        executor.unreal_node_id = None

        result = executor.open_connection()

        assert result is False

    @patch('socket.socket')
    @patch.object(UE5RemoteExecution, '_send_message')
    def test_open_connection_success(self, mock_send, mock_socket_class):
        """Test successful connection opening."""
        # Create mock sockets
        port_socket = MagicMock()
        port_socket.getsockname.return_value = ('', 12345)

        cmd_socket = MagicMock()
        mock_connection = MagicMock()
        cmd_socket.accept.return_value = (mock_connection, ('127.0.0.1', 54321))

        # Configure mock to return different sockets
        mock_socket_class.side_effect = [port_socket, cmd_socket]

        executor = UE5RemoteExecution()
        executor.unreal_node_id = "ue5_node"
        executor.mcast_sock = MagicMock()

        result = executor.open_connection()

        assert result is True
        assert executor.cmd_sock is cmd_socket
        assert executor.cmd_connection is mock_connection

        # Verify open_connection message was sent
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        open_msg = call_args[1]
        assert open_msg["type"] == "open_connection"
        assert open_msg["dest"] == "ue5_node"

    @patch('socket.socket')
    @patch.object(UE5RemoteExecution, '_send_message')
    def test_open_connection_timeout(self, mock_send, mock_socket_class):
        """Test timeout when UE5 doesn't connect back."""
        port_socket = MagicMock()
        port_socket.getsockname.return_value = ('', 12345)

        cmd_socket = MagicMock()
        cmd_socket.accept.side_effect = socket.timeout()

        mock_socket_class.side_effect = [port_socket, cmd_socket]

        executor = UE5RemoteExecution()
        executor.unreal_node_id = "ue5_node"
        executor.mcast_sock = MagicMock()

        result = executor.open_connection()

        assert result is False


class TestExecuteCommand:
    """Test command execution."""

    def test_execute_command_success(self, sample_command_success_response):
        """Test successful command execution."""
        mock_connection = MagicMock()
        mock_connection.recvfrom.side_effect = [
            (sample_command_success_response, ("127.0.0.1", 0)),
            socket.timeout()
        ]

        executor = UE5RemoteExecution()
        executor.unreal_node_id = "ue5_node"
        executor.cmd_connection = mock_connection

        result = executor.execute_command("1 + 1")

        assert result["success"] is True
        assert result["result"] == "42"

    def test_execute_command_error_response(self, sample_command_error_response):
        """Test command execution with error response."""
        mock_connection = MagicMock()
        mock_connection.recvfrom.side_effect = [
            (sample_command_error_response, ("127.0.0.1", 0)),
            socket.timeout()
        ]

        executor = UE5RemoteExecution()
        executor.unreal_node_id = "ue5_node"
        executor.cmd_connection = mock_connection

        result = executor.execute_command("undefined_variable")

        assert result["success"] is False

    def test_execute_command_timeout(self):
        """Test command execution timeout."""
        mock_connection = MagicMock()
        mock_connection.recvfrom.side_effect = socket.timeout()

        executor = UE5RemoteExecution()
        executor.unreal_node_id = "ue5_node"
        executor.cmd_connection = mock_connection

        result = executor.execute_command("import time; time.sleep(10)")

        assert result["success"] is False
        assert "No response" in result.get("error", "")

    def test_execute_command_default_exec_type(self):
        """Test default exec type is EVALUATE_STATEMENT."""
        mock_connection = MagicMock()
        mock_connection.recvfrom.side_effect = socket.timeout()

        executor = UE5RemoteExecution()
        executor.unreal_node_id = "ue5_node"
        executor.cmd_connection = mock_connection

        executor.execute_command("test")

        # Check the sent message
        call_args = mock_connection.sendto.call_args[0]
        sent_data = json.loads(call_args[0].decode())
        assert sent_data["data"]["exec_mode"] == "EvaluateStatement"

    def test_execute_command_custom_exec_type(self):
        """Test custom exec type is used."""
        mock_connection = MagicMock()
        mock_connection.recvfrom.side_effect = socket.timeout()

        executor = UE5RemoteExecution()
        executor.unreal_node_id = "ue5_node"
        executor.cmd_connection = mock_connection

        executor.execute_command(
            "print('test')",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        call_args = mock_connection.sendto.call_args[0]
        sent_data = json.loads(call_args[0].decode())
        assert sent_data["data"]["exec_mode"] == "ExecuteStatement"

    def test_execute_command_sends_correct_message(self):
        """Test command message format."""
        mock_connection = MagicMock()
        mock_connection.recvfrom.side_effect = socket.timeout()

        executor = UE5RemoteExecution()
        executor.unreal_node_id = "ue5_node"
        executor.cmd_connection = mock_connection

        executor.execute_command("print('hello')")

        call_args = mock_connection.sendto.call_args[0]
        sent_data = json.loads(call_args[0].decode())

        assert sent_data["type"] == "command"
        assert sent_data["magic"] == "ue_py"
        assert sent_data["version"] == 1
        assert sent_data["dest"] == "ue5_node"
        assert sent_data["data"]["command"] == "print('hello')"
        assert sent_data["data"]["unattended"] is True


class TestCloseConnection:
    """Test connection closing."""

    def test_close_connection_full(self):
        """Test closing all connections."""
        mock_mcast = MagicMock()
        mock_cmd_sock = MagicMock()
        mock_cmd_conn = MagicMock()

        executor = UE5RemoteExecution()
        executor.unreal_node_id = "ue5_node"
        executor.mcast_sock = mock_mcast
        executor.cmd_sock = mock_cmd_sock
        executor.cmd_connection = mock_cmd_conn

        executor.close_connection()

        mock_mcast.close.assert_called_once()
        mock_cmd_sock.close.assert_called_once()
        mock_cmd_conn.close.assert_called_once()

    def test_close_connection_sends_message(self):
        """Test close_connection message is sent."""
        mock_mcast = MagicMock()

        executor = UE5RemoteExecution()
        executor.unreal_node_id = "ue5_node"
        executor.mcast_sock = mock_mcast
        executor.multicast_group = ("239.0.0.1", 6766)

        executor.close_connection()

        # Verify close message was sent
        mock_mcast.sendto.assert_called_once()
        call_args = mock_mcast.sendto.call_args[0]
        sent_data = json.loads(call_args[0].decode())

        assert sent_data["type"] == "close_connection"
        assert sent_data["dest"] == "ue5_node"

    def test_close_connection_without_sockets(self):
        """Test close_connection handles missing sockets gracefully."""
        executor = UE5RemoteExecution()
        executor.unreal_node_id = None
        executor.mcast_sock = None
        executor.cmd_sock = None
        executor.cmd_connection = None

        # Should not raise
        executor.close_connection()

    def test_close_connection_handles_errors(self):
        """Test close_connection handles socket errors gracefully."""
        mock_mcast = MagicMock()
        mock_mcast.close.side_effect = OSError("Already closed")

        executor = UE5RemoteExecution()
        executor.unreal_node_id = "ue5_node"
        executor.mcast_sock = mock_mcast

        # Should not raise
        executor.close_connection()
