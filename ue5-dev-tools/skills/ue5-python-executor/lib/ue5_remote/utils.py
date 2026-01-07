#!/usr/bin/env python3
"""
UE5 Development Tools - Path Resolution Utilities

Consistent path resolution leveraging Claude Code environment variables.
Consolidated from multiple sources for shared use across skills.
"""

import os
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


def get_default_project_name() -> Optional[str]:
    """
    Get project name from CLAUDE_PROJECT_DIR basename.

    Returns:
        Project name as string, or None if CLAUDE_PROJECT_DIR not set
    """
    if "CLAUDE_PROJECT_DIR" in os.environ:
        project_dir = os.environ["CLAUDE_PROJECT_DIR"]
        return os.path.basename(project_dir.rstrip("/"))
    return None


def get_default_project_path() -> Path:
    """
    Alias for get_project_root() for compatibility.

    Returns:
        Path to project root directory
    """
    return get_project_root()
