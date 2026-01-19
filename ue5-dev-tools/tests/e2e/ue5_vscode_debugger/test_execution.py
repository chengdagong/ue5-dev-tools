"""
E2E tests for Python script execution in UE5.

These tests require a running UE5 editor with Python plugin enabled.
"""

import pytest
from pathlib import Path

from ue5_remote import UE5RemoteExecution


@pytest.mark.e2e
class TestScriptExecution:
    """E2E tests for Python script execution in UE5."""

    def test_execute_simple_print(self, ue5_executor):
        """Test executing simple print statement."""
        result = ue5_executor.execute_command(
            "print('Hello from E2E test')",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        assert result["success"] is True

    def test_evaluate_simple_expression(self, ue5_executor):
        """Test evaluating a simple Python expression."""
        result = ue5_executor.execute_command(
            "1 + 1",
            exec_type=UE5RemoteExecution.ExecTypes.EVALUATE_STATEMENT
        )

        assert result["success"] is True
        # Result should contain "2"
        assert "2" in str(result.get("result", ""))

    def test_evaluate_string_expression(self, ue5_executor):
        """Test evaluating a string expression."""
        result = ue5_executor.execute_command(
            "'Hello' + ' World'",
            exec_type=UE5RemoteExecution.ExecTypes.EVALUATE_STATEMENT
        )

        assert result["success"] is True
        assert "Hello World" in str(result.get("result", ""))

    def test_execute_multiline_code(self, ue5_executor):
        """Test executing multiline Python code."""
        code = """
x = 10
y = 20
print(f'Sum: {x + y}')
"""
        # Multiline code must use EXECUTE_FILE type
        result = ue5_executor.execute_command(
            code,
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_FILE
        )

        assert result["success"] is True

    def test_execute_import_statement(self, ue5_executor):
        """Test executing import statements."""
        result = ue5_executor.execute_command(
            "import sys; print(sys.version)",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        assert result["success"] is True

    def test_execute_unreal_module_available(self, ue5_executor):
        """Test that unreal module is available."""
        result = ue5_executor.execute_command(
            "import unreal; print(type(unreal))",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        assert result["success"] is True

    def test_execute_get_engine_version(self, ue5_executor):
        """Test getting engine version via unreal module."""
        result = ue5_executor.execute_command(
            "import unreal; print(unreal.SystemLibrary.get_engine_version())",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        assert result["success"] is True

    def test_execute_with_syntax_error(self, ue5_executor):
        """Test handling of syntax errors in executed code."""
        result = ue5_executor.execute_command(
            "print('unclosed string",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        # Should return error but not crash
        assert result["success"] is False

    def test_execute_with_name_error(self, ue5_executor):
        """Test handling of undefined variable errors."""
        result = ue5_executor.execute_command(
            "print(undefined_variable_xyz)",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        assert result["success"] is False

    def test_execute_with_runtime_error(self, ue5_executor):
        """Test handling of runtime errors (ValueError)."""
        result = ue5_executor.execute_command(
            "raise ValueError('Test error from E2E')",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        assert result["success"] is False

    def test_execute_with_zero_division(self, ue5_executor):
        """Test handling of ZeroDivisionError."""
        result = ue5_executor.execute_command(
            "x = 1 / 0",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        assert result["success"] is False

    def test_execute_file(self, ue5_executor, sample_scripts_dir):
        """Test executing a Python file."""
        script_path = sample_scripts_dir / "hello_world.py"

        if not script_path.exists():
            pytest.skip(f"Test script not found: {script_path}")

        result = ue5_executor.execute_command(
            str(script_path.absolute()),
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_FILE
        )

        assert result["success"] is True

    def test_execute_with_custom_timeout(self, ue5_executor):
        """Test command execution with custom timeout."""
        # Quick command should complete within short timeout
        result = ue5_executor.execute_command(
            "print('quick')",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT,
            timeout=1.0
        )

        assert result["success"] is True

    def test_execute_returns_output(self, ue5_executor):
        """Test that execution returns output."""
        result = ue5_executor.execute_command(
            "print('Test output message')",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        assert result["success"] is True
        # Output should be present
        assert "output" in result


@pytest.mark.e2e
class TestUnrealAPIExecution:
    """E2E tests specifically for Unreal Engine API calls."""

    def test_get_project_directory(self, ue5_executor):
        """Test getting project directory via unreal module."""
        result = ue5_executor.execute_command(
            "import unreal; print(unreal.SystemLibrary.get_project_directory())",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        assert result["success"] is True

    def test_list_asset_paths(self, ue5_executor):
        """Test listing asset paths."""
        # Multiline code must use EXECUTE_FILE type
        result = ue5_executor.execute_command(
            """
import unreal
editor_asset_lib = unreal.EditorAssetLibrary()
# Just verify the module loads without error
print("EditorAssetLibrary loaded successfully")
""",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_FILE
        )

        assert result["success"] is True

    def test_log_message(self, ue5_executor):
        """Test logging via unreal.log."""
        result = ue5_executor.execute_command(
            "import unreal; unreal.log('Test log message from E2E test')",
            exec_type=UE5RemoteExecution.ExecTypes.EXECUTE_STATEMENT
        )

        assert result["success"] is True
