#!/usr/bin/env python3
"""
UE5 Development Tools - Path Resolution Utilities

Consistent path resolution leveraging Claude Code environment variables.
Consolidated from multiple sources for shared use across skills.
"""

import os
import time
from pathlib import Path
from typing import Optional


def get_plugin_root() -> Path:
    """
    Get plugin root from CLAUDE_PLUGIN_ROOT or infer from file location.

    Returns:
        Path to plugin root directory
    """
    if "CLAUDE_PLUGIN_ROOT" in os.environ:
        return Path(os.environ["CLAUDE_PLUGIN_ROOT"])

    # Fallback: assumes <plugin-root>/skills/ue5-python-executor/lib/ue5_remote/utils.py
    return Path(__file__).parent.parent.parent.parent


def get_project_root() -> Path:
    """
    Get project root from CLAUDE_PROJECT_DIR or current working directory.

    Returns:
        Path to project root directory
    """
    if "CLAUDE_PROJECT_DIR" in os.environ:
        return Path(os.environ["CLAUDE_PROJECT_DIR"])
    return Path.cwd()


def infer_project_name_from_filesystem() -> Optional[str]:
    """
    Infer project name by searching for .uproject file.

    Search order:
    1. Current working directory
    2. Parent directories (up to 3 levels)

    Returns:
        Project name (without .uproject extension) or None if not found or ambiguous
    """
    cwd = Path.cwd()

    # Search in cwd and up to 3 parent levels
    for parent in [cwd] + list(cwd.parents[:3]):
        uprojects = list(parent.glob("*.uproject"))
        if len(uprojects) == 1:
            return uprojects[0].stem
        elif len(uprojects) > 1:
            # Multiple .uproject files, ambiguous
            return None

    return None


def get_default_project_name() -> Optional[str]:
    """
    Get project name from CLAUDE_PROJECT_DIR or filesystem.

    Priority:
    1. CLAUDE_PROJECT_DIR basename (if available in hooks)
    2. .uproject file in current directory tree
    3. None (require explicit --project-name)

    Returns:
        Project name as string, or None if could not determine
    """
    # Try CLAUDE_PROJECT_DIR first (available in hooks)
    if "CLAUDE_PROJECT_DIR" in os.environ:
        project_dir = os.environ["CLAUDE_PROJECT_DIR"]
        return os.path.basename(project_dir.rstrip("/"))

    # Fall back to filesystem inference
    return infer_project_name_from_filesystem()


def get_default_project_path() -> Path:
    """
    Alias for get_project_root() for compatibility.

    Returns:
        Path to project root directory
    """
    return get_project_root()


def find_ue5_editor() -> Optional[Path]:
    """
    Find the latest installed UE5 Editor executable.
    
    Returns:
        Path to UnrealEditor.exe or None if not found
    """
    # Check common installation paths
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    search_roots = [
        Path(program_files) / "Epic Games",
        Path("D:\\Epic Games"), 
        Path("E:\\Epic Games"),
        Path("C:\\Epic Games")
    ]
    
    found_editors = []
    
    for base_path in search_roots:
        if not base_path.exists():
            continue
            
        for item in base_path.iterdir():
            if item.is_dir() and item.name.startswith("UE_5"):
                editor_path = item / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
                if editor_path.exists():
                    found_editors.append(editor_path)

    # Sort to find the latest version (assuming lexicographical sort works for UE_5.x)
    found_editors.sort(key=lambda p: p.parts[-5], reverse=True) # parts[-5] is the UE_5.x folder

    return found_editors[0] if found_editors else None
