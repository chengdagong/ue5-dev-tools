#!/usr/bin/env python3
"""
Hook script to check if a file operation involves a UE5 Python script.
- Non-UE5 Python: Silent allow (exit 0, no output)
- UE5 Python: Allow with context for Claude (exit 0, hookSpecificOutput)
"""
import sys
import json
import os

def main():
    # Read tool input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Can't parse input, allow operation
        sys.exit(0)
    
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    
    # Condition 1: Is it a Python file?
    if not file_path.endswith(".py"):
        # Not a Python file, silent ALLOW
        sys.exit(0)
    
    # Condition 2: Check if content contains 'import unreal'
    is_ue5_script = False
    
    # For Write tool, check the content being written
    if "content" in tool_input:
        content = tool_input.get("content", "")
        if "import unreal" in content:
            is_ue5_script = True
    
    # For Edit tool, check existing file content
    if "new_string" in tool_input or "old_string" in tool_input:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
                if "import unreal" in existing_content:
                    is_ue5_script = True
            except Exception:
                pass
    
    # If UE5 Python script, output context for Claude but still ALLOW
    if is_ue5_script:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "UE5 Python Script Detected - Please use the develop-ue5-python skill to follow the best-practice workflow if you're not using it."
            }
        }
        print(json.dumps(output))
    
    # Always allow (exit 0)
    sys.exit(0)

if __name__ == "__main__":
    main()
