#!/usr/bin/env python3
import json
import sys
import re
from dataclasses import dataclass


@dataclass
class ApiRule:
    """Rule for checking discouraged API usage."""
    pattern: str  # Regex pattern to match the API
    message: str  # Message to display when the API is detected


# List of API usage rules
# This includes deprecated APIs, APIs with better alternatives, and APIs that violate best practices
API_RULES = [
    # Deprecated EditorLevelLibrary APIs - use LevelEditorSubsystem instead
    ApiRule(
        pattern=r"EditorLevelLibrary\.load_level",
        message="EditorLevelLibrary.load_level() is deprecated. Use unreal.LevelEditorSubsystem's function instead"
    ),

    # Be careful with parameter order of unreal.Rotator
    ApiRule(
        pattern=r"unreal\.Rotator\((?![^)]*=)[^)]",
        message="unreal.Rotator's parameter order might be confusing. Use named parameters to avoid mistakes, like unreal.Rotator(roll=0, pitch=0, yaw=0)"
    )
]


def check_api_usage(content: str) -> list[str]:
    """Check content for discouraged API usage and return list of violation messages."""
    violations = []
    for rule in API_RULES:
        if re.search(rule.pattern, content):
            violations.append(rule.message)
    return violations


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # 仅对 Write 和 Edit 工具进行检查
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    # 仅检查 Python 文件
    if not file_path.endswith(".py"):
        sys.exit(0)

    # 获取要写入的内容
    if tool_name == "Write":
        content = tool_input.get("content", "")
    else:  # Edit
        content = tool_input.get("new_string", "")

    if not 'unreal' in content:
        sys.exit(0)  # 如果内容中不包含 'unreal'，则跳过检查

    # 检查是否使用了不推荐的 API
    violations = check_api_usage(content)
    if violations:
        for message in violations:
            print(message, file=sys.stderr)
        sys.exit(2)  # Exit code 2 阻止工具执行

    sys.exit(0)


if __name__ == "__main__":
    main()
