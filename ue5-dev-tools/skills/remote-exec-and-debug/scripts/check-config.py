#!/usr/bin/env python3
"""
UE5 项目配置检查和修复工具

自动检查并修复 UE5 项目的 Python 插件配置：
- .uproject 文件中的 PythonScriptPlugin
- DefaultEngine.ini 中的 remote execution 设置
"""

import json
import configparser
import sys
import os
import argparse
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional


def find_uproject(project_root: Path) -> Optional[Path]:
    """
    查找项目根目录的 .uproject 文件

    Args:
        project_root: 项目根目录路径

    Returns:
        .uproject 文件路径，如果未找到返回 None
    """
    uproject_files = list(project_root.glob("*.uproject"))

    if not uproject_files:
        return None

    if len(uproject_files) > 1:
        print(f"警告: 发现多个 .uproject 文件，使用第一个: {uproject_files[0].name}",
              file=sys.stderr)

    return uproject_files[0]


def check_python_plugin(uproject_path: Path, auto_fix: bool = False) -> Tuple[bool, bool, str]:
    """
    检查并可选修复 .uproject 中的 PythonScriptPlugin

    Args:
        uproject_path: .uproject 文件路径
        auto_fix: 是否自动修复

    Returns:
        (enabled, modified, message) 元组
        - enabled: 插件是否已启用
        - modified: 是否进行了修改
        - message: 详细说明
    """
    try:
        with open(uproject_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        return False, False, f"JSON 解析错误: {e}"
    except Exception as e:
        return False, False, f"读取文件失败: {e}"

    plugins = config.get("Plugins", [])
    python_plugin = next(
        (p for p in plugins if p.get("Name") == "PythonScriptPlugin"),
        None
    )

    # 检查插件状态
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
                return True, True, "已添加 PythonScriptPlugin 到 Plugins 数组"
            except Exception as e:
                return False, False, f"写入文件失败: {e}"
        else:
            return False, False, "PythonScriptPlugin 未在 Plugins 数组中"

    elif not python_plugin.get("Enabled", False):
        if auto_fix:
            python_plugin["Enabled"] = True

            try:
                with open(uproject_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent="\t")
                return True, True, "已启用 PythonScriptPlugin"
            except Exception as e:
                return False, False, f"写入文件失败: {e}"
        else:
            return False, False, "PythonScriptPlugin 已存在但未启用"

    return True, False, "PythonScriptPlugin 已正确配置"


def check_remote_execution(ini_path: Path, auto_fix: bool = False) -> Tuple[bool, bool, List[str]]:
    """
    检查并可选修复 DefaultEngine.ini 中的远程执行设置

    Args:
        ini_path: DefaultEngine.ini 文件路径
        auto_fix: 是否自动修复

    Returns:
        (enabled, modified, changes) 元组
        - enabled: 远程执行是否已启用
        - modified: 是否进行了修改
        - changes: 修改内容列表
    """
    section = "/Script/PythonScriptPlugin.PythonScriptPluginSettings"

    # 如果文件不存在且需要修复，创建新文件
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
                    "创建了 DefaultEngine.ini",
                    "设置 bRemoteExecution=True",
                    "设置 bDeveloperMode=True",
                    "设置 RemoteExecutionMulticastBindAddress=0.0.0.0"
                ]
            except Exception as e:
                return False, False, [f"写入文件失败: {e}"]
        else:
            return False, False, ["DefaultEngine.ini 文件不存在"]

    # 读取现有配置（允许重复键，UE5 使用重复键表示数组）
    config = configparser.ConfigParser(strict=False)
    try:
        config.read(ini_path, encoding='utf-8')
    except Exception as e:
        return False, False, [f"读取文件失败: {e}"]

    changes = []
    needs_fix = False

    # 检查 section 是否存在
    if section not in config:
        if auto_fix:
            config.add_section(section)
            changes.append(f"创建了 section [{section}]")
            needs_fix = True
        else:
            return False, False, [f"缺少 section [{section}]"]

    # 检查 bRemoteExecution
    remote_exec = config.get(section, "bRemoteExecution", fallback=None)
    if remote_exec != "True":
        if auto_fix:
            config.set(section, "bRemoteExecution", "True")
            config.set(section, "RemoteExecutionMulticastBindAddress", "0.0.0.0")
            changes.append(f"设置 bRemoteExecution=True (原值: {remote_exec})")
            needs_fix = True
        else:
            needs_fix = True
            changes.append(f"bRemoteExecution 需要设置为 True (当前值: {remote_exec})")

    # 检查 bDeveloperMode
    dev_mode = config.get(section, "bDeveloperMode", fallback=None)
    if dev_mode != "True":
        if auto_fix:
            config.set(section, "bDeveloperMode", "True")
            changes.append(f"设置 bDeveloperMode=True (原值: {dev_mode})")
            needs_fix = True
        else:
            needs_fix = True
            changes.append(f"bDeveloperMode 需要设置为 True (当前值: {dev_mode})")

    # 写回文件（如果修改了）
    if auto_fix and needs_fix:
        try:
            with open(ini_path, 'w', encoding='utf-8') as f:
                config.write(f)
        except Exception as e:
            return False, False, [f"写入文件失败: {e}"]

    if not changes:
        changes = ["远程执行配置已正确"]

    enabled = not needs_fix or auto_fix
    modified = auto_fix and needs_fix

    return enabled, modified, changes


def run_config_check(project_root: Path, auto_fix: bool = False) -> Dict[str, Any]:
    """
    完整的配置检查和修复流程

    Args:
        project_root: 项目根目录
        auto_fix: 是否自动修复

    Returns:
        配置检查结果字典
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

    # 查找 .uproject 文件
    uproject_path = find_uproject(project_root)
    if not uproject_path:
        result["status"] = "error"
        result["summary"] = f"未在 {project_root} 找到 .uproject 文件"
        return result

    result["python_plugin"]["path"] = str(uproject_path.name)

    # 检查 Python 插件
    enabled, modified, message = check_python_plugin(uproject_path, auto_fix)
    result["python_plugin"]["enabled"] = enabled
    result["python_plugin"]["modified"] = modified
    result["python_plugin"]["message"] = message

    if modified:
        result["restart_needed"] = True
        result["status"] = "fixed"
    elif not enabled:
        result["status"] = "needs_fix"

    # 检查 DefaultEngine.ini
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

    # 生成摘要
    if result["status"] == "error":
        pass  # 已经设置了摘要
    elif result["status"] == "fixed":
        fix_count = (1 if result["python_plugin"]["modified"] else 0) + \
                   (1 if result["remote_execution"]["modified"] else 0)
        result["summary"] = f"已修复 {fix_count} 个配置问题，需要重启 UE5 编辑器"
    elif result["status"] == "needs_fix":
        result["summary"] = "发现配置问题，请使用 --auto-fix 参数自动修复"
    else:
        result["summary"] = "所有配置已正确"

    return result


def get_default_project_path() -> Path:
    """
    获取默认项目路径

    优先级：
    1. CLAUDE_PROJECT_DIR 环境变量
    2. 当前工作目录
    """
    if "CLAUDE_PROJECT_DIR" in os.environ:
        return Path(os.environ["CLAUDE_PROJECT_DIR"])
    return Path.cwd()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="UE5 项目配置检查和修复工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 只检查配置 (使用当前项目或 CLAUDE_PROJECT_DIR)
  %(prog)s --check-only

  # 自动检查并修复
  %(prog)s --auto-fix

  # 指定项目路径
  %(prog)s --project /path/to/project --auto-fix

  # 输出 JSON 格式
  %(prog)s --auto-fix --json

环境变量:
  CLAUDE_PROJECT_DIR - Claude Code 自动注入的项目根目录
        """
    )

    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help="项目根目录路径 (默认: CLAUDE_PROJECT_DIR 或当前目录)"
    )

    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="自动修复配置问题"
    )

    parser.add_argument(
        "--check-only",
        action="store_true",
        help="只检查，不修复 (默认行为)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果"
    )

    args = parser.parse_args()

    # 确定项目路径
    project_path = args.project if args.project else get_default_project_path()

    # 确定是否自动修复
    auto_fix = args.auto_fix and not args.check_only

    # 运行配置检查
    result = run_config_check(project_path, auto_fix)

    # 输出结果
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*60}")
        print("UE5 项目配置检查结果")
        print(f"{'='*60}\n")

        print(f"项目路径: {project_path}")
        print(f"状态: {result['status']}\n")

        print("Python 插件配置:")
        print(f"  文件: {result['python_plugin']['path']}")
        print(f"  已启用: {'✓' if result['python_plugin']['enabled'] else '✗'}")
        print(f"  已修改: {'✓' if result['python_plugin']['modified'] else '✗'}")
        print(f"  说明: {result['python_plugin']['message']}\n")

        print("远程执行配置:")
        print(f"  文件: {result['remote_execution']['path']}")
        print(f"  已启用: {'✓' if result['remote_execution']['enabled'] else '✗'}")
        print(f"  已修改: {'✓' if result['remote_execution']['modified'] else '✗'}")
        print(f"  说明: {result['remote_execution']['message']}\n")

        if result['restart_needed']:
            print("⚠️  配置文件已修改，需要重启 UE5 编辑器使配置生效\n")

        print(f"摘要: {result['summary']}")
        print(f"{'='*60}\n")

    # 根据状态返回退出码
    if result["status"] == "error":
        sys.exit(1)
    elif result["status"] == "needs_fix":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
