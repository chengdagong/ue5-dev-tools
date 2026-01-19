"""
E2E test configuration and fixtures.

These fixtures require a real UE5 editor to be running or launchable.
"""

import pytest
import os
import sys
import json
import re
import subprocess
import time
from pathlib import Path

# Add lib to path for imports
LIB_PATH = Path(__file__).parent.parent.parent / "skills" / "ue5-vscode-debugger" / "lib"
if str(LIB_PATH) not in sys.path:
    sys.path.insert(0, str(LIB_PATH))

from ue5_remote import UE5RemoteExecution
from ue5_remote.utils import find_ue5_editor
from ue5_remote.config import run_config_check

# Test project directory (inside tests/)
TESTS_DIR = Path(__file__).parent.parent
AUTO_GENERATED_PROJECT_DIR = TESTS_DIR / "fixtures" / "E2ETestProject"


def is_ue5_available() -> bool:
    """Check if any UE5 instance is responding to multicast."""
    executor = UE5RemoteExecution()
    try:
        return executor.find_unreal_instance()
    except Exception:
        return False
    finally:
        if executor.mcast_sock:
            try:
                executor.mcast_sock.close()
            except Exception:
                pass


def can_launch_ue5() -> bool:
    """Check if UE5 editor can be found for auto-launch."""
    return find_ue5_editor() is not None


def close_all_ue5_instances() -> bool:
    """
    Close all running UE5 editor instances.

    Returns:
        True if any instances were closed, False otherwise
    """
    import platform

    closed_any = False

    if platform.system() == "Windows":
        result = subprocess.run(
            ["taskkill", "/F", "/IM", "UnrealEditor.exe"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            closed_any = True
            print("[E2E] Closed UE5 instances via taskkill")
    else:
        result = subprocess.run(
            ["pkill", "-f", "UnrealEditor"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            closed_any = True
            print("[E2E] Closed UE5 instances via pkill")

    if closed_any:
        print("[E2E] Waiting for UE5 to fully close...")
        time.sleep(5)

        # Verify no instances are running
        executor = UE5RemoteExecution()
        for _ in range(3):
            if not executor.find_unreal_instance():
                break
            time.sleep(2)
        if executor.mcast_sock:
            executor.mcast_sock.close()

    return closed_any


def launch_ue5_and_wait(uproject_path: Path, executor: UE5RemoteExecution, timeout: int = 120) -> bool:
    """
    Launch UE5 editor with the given project and wait for it to be ready.

    Args:
        uproject_path: Path to the .uproject file
        executor: UE5RemoteExecution instance to use for checking readiness
        timeout: Maximum time to wait in seconds

    Returns:
        True if UE5 started successfully, False otherwise
    """
    # Find editor
    editor_path = find_ue5_editor()
    if not editor_path:
        print("[E2E] Could not find UE5 editor executable")
        return False

    # Check and fix configuration
    project_dir = uproject_path.parent
    print(f"[E2E] Checking project configuration: {project_dir}")
    config_result = run_config_check(project_dir, auto_fix=True)

    if config_result["status"] == "error":
        print(f"[E2E] Configuration check failed: {config_result['summary']}")
        return False

    if config_result["python_plugin"]["modified"]:
        print(f"[E2E] Fixed Python Plugin: {config_result['python_plugin']['message']}")

    if config_result["remote_execution"]["modified"]:
        print(f"[E2E] Fixed Remote Execution: {config_result['remote_execution']['message']}")

    # Launch editor
    print(f"[E2E] Launching UE5 Editor: {editor_path}")
    print(f"[E2E] Project: {uproject_path}")

    subprocess.Popen(
        [str(editor_path), str(uproject_path)],
        start_new_session=True
    )

    # Wait for editor to start
    max_attempts = timeout // 2
    print(f"[E2E] Waiting for UE5 to start (timeout: {timeout}s)...")

    for i in range(max_attempts):
        if executor.find_unreal_instance():
            print(f"[E2E] UE5 instance found after {(i + 1) * 2}s")
            return True
        time.sleep(2.0)

    print(f"[E2E] Timeout waiting for UE5 to start after {timeout}s")
    return False


def detect_ue5_version() -> str:
    """
    Detect installed UE5 version from editor path.

    Returns:
        Version string like "5.4" or "5.5", defaults to "5.4"
    """
    editor_path = find_ue5_editor()
    if editor_path:
        # Extract version from path like "UE_5.4" or "UE_5.5"
        path_str = str(editor_path)
        match = re.search(r'UE_(\d+\.\d+)', path_str)
        if match:
            return match.group(1)
    return "5.4"  # Default


def create_blank_ue5_project(
    project_dir: Path,
    project_name: str = "E2ETestProject",
    clean_first: bool = False
) -> Path:
    """
    Create a minimal blank UE5 project for testing.

    This creates a truly blank project WITHOUT PythonScriptPlugin or remote execution
    settings pre-configured. This allows testing of remote-execute's auto-configuration
    and auto-launch capabilities.

    Args:
        project_dir: Directory to create the project in
        project_name: Name of the project
        clean_first: If True, remove existing project directory before creating

    Returns:
        Path to the created .uproject file
    """
    import shutil

    # Remove existing project if requested
    if clean_first and project_dir.exists():
        shutil.rmtree(project_dir)

    # Create directory structure
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "Config").mkdir(exist_ok=True)
    (project_dir / "Content").mkdir(exist_ok=True)
    (project_dir / "Source").mkdir(exist_ok=True)

    # Detect UE5 version
    ue_version = detect_ue5_version()

    # Create .uproject file - NO plugins pre-configured
    # remote-execute should auto-configure PythonScriptPlugin when needed
    uproject_path = project_dir / f"{project_name}.uproject"
    uproject_content = {
        "FileVersion": 3,
        "EngineAssociation": ue_version,
        "Category": "",
        "Description": "Auto-generated test project for E2E testing",
        "Modules": [],
        "Plugins": []  # Empty - let remote-execute configure this
    }

    uproject_path.write_text(
        json.dumps(uproject_content, indent="\t"),
        encoding='utf-8'
    )

    # Create minimal DefaultEngine.ini - NO remote execution settings
    # remote-execute should auto-configure these when needed
    default_engine_ini = project_dir / "Config" / "DefaultEngine.ini"
    ini_content = """[/Script/EngineSettings.GameMapsSettings]
GameDefaultMap=
EditorStartupMap=
"""
    default_engine_ini.write_text(ini_content, encoding='utf-8')

    # Create DefaultGame.ini
    default_game_ini = project_dir / "Config" / "DefaultGame.ini"
    game_ini_content = f"""[/Script/EngineSettings.GeneralProjectSettings]
ProjectID=E2ETestProject
ProjectName={project_name}
"""
    default_game_ini.write_text(game_ini_content, encoding='utf-8')

    # Create DefaultEditor.ini
    default_editor_ini = project_dir / "Config" / "DefaultEditor.ini"
    default_editor_ini.write_text("", encoding='utf-8')

    print(f"[E2E Setup] Created blank UE5 project at: {project_dir}")
    print(f"[E2E Setup] UE5 version: {ue_version}")
    print("[E2E Setup] Note: PythonScriptPlugin and remote execution NOT pre-configured")
    print("[E2E Setup] remote-execute will auto-configure these settings when needed")

    return uproject_path


@pytest.fixture(scope="session")
def ue5_test_project_path():
    """
    Path to a test UE5 project.

    Priority:
    1. Use UE5_TEST_PROJECT_PATH environment variable if set
    2. Auto-generate a blank test project in tests/fixtures/E2ETestProject/

    Returns:
        Path to the test project directory
    """
    # Check environment variable first
    env_path = os.environ.get("UE5_TEST_PROJECT_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists():
            print(f"[E2E Setup] Using project from environment: {path}")
            return path
        else:
            print(f"[E2E Setup] Warning: UE5_TEST_PROJECT_PATH={env_path} does not exist")

    # Auto-generate blank project
    print("[E2E Setup] No UE5_TEST_PROJECT_PATH set, auto-generating test project...")

    # Check if UE5 is installed (required for auto-generated project to work)
    if not find_ue5_editor():
        pytest.skip("UE5 editor not found - cannot create test project")

    # Create the project
    create_blank_ue5_project(AUTO_GENERATED_PROJECT_DIR)

    return AUTO_GENERATED_PROJECT_DIR


@pytest.fixture(scope="session")
def ue5_uproject_path(ue5_test_project_path):
    """
    Path to the .uproject file in the test project.

    Returns:
        Path to the .uproject file
    """
    uproject_files = list(ue5_test_project_path.glob("*.uproject"))
    if not uproject_files:
        pytest.skip(f"No .uproject file found in {ue5_test_project_path}")
    return uproject_files[0]


@pytest.fixture(scope="session")
def ue5_project_name(ue5_uproject_path):
    """
    Name of the UE5 test project.

    Returns:
        Project name string
    """
    return ue5_uproject_path.stem


@pytest.fixture(scope="function")
def ue5_executor(ue5_project_name, ue5_uproject_path):
    """
    Provide a connected UE5RemoteExecution instance.

    This fixture:
    1. Creates an executor with the test project name
    2. Finds a running UE5 instance (or auto-launches one)
    3. Opens a command connection
    4. Yields the executor for test use
    5. Closes the connection after the test

    Auto-launches UE5 if no instance is found and UE5 is installed.
    """
    executor = UE5RemoteExecution(project_name=ue5_project_name)

    # Try to find existing instance
    if not executor.find_unreal_instance():
        # Try to auto-launch UE5
        if not can_launch_ue5():
            pytest.skip("No UE5 instance found and UE5 editor not installed")

        # Launch UE5 with the test project
        if not launch_ue5_and_wait(ue5_uproject_path, executor, timeout=180):
            pytest.skip("Failed to auto-launch UE5 editor")

    if not executor.open_connection():
        pytest.skip("Could not open connection to UE5")

    yield executor

    executor.close_connection()


@pytest.fixture(scope="function")
def ue5_executor_any_project(ue5_uproject_path):
    """
    Provide a connected UE5RemoteExecution instance without project filtering.

    Useful for tests that don't care about project name.
    Auto-launches UE5 with the test project if no instance is found.
    """
    executor = UE5RemoteExecution()

    if not executor.find_unreal_instance():
        # Try to auto-launch UE5 with test project
        if not can_launch_ue5():
            pytest.skip("No UE5 instance found and UE5 editor not installed")

        if not launch_ue5_and_wait(ue5_uproject_path, executor, timeout=180):
            pytest.skip("Failed to auto-launch UE5 editor")

    if not executor.open_connection():
        pytest.skip("Could not open connection to UE5")

    yield executor

    executor.close_connection()


@pytest.fixture
def sample_scripts_dir():
    """Path to sample test scripts."""
    return Path(__file__).parent.parent / "fixtures" / "sample_scripts"


# Helper function to check UE5 availability for markers
def pytest_configure(config):
    """Configure E2E-specific markers."""
    config.addinivalue_line(
        "markers",
        "requires_ue5_running: Test requires a running UE5 instance"
    )
    config.addinivalue_line(
        "markers",
        "requires_ue5_launchable: Test requires UE5 to be installed for auto-launch"
    )
