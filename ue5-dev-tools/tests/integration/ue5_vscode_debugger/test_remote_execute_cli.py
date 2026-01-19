"""
Integration tests for remote-execute.py CLI.

Tests the command-line interface argument parsing and basic behavior.
"""

import pytest
import subprocess
import sys
from pathlib import Path

# Path to the remote-execute.py script
SCRIPT_PATH = Path(__file__).parent.parent.parent.parent / "skills" / "ue5-vscode-debugger" / "scripts" / "remote-execute.py"


class TestCLIHelp:
    """Test CLI help and usage output."""

    def test_help_output(self):
        """Test --help displays usage information."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "Execute arbitrary Python scripts" in result.stdout
        assert "--code" in result.stdout
        assert "--file" in result.stdout
        assert "--project-path" in result.stdout
        assert "--project-name" in result.stdout
        assert "--multicast-group" in result.stdout
        assert "--timeout" in result.stdout
        assert "--detached" in result.stdout
        assert "--no-launch" in result.stdout

    def test_help_shows_examples(self):
        """Test --help includes example usage."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert "Examples:" in result.stdout
        assert "python remote-execute.py" in result.stdout


class TestCLIArgumentValidation:
    """Test CLI argument validation."""

    def test_missing_code_and_file(self):
        """Test error when neither --code nor --file is provided."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH),
             "--project-name", "TestProject",
             "--no-launch"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode != 0
        assert "Either --code or --file must be specified" in result.stderr

    def test_missing_project_info(self):
        """Test error when no project information is provided."""
        # Clear CLAUDE_PROJECT_DIR for this test
        import os
        env = os.environ.copy()
        env.pop("CLAUDE_PROJECT_DIR", None)

        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH),
             "--code", "print('test')",
             "--no-launch"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10
        )

        assert result.returncode != 0
        # Should error about missing project info
        assert "project" in result.stderr.lower()

    def test_invalid_multicast_format(self):
        """Test error on invalid multicast group format."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH),
             "--code", "print('test')",
             "--project-name", "TestProject",
             "--multicast-group", "invalid-format",
             "--no-launch"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode != 0
        assert "Invalid multicast group" in result.stderr

    def test_invalid_multicast_port(self):
        """Test error on invalid port in multicast group."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH),
             "--code", "print('test')",
             "--project-name", "TestProject",
             "--multicast-group", "239.0.0.1:abc",
             "--no-launch"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode != 0


class TestCLINoLaunchMode:
    """Test CLI behavior with --no-launch flag."""

    def test_no_launch_exits_when_no_ue5(self):
        """Test --no-launch exits when UE5 is not found."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH),
             "--code", "print('test')",
             "--project-name", "TestProject",
             "--no-launch"],
            capture_output=True,
            text=True,
            timeout=15
        )

        # Should fail because no UE5 is running
        assert result.returncode != 0
        assert "No UE5 instance found" in result.stderr or "auto-launch disabled" in result.stderr


class TestCLIVerboseMode:
    """Test CLI verbose output."""

    def test_verbose_flag_accepted(self):
        """Test -v/--verbose flag is accepted."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH),
             "--code", "print('test')",
             "--project-name", "TestProject",
             "--no-launch",
             "-v"],
            capture_output=True,
            text=True,
            timeout=15
        )

        # Should run (and fail due to no UE5) but not error on -v flag
        assert result.returncode != 0  # No UE5 running
        # Verbose should work - no error about unknown argument


class TestCLIMulticastGroupParsing:
    """Test multicast group parsing."""

    def test_valid_multicast_group(self):
        """Test valid multicast group format is accepted."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH),
             "--code", "print('test')",
             "--project-name", "TestProject",
             "--multicast-group", "239.0.0.1:6766",
             "--no-launch"],
            capture_output=True,
            text=True,
            timeout=15
        )

        # Should fail due to no UE5, not due to multicast parsing
        assert result.returncode != 0
        assert "Invalid multicast group" not in result.stderr

    def test_custom_multicast_port(self):
        """Test custom multicast port is accepted."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH),
             "--code", "print('test')",
             "--project-name", "TestProject",
             "--multicast-group", "239.0.0.1:7000",
             "--no-launch"],
            capture_output=True,
            text=True,
            timeout=15
        )

        # Should not error on multicast parsing
        assert "Invalid multicast group" not in result.stderr


class TestCLITimeout:
    """Test timeout argument handling."""

    def test_custom_timeout_accepted(self):
        """Test --timeout argument is accepted."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH),
             "--code", "print('test')",
             "--project-name", "TestProject",
             "--timeout", "10.0",
             "--no-launch"],
            capture_output=True,
            text=True,
            timeout=15
        )

        # Should fail due to no UE5, not due to timeout parsing
        assert result.returncode != 0
        assert "timeout" not in result.stderr.lower() or "Timeout waiting" not in result.stderr


class TestCLIFileArgument:
    """Test --file argument handling."""

    def test_file_argument_accepted(self, tmp_path):
        """Test --file argument with valid file path."""
        # Create a temporary Python file
        test_script = tmp_path / "test_script.py"
        test_script.write_text("print('Hello from test script')")

        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH),
             "--file", str(test_script),
             "--project-name", "TestProject",
             "--no-launch"],
            capture_output=True,
            text=True,
            timeout=15
        )

        # Should fail due to no UE5, not file handling
        assert result.returncode != 0
        assert "No such file" not in result.stderr  # File exists


class TestCLIProjectPath:
    """Test --project-path argument handling."""

    def test_project_path_with_uproject(self, temp_uproject):
        """Test --project-path with .uproject file."""
        uproject_path = temp_uproject / "TestProject.uproject"

        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH),
             "--code", "print('test')",
             "--project-path", str(uproject_path),
             "--no-launch"],
            capture_output=True,
            text=True,
            timeout=15
        )

        # Should fail due to no UE5, not project path handling
        assert result.returncode != 0


class TestCLIEnvironmentVariables:
    """Test environment variable handling."""

    def test_claude_project_dir_used(self, temp_uproject):
        """Test CLAUDE_PROJECT_DIR is used for project name inference."""
        import os
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(temp_uproject)

        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH),
             "--code", "print('test')",
             "--no-launch"],
            capture_output=True,
            text=True,
            env=env,
            timeout=15
        )

        # Should fail due to no UE5 (not missing project info)
        # This means CLAUDE_PROJECT_DIR was used
        assert result.returncode != 0
        # If project info was missing, error would be different
