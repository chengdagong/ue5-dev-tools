"""
E2E tests for multiple UE5 instance scenarios.

Tests behavior when multiple UE5 instances might be running.
"""

import pytest

from ue5_remote import UE5RemoteExecution


@pytest.mark.e2e
class TestMultiInstanceFiltering:
    """E2E tests for project name filtering with multiple instances."""

    def test_project_filter_finds_correct_instance(self, ue5_project_name):
        """Test that project name filter selects correct instance."""
        executor = UE5RemoteExecution(project_name=ue5_project_name)

        try:
            if executor.find_unreal_instance():
                # Verify connection works
                assert executor.open_connection()

                # Execute a command to verify we're connected to right project
                result = executor.execute_command(
                    f"print('Connected to project: {ue5_project_name}')",
                    exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
                )

                assert result["success"] is True

                executor.close_connection()
            else:
                pytest.skip(f"No UE5 instance found for project {ue5_project_name}")
        finally:
            if executor.mcast_sock:
                executor.mcast_sock.close()

    def test_no_filter_connects_to_any(self):
        """Test that no project filter connects to any available instance."""
        executor = UE5RemoteExecution()  # No project filter

        try:
            if executor.find_unreal_instance():
                assert executor.unreal_node_id is not None
            else:
                pytest.skip("No UE5 instance available")
        finally:
            if executor.mcast_sock:
                executor.mcast_sock.close()


@pytest.mark.e2e
class TestSequentialConnections:
    """E2E tests for sequential connection handling."""

    def test_connect_disconnect_reconnect(self, ue5_project_name):
        """Test connecting, disconnecting, and reconnecting."""
        executor = UE5RemoteExecution(project_name=ue5_project_name)

        try:
            # First connection
            if not executor.find_unreal_instance():
                pytest.skip("No UE5 instance available")

            assert executor.open_connection()

            # Execute something
            result1 = executor.execute_command(
                "print('First connection')",
                exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
            )
            assert result1["success"] is True

            # Disconnect
            executor.close_connection()

            # Reconnect
            executor.unreal_node_id = None
            if executor.mcast_sock:
                executor.mcast_sock.close()
            executor.mcast_sock = None

            if executor.find_unreal_instance():
                assert executor.open_connection()

                # Execute again
                result2 = executor.execute_command(
                    "print('Second connection')",
                    exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
                )
                assert result2["success"] is True

                executor.close_connection()

        finally:
            if executor.mcast_sock:
                try:
                    executor.mcast_sock.close()
                except Exception:
                    pass

    def test_multiple_executors_same_project(self, ue5_project_name):
        """Test creating multiple executors for the same project."""
        executor1 = UE5RemoteExecution(project_name=ue5_project_name)
        executor2 = UE5RemoteExecution(project_name=ue5_project_name)

        try:
            # Find with first executor
            if not executor1.find_unreal_instance():
                pytest.skip("No UE5 instance available")

            node_id_1 = executor1.unreal_node_id

            # Find with second executor
            assert executor2.find_unreal_instance()
            node_id_2 = executor2.unreal_node_id

            # Both should find valid instances
            # Note: If multiple UE5 instances are running, they may find different ones
            # The key test is that both can discover and connect
            assert node_id_1 is not None
            assert node_id_2 is not None

        finally:
            if executor1.mcast_sock:
                executor1.mcast_sock.close()
            if executor2.mcast_sock:
                executor2.mcast_sock.close()
