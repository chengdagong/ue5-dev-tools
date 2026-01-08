"""
Unit tests for AstValidator class.

Tests the AST-based validation of UE5 Python scripts.
Migrated from skills/api-validator/tests/test_ast_validator.py
"""

import pytest
import ast
import sys
from pathlib import Path
from unittest.mock import patch

# Ensure modules can be imported
API_VALIDATOR_SCRIPTS = Path(__file__).parent.parent.parent.parent / "skills" / "api-validator" / "scripts"
if str(API_VALIDATOR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(API_VALIDATOR_SCRIPTS))

from . import utils_for_test
import validate


class TestAstValidator:
    """Tests for AstValidator class."""

    @pytest.fixture
    def setup_validator(self):
        """Create validator with mocked unreal module."""
        report = validate.ValidationReport()
        validator = validate.AstValidator(report)

        # Patch global variables in validate module
        mock_unreal = utils_for_test.setup_mock_unreal()
        patcher_unreal = patch('validate.unreal', mock_unreal)
        patcher_metadata = patch('validate.METADATA', utils_for_test.create_mock_metadata())

        patcher_unreal.start()
        patcher_metadata.start()

        yield {
            'report': report,
            'validator': validator,
            'mock_unreal': mock_unreal,
            'patcher_unreal': patcher_unreal,
            'patcher_metadata': patcher_metadata
        }

        patcher_unreal.stop()
        patcher_metadata.stop()

    def _visit(self, validator, code):
        """Helper to parse and visit code."""
        tree = ast.parse(code)
        validator.visit(tree)

    def test_valid_class_instantiation(self, setup_validator):
        """Test valid class instantiation is accepted."""
        code = "obj = unreal.Object()"
        self._visit(setup_validator['validator'], code)

        assert len(setup_validator['report'].errors) == 0
        assert setup_validator['validator'].variable_types.get("obj") == "Object"

    def test_non_existent_class(self, setup_validator):
        """Test non-existent class is flagged."""
        code = "obj = unreal.NonExistentClass()"
        self._visit(setup_validator['validator'], code)

        assert len(setup_validator['report'].errors) == 1
        assert "NonExistentClass" in setup_validator['report'].errors[0]

    def test_deprecated_class_metadata(self, setup_validator):
        """Test deprecated class (from metadata) generates warning."""
        # Ensure 'DeprecatedClass' exists on the mock so hasattr returns True
        setup_validator['mock_unreal'].DeprecatedClass = type('DeprecatedClass', (), {})
        setup_validator['mock_unreal'].mock_add_spec(
            ['DeprecatedClass', 'Actor', 'Object', 'DeprecatedError']
        )

        code = "obj = unreal.DeprecatedClass()"
        self._visit(setup_validator['validator'], code)

        assert len(setup_validator['report'].warnings) == 1
        assert "DeprecatedClass" in setup_validator['report'].warnings[0]
        assert "no longer supported" in setup_validator['report'].warnings[0]

    def test_runtime_deprecation_class(self, setup_validator):
        """Test runtime deprecated class generates warning."""
        # Simulate runtime deprecated error
        class RuntimeDeprecated:
            def __init__(self, *args, **kwargs):
                raise validate.DeprecatedError("Runtime deprecated")

        setup_validator['mock_unreal'].RuntimeDeprecated = RuntimeDeprecated
        setup_validator['mock_unreal'].mock_add_spec(
            ['RuntimeDeprecated', 'Actor', 'Object', 'DeprecatedError']
        )

        code = "obj = unreal.RuntimeDeprecated()"
        self._visit(setup_validator['validator'], code)

        assert len(setup_validator['report'].warnings) == 1
        assert "Runtime deprecated" in setup_validator['report'].warnings[0]

    def test_variable_tracking(self, setup_validator):
        """Test variable type tracking."""
        code = """
import unreal
my_actor = unreal.Actor()
        """
        self._visit(setup_validator['validator'], code)

        assert setup_validator['validator'].variable_types.get("my_actor") == "Actor"

    def test_editor_property_valid(self, setup_validator):
        """Test valid editor property access."""
        code = """
import unreal
actor = unreal.Actor()
actor.get_editor_property("ActorLabel")
        """
        self._visit(setup_validator['validator'], code)

        assert len(setup_validator['report'].errors) == 0
        assert len(setup_validator['report'].warnings) == 0

    def test_editor_property_invalid(self, setup_validator):
        """Test invalid editor property generates error."""
        code = """
import unreal
actor = unreal.Actor()
actor.get_editor_property("InvalidProp")
        """
        self._visit(setup_validator['validator'], code)

        assert len(setup_validator['report'].errors) == 1
        assert "InvalidProp" in setup_validator['report'].errors[0]

    def test_editor_property_deprecated(self, setup_validator):
        """Test deprecated editor property generates warning."""
        code = """
import unreal
actor = unreal.Actor()
actor.set_editor_property("HiddenProp", 1)
        """
        self._visit(setup_validator['validator'], code)

        assert len(setup_validator['report'].warnings) == 1
        assert "HiddenProp" in setup_validator['report'].warnings[0]
        assert "Do not use" in setup_validator['report'].warnings[0]

    def test_editor_property_unknown_variable(self, setup_validator):
        """Test unknown variable type is handled gracefully."""
        code = """
unknown.get_editor_property("Anything")
        """
        self._visit(setup_validator['validator'], code)

        # Should be ignored because we don't know the type
        assert len(setup_validator['report'].errors) == 0
