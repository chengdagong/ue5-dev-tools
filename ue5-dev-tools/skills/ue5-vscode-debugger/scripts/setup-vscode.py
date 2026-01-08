#!/usr/bin/env python3
"""
VSCode Configuration Setup Tool

Automatically generates .vscode/launch.json and .vscode/tasks.json,
Using correct plugin paths (from CLAUDE_PLUGIN_ROOT).
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Add dependency check and import from executor's lib
plugin_root = Path(__file__).parent.parent.parent.parent
executor_lib = plugin_root / "skills" / "ue5-python-executor" / "lib"
if not executor_lib.exists():
    print("ERROR: ue5-python-executor skill not found", file=sys.stderr)
    print(f"Expected location: {executor_lib}", file=sys.stderr)
    print("Please ensure ue5-python-executor skill is installed", file=sys.stderr)
    sys.exit(1)
sys.path.insert(0, str(executor_lib))
from ue5_remote import get_plugin_root, get_project_root


def create_launch_config(plugin_root: Path) -> Dict[str, Any]:
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


def create_tasks_config(plugin_root: Path) -> Dict[str, Any]:
    """Create tasks.json configuration"""
    # Calculate absolute paths for scripts (referencing executor and debugger skills)
    executor_skill = plugin_root / "skills" / "ue5-python-executor"
    remote_execute_script = executor_skill / "scripts" / "remote-execute.py"
    debugger_skill = plugin_root / "skills" / "ue5-vscode-debugger"
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
                    # --project-name will be automatically inferred from CLAUDE_PROJECT_DIR
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
                    # --project-name will be automatically inferred from CLAUDE_PROJECT_DIR
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
                print(f"✓ {file_path.name} already contains all necessary configurations, skipping")
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
            print(f"⚠️  Warning: {file_path.name} format error, will backup and overwrite: {e}")
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            file_path.rename(backup_path)
            print(f"   Backup saved to: {backup_path}")

    # Write configuration
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(new_config, f, indent=2, ensure_ascii=False)

    return True


def setup_vscode_config(project_root: Path, plugin_root: Path, force: bool = False) -> bool:
    """
    Setup VSCode Configuration

    Args:
        project_root: Project Root
        plugin_root: Plugin Root
        force: Whether to force overwrite existing configuration

    Returns:
        Whether setup was successful
    """
    vscode_dir = project_root / ".vscode"
    launch_json = vscode_dir / "launch.json"
    tasks_json = vscode_dir / "tasks.json"

    print(f"Project Root: {project_root}")
    print(f"Plugin Root: {plugin_root}")
    print()

    # Create configurations
    launch_config = create_launch_config(plugin_root)
    tasks_config = create_tasks_config(plugin_root)

    # Process launch.json
    print("Processing launch.json...")
    if force or not launch_json.exists():
        launch_json.parent.mkdir(parents=True, exist_ok=True)
        with open(launch_json, 'w', encoding='utf-8') as f:
            json.dump(launch_config, f, indent=2, ensure_ascii=False)
        print(f"✓ Created {launch_json}")
    else:
        if merge_json_file(launch_json, launch_config, "configurations"):
            print(f"✓ Updated {launch_json}")

    # Process tasks.json
    print("Processing tasks.json...")
    if force or not tasks_json.exists():
        tasks_json.parent.mkdir(parents=True, exist_ok=True)
        with open(tasks_json, 'w', encoding='utf-8') as f:
            json.dump(tasks_config, f, indent=2, ensure_ascii=False)
        print(f"✓ Created {tasks_json}")
    else:
        if merge_json_file(tasks_json, tasks_config, "tasks"):
            print(f"✓ Updated {tasks_json}")

    print()
    print("✓ VSCode configuration completed!")
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
  CLAUDE_PLUGIN_ROOT - Plugin root directory injected by Claude Code
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

    # Get paths
    project_root = args.project if args.project else get_project_root()
    plugin_root = get_plugin_root()

    # Validate plugin path (verify dependent executor skill)
    remote_exec_script = plugin_root / "skills" / "ue5-python-executor" / "scripts" / "remote-execute.py"
    if not remote_exec_script.exists():
        print(f"Error: Cannot find ue5-python-executor skill script: {remote_exec_script}", file=sys.stderr)
        print(f"Plugin Root: {plugin_root}", file=sys.stderr)
        print("Please ensure ue5-python-executor skill is installed", file=sys.stderr)
        sys.exit(1)

    # Setup configuration
    try:
        setup_vscode_config(project_root, plugin_root, args.force)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
