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


def find_stub_file(input_path=None):
    """Find the unreal.py stub file."""
    if input_path:
        input_path = input_path.strip()
        if os.path.exists(input_path):
            return input_path
        raise FileNotFoundError(f"Stub file not found: {input_path}")

    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    if project_dir:
        stub_path = os.path.join(project_dir, 'Intermediate', 'PythonStub', 'unreal.py')
        if os.path.exists(stub_path):
            return stub_path

    raise FileNotFoundError(
        "Cannot find unreal.py stub file. "
        "Use --input to specify path or set CLAUDE_PROJECT_DIR environment variable."
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


def find_class_definition(content, class_name):
    """Find a class definition and return its full text."""
    # Pattern: class ClassName(...): followed by content until next class or module-level def
    pattern = rf'^class {re.escape(class_name)}\([^)]*\):.*?(?=\nclass |\ndef [a-z_]+\(|\Z)'
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(0).rstrip()
    return None


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
            result = find_class_definition(content, name)
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
