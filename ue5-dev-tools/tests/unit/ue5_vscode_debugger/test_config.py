"""
Unit tests for UE5 project configuration checking and fixing.

Tests the config.py module that handles .uproject and DefaultEngine.ini validation.
"""

import pytest
import json
from pathlib import Path

from ue5_remote.config import (
    find_uproject,
    check_python_plugin,
    check_remote_execution,
    run_config_check
)


class TestFindUproject:
    """Test .uproject file discovery."""

    def test_find_uproject_exists(self, temp_uproject):
        """Test finding existing .uproject file."""
        result = find_uproject(temp_uproject)

        assert result is not None
        assert result.name == "TestProject.uproject"
        assert result.exists()

    def test_find_uproject_not_exists(self, tmp_path):
        """Test when no .uproject file exists."""
        empty_dir = tmp_path / "EmptyDir"
        empty_dir.mkdir()

        result = find_uproject(empty_dir)

        assert result is None

    def test_find_uproject_multiple(self, tmp_path):
        """Test when multiple .uproject files exist (picks first)."""
        project_dir = tmp_path / "MultiProject"
        project_dir.mkdir()

        (project_dir / "ProjectA.uproject").write_text("{}")
        (project_dir / "ProjectB.uproject").write_text("{}")

        result = find_uproject(project_dir)

        # Should return one of them (implementation picks first from glob)
        assert result is not None
        assert result.suffix == ".uproject"


class TestCheckPythonPlugin:
    """Test PythonScriptPlugin checking and fixing."""

    def test_plugin_not_in_plugins_array(self, temp_uproject):
        """Test detection when PythonScriptPlugin is missing."""
        uproject_path = temp_uproject / "TestProject.uproject"

        enabled, modified, message = check_python_plugin(uproject_path, auto_fix=False)

        assert enabled is False
        assert modified is False
        assert "not in Plugins array" in message

    def test_plugin_auto_fix_adds_plugin(self, temp_uproject):
        """Test auto-fix adds PythonScriptPlugin."""
        uproject_path = temp_uproject / "TestProject.uproject"

        enabled, modified, message = check_python_plugin(uproject_path, auto_fix=True)

        assert enabled is True
        assert modified is True
        assert "Added" in message

        # Verify file was modified
        with open(uproject_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        python_plugin = next(
            (p for p in config["Plugins"] if p.get("Name") == "PythonScriptPlugin"),
            None
        )
        assert python_plugin is not None
        assert python_plugin["Enabled"] is True

    def test_plugin_exists_but_disabled(self, tmp_path):
        """Test detection when plugin exists but is disabled."""
        project_dir = tmp_path / "DisabledPlugin"
        project_dir.mkdir()

        uproject_path = project_dir / "Test.uproject"
        uproject_path.write_text(json.dumps({
            "Plugins": [
                {"Name": "PythonScriptPlugin", "Enabled": False}
            ]
        }), encoding='utf-8')

        enabled, modified, message = check_python_plugin(uproject_path, auto_fix=False)

        assert enabled is False
        assert modified is False
        assert "disabled" in message

    def test_plugin_exists_disabled_auto_fix(self, tmp_path):
        """Test auto-fix enables disabled plugin."""
        project_dir = tmp_path / "DisabledPlugin"
        project_dir.mkdir()

        uproject_path = project_dir / "Test.uproject"
        uproject_path.write_text(json.dumps({
            "Plugins": [
                {"Name": "PythonScriptPlugin", "Enabled": False}
            ]
        }), encoding='utf-8')

        enabled, modified, message = check_python_plugin(uproject_path, auto_fix=True)

        assert enabled is True
        assert modified is True
        assert "Enabled" in message

        # Verify file was modified
        with open(uproject_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        assert config["Plugins"][0]["Enabled"] is True

    def test_plugin_already_enabled(self, temp_uproject_with_plugin):
        """Test when plugin is already correctly configured."""
        uproject_path = temp_uproject_with_plugin / "TestProjectWithPlugin.uproject"

        enabled, modified, message = check_python_plugin(uproject_path, auto_fix=False)

        assert enabled is True
        assert modified is False
        assert "correctly configured" in message

    def test_invalid_json_file(self, tmp_path):
        """Test handling of invalid JSON in .uproject."""
        project_dir = tmp_path / "InvalidJson"
        project_dir.mkdir()

        uproject_path = project_dir / "Test.uproject"
        uproject_path.write_text("{ invalid json }", encoding='utf-8')

        enabled, modified, message = check_python_plugin(uproject_path, auto_fix=False)

        assert enabled is False
        assert modified is False
        assert "Parse Error" in message or "JSON" in message

    def test_file_not_found(self, tmp_path):
        """Test handling of non-existent file."""
        uproject_path = tmp_path / "NonExistent.uproject"

        enabled, modified, message = check_python_plugin(uproject_path, auto_fix=False)

        assert enabled is False
        assert modified is False


class TestCheckRemoteExecution:
    """Test remote execution settings checking and fixing."""

    def test_ini_file_not_exists(self, temp_uproject):
        """Test when DefaultEngine.ini doesn't exist."""
        ini_path = temp_uproject / "Config" / "DefaultEngine.ini"

        enabled, modified, changes = check_remote_execution(ini_path, auto_fix=False)

        assert enabled is False
        assert modified is False
        assert any("does not exist" in c for c in changes)

    def test_ini_file_auto_fix_creates(self, temp_uproject):
        """Test auto-fix creates DefaultEngine.ini with correct settings."""
        ini_path = temp_uproject / "Config" / "DefaultEngine.ini"

        enabled, modified, changes = check_remote_execution(ini_path, auto_fix=True)

        assert enabled is True
        assert modified is True
        assert ini_path.exists()

        # Verify content (configparser lowercases keys, so check case-insensitive)
        content = ini_path.read_text(encoding='utf-8').lower()
        assert "bremoteexecution" in content
        assert "true" in content

    def test_ini_missing_section(self, tmp_path):
        """Test when ini exists but missing PythonScriptPlugin section."""
        project_dir = tmp_path / "MissingSection"
        project_dir.mkdir()
        config_dir = project_dir / "Config"
        config_dir.mkdir()

        ini_path = config_dir / "DefaultEngine.ini"
        ini_path.write_text("[SomeOtherSection]\nKey=Value\n", encoding='utf-8')

        enabled, modified, changes = check_remote_execution(ini_path, auto_fix=False)

        assert enabled is False
        assert any("Missing section" in c for c in changes)

    def test_ini_missing_section_auto_fix(self, tmp_path):
        """Test auto-fix adds missing section."""
        project_dir = tmp_path / "MissingSection"
        project_dir.mkdir()
        config_dir = project_dir / "Config"
        config_dir.mkdir()

        ini_path = config_dir / "DefaultEngine.ini"
        ini_path.write_text("[SomeOtherSection]\nKey=Value\n", encoding='utf-8')

        enabled, modified, changes = check_remote_execution(ini_path, auto_fix=True)

        assert enabled is True
        assert modified is True

        # configparser lowercases keys, check case-insensitive
        content = ini_path.read_text(encoding='utf-8')
        assert "PythonScriptPlugin" in content
        assert "bremoteexecution" in content.lower()

    def test_ini_remote_execution_disabled(self, tmp_path):
        """Test when bRemoteExecution is False."""
        project_dir = tmp_path / "DisabledRemote"
        project_dir.mkdir()
        config_dir = project_dir / "Config"
        config_dir.mkdir()

        ini_path = config_dir / "DefaultEngine.ini"
        ini_content = """[/Script/PythonScriptPlugin.PythonScriptPluginSettings]
bRemoteExecution = False
bDeveloperMode = True
"""
        ini_path.write_text(ini_content, encoding='utf-8')

        enabled, modified, changes = check_remote_execution(ini_path, auto_fix=False)

        assert enabled is False
        assert any("bRemoteExecution" in c for c in changes)

    def test_ini_remote_execution_auto_fix(self, tmp_path):
        """Test auto-fix enables remote execution."""
        project_dir = tmp_path / "DisabledRemote"
        project_dir.mkdir()
        config_dir = project_dir / "Config"
        config_dir.mkdir()

        ini_path = config_dir / "DefaultEngine.ini"
        ini_content = """[/Script/PythonScriptPlugin.PythonScriptPluginSettings]
bRemoteExecution = False
"""
        ini_path.write_text(ini_content, encoding='utf-8')

        enabled, modified, changes = check_remote_execution(ini_path, auto_fix=True)

        assert enabled is True
        assert modified is True

    def test_ini_already_configured(self, temp_uproject_with_plugin):
        """Test when ini is already correctly configured."""
        ini_path = temp_uproject_with_plugin / "Config" / "DefaultEngine.ini"

        enabled, modified, changes = check_remote_execution(ini_path, auto_fix=False)

        assert enabled is True
        assert modified is False


class TestRunConfigCheck:
    """Test full configuration check workflow."""

    def test_no_uproject_found(self, tmp_path):
        """Test error when no .uproject found."""
        empty_dir = tmp_path / "Empty"
        empty_dir.mkdir()

        result = run_config_check(empty_dir, auto_fix=False)

        assert result["status"] == "error"
        assert "No .uproject" in result["summary"]

    def test_needs_fix_status(self, temp_uproject):
        """Test needs_fix status when issues found."""
        result = run_config_check(temp_uproject, auto_fix=False)

        assert result["status"] == "needs_fix"
        assert result["python_plugin"]["enabled"] is False or result["remote_execution"]["enabled"] is False

    def test_fixed_status(self, temp_uproject):
        """Test fixed status after auto-fix."""
        result = run_config_check(temp_uproject, auto_fix=True)

        assert result["status"] == "fixed"
        assert result["restart_needed"] is True
        assert result["python_plugin"]["enabled"] is True
        assert result["remote_execution"]["enabled"] is True

    def test_ok_status_already_configured(self, temp_uproject_with_plugin):
        """Test ok status when already configured."""
        result = run_config_check(temp_uproject_with_plugin, auto_fix=False)

        assert result["status"] == "ok"
        assert result["python_plugin"]["enabled"] is True
        assert result["remote_execution"]["enabled"] is True
        assert result["restart_needed"] is False

    def test_result_contains_paths(self, temp_uproject):
        """Test result contains file paths."""
        result = run_config_check(temp_uproject, auto_fix=False)

        assert result["python_plugin"]["path"] is not None
        assert result["remote_execution"]["path"] is not None

    def test_fix_then_check(self, temp_uproject):
        """Test fix then check shows ok status."""
        # First fix
        result1 = run_config_check(temp_uproject, auto_fix=True)
        assert result1["status"] == "fixed"

        # Then check
        result2 = run_config_check(temp_uproject, auto_fix=False)
        assert result2["status"] == "ok"
