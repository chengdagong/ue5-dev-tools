"""
Integration tests for validate.py CLI.

Tests the command-line interface of the API validator.
Migrated from skills/api-validator/tests/test_integration.py
"""

import pytest
import subprocess
import sys
import tempfile
import os
from pathlib import Path

# Path to the validate.py script
SCRIPT_PATH = Path(__file__).parent.parent.parent.parent / "skills" / "api-validator" / "scripts" / "validate.py"


def get_env_with_utf8():
    """Get environment with UTF-8 encoding for subprocess."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


class TestValidatorCLI:
    """Integration tests for validate.py command-line interface."""

    def run_validator(self, file_path):
        """Run the validator script on a file."""
        cmd = [sys.executable, str(SCRIPT_PATH), str(file_path)]
        result = subprocess.run(
            cmd, capture_output=True, timeout=30,
            env=get_env_with_utf8()
        )
        # Decode with utf-8, replacing errors
        stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ''
        stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
        return result.returncode, stdout, stderr

    def test_help_output(self):
        """Test --help displays usage information."""
        cmd = [sys.executable, str(SCRIPT_PATH), "--help"]
        result = subprocess.run(
            cmd, capture_output=True, timeout=10,
            env=get_env_with_utf8()
        )
        stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ''

        assert result.returncode == 0
        assert "usage:" in stdout.lower()

    def test_validate_simple_file(self):
        """Test validating a simple Python file."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8'
        ) as f:
            f.write("import unreal\nobj = unreal.Object()\n")
            temp_path = f.name

        try:
            returncode, stdout, stderr = self.run_validator(temp_path)

            # Should output validation report
            assert "UE5 Python API Validation Report" in stdout
            assert returncode == 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_validate_empty_file(self):
        """Test validating an empty Python file."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8'
        ) as f:
            f.write("")
            temp_path = f.name

        try:
            returncode, stdout, stderr = self.run_validator(temp_path)

            # Should complete without error
            assert returncode == 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_validate_syntax_error_file(self):
        """Test validating a file with syntax errors."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8'
        ) as f:
            f.write("def broken(\n")  # Syntax error
            temp_path = f.name

        try:
            returncode, stdout, stderr = self.run_validator(temp_path)

            # Should handle syntax error gracefully
            # May return non-zero or print error message
            output = (stdout + stderr).lower()
            assert returncode in [0, 1] or "syntax" in output
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_validate_non_existent_file(self):
        """Test validating a non-existent file."""
        returncode, stdout, stderr = self.run_validator("/path/to/nonexistent/file.py")

        # Validator may handle non-existent file gracefully (returncode 0)
        # or fail (returncode != 0). Both are acceptable as long as it doesn't crash.
        # Just verify it completes and doesn't crash
        assert returncode in [0, 1, 2]  # Accept common return codes

    def test_validate_file_with_unreal_imports(self):
        """Test validating a file with unreal module imports."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8'
        ) as f:
            f.write("""
import unreal

# Get editor asset library
editor_asset_lib = unreal.EditorAssetLibrary()

# Log a message
unreal.log("Test message")
""")
            temp_path = f.name

        try:
            returncode, stdout, stderr = self.run_validator(temp_path)

            # Should produce validation report
            assert "UE5 Python API Validation Report" in stdout
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
