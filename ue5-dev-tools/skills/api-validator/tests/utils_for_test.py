
import sys
import unittest
from unittest.mock import MagicMock, Mock
import json
import os

# Ensure validate.py can be imported
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "scripts"))

# Import validate module (it might fail if dependencies are missing, but we will mock them)
# We need to mock 'unreal' before importing validate if possible, or patch it afterwards.
# 'validate.py' tries to import 'unreal_mock', so we should ensure it uses our mock.

def setup_mock_unreal():
    """Context manager or setup helper to mock the unreal module structure."""
    # Use a non-magical Mock or explicit class to control attributes for hasattr tests
    unreal_mock = Mock(name='unreal')
    
    # Common classes
    class Object: 
        def get_editor_property(self, name): pass
        def set_editor_property(self, name, value): pass
        
    class Actor(Object): 
        def get_actor_location(self): pass
        def k2_destroy_actor(self): pass
        def get_editor_property(self, name): pass
        def set_editor_property(self, name, value): pass
    
    # Attach to mock
    unreal_mock.Object = Object
    unreal_mock.Actor = Actor
    
    # Deprecated Error
    class DeprecatedError(Exception): pass
    unreal_mock.DeprecatedError = DeprecatedError
    
    # Let's populate the spec list with Keys we added.
    unreal_mock.mock_add_spec(list(unreal_mock.__dict__.keys()) + ['Object', 'Actor', 'DeprecatedError'])
    
    return unreal_mock
