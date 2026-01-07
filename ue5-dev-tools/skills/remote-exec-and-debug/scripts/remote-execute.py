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

# Configure logging
logging.basicConfig(
    format="[%(levelname)s] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class UE5RemoteExecution:
    """
    Execute commands in UE5 editor via Python Remote Execution (socket-based).

    Requires:
    - Python plugin with remote execution enabled
    - UE5 project with proper configuration
    """

    # Protocol constants
    MAGIC = "ue_py"
    PROTOCOL_VERSION = 1
    SOCKET_TIMEOUT = 0.5
    BUFFER_SIZE = 2_097_152

    class ExecTypes:
        EXECUTE_FILE = "ExecuteFile"
        EXECUTE_STATEMENT = "ExecuteStatement"
        EVALUATE_STATEMENT = "EvaluateStatement"

    def __init__(self,
                 multicast_group: Tuple[str, int] = ("239.0.0.1", 6766),
                 multicast_bind_address: str = "0.0.0.0",
                 project_name: str = ""):
        self.multicast_group = multicast_group
        self.multicast_bind_address = multicast_bind_address
        self.project_name = project_name
        self.unreal_node_id = None
        self.mcast_sock = None
        self.cmd_sock = None
        self.cmd_connection = None

    def _create_multicast_socket(self) -> socket.socket:
        """Create and configure multicast socket."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(self.SOCKET_TIMEOUT)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 0)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.bind((self.multicast_bind_address, self.multicast_group[1]))

        membership = socket.inet_aton(self.multicast_group[0])
        bind_addr = socket.inet_aton(self.multicast_bind_address)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership + bind_addr)

        return sock

    def _send_message(self, sock: socket.socket, message: Dict[str, Any]):
        """Send JSON message via socket."""
        data = json.dumps(message).encode()
        sock.sendto(data, self.multicast_group)

    def _receive_messages(self, sock: socket.socket, message_type: str) -> Optional[Dict]:
        """Receive and parse JSON messages from socket."""
        data_received = b''

        try:
            while True:
                try:
                    data, _ = sock.recvfrom(self.BUFFER_SIZE)
                    data_received += data

                    try:
                        json_data = json.loads(data_received)
                        data_received = b''
                    except json.JSONDecodeError:
                        continue

                    if json_data.get("type") == message_type:
                        continue  # Ignore echo

                    # Check project name if specified
                    if self.project_name and "data" in json_data:
                        if json_data["data"].get("project_name") != self.project_name:
                            continue

                    return json_data

                except socket.timeout:
                    break
        except Exception as e:
            logger.error(f"Error receiving message: {e}")

        return None

    def find_unreal_instance(self) -> bool:
        """Find and connect to running UE5 instance."""
        try:
            self.mcast_sock = self._create_multicast_socket()

            # Send ping message
            ping_msg = {
                "version": self.PROTOCOL_VERSION,
                "magic": self.MAGIC,
                "source": "python_executor",
                "type": "ping"
            }

            self._send_message(self.mcast_sock, ping_msg)
            logger.info(f"Searching for UE5 instance{'...' if not self.project_name else f' (project: {self.project_name})...'}")

            # Receive pong
            pong = self._receive_messages(self.mcast_sock, "ping")

            if pong:
                self.unreal_node_id = pong.get("source")
                project = pong.get("data", {}).get("project_name", "Unknown")
                engine = pong.get("data", {}).get("engine_version", "Unknown")
                logger.info(f"Found UE5: {project} ({engine})")
                return True
            else:
                logger.error("No UE5 instance found")
                return False

        except Exception as e:
            logger.error(f"Failed to find UE5: {e}")
            return False

    def open_connection(self) -> bool:
        """Open command connection to UE5."""
        try:
            if not self.unreal_node_id:
                logger.error("Must find UE5 instance first")
                return False

            # Get available port
            with socket.socket() as s:
                s.bind(('', 0))
                cmd_port = s.getsockname()[1]

            # Send open connection message
            open_msg = {
                "type": "open_connection",
                "version": self.PROTOCOL_VERSION,
                "magic": self.MAGIC,
                "source": "python_executor",
                "dest": self.unreal_node_id,
                "data": {
                    "command_ip": "127.0.0.1",
                    "command_port": cmd_port
                }
            }

            self._send_message(self.mcast_sock, open_msg)

            # Create command socket
            self.cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.cmd_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.cmd_sock.bind(("127.0.0.1", cmd_port))
            self.cmd_sock.settimeout(2.0)
            self.cmd_sock.listen()

            self.cmd_connection, _ = self.cmd_sock.accept()
            self.cmd_connection.settimeout(5.0)

            logger.info("Command connection established")
            return True

        except Exception as e:
            logger.error(f"Failed to open connection: {e}")
            return False

    def execute_command(self, command: str,
                       exec_type: str = None,
                       timeout: float = 5.0) -> Dict[str, Any]:
        """
        Execute Python command in UE5.

        Args:
            command: Python code or file path
            exec_type: ExecTypes.EXECUTE_FILE, EXECUTE_STATEMENT, or EVALUATE_STATEMENT
            timeout: Timeout for command execution

        Returns:
            Dictionary with execution result
        """
        if exec_type is None:
            exec_type = self.ExecTypes.EVALUATE_STATEMENT

        try:
            # Send command message
            cmd_msg = {
                "type": "command",
                "version": self.PROTOCOL_VERSION,
                "magic": self.MAGIC,
                "source": "python_executor",
                "dest": self.unreal_node_id,
                "data": {
                    "command": command,
                    "unattended": True,
                    "exec_mode": exec_type
                }
            }

            data = json.dumps(cmd_msg).encode()
            self.cmd_connection.sendto(data, ("127.0.0.1", 0))

            # Receive result
            self.cmd_connection.settimeout(timeout)
            data_received = b''
            result_data = None

            while True:
                try:
                    data, _ = self.cmd_connection.recvfrom(self.BUFFER_SIZE)
                    data_received += data

                    try:
                        json_data = json.loads(data_received)
                        data_received = b''
                    except json.JSONDecodeError:
                        continue

                    if json_data.get("type") == "command":
                        continue  # Ignore echo

                    result_data = json_data
                    break

                except socket.timeout:
                    break

            if result_data:
                success = result_data.get("data", {}).get("success", False)
                result = result_data.get("data", {}).get("result", "")
                output = result_data.get("data", {}).get("output", [])

                logger.info(f"Command executed: {'Success' if success else 'Failed'}")

                return {
                    "success": success,
                    "result": result,
                    "output": output,
                    "raw": result_data
                }
            else:
                return {
                    "success": False,
                    "error": "No response from UE5",
                    "output": []
                }

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "output": []
            }

    def close_connection(self):
        """Close connection to UE5."""
        try:
            if self.unreal_node_id and self.mcast_sock:
                close_msg = {
                    "type": "close_connection",
                    "version": self.PROTOCOL_VERSION,
                    "magic": self.MAGIC,
                    "source": "python_executor",
                    "dest": self.unreal_node_id
                }

                self._send_message(self.mcast_sock, close_msg)

            if self.cmd_connection:
                self.cmd_connection.close()
            if self.cmd_sock:
                self.cmd_sock.close()
            if self.mcast_sock:
                self.mcast_sock.close()

            logger.info("Connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")


def get_default_project_name() -> Optional[str]:
    """
    获取默认项目名称（从 CLAUDE_PROJECT_DIR 推断）

    如果设置了 CLAUDE_PROJECT_DIR，提取目录名作为项目名
    """
    if "CLAUDE_PROJECT_DIR" in os.environ:
        project_dir = os.environ["CLAUDE_PROJECT_DIR"]
        return os.path.basename(project_dir.rstrip("/"))
    return None


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
