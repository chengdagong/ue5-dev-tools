"""
PreToolUse hook to check if UE5 Python scripts with asset operations use transactions.
"""
import sys
import re

def check_transaction_usage(content, file_path):
    """
    Check if a Python file with 'import unreal' contains asset operations
    that are not wrapped in transactions.

    Returns (is_valid, error_message)
    """
    # Check if this is a UE5 Python script
    if 'import unreal' not in content:
        return True, None

    # Asset operation patterns that should be in transactions
    asset_operations = [
        r'\.set_editor_property\(',
        r'.*save.*\(',
        r'\.set_editor_properties\(',
        r'\.modify\(',
    ]

    # Check if any asset operations exist
    has_asset_ops = False
    for pattern in asset_operations:
        if re.search(pattern, content):
            has_asset_ops = True
            break

    if not has_asset_ops:
        return True, None  # No asset operations, OK

    # Check if transaction is used
    has_transaction = bool(
        re.search(r'with\s+unreal\.ScopedEditorTransaction\s*\(', content) or
        re.search(r'unreal\.ScopedEditorTransaction\(', content)
    )

    if not has_transaction:
        error_msg = f"""
❌ Transaction Check Failed for: {file_path}

This Python file contains UE5 asset modification operations but does NOT use transactions.

Asset operations detected (one or more of):
- set_editor_property()
- save_loaded_asset()
- set_editor_properties()
- modify()

REQUIRED: Wrap asset modifications in a transaction:

    with unreal.ScopedEditorTransaction("Description") as trans:
        asset.set_editor_property("property_name", value)
        unreal.EditorAssetLibrary.save_loaded_asset(asset)

Why transactions are required:
- Enables automatic rollback on failure
- Provides undo functionality in editor
- Ensures data consistency

Please fix the code before proceeding.
"""
        return False, error_msg

    return True, None


def main():
    """Main hook entry point."""
    # Read tool input from stdin (JSON format)
    import json

    try:
        tool_input = json.load(sys.stdin)
        tool_name = tool_input.get('tool_name', '')

        # Only check Write and Edit tools
        if tool_name not in ['Write', 'Edit']:
            sys.exit(0)

        # Get file path and content
        file_path = tool_input.get('tool_input', {}).get('file_path', '')

        # Only check Python files
        if not file_path.endswith('.py'):
            sys.exit(0)

        # For Write tool, get content directly
        if tool_name == 'Write':
            content = tool_input.get('tool_input', {}).get('content', '')
        # For Edit tool, we need to read the file (after edit is applied)
        else:
            # For Edit, we can't easily check without reading the file
            # Skip for now or implement file reading logic
            sys.exit(0)

        # Check transaction usage
        is_valid, error_msg = check_transaction_usage(content, file_path)

        if not is_valid:
            print(error_msg, file=sys.stderr)
            sys.exit(2)  # Exit code 2 blocks the tool execution

        sys.exit(0)  # Success

    except Exception as e:
        # Don't block on hook errors
        print(f"Hook error (non-blocking): {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == '__main__':
    main()
