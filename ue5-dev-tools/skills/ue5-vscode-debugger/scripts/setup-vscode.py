#!/usr/bin/env python3
"""
VSCode Configuration Setup Tool

Automatically generates .vscode/launch.json and .vscode/tasks.json,
Using correct plugin paths by searching upward for ue5-python-executor.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


def find_skills_root(start_path: Path = None) -> Optional[Path]:
    """
    Find the skills root directory by searching upward for a directory
    that contains 'ue5-python-executor' as a subdirectory.

    Args:
        start_path: Starting path for search (defaults to script location)

    Returns:
        Path to the directory containing ue5-python-executor, or None if not found
    """
    if start_path is None:
        start_path = Path(__file__).resolve().parent

    current = start_path
    # Search up to 10 levels up
    for _ in range(10):
        executor_path = current / "ue5-python-executor"
        if executor_path.exists() and executor_path.is_dir():
            # Verify it's the right directory by checking for scripts/remote-execute.py
            if (executor_path / "scripts" / "remote-execute.py").exists():
                return current

        parent = current.parent
        if parent == current:  # Reached root
            break
        current = parent

    return None


def find_executor_paths(start_path: Path = None) -> Tuple[Path, Path]:
    """
    Find paths to ue5-python-executor and ue5-vscode-debugger skills.

    Args:
        start_path: Starting path for search

    Returns:
        Tuple of (executor_skill_path, debugger_skill_path)

    Raises:
        FileNotFoundError: If skills cannot be found
    """
    skills_root = find_skills_root(start_path)

    if skills_root is None:
        raise FileNotFoundError(
            "Cannot find ue5-python-executor skill. "
            "Searched upward from: " + str(start_path or Path(__file__).parent)
        )

    executor_skill = skills_root / "ue5-python-executor"
    debugger_skill = skills_root / "ue5-vscode-debugger"

    # Validate executor exists
    remote_exec = executor_skill / "scripts" / "remote-execute.py"
    if not remote_exec.exists():
        raise FileNotFoundError(f"Cannot find remote-execute.py at: {remote_exec}")

    return executor_skill, debugger_skill


def get_project_root() -> Path:
    """
    Get project root from CLAUDE_PROJECT_DIR or current working directory.

    Returns:
        Path to project root directory
    """
    if "CLAUDE_PROJECT_DIR" in os.environ:
        return Path(os.environ["CLAUDE_PROJECT_DIR"])
    return Path.cwd()


def create_launch_config() -> Dict[str, Any]:
    """Create launch.json configuration"""
    return {
        "version": "0.2.1",
        "configurations": [
            {
                "name": "UE5 Python: Debug Current File",
                "type": "debugpy",
                "request": "attach",
                "connect": {
                    "host": "127.0.0.1",
                    "port": 19678
                },
                "pathMappings": [
                    {
                        "localRoot": "${workspaceFolder}",
                        "remoteRoot": "${workspaceFolder}"
                    }
                ],
                "justMyCode": False,
                "preLaunchTask": "ue5-start-debug-and-execute"
            },
            {
                "name": "UE5 Python: Attach Only",
                "type": "debugpy",
                "request": "attach",
                "connect": {
                    "host": "127.0.0.1",
                    "port": 19678
                },
                "pathMappings": [
                    {
                        "localRoot": "${workspaceFolder}",
                        "remoteRoot": "${workspaceFolder}"
                    }
                ],
                "justMyCode": False
            }
        ]
    }


def create_tasks_config(executor_skill: Path, debugger_skill: Path) -> Dict[str, Any]:
    """Create tasks.json configuration"""
    remote_execute_script = executor_skill / "scripts" / "remote-execute.py"
    start_debug_script = debugger_skill / "scripts" / "start_debug_server.py"

    return {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "ue5-start-debug-server",
                "type": "shell",
                "command": "python3",
                "args": [
                    str(remote_execute_script),
                    "--file",
                    str(start_debug_script)
                ],
                "isBackground": False,
                "presentation": {
                    "reveal": "always",
                    "panel": "dedicated",
                    "clear": True
                },
                "problemMatcher": {
                    "owner": "ue5-debug",
                    "pattern": {
                        "regexp": "^\\[UE5-DEBUG\\] ERROR: (.*)$",
                        "message": 1
                    },
                    "background": {
                        "activeOnStart": True,
                        "beginsPattern": "^\\[UE5-DEBUG\\] Starting debug server setup",
                        "endsPattern": "^\\[UE5-DEBUG\\] READY"
                    }
                }
            },
            {
                "label": "ue5-execute-python",
                "type": "shell",
                "command": "python3",
                "args": [
                    str(remote_execute_script),
                    "--file",
                    "${file}",
                    "--detached",
                    "--wait",
                    "1"
                ],
                "isBackground": True,
                "presentation": {
                    "reveal": "always",
                    "panel": "shared"
                },
                "problemMatcher": {
                    "pattern": {
                        "regexp": "^$",
                        "file": 1
                    },
                    "background": {
                        "activeOnStart": True,
                        "beginsPattern": ".*",
                        "endsPattern": "^$"
                    }
                }
            },
            {
                "label": "ue5-start-debug-and-execute",
                "dependsOrder": "sequence",
                "dependsOn": [
                    "ue5-start-debug-server",
                    "ue5-execute-python"
                ],
                "problemMatcher": []
            }
        ]
    }


def merge_json_file(file_path: Path, new_config: Dict[str, Any], key: str) -> bool:
    """
    Merge JSON Configuration File

    Args:
        file_path: Configuration file path
        new_config: New configuration content
        key: Key to merge (e.g., 'configurations' or 'tasks')

    Returns:
        Whether the merge was performed
    """
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)

            # Check if the same configuration already exists
            existing_items = existing.get(key, [])
            new_items = new_config.get(key, [])

            # Deduplicate by name/label
            name_key = "name" if key == "configurations" else "label"
            existing_names = {item.get(name_key) for item in existing_items}
            new_names = {item.get(name_key) for item in new_items}

            if new_names.issubset(existing_names):
                print(f"[OK] {file_path.name} already contains all necessary configurations, skipping")
                return False

            # Merge configurations
            for item in new_items:
                item_name = item.get(name_key)
                # If exists, replace; otherwise add
                found = False
                for i, existing_item in enumerate(existing_items):
                    if existing_item.get(name_key) == item_name:
                        existing_items[i] = item
                        found = True
                        break
                if not found:
                    existing_items.append(item)

            existing[key] = existing_items
            new_config = existing

        except json.JSONDecodeError as e:
            print(f"[WARN] Warning: {file_path.name} format error, will backup and overwrite: {e}")
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            file_path.rename(backup_path)
            print(f"   Backup saved to: {backup_path}")

    # Write configuration
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(new_config, f, indent=2, ensure_ascii=False)

    return True


def setup_vscode_config(project_root: Path, executor_skill: Path, debugger_skill: Path, force: bool = False) -> bool:
    """
    Setup VSCode Configuration

    Args:
        project_root: Project Root
        executor_skill: Path to ue5-python-executor skill
        debugger_skill: Path to ue5-vscode-debugger skill
        force: Whether to force overwrite existing configuration

    Returns:
        Whether setup was successful
    """
    vscode_dir = project_root / ".vscode"
    launch_json = vscode_dir / "launch.json"
    tasks_json = vscode_dir / "tasks.json"

    print(f"Project Root: {project_root}")
    print(f"Executor Skill: {executor_skill}")
    print(f"Debugger Skill: {debugger_skill}")
    print()

    # Create configurations
    launch_config = create_launch_config()
    tasks_config = create_tasks_config(executor_skill, debugger_skill)

    # Process launch.json
    print("Processing launch.json...")
    if force or not launch_json.exists():
        launch_json.parent.mkdir(parents=True, exist_ok=True)
        with open(launch_json, 'w', encoding='utf-8') as f:
            json.dump(launch_config, f, indent=2, ensure_ascii=False)
        print(f"[OK] Created {launch_json}")
    else:
        if merge_json_file(launch_json, launch_config, "configurations"):
            print(f"[OK] Updated {launch_json}")

    # Process tasks.json
    print("Processing tasks.json...")
    if force or not tasks_json.exists():
        tasks_json.parent.mkdir(parents=True, exist_ok=True)
        with open(tasks_json, 'w', encoding='utf-8') as f:
            json.dump(tasks_config, f, indent=2, ensure_ascii=False)
        print(f"[OK] Created {tasks_json}")
    else:
        if merge_json_file(tasks_json, tasks_config, "tasks"):
            print(f"[OK] Updated {tasks_json}")

    print()
    print("[OK] VSCode configuration completed!")
    print()
    print("Usage:")
    print("  1. Open any Python file in VSCode")
    print("  2. Press F5 to start debugging")
    print("  3. Select 'UE5 Python: Debug Current File' configuration")
    print()

    return True


def main():
    parser = argparse.ArgumentParser(
        description="VSCode Configuration Setup Tool - Automatically generate UE5 Python debug configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default paths (from environment variables)
  %(prog)s

  # Specify project path
  %(prog)s --project /path/to/ue5/project

  # Force overwrite existing configuration
  %(prog)s --force

Environment Variables:
  CLAUDE_PROJECT_DIR - Project root directory injected by Claude Code
        """
    )

    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help="Project root path (Default: CLAUDE_PROJECT_DIR or current directory)"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite existing configuration"
    )

    args = parser.parse_args()

    # Get project root
    project_root = args.project if args.project else get_project_root()

    # Find skill paths by searching upward
    try:
        executor_skill, debugger_skill = find_executor_paths()
        print(f"Found skills root: {executor_skill.parent}")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup configuration
    try:
        setup_vscode_config(project_root, executor_skill, debugger_skill, args.force)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
