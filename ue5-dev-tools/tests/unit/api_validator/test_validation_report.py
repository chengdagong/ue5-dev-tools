"""
Unit tests for ValidationReport class.

Tests the error, warning, and info reporting functionality.
Migrated from skills/api-validator/tests/test_validation_report.py
"""

import pytest
import sys
from pathlib import Path

# Ensure validate module can be imported
API_VALIDATOR_SCRIPTS = Path(__file__).parent.parent.parent.parent / "skills" / "api-validator" / "scripts"
if str(API_VALIDATOR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(API_VALIDATOR_SCRIPTS))

import validate


class TestValidationReport:
    """Tests for ValidationReport class."""

    @pytest.fixture
    def report(self):
        """Create a fresh ValidationReport for each test."""
        return validate.ValidationReport()

    def test_initial_state(self, report):
        """Test initial state of ValidationReport."""
        assert report.errors == []
        assert report.warnings == []
        assert report.infos == []
        assert report.stats == {"classes": 0, "methods": 0}

    def test_add_error(self, report):
        """Test adding an error."""
        report.add_error("Test Error", 10)

        assert len(report.errors) == 1
        assert "Test Error" in report.errors[0]
        assert "Line 10" in report.errors[0]

    def test_add_error_without_line(self, report):
        """Test adding an error without line number."""
        report.add_error("Test Error")

        assert len(report.errors) == 1
        assert "Test Error" in report.errors[0]

    def test_add_multiple_errors(self, report):
        """Test adding multiple errors."""
        report.add_error("Error 1", 10)
        report.add_error("Error 2", 20)
        report.add_error("Error 3", 30)

        assert len(report.errors) == 3

    def test_add_warning(self, report):
        """Test adding a warning."""
        report.add_warning("Test Warning", 20)

        assert len(report.warnings) == 1
        assert "Test Warning" in report.warnings[0]
        assert "Line 20" in report.warnings[0]

    def test_add_warning_without_line(self, report):
        """Test adding a warning without line number."""
        report.add_warning("Test Warning")

        assert len(report.warnings) == 1
        assert "Test Warning" in report.warnings[0]

    def test_add_multiple_warnings(self, report):
        """Test adding multiple warnings."""
        report.add_warning("Warning 1", 10)
        report.add_warning("Warning 2", 20)

        assert len(report.warnings) == 2

    def test_add_info(self, report):
        """Test adding an info message."""
        report.add_info("Test Info")

        assert len(report.infos) == 1
        assert "Test Info" in report.infos[0]

    def test_add_multiple_infos(self, report):
        """Test adding multiple info messages."""
        report.add_info("Info 1")
        report.add_info("Info 2")

        assert len(report.infos) == 2

    def test_mixed_messages(self, report):
        """Test adding mixed message types."""
        report.add_error("Error", 1)
        report.add_warning("Warning", 2)
        report.add_info("Info")

        assert len(report.errors) == 1
        assert len(report.warnings) == 1
        assert len(report.infos) == 1

    def test_stats_initialization(self, report):
        """Test stats are initialized correctly."""
        assert "classes" in report.stats
        assert "methods" in report.stats
        assert report.stats["classes"] == 0
        assert report.stats["methods"] == 0
