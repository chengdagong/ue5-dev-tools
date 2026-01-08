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
    from .utils import get_default_project_path
except ImportError:
    # Fallback for direct execution
    from utils import get_default_project_path

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
    Check and optionally fix PythonScriptPlugin in .uproject.

    Args:
        uproject_path: Path to .uproject file
        auto_fix: Whether to automatically fix issues

    Returns:
        (enabled, modified, message)
    """
    try:
        with open(uproject_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        return False, False, f"JSON Parse Error: {e}"
    except Exception as e:
        return False, False, f"Read Failed: {e}"

    plugins = config.get("Plugins", [])
    python_plugin = next(
        (p for p in plugins if p.get("Name") == "PythonScriptPlugin"),
        None
    )

    # Check plugin status
    if python_plugin is None:
        if auto_fix:
            plugins.append({
                "Name": "PythonScriptPlugin",
                "Enabled": True
            })
            config["Plugins"] = plugins

            try:
                with open(uproject_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent="\t")
                return True, True, "Added PythonScriptPlugin to Plugins array"
            except Exception as e:
                return False, False, f"Write Failed: {e}"
        else:
            return False, False, "PythonScriptPlugin not in Plugins array"

    elif not python_plugin.get("Enabled", False):
        if auto_fix:
            python_plugin["Enabled"] = True

            try:
                with open(uproject_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent="\t")
                return True, True, "Enabled PythonScriptPlugin"
            except Exception as e:
                return False, False, f"Write Failed: {e}"
        else:
            return False, False, "PythonScriptPlugin exists but disabled"

    return True, False, "PythonScriptPlugin correctly configured"


def check_remote_execution(ini_path: Path, auto_fix: bool = False) -> Tuple[bool, bool, List[str]]:
    """
    Check and optionally fix Remote Execution settings in DefaultEngine.ini.

    Args:
        ini_path: Path to DefaultEngine.ini
        auto_fix: Whether to automatically fix issues

    Returns:
        (enabled, modified, changes_list)
    """
    section = "/Script/PythonScriptPlugin.PythonScriptPluginSettings"

    # If file doesn't exist
    if not ini_path.exists():
        if auto_fix:
            ini_path.parent.mkdir(parents=True, exist_ok=True)
            config = configparser.ConfigParser()
            config.add_section(section)
            config.set(section, "bRemoteExecution", "True")
            config.set(section, "bDeveloperMode", "True")
            config.set(section, "RemoteExecutionMulticastBindAddress", "0.0.0.0")

            try:
                with open(ini_path, 'w', encoding='utf-8') as f:
                    config.write(f)
                return True, True, [
                    "Created DefaultEngine.ini",
                    "Set bRemoteExecution=True",
                    "Set bDeveloperMode=True",
                    "Set RemoteExecutionMulticastBindAddress=0.0.0.0"
                ]
            except Exception as e:
                return False, False, [f"Write Failed: {e}"]
        else:
            return False, False, ["DefaultEngine.ini does not exist"]

    # Read existing config
    config = configparser.ConfigParser(strict=False)
    try:
        config.read(ini_path, encoding='utf-8')
    except Exception as e:
        return False, False, [f"Read Failed: {e}"]

    changes = []
    needs_fix = False

    # Check section
    if section not in config:
        if auto_fix:
            config.add_section(section)
            changes.append(f"Created section [{section}]")
            needs_fix = True
        else:
            return False, False, [f"Missing section [{section}]"]

    # Check bRemoteExecution
    remote_exec = config.get(section, "bRemoteExecution", fallback=None)
    if remote_exec != "True":
        if auto_fix:
            config.set(section, "bRemoteExecution", "True")
            # Usually strict requirement for multicast discovery
            config.set(section, "RemoteExecutionMulticastBindAddress", "0.0.0.0")
            changes.append(f"Set bRemoteExecution=True (was: {remote_exec})")
            needs_fix = True
        else:
            needs_fix = True
            changes.append(f"bRemoteExecution needs True (is: {remote_exec})")

    # Check bDeveloperMode
    dev_mode = config.get(section, "bDeveloperMode", fallback=None)
    if dev_mode != "True":
        if auto_fix:
            config.set(section, "bDeveloperMode", "True")
            changes.append(f"Set bDeveloperMode=True (was: {dev_mode})")
            needs_fix = True
        else:
            needs_fix = True
            changes.append(f"bDeveloperMode needs True (is: {dev_mode})")

    # Write back
    if auto_fix and needs_fix:
        try:
            with open(ini_path, 'w', encoding='utf-8') as f:
                config.write(f)
        except Exception as e:
            return False, False, [f"Write Failed: {e}"]

    if not changes:
        changes = ["Remote execution config correct"]

    enabled = not needs_fix or auto_fix
    modified = auto_fix and needs_fix

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

    project_path = args.project if args.project else get_default_project_path()
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
        print(f"  Enabled: {'✓' if result['python_plugin']['enabled'] else '✗'}")
        print(f"  Modified: {'✓' if result['python_plugin']['modified'] else '✗'}")
        print(f"  Message: {result['python_plugin']['message']}\n")
        
        print("Remote Execution:")
        print(f"  Path: {result['remote_execution']['path']}")
        print(f"  Enabled: {'✓' if result['remote_execution']['enabled'] else '✗'}")
        print(f"  Modified: {'✓' if result['remote_execution']['modified'] else '✗'}")
        print(f"  Message: {result['remote_execution']['message']}\n")
        
        if result['restart_needed']:
            print("⚠️  Configuration changed. Please restart UE5 Editor.\n")
            
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
