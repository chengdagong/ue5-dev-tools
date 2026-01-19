"""
Integration tests for configuration check and fix workflow.

Tests the complete workflow from broken configuration to working state.
"""

import pytest
import json
from pathlib import Path

from ue5_remote.config import run_config_check


class TestConfigCheckToFixWorkflow:
    """Test complete configuration check-to-fix workflow."""

    @pytest.fixture
    def broken_project(self, tmp_path):
        """Create a project with missing Python plugin and remote execution."""
        project_dir = tmp_path / "BrokenProject"
        project_dir.mkdir()

        # Create .uproject without Python plugin
        uproject = project_dir / "BrokenProject.uproject"
        uproject.write_text(json.dumps({
            "FileVersion": 3,
            "EngineAssociation": "5.4",
            "Plugins": [
                {"Name": "SomeOtherPlugin", "Enabled": True}
            ]
        }, indent=2), encoding='utf-8')

        # Create Config directory without DefaultEngine.ini
        (project_dir / "Config").mkdir()

        return project_dir

    @pytest.fixture
    def partially_broken_project(self, tmp_path):
        """Create a project with Python plugin but missing remote execution."""
        project_dir = tmp_path / "PartialProject"
        project_dir.mkdir()

        # Create .uproject with Python plugin
        uproject = project_dir / "PartialProject.uproject"
        uproject.write_text(json.dumps({
            "FileVersion": 3,
            "EngineAssociation": "5.4",
            "Plugins": [
                {"Name": "PythonScriptPlugin", "Enabled": True}
            ]
        }, indent=2), encoding='utf-8')

        # Create Config directory without DefaultEngine.ini
        (project_dir / "Config").mkdir()

        return project_dir

    def test_check_broken_project_reports_issues(self, broken_project):
        """Test that checking a broken project reports issues correctly."""
        result = run_config_check(broken_project, auto_fix=False)

        assert result["status"] == "needs_fix"
        assert result["python_plugin"]["enabled"] is False
        assert result["remote_execution"]["enabled"] is False
        assert result["restart_needed"] is False  # No changes made

    def test_fix_broken_project(self, broken_project):
        """Test fixing a completely broken project."""
        result = run_config_check(broken_project, auto_fix=True)

        assert result["status"] == "fixed"
        assert result["python_plugin"]["enabled"] is True
        assert result["python_plugin"]["modified"] is True
        assert result["remote_execution"]["enabled"] is True
        assert result["remote_execution"]["modified"] is True
        assert result["restart_needed"] is True

    def test_verify_after_fix(self, broken_project):
        """Test that verification after fix shows ok status."""
        # First fix
        fix_result = run_config_check(broken_project, auto_fix=True)
        assert fix_result["status"] == "fixed"

        # Then verify
        check_result = run_config_check(broken_project, auto_fix=False)
        assert check_result["status"] == "ok"
        assert check_result["python_plugin"]["enabled"] is True
        assert check_result["remote_execution"]["enabled"] is True
        assert check_result["restart_needed"] is False

    def test_fix_partial_project(self, partially_broken_project):
        """Test fixing a partially broken project."""
        result = run_config_check(partially_broken_project, auto_fix=True)

        # Should fix remote execution
        assert result["status"] == "fixed"
        assert result["python_plugin"]["enabled"] is True
        assert result["python_plugin"]["modified"] is False  # Already correct
        assert result["remote_execution"]["enabled"] is True
        assert result["remote_execution"]["modified"] is True

    def test_idempotent_fix(self, broken_project):
        """Test that running fix multiple times is idempotent."""
        # First fix
        result1 = run_config_check(broken_project, auto_fix=True)
        assert result1["status"] == "fixed"

        # Second fix - should be ok, no modifications
        result2 = run_config_check(broken_project, auto_fix=True)
        assert result2["status"] == "ok"
        assert result2["python_plugin"]["modified"] is False
        assert result2["remote_execution"]["modified"] is False

    def test_already_configured_project(self, temp_uproject_with_plugin):
        """Test checking an already configured project."""
        result = run_config_check(temp_uproject_with_plugin, auto_fix=False)

        assert result["status"] == "ok"
        assert result["python_plugin"]["enabled"] is True
        assert result["remote_execution"]["enabled"] is True
        assert result["restart_needed"] is False
        assert "All good" in result["summary"] or result["status"] == "ok"


class TestConfigFileIntegrity:
    """Test that config files maintain integrity after modifications."""

    def test_uproject_json_valid_after_fix(self, tmp_path):
        """Test that .uproject remains valid JSON after fix."""
        project_dir = tmp_path / "JsonTest"
        project_dir.mkdir()

        # Create minimal .uproject
        uproject = project_dir / "JsonTest.uproject"
        original_content = {
            "FileVersion": 3,
            "EngineAssociation": "5.4",
            "Category": "Game",
            "Description": "Test project",
            "Plugins": []
        }
        uproject.write_text(json.dumps(original_content, indent=2), encoding='utf-8')
        (project_dir / "Config").mkdir()

        # Fix the project
        run_config_check(project_dir, auto_fix=True)

        # Verify JSON is still valid
        with open(uproject, 'r', encoding='utf-8') as f:
            modified_content = json.load(f)

        # Check original fields preserved
        assert modified_content["FileVersion"] == 3
        assert modified_content["EngineAssociation"] == "5.4"
        assert modified_content["Category"] == "Game"

        # Check plugin was added
        python_plugin = next(
            (p for p in modified_content["Plugins"] if p["Name"] == "PythonScriptPlugin"),
            None
        )
        assert python_plugin is not None
        assert python_plugin["Enabled"] is True

    def test_existing_plugins_preserved(self, tmp_path):
        """Test that existing plugins are preserved when adding Python plugin."""
        project_dir = tmp_path / "PluginTest"
        project_dir.mkdir()

        # Create .uproject with existing plugins
        uproject = project_dir / "PluginTest.uproject"
        uproject.write_text(json.dumps({
            "FileVersion": 3,
            "Plugins": [
                {"Name": "ExistingPlugin1", "Enabled": True},
                {"Name": "ExistingPlugin2", "Enabled": False}
            ]
        }, indent=2), encoding='utf-8')
        (project_dir / "Config").mkdir()

        # Fix the project
        run_config_check(project_dir, auto_fix=True)

        # Verify existing plugins preserved
        with open(uproject, 'r', encoding='utf-8') as f:
            content = json.load(f)

        plugin_names = [p["Name"] for p in content["Plugins"]]
        assert "ExistingPlugin1" in plugin_names
        assert "ExistingPlugin2" in plugin_names
        assert "PythonScriptPlugin" in plugin_names

    def test_ini_file_created_correctly(self, tmp_path):
        """Test that DefaultEngine.ini is created with correct format."""
        project_dir = tmp_path / "IniTest"
        project_dir.mkdir()

        uproject = project_dir / "IniTest.uproject"
        uproject.write_text(json.dumps({"FileVersion": 3, "Plugins": []}))
        (project_dir / "Config").mkdir()

        # Fix the project
        run_config_check(project_dir, auto_fix=True)

        # Verify ini file content
        ini_path = project_dir / "Config" / "DefaultEngine.ini"
        assert ini_path.exists()

        # configparser lowercases keys, check case-insensitive
        content = ini_path.read_text(encoding='utf-8')
        assert "PythonScriptPlugin" in content
        assert "bremoteexecution" in content.lower()
        assert "true" in content.lower()


class TestConfigErrorHandling:
    """Test configuration error handling."""

    def test_missing_project_directory(self, tmp_path):
        """Test handling of non-existent project directory."""
        non_existent = tmp_path / "NonExistent"

        result = run_config_check(non_existent, auto_fix=False)

        assert result["status"] == "error"

    def test_empty_project_directory(self, tmp_path):
        """Test handling of empty project directory."""
        empty_dir = tmp_path / "Empty"
        empty_dir.mkdir()

        result = run_config_check(empty_dir, auto_fix=False)

        assert result["status"] == "error"
        assert "No .uproject" in result["summary"]

    def test_invalid_uproject_json(self, tmp_path):
        """Test handling of invalid JSON in .uproject."""
        project_dir = tmp_path / "InvalidJson"
        project_dir.mkdir()

        uproject = project_dir / "InvalidJson.uproject"
        uproject.write_text("{ this is not valid json }", encoding='utf-8')
        (project_dir / "Config").mkdir()

        result = run_config_check(project_dir, auto_fix=False)

        # Should report error for python plugin
        assert result["python_plugin"]["enabled"] is False
        assert "Parse Error" in result["python_plugin"]["message"] or "JSON" in result["python_plugin"]["message"]
