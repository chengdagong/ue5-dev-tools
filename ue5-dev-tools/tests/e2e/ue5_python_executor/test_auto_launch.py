"""
E2E tests for auto-launching UE5 editor.

These tests are slow and may launch UE5 editor.
Only run in controlled environments.
"""

import pytest
import subprocess
import sys
import json
from pathlib import Path

# Add e2e directory to path for conftest imports
E2E_DIR = Path(__file__).parent.parent
if str(E2E_DIR) not in sys.path:
    sys.path.insert(0, str(E2E_DIR))

from ue5_remote import UE5RemoteExecution
from ue5_remote.utils import find_ue5_editor

# Import shared helpers from conftest
from conftest import (
    close_all_ue5_instances,
    create_blank_ue5_project,
    detect_ue5_version,
)

REMOTE_EXECUTE_SCRIPT = Path(__file__).parent.parent.parent.parent / "skills" / "ue5-python-executor" / "scripts" / "remote-execute.py"
TESTS_DIR = Path(__file__).parent.parent.parent
AUTO_LAUNCH_TEST_PROJECT_DIR = TESTS_DIR / "fixtures" / "AutoLaunchTestProject"
CONFIG_FIX_TEST_PROJECT_DIR = TESTS_DIR / "fixtures" / "ConfigFixTestProject"


@pytest.mark.e2e
@pytest.mark.slow
class TestAutoLaunch:
    """
    E2E tests for auto-launching UE5 editor.

    WARNING: These tests may launch UE5 editor if not already running.
    Only run in controlled environments where this is acceptable.
    """

    def test_find_ue5_editor(self):
        """Test that UE5 editor can be found on the system."""
        editor_path = find_ue5_editor()

        if editor_path is None:
            pytest.skip("UE5 editor not found on system")

        assert editor_path.exists()
        assert editor_path.name == "UnrealEditor.exe" or "UnrealEditor" in editor_path.name

    def test_no_launch_flag_prevents_launch(self, ue5_uproject_path):
        """Test --no-launch flag behavior.

        When UE5 is NOT running: --no-launch should prevent auto-launch and fail.
        When UE5 IS running: --no-launch should still allow connection and execution.
        """
        # Check if UE5 is already running
        executor = UE5RemoteExecution()
        ue5_running = executor.find_unreal_instance()
        if executor.mcast_sock:
            executor.mcast_sock.close()

        # Run with --no-launch
        result = subprocess.run(
            [sys.executable, str(REMOTE_EXECUTE_SCRIPT),
             "--code", "print('test')",
             "--project-path", str(ue5_uproject_path),
             "--no-launch"],
            capture_output=True,
            text=True,
            timeout=15
        )

        if ue5_running:
            # When UE5 is running, --no-launch should still work (just skip launch step)
            assert result.returncode == 0, f"--no-launch should work when UE5 is running: {result.stderr}"
        else:
            # When UE5 is not running, --no-launch should prevent launch and fail
            assert result.returncode != 0
            assert "No UE5 instance found" in result.stderr or "auto-launch disabled" in result.stderr

    def test_auto_launch_when_no_instance(self, ue5_test_project_path, ue5_uproject_path):
        """
        Test auto-launch functionality or normal execution when UE5 is available.

        WARNING: This test will launch UE5 editor if not running.
        Only run with: pytest --run-e2e --run-slow

        Test logic:
        - If UE5 is already running: Verify execution works via remote-execute
        - If UE5 is not running: Test auto-launch, wait for it to start, then execute
        """
        # Check if UE5 is already running
        executor = UE5RemoteExecution()
        ue5_running = executor.find_unreal_instance()
        if executor.mcast_sock:
            executor.mcast_sock.close()

        # Check if we can find UE5 editor on system
        editor_path = find_ue5_editor()
        if not editor_path and not ue5_running:
            pytest.skip("UE5 editor not found and no instance running - cannot test")

        if ue5_running:
            print("\n[Auto-Launch Test] UE5 already running - testing execution via remote-execute")
        else:
            print(f"\n[Auto-Launch Test] UE5 Editor found: {editor_path}")
            print(f"[Auto-Launch Test] Project: {ue5_uproject_path}")
            print("[Auto-Launch Test] Starting auto-launch test (may take 2-3 minutes)...")

        # Run remote-execute (will auto-launch if needed, or connect to existing)
        result = subprocess.run(
            [sys.executable, str(REMOTE_EXECUTE_SCRIPT),
             "--code", "import unreal; print(f'Execution SUCCESS! Engine: {unreal.SystemLibrary.get_engine_version()}')",
             "--project-path", str(ue5_uproject_path),
             "-v"],  # Verbose mode to see what's happening
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for UE5 to start
        )

        print(f"[Auto-Launch Test] Return code: {result.returncode}")
        print(f"[Auto-Launch Test] stdout: {result.stdout}")
        print(f"[Auto-Launch Test] stderr: {result.stderr}")

        # Verify success - whether via auto-launch or existing instance
        assert result.returncode == 0, f"Execution failed: {result.stderr}"
        assert "Execution SUCCESS" in result.stdout or "Success" in result.stdout


@pytest.mark.e2e
class TestConfigCheckIntegration:
    """E2E tests for config check integration with auto-launch."""

    def test_config_check_runs_before_launch(self, ue5_test_project_path):
        """Test that configuration is checked before attempting launch."""
        from ue5_remote.config import run_config_check

        # Run config check
        result = run_config_check(ue5_test_project_path, auto_fix=False)

        # Should complete without error
        assert result["status"] in ["ok", "needs_fix", "fixed", "error"]
        assert "python_plugin" in result
        assert "remote_execution" in result


@pytest.mark.e2e
@pytest.mark.slow
class TestAutoLaunchFromScratch:
    """
    E2E tests for the complete auto-launch workflow from a blank project.

    IMPORTANT: These tests REQUIRE that NO UE5 instance is running.
    They test the full workflow:
    1. Start with a completely blank project (no PythonScriptPlugin, no remote execution)
    2. Run remote-execute.py
    3. Verify it auto-configures the project
    4. Verify it launches UE5
    5. Verify code executes successfully

    Run with: pytest --run-e2e --run-slow -k "TestAutoLaunchFromScratch"
    """

    def test_full_auto_launch_workflow(self):
        """
        Test the complete auto-launch workflow from a blank project.

        This test verifies that remote-execute.py can:
        1. Detect missing PythonScriptPlugin and add it
        2. Detect missing remote execution settings and add them
        3. Find and launch UE5 editor
        4. Wait for UE5 to start
        5. Execute code successfully

        NOTE: This test will automatically close any running UE5 instances.
        """
        # Step 1: Check and close any running UE5 instances
        print("\n" + "="*60)
        print("[Auto-Launch Test] Checking for running UE5 instances...")

        executor = UE5RemoteExecution()
        if executor.find_unreal_instance():
            if executor.mcast_sock:
                executor.mcast_sock.close()
            print("[Auto-Launch Test] UE5 is running, closing it...")
            close_all_ue5_instances()

            # Verify UE5 is closed
            import time
            executor2 = UE5RemoteExecution()
            if executor2.find_unreal_instance():
                if executor2.mcast_sock:
                    executor2.mcast_sock.close()
                pytest.skip("Failed to close UE5 instances. Please close manually.")
            print("[Auto-Launch Test] UE5 successfully closed")
        else:
            if executor.mcast_sock:
                executor.mcast_sock.close()
            print("[Auto-Launch Test] No UE5 instance running")

        editor_path = find_ue5_editor()
        if not editor_path:
            pytest.skip("UE5 editor not found on system - cannot test auto-launch")

        # Step 2: Create a fresh blank project
        print("\n" + "="*60)
        print("[Auto-Launch Test] Creating fresh blank project...")
        uproject_path = create_blank_ue5_project(AUTO_LAUNCH_TEST_PROJECT_DIR, "AutoLaunchTestProject", clean_first=True)
        print(f"[Auto-Launch Test] Project created: {uproject_path}")

        # Verify project is truly blank
        with open(uproject_path, 'r', encoding='utf-8') as f:
            uproject_data = json.load(f)
        assert uproject_data["Plugins"] == [], "Project should have no plugins configured"

        ini_path = AUTO_LAUNCH_TEST_PROJECT_DIR / "Config" / "DefaultEngine.ini"
        ini_content = ini_path.read_text(encoding='utf-8')
        assert "PythonScriptPlugin" not in ini_content, "INI should have no Python plugin settings"
        assert "bRemoteExecution" not in ini_content, "INI should have no remote execution settings"

        print("[Auto-Launch Test] Verified project is blank (no plugins, no remote execution)")

        # Step 3: Run remote-execute.py (should auto-configure and launch)
        print(f"[Auto-Launch Test] Running remote-execute.py...")
        print(f"[Auto-Launch Test] Editor: {editor_path}")
        print("[Auto-Launch Test] This may take 2-3 minutes while UE5 starts...")
        print("="*60)

        result = subprocess.run(
            [sys.executable, str(REMOTE_EXECUTE_SCRIPT),
             "--code", "import unreal; print(f'AUTO-LAUNCH SUCCESS! Engine: {unreal.SystemLibrary.get_engine_version()}')",
             "--project-path", str(uproject_path),
             "-v"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        print(f"\n[Auto-Launch Test] Return code: {result.returncode}")
        print(f"[Auto-Launch Test] stdout:\n{result.stdout}")
        print(f"[Auto-Launch Test] stderr:\n{result.stderr}")

        # Step 4: Verify configuration was fixed
        print("\n[Auto-Launch Test] Verifying configuration was auto-fixed...")

        with open(uproject_path, 'r', encoding='utf-8') as f:
            uproject_data = json.load(f)

        python_plugin = next(
            (p for p in uproject_data.get("Plugins", []) if p.get("Name") == "PythonScriptPlugin"),
            None
        )
        assert python_plugin is not None, "PythonScriptPlugin should have been added"
        assert python_plugin.get("Enabled") is True, "PythonScriptPlugin should be enabled"
        print("[Auto-Launch Test] [OK] PythonScriptPlugin was added and enabled")

        ini_content = ini_path.read_text(encoding='utf-8').lower()
        assert "bremoteexecution" in ini_content, "bRemoteExecution should have been added"
        assert "true" in ini_content, "bRemoteExecution should be True"
        print("[Auto-Launch Test] [OK] Remote execution settings were added")

        # Step 5: Verify execution succeeded
        assert result.returncode == 0, f"Execution failed: {result.stderr}"
        assert "AUTO-LAUNCH SUCCESS" in result.stdout, "Code should have executed successfully"
        print("[Auto-Launch Test] [OK] Code executed successfully in UE5")

        print("\n" + "="*60)
        print("[Auto-Launch Test] FULL AUTO-LAUNCH WORKFLOW TEST PASSED!")
        print("="*60)

    def test_auto_config_fix_only(self):
        """
        Test that remote-execute.py correctly fixes project configuration.

        This test focuses on the configuration fix part without waiting for full UE5 launch.
        It verifies the config check and fix logic works correctly.
        """
        from ue5_remote.config import run_config_check

        # Create fresh blank project (use separate dir to avoid conflicts with full launch test)
        print("\n[Config Fix Test] Creating fresh blank project...")
        uproject_path = create_blank_ue5_project(CONFIG_FIX_TEST_PROJECT_DIR, "ConfigFixTestProject", clean_first=True)

        # Verify initially blank
        with open(uproject_path, 'r', encoding='utf-8') as f:
            initial_data = json.load(f)
        assert initial_data["Plugins"] == []

        # Run config check with auto_fix=True
        print("[Config Fix Test] Running config check with auto_fix=True...")
        result = run_config_check(CONFIG_FIX_TEST_PROJECT_DIR, auto_fix=True)

        print(f"[Config Fix Test] Result: {result['status']}")
        print(f"[Config Fix Test] Python Plugin: {result['python_plugin']}")
        print(f"[Config Fix Test] Remote Execution: {result['remote_execution']}")

        # Verify fixes were applied
        assert result["status"] == "fixed", f"Status should be 'fixed', got '{result['status']}'"
        assert result["python_plugin"]["enabled"] is True
        assert result["python_plugin"]["modified"] is True
        assert result["remote_execution"]["enabled"] is True
        assert result["remote_execution"]["modified"] is True

        # Verify files were actually modified
        with open(uproject_path, 'r', encoding='utf-8') as f:
            fixed_data = json.load(f)

        python_plugin = next(
            (p for p in fixed_data.get("Plugins", []) if p.get("Name") == "PythonScriptPlugin"),
            None
        )
        assert python_plugin is not None
        assert python_plugin.get("Enabled") is True

        ini_path = CONFIG_FIX_TEST_PROJECT_DIR / "Config" / "DefaultEngine.ini"
        ini_content = ini_path.read_text(encoding='utf-8').lower()
        assert "bremoteexecution" in ini_content

        print("[Config Fix Test] [OK] Configuration was correctly fixed")

        # Run config check again - should now be "ok"
        result2 = run_config_check(CONFIG_FIX_TEST_PROJECT_DIR, auto_fix=False)
        assert result2["status"] == "ok", "Second check should return 'ok'"
        print("[Config Fix Test] [OK] Second check confirms configuration is correct")
