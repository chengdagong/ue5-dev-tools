
import unittest
import sys
import os

# Adjust path to import validate
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "scripts"))

try:
    import validate
except ImportError:
    # If imports fail due to global code in validate.py, we might need to mock them in setUp or just accept it if utils_for_test helps
    pass

class TestValidationReport(unittest.TestCase):
    def setUp(self):
        self.report = validate.ValidationReport()

    def test_initial_state(self):
        self.assertEqual(self.report.errors, [])
        self.assertEqual(self.report.warnings, [])
        self.assertEqual(self.report.infos, [])
        self.assertEqual(self.report.stats, {"classes": 0, "methods": 0})

    def test_add_error(self):
        self.report.add_error("Test Error", 10)
        self.assertEqual(len(self.report.errors), 1)
        self.assertIn("Test Error", self.report.errors[0])
        self.assertIn("Line 10", self.report.errors[0])

    def test_add_warning(self):
        self.report.add_warning("Test Warning", 20)
        self.assertEqual(len(self.report.warnings), 1)
        self.assertIn("Test Warning", self.report.warnings[0])
        self.assertIn("Line 20", self.report.warnings[0])

    def test_add_info(self):
        self.report.add_info("Test Info")
        self.assertEqual(len(self.report.infos), 1)
        self.assertIn("Test Info", self.report.infos[0])

if __name__ == "__main__":
    unittest.main()
