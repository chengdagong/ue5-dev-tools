"""
Test utilities for api-validator tests.

Provides mock objects for unreal module and metadata.
Migrated from skills/api-validator/tests/utils_for_test.py
"""

import sys
from unittest.mock import Mock


def setup_mock_unreal():
    """
    Setup a mock unreal module for testing.

    Returns:
        Mock object representing the unreal module with common classes.
    """
    unreal_mock = Mock(name='unreal')

    # Common classes
    class Object:
        def get_editor_property(self, name):
            pass

        def set_editor_property(self, name, value):
            pass

    class Actor(Object):
        def get_actor_location(self):
            pass

        def k2_destroy_actor(self):
            pass

        def get_editor_property(self, name):
            pass

        def set_editor_property(self, name, value):
            pass

    # Attach to mock
    unreal_mock.Object = Object
    unreal_mock.Actor = Actor

    # Deprecated Error
    class DeprecatedError(Exception):
        pass

    unreal_mock.DeprecatedError = DeprecatedError

    # Populate the spec list
    unreal_mock.mock_add_spec(
        list(unreal_mock.__dict__.keys()) + ['Object', 'Actor', 'DeprecatedError']
    )

    return unreal_mock


def create_mock_metadata():
    """
    Create mock C++ metadata for testing.

    Returns:
        Dictionary resembling the C++ metadata structure.
    """
    return {
        "Actor": {
            "deprecated": False,
            "functions": {
                "get_actor_location": {"deprecated": False},
                "k2_destroy_actor": {
                    "deprecated": True,
                    "deprecation_message": "Use DestroyActor instead"
                }
            },
            "properties": {
                "ActorLabel": {"deprecated": False, "type": "str"},
                "HiddenProp": {
                    "deprecated": True,
                    "deprecation_message": "Do not use"
                }
            }
        },
        "DeprecatedClass": {
            "deprecated": True,
            "deprecation_message": "This class is no longer supported"
        }
    }
