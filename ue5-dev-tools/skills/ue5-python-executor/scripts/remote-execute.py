#!/usr/bin/env python3
"""
UE5 Remote Python Script Executor

This script allows you to execute arbitrary Python scripts in a connected UE5 editor
using the Python plugin's socket-based remote execution capabilities.

The script uses multicast discovery to find running UE5 instances and establishes
a socket connection for direct Python code execution.

Usage:
    # Execute Python code
    python remote-exec --code "print('Hello')" --project-path /path/to/project.uproject

    # Execute a Python file
    python remote-exec --file /path/to/script.py --project-path /path/to/project.uproject

    # Execute with project name filter
    python remote-exec --code "print('Hello')" --project-name MyProject

    # Execute file with custom multicast group
    python remote-exec --file script.py --project-path project.uproject --multicast-group 239.0.0.1:6766

Requirements:
    - UE5 with Python plugin enabled
    - Python remote execution enabled in project settings
"""

import argparse
import json
import logging
import os
import socket
import sys
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# Add lib directory to Python path
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))
from ue5_remote import UE5RemoteExecution, get_default_project_name

# Configure logging
logging.basicConfig(
    format="[%(levelname)s] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Execute arbitrary Python scripts in UE5 editor via socket-based remote execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute Python code
  python remote-execute.py --code "print('Hello')" --project-path /path/to/project.uproject

  # Execute a Python file
  python remote-execute.py --file script.py --project-path /path/to/project.uproject

  # Filter by project name (auto-detected from CLAUDE_PROJECT_DIR)
  python remote-execute.py --code "print('Hello')"

  # Custom multicast group
  python remote-execute.py --file script.py --project-path project.uproject --multicast-group 239.0.0.1:6766

  # Enable verbose logging
  python remote-execute.py --code "..." --project-path project.uproject -v

Environment Variables:
  CLAUDE_PROJECT_DIR - Auto-injected by Claude Code, used to infer project name
        """
    )

    parser.add_argument(
        "--code",
        help="Python code to execute"
    )

    parser.add_argument(
        "--file",
        type=Path,
        help="Python file to execute"
    )

    parser.add_argument(
        "--project-path",
        type=Path,
        help="Path to .uproject file (optional if --project-name is specified)"
    )

    parser.add_argument(
        "--project-name",
        default=None,
        help="Project name to filter UE5 instances (default: auto-detect from CLAUDE_PROJECT_DIR)"
    )

    parser.add_argument(
        "--multicast-group",
        default="239.0.0.1:6766",
        help="Multicast group IP:port (default: 239.0.0.1:6766)"
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Command execution timeout in seconds (default: 5.0)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--detached",
        action="store_true",
        help="Run in detached mode (spawn subprocess and exit)"
    )

    parser.add_argument(
        "--wait",
        type=float,
        default=0.0,
        help="Wait time in seconds before execution (useful for detached mode)"
    )

    args = parser.parse_args()

    # Handle detached mode
    if args.detached:
        # Filter out --detached from arguments
        new_args = [sys.executable] + [arg for arg in sys.argv if arg != "--detached"]

        # Spawn detached subprocess
        subprocess.Popen(
            new_args,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
        sys.exit(0)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Wait if requested
    if args.wait > 0:
        logger.info(f"Waiting {args.wait} seconds before execution...")
        time.sleep(args.wait)

    # Validate arguments
    if not args.code and not args.file:
        parser.error("Either --code or --file must be specified")

    # 确定项目名称（优先级：命令行参数 > 环境变量自动检测）
    project_name = args.project_name if args.project_name else get_default_project_name()

    if not args.project_path and not project_name:
        parser.error("Either --project-path or --project-name must be specified (or CLAUDE_PROJECT_DIR must be set)")

    # Prepare command
    if args.code:
        command = args.code
        exec_type = UE5RemoteExecution.ExecTypes.EXECUTE_FILE
    else:
        command = str(args.file.absolute())
        exec_type = UE5RemoteExecution.ExecTypes.EXECUTE_FILE

    # Parse multicast group
    try:
        ip, port = args.multicast_group.split(":")
        multicast_group = (ip, int(port))
    except ValueError:
        parser.error("Invalid multicast group format. Use IP:port")

    # Create executor
    executor = UE5RemoteExecution(
        multicast_group=multicast_group,
        project_name=project_name or ""
    )

    # Find and connect to UE5
    if not executor.find_unreal_instance():
        sys.exit(1)

    if not executor.open_connection():
        sys.exit(1)

    # Execute command
    try:
        result = executor.execute_command(command, exec_type=exec_type, timeout=args.timeout)
    finally:
        executor.close_connection()

    # Print results
    if "error" in result and result.get("error"):
        logger.error(f"Execution failed: {result['error']}")
        sys.exit(1)

    if "success" in result and result["success"]:
        if "result" in result:
            print(f"Result: {result['result']}")
        if "output" in result and result["output"]:
            print("Output:")
            for line in result["output"]:
                if isinstance(line, dict):
                    print(f"  {line.get('type', 'log')}: {line.get('output', '')}")
                else:
                    print(f"  {line}")
        sys.exit(0)
    else:
        logger.error("Command execution failed")
        if "raw" in result:
            print(json.dumps(result["raw"], indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
