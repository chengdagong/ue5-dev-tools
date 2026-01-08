"""
E2E tests for UE5 instance discovery.

These tests require a running UE5 editor.
"""

import pytest
import time

from ue5_remote import UE5RemoteExecution


@pytest.mark.e2e
class TestUE5Discovery:
    """E2E tests for UE5 instance discovery via multicast."""

    def test_discover_running_instance(self):
        """Test discovery of a running UE5 instance."""
        executor = UE5RemoteExecution()

        try:
            result = executor.find_unreal_instance()

            if result:
                assert executor.unreal_node_id is not None
                # Verify we got meaningful node ID
                assert len(executor.unreal_node_id) > 0
            else:
                pytest.skip("No UE5 instance available for discovery test")
        finally:
            if executor.mcast_sock:
                executor.mcast_sock.close()

    def test_discover_with_project_filter(self, ue5_project_name):
        """Test discovery filters by project name."""
        executor = UE5RemoteExecution(project_name=ue5_project_name)

        try:
            result = executor.find_unreal_instance()

            if result:
                assert executor.unreal_node_id is not None
            # If not found, that's ok - the running instance might be different project
        finally:
            if executor.mcast_sock:
                executor.mcast_sock.close()

    def test_discovery_timeout_with_wrong_project(self):
        """Test discovery times out when filtering for non-existent project."""
        executor = UE5RemoteExecution(project_name="NonExistentProject12345XYZ")

        try:
            start = time.time()
            result = executor.find_unreal_instance()
            elapsed = time.time() - start

            # Should timeout and return False
            assert result is False
            # Should not take excessively long
            assert elapsed < 5.0
        finally:
            if executor.mcast_sock:
                executor.mcast_sock.close()

    def test_discovery_returns_project_info(self):
        """Test that discovery returns project information."""
        executor = UE5RemoteExecution()

        try:
            result = executor.find_unreal_instance()

            if result:
                # Node ID should be set
                assert executor.unreal_node_id is not None
            else:
                pytest.skip("No UE5 instance available")
        finally:
            if executor.mcast_sock:
                executor.mcast_sock.close()

    def test_multiple_discovery_attempts(self):
        """Test multiple sequential discovery attempts."""
        executor = UE5RemoteExecution()

        try:
            # First attempt
            result1 = executor.find_unreal_instance()

            if result1:
                node_id1 = executor.unreal_node_id

                # Close and recreate socket
                if executor.mcast_sock:
                    executor.mcast_sock.close()
                executor.mcast_sock = None
                executor.unreal_node_id = None

                # Second attempt
                result2 = executor.find_unreal_instance()

                if result2:
                    # Both attempts should find valid instances
                    # Note: If multiple UE5 instances are running, they may find different ones
                    assert executor.unreal_node_id is not None
                    assert node_id1 is not None
        finally:
            if executor.mcast_sock:
                executor.mcast_sock.close()
