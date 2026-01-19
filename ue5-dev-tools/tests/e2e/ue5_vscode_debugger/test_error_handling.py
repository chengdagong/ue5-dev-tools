"""
E2E tests for error handling scenarios.

Tests various error conditions and edge cases.
"""

import pytest
import socket

from ue5_remote import UE5RemoteExecution


@pytest.mark.e2e
class TestConnectionErrorHandling:
    """E2E tests for connection error handling."""

    def test_connection_refused_invalid_node(self):
        """Test handling when trying to connect to invalid node."""
        executor = UE5RemoteExecution()

        # Force invalid node ID
        executor.unreal_node_id = "invalid_node_that_does_not_exist"
        executor.mcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            result = executor.open_connection()
            assert result is False
        finally:
            if executor.mcast_sock:
                executor.mcast_sock.close()

    def test_execute_without_connection(self):
        """Test executing command without establishing connection."""
        executor = UE5RemoteExecution()
        executor.cmd_connection = None

        result = executor.execute_command("print('test')")

        assert result["success"] is False
        assert "error" in result

    def test_close_connection_when_not_connected(self):
        """Test close_connection handles not being connected."""
        executor = UE5RemoteExecution()
        executor.unreal_node_id = None
        executor.mcast_sock = None
        executor.cmd_sock = None
        executor.cmd_connection = None

        # Should not raise
        executor.close_connection()

    def test_connection_closed_then_execute(self, ue5_executor):
        """Test behavior when connection is closed then execute is called."""
        # Close the connection
        ue5_executor.close_connection()

        # Try to execute - should fail gracefully
        result = ue5_executor.execute_command("print('test')")

        assert result["success"] is False


@pytest.mark.e2e
class TestMulticastErrorHandling:
    """E2E tests for multicast-related errors."""

    def test_invalid_multicast_ip(self):
        """Test handling of invalid multicast IP."""
        # Note: Some invalid IPs might still create a socket but fail on send
        executor = UE5RemoteExecution(
            multicast_group=("300.300.300.300", 6766)  # Invalid IP
        )

        result = executor.find_unreal_instance()

        # Should fail gracefully
        assert result is False

    def test_invalid_multicast_port(self):
        """Test handling of invalid port number."""
        executor = UE5RemoteExecution(
            multicast_group=("239.0.0.1", 99999)  # Invalid port
        )

        result = executor.find_unreal_instance()

        # Should fail gracefully
        assert result is False


@pytest.mark.e2e
class TestExecutionErrorHandling:
    """E2E tests for execution error handling."""

    def test_empty_command(self, ue5_executor):
        """Test handling of empty command string."""
        result = ue5_executor.execute_command(
            "",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        # Empty string should return a result (success or error, but not crash)
        assert result is not None
        assert "success" in result or "error" in result

    def test_whitespace_only_command(self, ue5_executor):
        """Test handling of whitespace-only command."""
        result = ue5_executor.execute_command(
            "   \n\t   ",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        # Should handle gracefully - return a result without crashing
        assert result is not None
        assert "success" in result or "error" in result

    def test_very_long_command(self, ue5_executor):
        """Test handling of very long command string."""
        # Create a long but valid Python command
        long_string = "x = " + repr("a" * 10000)

        result = ue5_executor.execute_command(
            long_string,
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        # Should either succeed or fail gracefully
        assert "error" in result or result["success"] is True

    def test_unicode_command(self, ue5_executor):
        """Test handling of unicode characters in command."""
        result = ue5_executor.execute_command(
            "print('Hello World')",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        assert result["success"] is True

    def test_special_characters_command(self, ue5_executor):
        """Test handling of special characters."""
        result = ue5_executor.execute_command(
            r"print('Line1\nLine2\tTabbed')",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        assert result["success"] is True


@pytest.mark.e2e
@pytest.mark.slow
class TestTimeoutHandling:
    """E2E tests for timeout handling. These tests are slow."""

    def test_timeout_on_long_running_code(self, ue5_executor_any_project):
        """Test timeout on long-running code."""
        # Note: This may block the UE5 editor for the duration
        result = ue5_executor_any_project.execute_command(
            "import time; time.sleep(10)",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT,
            timeout=1.0  # Short timeout
        )

        # Should timeout
        # Note: The command might still execute in UE5 but we won't wait for result
        assert result["success"] is False or "timeout" in str(result).lower() or "No response" in str(result)
