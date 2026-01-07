
import unittest
import ast
import sys
import os
from unittest.mock import MagicMock, patch

# Add module path
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "scripts"))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "tests"))

import utils_for_test
import validate

class TestAstValidator(unittest.TestCase):
    def setUp(self):
        self.report = validate.ValidationReport()
        self.validator = validate.AstValidator(self.report)
        
        # Patch global variables in validate module
        self.mock_unreal = utils_for_test.setup_mock_unreal()
        self.patcher_unreal = patch('validate.unreal', self.mock_unreal)
        self.patcher_metadata = patch('validate.METADATA', utils_for_test.create_mock_metadata())
        
        self.patcher_unreal.start()
        self.patcher_metadata.start()

    def tearDown(self):
        self.patcher_unreal.stop()
        self.patcher_metadata.stop()

    def _visit(self, code):
        tree = ast.parse(code)
        self.validator.visit(tree)

    def test_valid_class_instantiation(self):
        code = "obj = unreal.Object()"
        self._visit(code)
        self.assertEqual(len(self.report.errors), 0)
        self.assertEqual(self.validator.variable_types.get("obj"), "Object")

    def test_non_existent_class(self):
        code = "obj = unreal.NonExistentClass()"
        self._visit(code)
        self.assertEqual(len(self.report.errors), 1)
        self.assertIn("NonExistentClass", self.report.errors[0])

    def test_deprecated_class_metadata(self):
        # We need to ensure 'DeprecatedClass' exists on the mock so hasattr returns True
        self.mock_unreal.DeprecatedClass = type('DeprecatedClass', (), {})
        # Update spec to include this new class
        self.mock_unreal.mock_add_spec(['DeprecatedClass', 'Actor', 'Object', 'DeprecatedError'])
        
        code = "obj = unreal.DeprecatedClass()"
        self._visit(code)
        self.assertEqual(len(self.report.warnings), 1)
        self.assertIn("DeprecatedClass", self.report.warnings[0])
        self.assertIn("no longer supported", self.report.warnings[0])

    def test_runtime_deprecation_class(self):
        # Simulate runtime deprecated error
        # NOTE: validate.py uses isinstance(member, type) to decide if it's a class check.
        # MagicMock is not a type. So we must use a real class.
        class RuntimeDeprecated:
            def __init__(self, *args, **kwargs):
                raise validate.DeprecatedError("Runtime deprecated")
        
        # Add to mock
        self.mock_unreal.RuntimeDeprecated = RuntimeDeprecated
        self.mock_unreal.mock_add_spec(['RuntimeDeprecated', 'Actor', 'Object', 'DeprecatedError'])
        
        code = "obj = unreal.RuntimeDeprecated()"
        self._visit(code)
        self.assertEqual(len(self.report.warnings), 1)
        self.assertIn("Runtime deprecated", self.report.warnings[0])

    def test_variable_tracking(self):
        code = """
import unreal
my_actor = unreal.Actor()
        """
        self._visit(code)
        self.assertEqual(self.validator.variable_types.get("my_actor"), "Actor")

    def test_editor_property_valid(self):
        code = """
import unreal
actor = unreal.Actor()
actor.get_editor_property("ActorLabel")
        """
        self._visit(code)
        self.assertEqual(len(self.report.errors), 0)
        self.assertEqual(len(self.report.warnings), 0)

    def test_editor_property_invalid(self):
        code = """
import unreal
actor = unreal.Actor()
actor.get_editor_property("InvalidProp")
        """
        self._visit(code)
        self.assertEqual(len(self.report.errors), 1)
        self.assertIn("InvalidProp", self.report.errors[0])

    def test_editor_property_deprecated(self):
        code = """
import unreal
actor = unreal.Actor()
actor.set_editor_property("HiddenProp", 1)
        """
        self._visit(code)
        self.assertEqual(len(self.report.warnings), 1)
        self.assertIn("HiddenProp", self.report.warnings[0])
        self.assertIn("Do not use", self.report.warnings[0])

    def test_editor_property_unknown_variable(self):
        # variable type unknown
        code = """
unknown.get_editor_property("Anything")
        """
        self._visit(code)
        # Should be ignored or no error because we don't know the type
        self.assertEqual(len(self.report.errors), 0)

if __name__ == "__main__":
    unittest.main()
