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


def _get_ue5_search_roots() -> list[Path]:
    """Get common UE5 installation search roots."""
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    return [
        Path(program_files) / "Epic Games",
        Path("D:\\Epic Games"),
        Path("E:\\Epic Games"),
        Path("C:\\Epic Games"),
    ]


def _find_ue5_installations() -> list[Path]:
    """Find all UE5 installation directories, sorted by version (newest first)."""
    search_roots = _get_ue5_search_roots()
    installations = []

    for base_path in search_roots:
        if not base_path.exists():
            continue

        try:
            for item in base_path.iterdir():
                if item.is_dir() and item.name.startswith("UE_5"):
                    installations.append(item)
        except OSError:
            pass

    installations.sort(key=lambda p: p.name, reverse=True)
    return installations


def find_ue5_editor() -> Optional[Path]:
    """
    Find the latest installed UE5 Editor executable.

    Returns:
        Path to UnrealEditor.exe or None if not found
    """
    for install_dir in _find_ue5_installations():
        editor_path = install_dir / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
        if editor_path.exists():
            return editor_path
    return None


def find_runuat() -> Optional[Path]:
    """
    Find the RunUAT build tool from the latest installed UE5.

    Returns:
        Path to RunUAT.bat (Windows) or RunUAT.sh (Unix) or None if not found
    """
    import platform

    script_name = "RunUAT.bat" if platform.system() == "Windows" else "RunUAT.sh"

    for install_dir in _find_ue5_installations():
        runuat_path = install_dir / "Engine" / "Build" / "BatchFiles" / script_name
        if runuat_path.exists():
            return runuat_path
    return None


def find_build_bat() -> Optional[Path]:
    """
    Find the Build.bat script from the latest installed UE5.

    Returns:
        Path to Build.bat (Windows) or None if not found
    """
    import platform

    if platform.system() != "Windows":
        return None

    for install_dir in _find_ue5_installations():
        build_path = install_dir / "Engine" / "Build" / "BatchFiles" / "Build.bat"
        if build_path.exists():
            return build_path
    return None


def build_project(
    project_path: Path,
    config: str = "Development",
    platform: str = "Win64",
    timeout: int = 300,
) -> tuple[bool, str]:
    """
    Build UE5 project using Build.bat (UnrealBuildTool).

    This performs a quick editor build suitable for launching the editor
    with up-to-date binaries. Much faster than BuildCookRun.

    Args:
        project_path: Path to .uproject file
        config: Build configuration (Development, DebugGame, etc.)
        platform: Target platform (Win64, Mac, Linux)
        timeout: Build timeout in seconds (default 300 = 5 minutes)

    Returns:
        Tuple of (success: bool, message: str)
    """
    import subprocess

    build_bat = find_build_bat()
    if not build_bat:
        return False, "Could not find Build.bat tool"

    if not project_path.exists():
        return False, f"Project file not found: {project_path}"

    # Get project name from .uproject file
    project_name = project_path.stem

    # Build command using Build.bat for editor target
    # Format: Build.bat <TargetName> <Platform> <Configuration> -Project=<path> [options]
    target_name = f"{project_name}Editor"
    cmd = [
        str(build_bat),
        target_name,
        platform,
        config,
        f"-Project={project_path}",
        "-WaitMutex",
        "-FromMsBuild",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=project_path.parent,
        )

        if result.returncode == 0:
            return True, "Build completed successfully"
        else:
            # Extract relevant error info from output
            error_lines = []
            for line in result.stdout.split("\n") + result.stderr.split("\n"):
                if "error" in line.lower() or "failed" in line.lower():
                    error_lines.append(line.strip())

            error_msg = (
                "\n".join(error_lines[:10]) if error_lines else result.stderr[-500:]
            )
            return False, f"Build failed (exit code {result.returncode}):\n{error_msg}"

    except subprocess.TimeoutExpired:
        return False, f"Build timed out after {timeout} seconds"
    except Exception as e:
        return False, f"Build error: {e}"


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
        lib_path = current / "lib"

        if executor_path.exists() and executor_path.is_dir():
            if (executor_path / "scripts" / "remote-execute.py").exists():
                return current

        if lib_path.exists() and lib_path.is_dir():
            if (lib_path / "ue5_utils").exists():
                return current

        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


def find_skill_path(
    skill_name: str, start_path: Optional[Path] = None
) -> Optional[Path]:
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
