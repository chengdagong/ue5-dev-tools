"""
Shared pytest configuration and fixtures for ue5-dev-tools tests.
"""

import pytest
import sys
import json
from pathlib import Path

# Add skill lib directories to Python path
PLUGIN_ROOT = Path(__file__).parent.parent
SKILLS_ROOT = PLUGIN_ROOT / "skills"

# ue5-python-executor library
UE5_EXECUTOR_LIB = SKILLS_ROOT / "ue5-python-executor" / "lib"
if str(UE5_EXECUTOR_LIB) not in sys.path:
    sys.path.insert(0, str(UE5_EXECUTOR_LIB))

# api-validator scripts
API_VALIDATOR_SCRIPTS = SKILLS_ROOT / "api-validator" / "scripts"
if str(API_VALIDATOR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(API_VALIDATOR_SCRIPTS))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "e2e: End-to-end tests requiring real UE5")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "requires_ue5_running: Requires running UE5 instance")
    config.addinivalue_line("markers", "requires_ue5_launchable: Requires UE5 installation")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers and options."""
    # If not running E2E tests, skip them by default
    if not config.getoption("--run-e2e", default=False):
        skip_e2e = pytest.mark.skip(reason="E2E tests disabled (use --run-e2e to enable)")
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)

    # Skip slow tests unless explicitly requested
    if not config.getoption("--run-slow", default=False):
        skip_slow = pytest.mark.skip(reason="Slow tests disabled (use --run-slow to enable)")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run end-to-end tests that require real UE5 editor"
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests"
    )


# ============================================================================
# Shared Fixtures
# ============================================================================

@pytest.fixture
def temp_uproject(tmp_path):
    """
    Create a temporary minimal .uproject structure.

    Returns:
        Path to the temporary project directory
    """
    project_dir = tmp_path / "TestProject"
    project_dir.mkdir()

    uproject = project_dir / "TestProject.uproject"
    uproject.write_text(json.dumps({
        "FileVersion": 3,
        "EngineAssociation": "5.4",
        "Plugins": []
    }, indent=2), encoding='utf-8')

    (project_dir / "Config").mkdir()

    return project_dir


@pytest.fixture
def temp_uproject_with_plugin(tmp_path):
    """
    Create a temporary .uproject with PythonScriptPlugin already enabled.

    Returns:
        Path to the temporary project directory
    """
    project_dir = tmp_path / "TestProjectWithPlugin"
    project_dir.mkdir()

    uproject = project_dir / "TestProjectWithPlugin.uproject"
    uproject.write_text(json.dumps({
        "FileVersion": 3,
        "EngineAssociation": "5.4",
        "Plugins": [
            {"Name": "PythonScriptPlugin", "Enabled": True}
        ]
    }, indent=2), encoding='utf-8')

    config_dir = project_dir / "Config"
    config_dir.mkdir()

    # Create DefaultEngine.ini with remote execution enabled
    ini_content = """[/Script/PythonScriptPlugin.PythonScriptPluginSettings]
bRemoteExecution = True
bDeveloperMode = True
RemoteExecutionMulticastBindAddress = 0.0.0.0
"""
    (config_dir / "DefaultEngine.ini").write_text(ini_content, encoding='utf-8')

    return project_dir


@pytest.fixture
def plugin_root():
    """Return the plugin root directory."""
    return PLUGIN_ROOT


@pytest.fixture
def skills_root():
    """Return the skills root directory."""
    return SKILLS_ROOT


@pytest.fixture
def sample_pong_response():
    """
    Standard pong response from UE5 for testing.

    Returns:
        bytes: JSON-encoded pong message
    """
    return json.dumps({
        "type": "pong",
        "source": "ue5_test_node",
        "data": {
            "project_name": "TestProject",
            "engine_version": "5.4.0"
        }
    }).encode('utf-8')


@pytest.fixture
def sample_command_success_response():
    """
    Standard successful command response from UE5.

    Returns:
        bytes: JSON-encoded command result message
    """
    return json.dumps({
        "type": "command_result",
        "source": "ue5_test_node",
        "data": {
            "success": True,
            "result": "42",
            "output": [{"type": "log", "output": "Hello from UE5"}]
        }
    }).encode('utf-8')


@pytest.fixture
def sample_command_error_response():
    """
    Standard error command response from UE5.

    Returns:
        bytes: JSON-encoded command error message
    """
    return json.dumps({
        "type": "command_result",
        "source": "ue5_test_node",
        "data": {
            "success": False,
            "result": "",
            "output": [{"type": "error", "output": "NameError: name 'foo' is not defined"}]
        }
    }).encode('utf-8')
