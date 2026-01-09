#!/usr/bin/env python3
"""
UE5 API Search - Query class or function definitions from unreal.py stub files.

Usage:
    python api-search.py unreal.InputMappingContext
    python api-search.py unreal.log
    python api-search.py --input /path/to/unreal.py unreal.Actor
"""

import argparse
import os
import re
import sys


def find_ue5_project_root(start_dir):
    """Find UE5 project root by searching for .uproject file upward from start_dir."""
    current = os.path.abspath(start_dir)
    while True:
        # Check if any .uproject file exists in this directory
        try:
            for entry in os.listdir(current):
                if entry.endswith('.uproject'):
                    return current
        except OSError:
            pass
        parent = os.path.dirname(current)
        if parent == current:
            # Reached filesystem root
            return None
        current = parent


def find_stub_file(input_path=None):
    """Find the unreal.py stub file.

    Search order:
    1. Explicit --input path if provided
    2. Search upward from current working directory for UE5 project root
    """
    if input_path:
        input_path = input_path.strip()
        if os.path.exists(input_path):
            return input_path
        raise FileNotFoundError(f"Stub file not found: {input_path}")

    # Search upward from current working directory for UE5 project root
    project_root = find_ue5_project_root(os.getcwd())
    if project_root:
        stub_path = os.path.join(project_root, 'Intermediate', 'PythonStub', 'unreal.py')
        if os.path.exists(stub_path):
            return stub_path

    raise FileNotFoundError(
        "Cannot find unreal.py stub file. "
        "Use --input to specify path, or run from within a UE5 project directory."
    )


def parse_query(query):
    """Parse query string and extract the name to search for."""
    if query.startswith('unreal.'):
        name = query[7:]  # Remove 'unreal.' prefix
    else:
        name = query

    if not name:
        raise ValueError(f"Invalid query: {query}")

    return name


def is_class_name(name):
    """Check if name looks like a class (PascalCase) or function (snake_case/lowercase)."""
    return name[0].isupper()


def extract_deprecated_members(class_content):
    """Extract deprecated properties, methods, and enum values from a class definition.

    Returns a tuple of (deprecated_properties, deprecated_methods, deprecated_enum_values).
    Each is a dict mapping name to deprecation message.
    """
    deprecated_props = {}
    deprecated_methods = {}
    deprecated_enum_values = {}

    # Pattern A: Find @property with deprecated docstring
    # Look for @property followed by def name(...) with deprecated in docstring
    prop_pattern = r'@property\s+def\s+(\w+)\s*\([^)]*\)[^:]*:\s*r?"""[^"]*?(deprecated:[^\n"]+)'
    for match in re.finditer(prop_pattern, class_content, re.IGNORECASE | re.DOTALL):
        name = match.group(1)
        message = match.group(2).strip()
        deprecated_props[name] = message

    # Pattern B: Find "deprecated: Property 'name'" in docstrings (with full message)
    prop_explicit_pattern = r"(deprecated:\s*Property\s*'(\w+)'[^\n]*)"
    for match in re.finditer(prop_explicit_pattern, class_content, re.IGNORECASE):
        message = match.group(1).strip()
        prop_name = match.group(2)
        # Convert CamelCase to snake_case for property names
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', prop_name).lower()
        snake_name = snake_name.lstrip('b_')  # Handle bPropertyName -> property_name
        if snake_name.startswith('_'):
            snake_name = snake_name[1:]
        deprecated_props[snake_name] = message

    # Pattern C: Find enum values with _DEPRECATED suffix (extract comment if any)
    # Format: NAME_DEPRECATED: Type = ... #: number: optional comment
    enum_deprecated_pattern = r'^\s+(\w+_DEPRECATED)\s*:[^#\n]*#:\s*\d+(?::\s*(.+))?$'
    for match in re.finditer(enum_deprecated_pattern, class_content, re.MULTILINE):
        name = match.group(1)
        comment = match.group(2).strip() if match.group(2) else ""
        deprecated_enum_values[name] = comment if comment else "Deprecated"

    # Pattern D: Find "Will be deprecated" in enum value comments
    will_deprecate_pattern = r'^\s+(\w+)\s*:[^#\n]*#:\s*\d+:?\s*(.*Will be deprecated[^\n]*)'
    for match in re.finditer(will_deprecate_pattern, class_content, re.MULTILINE | re.IGNORECASE):
        name = match.group(1)
        message = match.group(2).strip()
        deprecated_enum_values[name] = message

    # Pattern E: Find methods with deprecated docstring (non-property methods)
    method_pattern = r'(?<!@property\s)def\s+(\w+)\s*\([^)]*\)[^:]*:\s*r?"""[^"]*?(deprecated:[^\n"]+)'
    for match in re.finditer(method_pattern, class_content, re.IGNORECASE | re.DOTALL):
        name = match.group(1)
        message = match.group(2).strip()
        # Exclude property setters (they follow @prop.setter)
        if name not in deprecated_props:
            deprecated_methods[name] = message

    # Sort by name
    return (
        dict(sorted(deprecated_props.items())),
        dict(sorted(deprecated_methods.items())),
        dict(sorted(deprecated_enum_values.items()))
    )


def find_class_definition(content, class_name):
    """Find a class definition and return its full text along with deprecated members.

    Returns a tuple of (class_definition, deprecated_properties, deprecated_methods, deprecated_enum_values).
    """
    # Pattern: class ClassName(...): followed by content until next class or module-level def
    pattern = rf'^class {re.escape(class_name)}\([^)]*\):.*?(?=\nclass |\ndef [a-z_]+\(|\Z)'
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        class_def = match.group(0).rstrip()
        deprecated_props, deprecated_methods, deprecated_enum_values = extract_deprecated_members(class_def)
        return class_def, deprecated_props, deprecated_methods, deprecated_enum_values
    return None, [], [], []


def find_function_definition(content, func_name):
    """Find a module-level function definition and return its full text."""
    # Pattern: def func_name(...): followed by content until next def or class
    pattern = rf'^def {re.escape(func_name)}\([^)]*\).*?(?=\ndef |\nclass |\Z)'
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(0).rstrip()
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Query class or function definitions in unreal module'
    )
    parser.add_argument(
        'query',
        help='Query string (e.g., unreal.InputMappingContext or unreal.log)'
    )
    parser.add_argument(
        '--input', '-i',
        help='Path to unreal.py stub file (auto-detects from CLAUDE_PROJECT_DIR if not provided)'
    )

    args = parser.parse_args()

    try:
        stub_file = find_stub_file(args.input)
        name = parse_query(args.query)

        with open(stub_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if is_class_name(name):
            result, deprecated_props, deprecated_methods, deprecated_enum_values = find_class_definition(content, name)
            if result:
                # Print deprecation notice if any deprecated members found
                has_deprecated = deprecated_props or deprecated_methods or deprecated_enum_values
                if has_deprecated:
                    print("------------------- NOTICE ----------------------")
                    print("The following members of this class are deprecated:")
                    if deprecated_props:
                        print("  Properties:")
                        for prop_name, message in deprecated_props.items():
                            print(f"    - {prop_name}: {message}")
                    if deprecated_methods:
                        print("  Methods:")
                        for method_name, message in deprecated_methods.items():
                            print(f"    - {method_name}: {message}")
                    if deprecated_enum_values:
                        print("  Enum values:")
                        for enum_name, message in deprecated_enum_values.items():
                            print(f"    - {enum_name}: {message}")
                    print("----------------------------------------------------")
                    print()  # Empty line after notice block
                print(result)
            else:
                print(f"Error: '{args.query}' is not defined in unreal module", file=sys.stderr)
                sys.exit(1)
        else:
            result = find_function_definition(content, name)
            if result:
                print(result)
            else:
                print(f"Error: '{args.query}' is not defined in unreal module", file=sys.stderr)
                sys.exit(1)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
