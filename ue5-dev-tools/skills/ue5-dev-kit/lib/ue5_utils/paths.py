#!/usr/bin/env python3
"""
UE5 Development Tools - Path and Discovery Utilities

All functions use filesystem-based discovery, no environment variable dependencies.
This is the canonical source for all path-related functions used across skills.
"""

import os
from pathlib import Path
from typing import Optional


def find_ue5_project_root(start_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Find UE5 project root by searching for .uproject file upward from start_dir.

    Args:
        start_dir: Starting directory for search (defaults to cwd)

    Returns:
        Path to project root directory containing .uproject file, or None if not found
    """
    if start_dir is None:
        start_dir = Path.cwd()

    current = Path(start_dir).resolve()

    while True:
        try:
            uprojects = list(current.glob("*.uproject"))
            if uprojects:
                return current
        except OSError:
            pass

        parent = current.parent
        if parent == current:
            return None
        current = parent


def find_project_name(start_dir: Optional[Path] = None) -> Optional[str]:
    """
    Find UE5 project name by searching for .uproject file.

    Args:
        start_dir: Starting directory for search (defaults to cwd)

    Returns:
        Project name (without .uproject extension) or None if not found or ambiguous
    """
    if start_dir is None:
        start_dir = Path.cwd()

    # Search in start_dir and up to 5 parent levels
    current = Path(start_dir).resolve()
    for _ in range(6):
        uprojects = list(current.glob("*.uproject"))
        if len(uprojects) == 1:
            return uprojects[0].stem
        elif len(uprojects) > 1:
            return None  # Ambiguous

        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


def find_ue5_editor() -> Optional[Path]:
    """
    Find the latest installed UE5 Editor executable.

    Returns:
        Path to UnrealEditor.exe or None if not found
    """
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    search_roots = [
        Path(program_files) / "Epic Games",
        Path("D:\\Epic Games"),
        Path("E:\\Epic Games"),
        Path("C:\\Epic Games"),
    ]

    found_editors = []

    for base_path in search_roots:
        if not base_path.exists():
            continue

        try:
            for item in base_path.iterdir():
                if item.is_dir() and item.name.startswith("UE_5"):
                    editor_path = item / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
                    if editor_path.exists():
                        found_editors.append(editor_path)
        except OSError:
            pass

    found_editors.sort(key=lambda p: p.parts[-5], reverse=True)
    return found_editors[0] if found_editors else None


def find_skills_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the skills root directory by searching upward.

    Args:
        start_path: Starting path for search (defaults to this file's location)

    Returns:
        Path to the skills root directory, or None if not found
    """
    if start_path is None:
        start_path = Path(__file__).resolve().parent

    current = Path(start_path).resolve()

    for _ in range(10):
        executor_path = current / "ue5-python-executor"
        dev_kit_path = current / "ue5-dev-kit"

        if executor_path.exists() and executor_path.is_dir():
            if (executor_path / "scripts" / "remote-execute.py").exists():
                return current

        if dev_kit_path.exists() and dev_kit_path.is_dir():
            if (dev_kit_path / "lib" / "ue5_utils").exists():
                return current

        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


def find_skill_path(skill_name: str, start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the path to a specific skill directory.

    Args:
        skill_name: Name of the skill (e.g., 'ue5-python-executor')
        start_path: Starting path for search

    Returns:
        Path to the skill directory, or None if not found
    """
    skills_root = find_skills_root(start_path)
    if skills_root is None:
        return None

    skill_path = skills_root / skill_name
    if skill_path.exists() and skill_path.is_dir():
        return skill_path

    return None
