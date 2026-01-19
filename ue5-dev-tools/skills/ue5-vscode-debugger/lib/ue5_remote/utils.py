#!/usr/bin/env python3
"""
UE5 Development Tools - Path Resolution Utilities

This module re-exports utilities from ue5_utils for backward compatibility.
The canonical implementation is in lib/ue5_utils/.
"""

import sys
from pathlib import Path

# Add ue5_utils to path
_ue5_utils_path = Path(__file__).parent.parent.parent.parent / "lib"
if str(_ue5_utils_path) not in sys.path:
    sys.path.insert(0, str(_ue5_utils_path))

# Re-export all utilities from ue5_utils
from ue5_utils import (
    find_ue5_project_root,
    find_project_name,
    find_ue5_editor,
    find_skills_root,
    find_skill_path,
)

__all__ = [
    "find_ue5_project_root",
    "find_project_name",
    "find_ue5_editor",
    "find_skills_root",
    "find_skill_path",
]
