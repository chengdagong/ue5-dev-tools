#!/usr/bin/env python3
"""
VSCode 配置设置工具

自动生成 .vscode/launch.json 和 .vscode/tasks.json，
使用正确的插件路径（从 CLAUDE_PLUGIN_ROOT 获取）。
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
    """创建 launch.json 配置"""
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
    """创建 tasks.json 配置"""
    # 计算脚本的绝对路径（引用 executor 和 debugger 技能）
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
                    # --project-name 会从 CLAUDE_PROJECT_DIR 自动推断
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
                    # --project-name 会从 CLAUDE_PROJECT_DIR 自动推断
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
    合并 JSON 配置文件

    Args:
        file_path: 配置文件路径
        new_config: 新配置内容
        key: 要合并的键（如 'configurations' 或 'tasks'）

    Returns:
        是否进行了合并
    """
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)

            # 检查是否已存在相同的配置
            existing_items = existing.get(key, [])
            new_items = new_config.get(key, [])

            # 按名称/label去重
            name_key = "name" if key == "configurations" else "label"
            existing_names = {item.get(name_key) for item in existing_items}
            new_names = {item.get(name_key) for item in new_items}

            if new_names.issubset(existing_names):
                print(f"✓ {file_path.name} 已包含所有必要的配置，跳过")
                return False

            # 合并配置
            for item in new_items:
                item_name = item.get(name_key)
                # 如果已存在，替换；否则添加
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
            print(f"⚠️  警告: {file_path.name} 格式错误，将备份并覆盖: {e}")
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            file_path.rename(backup_path)
            print(f"   备份保存到: {backup_path}")

    # 写入配置
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(new_config, f, indent=2, ensure_ascii=False)

    return True


def setup_vscode_config(project_root: Path, plugin_root: Path, force: bool = False) -> bool:
    """
    设置 VSCode 配置

    Args:
        project_root: 项目根目录
        plugin_root: 插件根目录
        force: 是否强制覆盖现有配置

    Returns:
        是否成功设置
    """
    vscode_dir = project_root / ".vscode"
    launch_json = vscode_dir / "launch.json"
    tasks_json = vscode_dir / "tasks.json"

    print(f"项目根目录: {project_root}")
    print(f"插件根目录: {plugin_root}")
    print()

    # 创建配置
    launch_config = create_launch_config(plugin_root)
    tasks_config = create_tasks_config(plugin_root)

    # 处理 launch.json
    print("配置 launch.json...")
    if force or not launch_json.exists():
        launch_json.parent.mkdir(parents=True, exist_ok=True)
        with open(launch_json, 'w', encoding='utf-8') as f:
            json.dump(launch_config, f, indent=2, ensure_ascii=False)
        print(f"✓ 创建 {launch_json}")
    else:
        if merge_json_file(launch_json, launch_config, "configurations"):
            print(f"✓ 更新 {launch_json}")

    # 处理 tasks.json
    print("配置 tasks.json...")
    if force or not tasks_json.exists():
        tasks_json.parent.mkdir(parents=True, exist_ok=True)
        with open(tasks_json, 'w', encoding='utf-8') as f:
            json.dump(tasks_config, f, indent=2, ensure_ascii=False)
        print(f"✓ 创建 {tasks_json}")
    else:
        if merge_json_file(tasks_json, tasks_config, "tasks"):
            print(f"✓ 更新 {tasks_json}")

    print()
    print("✓ VSCode 配置完成！")
    print()
    print("使用方法:")
    print("  1. 在 VSCode 中打开任意 Python 文件")
    print("  2. 按 F5 启动调试")
    print("  3. 选择 'UE5 Python: Debug Current File' 配置")
    print()

    return True


def main():
    parser = argparse.ArgumentParser(
        description="VSCode 配置设置工具 - 自动生成 UE5 Python 调试配置",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认路径（从环境变量获取）
  %(prog)s

  # 指定项目路径
  %(prog)s --project /path/to/ue5/project

  # 强制覆盖现有配置
  %(prog)s --force

环境变量:
  CLAUDE_PROJECT_DIR - Claude Code 自动注入的项目根目录
  CLAUDE_PLUGIN_ROOT - Claude Code 自动注入的插件根目录
        """
    )

    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help="项目根目录路径 (默认: CLAUDE_PROJECT_DIR 或当前目录)"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="强制覆盖现有配置"
    )

    args = parser.parse_args()

    # 获取路径
    project_root = args.project if args.project else get_project_root()
    plugin_root = get_plugin_root()

    # 验证插件路径（验证依赖的 executor 技能）
    remote_exec_script = plugin_root / "skills" / "ue5-python-executor" / "scripts" / "remote-execute.py"
    if not remote_exec_script.exists():
        print(f"错误: 无法找到 ue5-python-executor 技能脚本: {remote_exec_script}", file=sys.stderr)
        print(f"插件根目录: {plugin_root}", file=sys.stderr)
        print("请确保 ue5-python-executor 技能已安装", file=sys.stderr)
        sys.exit(1)

    # 设置配置
    try:
        setup_vscode_config(project_root, plugin_root, args.force)
        sys.exit(0)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
