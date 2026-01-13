"""
UE5 Project Configuration Checker
Logs and fixes issues with UE5 Python plugin and Remote Execution settings.
"""

import json
import configparser
import sys
import os
import argparse
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

try:
    from .utils import find_ue5_project_root
except ImportError:
    # Fallback for direct execution
    from utils import find_ue5_project_root

def find_uproject(project_root: Path) -> Optional[Path]:
    """
    Find .uproject file in project root.

    Args:
        project_root: Project root directory

    Returns:
        Path to .uproject file or None
    """
    uproject_files = list(project_root.glob("*.uproject"))

    if not uproject_files:
        return None

    if len(uproject_files) > 1:
        # Warning printed to stderr if called from script, but here we just pick first
        pass

    return uproject_files[0]


def check_python_plugin(uproject_path: Path, auto_fix: bool = False) -> Tuple[bool, bool, str]:
    """
    Check and optionally fix Python-related plugins in .uproject.

    Checks both PythonScriptPlugin and PythonAutomationTest plugins.

    Args:
        uproject_path: Path to .uproject file
        auto_fix: Whether to automatically fix issues

    Returns:
        (enabled, modified, message)
    """
    required_plugins = ["PythonScriptPlugin", "PythonAutomationTest"]

    try:
        with open(uproject_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        return False, False, f"JSON Parse Error: {e}"
    except Exception as e:
        return False, False, f"Read Failed: {e}"

    plugins = config.get("Plugins", [])
    modified = False
    messages = []
    all_enabled = True

    for plugin_name in required_plugins:
        plugin = next(
            (p for p in plugins if p.get("Name") == plugin_name),
            None
        )

        if plugin is None:
            if auto_fix:
                plugins.append({
                    "Name": plugin_name,
                    "Enabled": True
                })
                modified = True
                messages.append(f"Added {plugin_name}")
            else:
                all_enabled = False
                messages.append(f"{plugin_name} not in Plugins array")

        elif not plugin.get("Enabled", False):
            if auto_fix:
                plugin["Enabled"] = True
                modified = True
                messages.append(f"Enabled {plugin_name}")
            else:
                all_enabled = False
                messages.append(f"{plugin_name} exists but disabled")

    if modified:
        config["Plugins"] = plugins
        try:
            with open(uproject_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent="\t")
            return True, True, "; ".join(messages)
        except Exception as e:
            return False, False, f"Write Failed: {e}"

    if not messages:
        messages.append("Python plugins correctly configured")

    return all_enabled, False, "; ".join(messages)


def check_remote_execution(ini_path: Path, auto_fix: bool = False) -> Tuple[bool, bool, List[str]]:
    """
    Check and optionally fix Remote Execution settings in DefaultEngine.ini.

    Uses a conservative approach that preserves original file formatting by only
    appending missing settings rather than rewriting the entire file.

    Args:
        ini_path: Path to DefaultEngine.ini
        auto_fix: Whether to automatically fix issues

    Returns:
        (enabled, modified, changes_list)
    """
    section = "[/Script/PythonScriptPlugin.PythonScriptPluginSettings]"
    required_settings = {
        "bRemoteExecution": "True",
        "bDeveloperMode": "True",
        "RemoteExecutionMulticastBindAddress": "0.0.0.0"
    }

    # If file doesn't exist
    if not ini_path.exists():
        if auto_fix:
            ini_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                lines = [
                    "\n",
                    f"{section}\n",
                ]
                for key, value in required_settings.items():
                    lines.append(f"{key}={value}\n")

                with open(ini_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                return True, True, [
                    "Created DefaultEngine.ini",
                    f"Set bRemoteExecution=True",
                    f"Set bDeveloperMode=True",
                    f"Set RemoteExecutionMulticastBindAddress=0.0.0.0"
                ]
            except Exception as e:
                return False, False, [f"Write Failed: {e}"]
        else:
            return False, False, ["DefaultEngine.ini does not exist"]

    # Read existing file content
    try:
        with open(ini_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines(keepends=True)
    except Exception as e:
        return False, False, [f"Read Failed: {e}"]

    changes = []
    needs_fix = False
    missing_settings = {}

    # Check if section exists (case-insensitive for section name)
    section_lower = section.lower()
    section_exists = any(section_lower in line.lower() for line in lines)

    if not section_exists:
        missing_settings = required_settings.copy()
        needs_fix = True
        changes.append(f"Missing section {section}")
    else:
        # Check each required setting (case-insensitive key matching)
        content_lower = content.lower()
        for key, expected_value in required_settings.items():
            key_lower = key.lower()
            # Look for key=value pattern
            found = False
            for line in lines:
                line_stripped = line.strip().lower()
                if line_stripped.startswith(key_lower) and '=' in line_stripped:
                    # Extract value
                    _, _, value = line.partition('=')
                    value = value.strip()
                    if value.lower() == expected_value.lower():
                        found = True
                    else:
                        found = False
                        changes.append(f"{key} needs {expected_value} (is: {value})")
                    break

            if not found:
                missing_settings[key] = expected_value
                needs_fix = True
                if key not in [c.split()[0] for c in changes]:
                    changes.append(f"{key} needs {expected_value} (is: None)")

    # Auto-fix: append missing settings
    if auto_fix and (missing_settings or needs_fix):
        try:
            with open(ini_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # If section doesn't exist, append it at the end
            if not section_exists:
                if not content.endswith('\n'):
                    content += '\n'
                content += f"\n{section}\n"
                for key, value in required_settings.items():
                    content += f"{key}={value}\n"
                changes = [f"Added section {section}"]
                for key, value in required_settings.items():
                    changes.append(f"Set {key}={value}")
            else:
                # Find section and append missing settings after it
                lines = content.splitlines(keepends=True)
                new_lines = []
                in_target_section = False
                settings_added = False

                for i, line in enumerate(lines):
                    new_lines.append(line)

                    # Check if we're entering the target section
                    if section_lower in line.lower():
                        in_target_section = True
                        continue

                    # Check if we're leaving the section (next section starts)
                    if in_target_section and line.strip().startswith('[') and section_lower not in line.lower():
                        # Insert missing settings before this new section
                        if missing_settings and not settings_added:
                            for key, value in missing_settings.items():
                                new_lines.insert(-1, f"{key}={value}\n")
                            settings_added = True
                        in_target_section = False

                # If we're still in target section at end of file, append there
                if in_target_section and missing_settings and not settings_added:
                    # Ensure there's a newline before adding
                    if new_lines and not new_lines[-1].endswith('\n'):
                        new_lines[-1] += '\n'
                    for key, value in missing_settings.items():
                        new_lines.append(f"{key}={value}\n")
                    settings_added = True

                content = ''.join(new_lines)
                changes = []
                for key, value in missing_settings.items():
                    changes.append(f"Set {key}={value} (was: None)")

            with open(ini_path, 'w', encoding='utf-8') as f:
                f.write(content)

            needs_fix = False

        except Exception as e:
            return False, False, [f"Write Failed: {e}"]

    if not changes:
        changes = ["Remote execution config correct"]

    enabled = not needs_fix or auto_fix
    modified = auto_fix and bool(missing_settings)

    return enabled, modified, changes


def run_config_check(project_root: Path, auto_fix: bool = False) -> Dict[str, Any]:
    """
    Run full config check and fix.

    Args:
        project_root: Project root directory
        auto_fix: Whether to automatically fix issues

    Returns:
        Result dictionary
    """
    result = {
        "status": "ok",
        "python_plugin": {
            "path": None,
            "enabled": False,
            "modified": False,
            "message": ""
        },
        "remote_execution": {
            "path": None,
            "enabled": False,
            "modified": False,
            "message": ""
        },
        "restart_needed": False,
        "summary": ""
    }

    # Find .uproject
    uproject_path = find_uproject(project_root)
    if not uproject_path:
        result["status"] = "error"
        result["summary"] = f"No .uproject found in {project_root}"
        return result

    result["python_plugin"]["path"] = str(uproject_path.name)

    # Check Python Plugin
    enabled, modified, message = check_python_plugin(uproject_path, auto_fix)
    result["python_plugin"]["enabled"] = enabled
    result["python_plugin"]["modified"] = modified
    result["python_plugin"]["message"] = message

    if modified:
        result["restart_needed"] = True
        result["status"] = "fixed"
    elif not enabled:
        result["status"] = "needs_fix"

    # Check DefaultEngine.ini
    ini_path = project_root / "Config" / "DefaultEngine.ini"
    result["remote_execution"]["path"] = str(ini_path.relative_to(project_root))

    enabled, modified, changes = check_remote_execution(ini_path, auto_fix)
    result["remote_execution"]["enabled"] = enabled
    result["remote_execution"]["modified"] = modified
    result["remote_execution"]["message"] = "; ".join(changes)

    if modified:
        result["restart_needed"] = True
        if result["status"] == "ok":
            result["status"] = "fixed"
    elif not enabled and result["status"] != "fixed":
        result["status"] = "needs_fix"

    # Summary
    if result["status"] == "error":
        pass
    elif result["status"] == "fixed":
        fix_count = (1 if result["python_plugin"]["modified"] else 0) + \
                   (1 if result["remote_execution"]["modified"] else 0)
        result["summary"] = f"Fixed {fix_count} issues. Restart required."
    elif result["status"] == "needs_fix":
        result["summary"] = "Issues found. Auto-fix required."
    else:
        result["summary"] = "All good."

    return result


def main():
    """CLI Entry point"""
    parser = argparse.ArgumentParser(
        description="UE5 Project Configuration Check & Fix Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check only (using CLAUDE_PROJECT_DIR)
  python -m ue5_remote.config --check-only

  # Auto fix
  python -m ue5_remote.config --auto-fix

  # Specify project
  python -m ue5_remote.config --project /path/to/project --auto-fix
        """
    )
    
    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help="Project root path (default: CLAUDE_PROJECT_DIR or current dir)"
    )

    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Automatically fix configuration issues"
    )

    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check only, do not fix (default)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    project_path = args.project if args.project else find_ue5_project_root()
    auto_fix = args.auto_fix and not args.check_only

    result = run_config_check(project_path, auto_fix)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*60}")
        print("UE5 Project Configuration Check")
        print(f"{'='*60}\n")
        
        print(f"Project: {project_path}")
        print(f"Status: {result['status']}\n")
        
        print("Python Plugin:")
        print(f"  Path: {result['python_plugin']['path']}")
        print(f"  Enabled: {'[x]' if result['python_plugin']['enabled'] else '[ ]'}")
        print(f"  Modified: {'[x]' if result['python_plugin']['modified'] else '[ ]'}")
        print(f"  Message: {result['python_plugin']['message']}\n")
        
        print("Remote Execution:")
        print(f"  Path: {result['remote_execution']['path']}")
        print(f"  Enabled: {'[x]' if result['remote_execution']['enabled'] else '[ ]'}")
        print(f"  Modified: {'[x]' if result['remote_execution']['modified'] else '[ ]'}")
        print(f"  Message: {result['remote_execution']['message']}\n")
        
        if result['restart_needed']:
            print("[WARN] Configuration changed. Please restart UE5 Editor.\n")
            
        print(f"Summary: {result['summary']}")
        print(f"{'='*60}\n")

    if result["status"] == "error":
        sys.exit(1)
    elif result["status"] == "needs_fix":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
