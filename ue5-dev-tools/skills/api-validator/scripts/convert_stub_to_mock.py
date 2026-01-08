#!/usr/bin/env python3
"""
Convert Unreal Python stub files to importable Mock modules

Features:
1. Parse class, method, and property definitions from stub files
2. Generate implementations for each method that return mock values
3. Generate actual getter/setter for @property
4. Implement get_editor_property/set_editor_property in base classes
5. Detect deprecated markers and generate exception-throwing implementations
"""

import re
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class PropertyInfo:
    """Property information"""
    name: str
    type_hint: str
    docstring: str
    is_deprecated: bool = False
    deprecated_msg: str = ""


@dataclass
class MethodInfo:
    """Method information"""
    name: str
    signature: str  # Full signature line
    return_type: str
    docstring: str
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_deprecated: bool = False
    deprecated_msg: str = ""
    params: List[Tuple[str, str, str]] = field(default_factory=list)  # (name, type, default)


@dataclass
class ClassInfo:
    """Class information"""
    name: str
    bases: str  # Base class string
    docstring: str
    init_signature: str = ""
    init_params: List[Tuple[str, str, str]] = field(default_factory=list)  # (name, type, default)
    methods: List[MethodInfo] = field(default_factory=list)
    properties: List[PropertyInfo] = field(default_factory=list)
    enum_values: List[Tuple[str, str]] = field(default_factory=list)  # (name, value) enum values
    is_deprecated: bool = False
    deprecated_msg: str = ""


def escape_docstring(text: str) -> str:
    """Escape special characters in docstrings"""
    if not text:
        return text
    # Replace embedded double quotes with single quotes to avoid conflicts with triple quotes
    text = text.replace('\\"', "'")
    text = text.replace('"', "'")
    return text


def escape_string(text: str) -> str:
    """Escape special characters in string literals"""
    if not text:
        return text
    # Escape double quotes and backslashes
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    return text


def sanitize_default_value(default: str) -> str:
    """Convert complex default values (e.g., enum references) to safe None"""
    if not default:
        return "None"

    # Keep simple basic type default values
    safe_patterns = [
        # Numbers
        lambda s: s.replace('.', '', 1).replace('-', '', 1).isdigit(),
        # Strings
        lambda s: s.startswith('"') or s.startswith("'"),
        # Booleans
        lambda s: s in ('True', 'False'),
        # None
        lambda s: s == 'None',
        # Empty collections
        lambda s: s in ('[]', '{}', '()', 'set()'),
        # List/tuple/dict literals (simple cases)
        lambda s: s.startswith('[') and s.endswith(']'),
        lambda s: s.startswith('(') and s.endswith(')'),
        lambda s: s.startswith('{') and s.endswith('}'),
    ]

    for pattern in safe_patterns:
        try:
            if pattern(default):
                return default
        except:
            pass

    # Values containing . need to reference other types, not safe
    if '.' in default:
        return "None"

    # Other cases like Name("xxx") need to be checked
    if '(' in default:
        return "None"

    return default


def get_mock_return_value(return_type: str) -> str:
    """Generate mock return value based on return type"""
    if not return_type or return_type == "None":
        return "None"

    # Clean type annotation
    return_type = return_type.strip()

    # Handle Optional types
    if return_type.startswith("Optional["):
        return "None"

    # Basic types
    type_map = {
        "bool": "False",
        "int": "0",
        "float": "0.0",
        "str": '""',
        "bytes": 'b""',
        "list": "[]",
        "dict": "{}",
        "set": "set()",
        "tuple": "()",
        "List": "[]",
        "Dict": "{}",
        "Set": "set()",
        "Tuple": "()",
        "Any": "None",
        "object": "None",
        "Iterator": "iter([])",
        "Iterable": "[]",
    }

    # Direct match
    if return_type in type_map:
        return type_map[return_type]

    # Handle generic types
    for key in type_map:
        if return_type.startswith(f"{key}["):
            return type_map[key]

    # Unreal-specific types
    if return_type in ("Name", "Text"):
        return f'{return_type}("")' if return_type != "Name" else 'Name("None")'

    # Array types
    if return_type.startswith("Array["):
        return "Array(object)"

    # Other types return None
    return "None"


def check_deprecated(docstring: str) -> Tuple[bool, str]:
    """Check if there is a deprecated marker in the docstring"""
    if not docstring:
        return False, ""

    # Find deprecated-related text
    lines = docstring.split('\n')
    deprecated_lines = []
    in_deprecated = False

    for line in lines:
        line_lower = line.lower()
        if 'deprecated' in line_lower:
            in_deprecated = True
            deprecated_lines.append(line.strip())
        elif in_deprecated and line.strip() and not line.strip().startswith('-'):
            # Continue collecting deprecated description
            deprecated_lines.append(line.strip())
        elif in_deprecated and (not line.strip() or line.strip().startswith('-')):
            in_deprecated = False

    if deprecated_lines:
        return True, ' '.join(deprecated_lines)
    return False, ""


def parse_params(sig_line: str) -> List[Tuple[str, str, str]]:
    """Parse method parameters"""
    # Extract parameter section: def func_name(...) -> ...
    match = re.search(r'def\s+\w+\s*\(([^)]*)\)', sig_line)
    if not match:
        return []

    params_str = match.group(1)
    params = []

    # Simple parameter splitting (ignore nested parentheses)
    depth = 0
    current = ""
    for char in params_str:
        if char in '([{':
            depth += 1
            current += char
        elif char in ')]}':
            depth -= 1
            current += char
        elif char == ',' and depth == 0:
            params.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        params.append(current.strip())

    result = []
    for param in params:
        if param == 'self' or param.startswith('*'):
            # For *args, **kwargs we skip or can handle specially
            # but normally we want to preserve them
            if param.startswith('*'):
                result.append((param, "Any", None))
            continue

        # Parse name: type = default
        match = re.match(r'(\w+)\s*:\s*([^=]+)(?:\s*=\s*(.+))?', param)
        if match:
            name = match.group(1)
            type_hint = match.group(2).strip()
            default = match.group(3).strip() if match.group(3) else None
            result.append((name, type_hint, default))
        else:
            # Only name
            result.append((param, "Any", None))

    return result


def parse_method_signature(sig_line: str) -> Tuple[str, str, List[Tuple[str, str, str]]]:
    """Parse method signature, return (method_name, return_type, parameter_list)"""
    # 匹配 def method_name(...) -> ReturnType:
    match = re.match(r'\s*def\s+(\w+)\s*\([^)]*\)\s*(?:->\s*([^:]+))?\s*:', sig_line)
    name = ""
    return_type = "None"
    params = []

    if match:
        name = match.group(1)
        return_type = (match.group(2) or "None").strip()
        params = parse_params(sig_line)

    return name, return_type, params


def parse_stub_file(file_path: str) -> List[ClassInfo]:
    """Parse stub file and extract all class information"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    classes = []
    
    # Match class definitions
    class_pattern = re.compile(
        r'^class\s+(\w+)\s*(\([^)]*\))?\s*:\s*\n(.*?)(?=^class\s|\Z)',
        re.MULTILINE | re.DOTALL
    )
    
    for match in class_pattern.finditer(content):
        class_name = match.group(1)
        bases = match.group(2) or "()"
        class_body = match.group(3)

        # Extract class docstring
        docstring_match = re.match(r'\s*r?"""(.*?)"""\s*', class_body, re.DOTALL)
        docstring = docstring_match.group(1) if docstring_match else ""

        # Check if class is deprecated
        is_deprecated, deprecated_msg = check_deprecated(docstring)
        
        class_info = ClassInfo(
            name=class_name,
            bases=bases,
            docstring=docstring,
            is_deprecated=is_deprecated,
            deprecated_msg=deprecated_msg
        )
        
        # Parse methods
        method_pattern = re.compile(
            r'((?:^    @(?:classmethod|staticmethod)\s*\n)?)'  # Decorators
            r'^    def\s+(\w+)\s*\([^)]*\)(?:\s*->\s*[^:]+)?\s*:\s*\n'  # Method signature
            r'((?:\s*r?""".*?"""\s*)?)',  # Docstring
            re.MULTILINE | re.DOTALL
        )

        for m in method_pattern.finditer(class_body):
            decorator = m.group(1).strip() if m.group(1) else ""
            method_line = m.group(0)
            method_name, return_type, params = parse_method_signature(method_line)

            # Skip methods that failed to parse
            if not method_name:
                continue

            method_docstring = m.group(3) if m.group(3) else ""

            # Clean docstring
            if method_docstring:
                doc_match = re.search(r'r?"""(.*?)"""', method_docstring, re.DOTALL)
                method_docstring = doc_match.group(1) if doc_match else ""

            is_deprecated, deprecated_msg = check_deprecated(method_docstring)
            
            method_info = MethodInfo(
                name=method_name,
                signature=method_line.strip(),
                return_type=return_type,
                docstring=method_docstring,
                is_classmethod='@classmethod' in decorator,
                is_staticmethod='@staticmethod' in decorator,
                is_deprecated=is_deprecated,
                deprecated_msg=deprecated_msg,
                params=params
            )
            
            if method_name == '__init__':
                class_info.init_signature = method_line.strip()
                class_info.init_params = params
            else:
                class_info.methods.append(method_info)
        
        # Parse @property
        prop_pattern = re.compile(
            r'^    @property\s*\n'
            r'^    def\s+(\w+)\s*\(self\)\s*->\s*([^:]+):\s*\n'
            r'((?:\s*r?""".*?"""\s*)?)',
            re.MULTILINE | re.DOTALL
        )

        for m in prop_pattern.finditer(class_body):
            prop_name = m.group(1)
            prop_type = m.group(2).strip()
            prop_docstring = m.group(3) if m.group(3) else ""

            if prop_docstring:
                doc_match = re.search(r'r?"""(.*?)"""', prop_docstring, re.DOTALL)
                prop_docstring = doc_match.group(1) if doc_match else ""

            is_deprecated, deprecated_msg = check_deprecated(prop_docstring)
            
            prop_info = PropertyInfo(
                name=prop_name,
                type_hint=prop_type,
                docstring=prop_docstring,
                is_deprecated=is_deprecated,
                deprecated_msg=deprecated_msg
            )
            class_info.properties.append(prop_info)
        
        # Parse enum values (e.g., GAUSSIAN: RBFKernelType = ... #: 0)
        if 'EnumBase' in bases:
            enum_pattern = re.compile(
                r'^    (\w+)\s*:\s*\w+\s*=\s*\.\.\.\s*(?:#:\s*(\d+))?',
                re.MULTILINE
            )
            for m in enum_pattern.finditer(class_body):
                enum_name = m.group(1)
                enum_value = m.group(2) if m.group(2) else "0"
                class_info.enum_values.append((enum_name, enum_value))

        classes.append(class_info)

    # Scan all enum references and find missing enum values
    # First collect all defined enum classes and their values
    enum_classes = {}  # {class_name: {defined_enum_value_names}}
    for cls in classes:
        if 'EnumBase' in cls.bases:
            enum_classes[cls.name] = set(name for name, _ in cls.enum_values)

    # Search for enum references in the entire file (format: EnumClassName.VALUE_NAME)
    enum_ref_pattern = re.compile(r'\b([A-Z][A-Za-z0-9_]+)\.([A-Z][A-Z0-9_]+)\b')
    referenced_values = {}  # {class_name: {referenced_enum_value_names}}

    for match in enum_ref_pattern.finditer(content):
        enum_class = match.group(1)
        enum_value = match.group(2)
        if enum_class in enum_classes:
            if enum_class not in referenced_values:
                referenced_values[enum_class] = set()
            referenced_values[enum_class].add(enum_value)

    # Find missing enum values and add them to the corresponding class
    missing_count = 0
    for cls in classes:
        if cls.name in enum_classes and cls.name in referenced_values:
            defined = enum_classes[cls.name]
            referenced = referenced_values[cls.name]
            missing = referenced - defined

            # Add missing enum values, starting with max_value + 1 from the class
            if missing:
                max_value = max((int(v) for _, v in cls.enum_values), default=-1)
                for value_name in sorted(missing):
                    max_value += 1
                    cls.enum_values.append((value_name, str(max_value)))
                    missing_count += 1

    if missing_count > 0:
        print(f"  - Supplemented {missing_count} missing enum values")
    
    return classes


def generate_mock_module(classes: List[ClassInfo], output_dir: str):
    """Generate mock module"""
    os.makedirs(output_dir, exist_ok=True)

    # Generate __init__.py
    init_content = '''"""
Unreal Engine Python Mock module

This is a mock module generated from unreal.py stub files, usable without Unreal Engine environment.
Supports accessing properties through get_editor_property/set_editor_property.
"""

from .unreal_mock import *
'''
    
    with open(os.path.join(output_dir, '__init__.py'), 'w', encoding='utf-8') as f:
        f.write(init_content)
    
    # Generate main module
    lines = []

    # File header
    lines.append('"""')
    lines.append('Unreal Engine Python Mock module (Auto-generated)')
    lines.append('"""')
    lines.append('')
    lines.append('from __future__ import annotations')
    lines.append('from typing import Any, Callable, Dict, ItemsView, Iterable, Iterator, KeysView, List, Mapping, MutableMapping, MutableSequence, MutableSet, Optional, Set, Tuple, Type, TypeVar, Union, ValuesView, Sequence')
    lines.append('import io as _io')
    lines.append('')
    lines.append('_T = TypeVar("_T")')
    lines.append('_ElemType = TypeVar("_ElemType")')
    lines.append('_KeyType = TypeVar("_KeyType")')
    lines.append('_ValueType = TypeVar("_ValueType")')
    lines.append('')
    lines.append('')
    lines.append('class DeprecatedError(Exception):')
    lines.append('    """Raised when using deprecated methods or properties"""')
    lines.append('    pass')
    lines.append('')
    lines.append('')

    # Layered class processing: base classes -> enum classes -> other classes
    # This ensures enum classes are defined before being referenced by other classes
    base_classes = []  # Base classes (e.g., _WrapperBase, EnumBase, StructBase, etc.)
    enum_classes = []  # Enum classes (inheriting from EnumBase)
    other_classes = []  # Other classes
    
    base_class_names = {'_WrapperBase', '_ObjectBase', 'EnumBase', 'StructBase', 
                        'DelegateBase', 'MulticastDelegateBase', 'Name', 'Text', 
                        'Array', 'FixedArray', 'Set', 'Map', 'FieldPath',
                        '_EnumEntry', '_Logger'}
    
    for cls in classes:
        if cls.name in base_class_names:
            base_classes.append(cls)
        elif 'EnumBase' in cls.bases:
            enum_classes.append(cls)
        else:
            other_classes.append(cls)

    # Generate in order
    lines.append('# ============== Base Classes ==============')
    lines.append('')
    for cls in base_classes:
        lines.extend(generate_class_code(cls))
        lines.append('')

    lines.append('# ============== Enum Classes ==============')
    lines.append('')
    for cls in enum_classes:
        lines.extend(generate_class_code(cls))
        lines.append('')

    lines.append('# ============== Other Classes ==============')
    lines.append('')
    for cls in other_classes:
        lines.extend(generate_class_code(cls))
        lines.append('')

    with open(os.path.join(output_dir, 'unreal_mock.py'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"Generation complete: {len(classes)} classes")
    print(f"  - Base classes: {len(base_classes)}")
    print(f"  - Enum classes: {len(enum_classes)}")
    print(f"  - Other classes: {len(other_classes)}")
    print(f"Output directory: {output_dir}")


def generate_class_code(cls: ClassInfo) -> List[str]:
    """Generate code for a single class"""
    lines = []

    # Class definition
    lines.append(f'class {cls.name}{cls.bases}:')

    # Docstring
    if cls.docstring:
        escaped_doc = escape_docstring(cls.docstring.strip())
        lines.append(f'    r"""')
        for line in escaped_doc.split('\n'):
            lines.append(f'    {line}')
        lines.append(f'    """')

    # Enum values (if enum class)
    if cls.enum_values:
        lines.append('')
        for enum_name, enum_value in cls.enum_values:
            lines.append(f'    {enum_name} = {enum_value}')
        lines.append('')

    # __init__ method
    if cls.is_deprecated:
        escaped_msg = escape_string(cls.deprecated_msg)
        lines.append(f'    def __init__(self, *args, **kwargs):')
        lines.append(f'        raise DeprecatedError("{escaped_msg}")')
    else:
        # Generate __init__
        if cls.init_params:
            param_strs = ['self']
            sanitized_params = []  # Track parameters that need sanitization
            for name, type_hint, default in cls.init_params:
                if name.startswith('*'):  # *args or **kwargs
                    # Variable length parameters without default values
                    if type_hint and type_hint != "Any":
                        param_strs.append(f'{name}: {type_hint}')
                    else:
                        param_strs.append(f'{name}')
                elif default:
                    safe_default = sanitize_default_value(default)
                    param_strs.append(f'{name}: {type_hint} = {safe_default}')
                    if safe_default != default:
                        sanitized_params.append((name, default))
                else:
                    # For Mock, give all regular parameters default value None for better compatibility
                    param_strs.append(f'{name}: {type_hint} = None')

            # If any parameters were sanitized, add TODO comment
            if sanitized_params:
                lines.append(f'    # TODO: The following parameters have been sanitized and original values need to be restored in Unreal environment:')
                for param_name, original_default in sanitized_params:
                    lines.append(f'    #   - {param_name}: {original_default}')

            lines.append(f'    def __init__({", ".join(param_strs)}):')
        else:
            lines.append(f'    def __init__(self, *args, **kwargs):')

        # Initialize property storage
        lines.append(f'        self._properties = {{}}')

        # Set parameters as properties
        for name, type_hint, default in cls.init_params:
            if not name.startswith('*'):
                lines.append(f'        self._properties["{name}"] = {name}')

        # Initialize all properties
        for prop in cls.properties:
            if prop.name not in [p[0] for p in cls.init_params]:
                mock_val = get_mock_return_value(prop.type_hint)
                lines.append(f'        self._properties["{prop.name}"] = {mock_val}')

    # get_editor_property / set_editor_property
    if not cls.is_deprecated and ('_ObjectBase' in cls.bases or '_WrapperBase' in cls.bases or 'StructBase' in cls.bases or cls.name in ('_ObjectBase', 'StructBase', '_WrapperBase')):
        lines.append('')
        lines.append('    def get_editor_property(self, name: str) -> object:')
        lines.append('        """Get editor property value"""')
        lines.append('        return self._properties.get(name, None)')
        lines.append('')
        lines.append('    def set_editor_property(self, name: str, value: object, notify_mode=None) -> None:')
        lines.append('        """Set editor property value"""')
        lines.append('        self._properties[name] = value')
        lines.append('')
        lines.append('    def set_editor_properties(self, properties: dict) -> None:')
        lines.append('        """Batch set editor properties"""')
        lines.append('        self._properties.update(properties)')
    
    # Generate properties
    for prop in cls.properties:
        lines.append('')
        lines.append('    @property')
        lines.append(f'    def {prop.name}(self) -> {prop.type_hint}:')
        if prop.docstring:
            escaped_prop_doc = escape_docstring(prop.docstring.strip())
            lines.append(f'        r"""{escaped_prop_doc}"""')

        if prop.is_deprecated:
            escaped_prop_msg = escape_string(prop.deprecated_msg)
            lines.append(f'        raise DeprecatedError("{escaped_prop_msg}")')
        else:
            lines.append(f'        return self._properties.get("{prop.name}", None)')

        lines.append('')
        lines.append(f'    @{prop.name}.setter')
        lines.append(f'    def {prop.name}(self, value: {prop.type_hint}) -> None:')
        if prop.is_deprecated:
            escaped_prop_msg = escape_string(prop.deprecated_msg)
            lines.append(f'        raise DeprecatedError("{escaped_prop_msg}")')
        else:
            lines.append(f'        self._properties["{prop.name}"] = value')

    # Generate methods
    for method in cls.methods:
        if method.name.startswith('_') and method.name != '__init__':
            continue  # Skip private methods (except __init__)

        lines.append('')

        # Build parameter list
        param_strs = []
        if method.is_classmethod:
            param_strs.append('cls')
        elif method.is_staticmethod:
            pass
        else:
            param_strs.append('self')

        sanitized_params = []
        if method.params:
            for name, type_hint, default in method.params:
                if default:
                    safe_default = sanitize_default_value(default)
                    param_strs.append(f'{name}: {type_hint} = {safe_default}')
                    if safe_default != default:
                        sanitized_params.append((name, default))
                else:
                    if name.startswith('*'):  # *args or **kwargs
                        param_strs.append(f'{name}')
                    else:
                        param_strs.append(f'{name}: {type_hint}')
        else:
            # Fallback (should not happen unless parsing fails)
            param_strs.append("*args")
            param_strs.append("**kwargs")

        if method.is_classmethod:
            lines.append('    @classmethod')
        elif method.is_staticmethod:
            lines.append('    @staticmethod')

        lines.append(f'    def {method.name}({", ".join(param_strs)}) -> {method.return_type}:')

        if method.docstring:
            # Simplify docstring
            first_line = escape_docstring(method.docstring.strip().split('\n')[0])
            lines.append(f'        """{first_line}"""')

        if method.is_deprecated:
            escaped_method_msg = escape_string(method.deprecated_msg)
            lines.append(f'        raise DeprecatedError("{escaped_method_msg}")')
        else:
            mock_val = get_mock_return_value(method.return_type)
            lines.append(f'        return {mock_val}')

    # If class body is empty, add pass
    if len(lines) == 1 or (len(lines) == 2 and 'r"""' in lines[1]):
        lines.append('    pass')

    return lines


def main():
    import argparse
    import sys

    # 确保能导入同目录下的 config 模块
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    has_config = False
    default_input_path = None
    default_output_dir = None

    try:
        import config
        has_config = True
        project_dir = config.get_project_root()
        default_input_path = config.resolve_stub_path(project_dir)
        default_output_dir = config.get_mock_dir(project_dir)
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description='Convert Unreal Python stub files to Mock modules')

    # Always accept arguments, but set defaults when config is available
    parser.add_argument('--input', '-i',
                       required=(not has_config),
                       default=default_input_path,
                       help='Path to input stub file' + (f' (default: {default_input_path})' if default_input_path else ''))
    parser.add_argument('--output', '-o',
                       required=(not has_config),
                       default=default_output_dir,
                       help='Output directory' + (f' (default: {default_output_dir})' if default_output_dir else ''))

    args = parser.parse_args()

    # Get final paths (command line arguments take priority)
    input_path = args.input
    output_dir = args.output

    if not input_path:
        print(f"❌ Error: Could not find Unreal Stub file (Project: {config.get_project_root() if has_config else 'Unknown'})")
        sys.exit(1)

    print(f"Parsing stub file: {input_path}")
    if not os.path.exists(input_path):
        print(f"❌ File not found: {input_path}")
        sys.exit(1)

    classes = parse_stub_file(input_path)
    print(f"Found {len(classes)} class definitions")

    print(f"Generating Mock module...")
    print(f"Output directory: {output_dir}")
    generate_mock_module(classes, output_dir)


if __name__ == '__main__':
    main()
