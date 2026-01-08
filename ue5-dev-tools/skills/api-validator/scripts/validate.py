#!/usr/bin/env python3
"""
UE5 Python API Validator
"""

import os
import sys
import argparse
import ast
import inspect
import json
import importlib.util
import subprocess
from typing import List, Dict, Optional, Any, Tuple

# Ensure config module in the same directory can be imported
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import config

# Path definitions
# Prefer CLAUDE_PLUGIN_ROOT (injected by Claude Code)
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT")
if not PLUGIN_ROOT:
    # Fallback: Assume script location <root>/skills/api-validator/scripts/validate.py
    PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))

# Define internal plugin paths
SKILL_ROOT = os.path.join(PLUGIN_ROOT, "skills", "api-validator")
CONVERTER_SCRIPT = os.path.join(SKILL_ROOT, "scripts", "convert_stub_to_mock.py")

# Get project root and Mock path (via config)
PROJECT_ROOT = config.get_project_root()
MOCK_DIR = config.get_mock_dir(PROJECT_ROOT)
LIB_DIR = MOCK_DIR

def ensure_mock_module(custom_stub_path: Optional[str] = None):
    """Ensure mock_unreal module exists, try to generate if not

    Args:
        custom_stub_path: User specified unreal.py stub file path (via --input argument)
    """
    # Check if exists (check unreal_mock.py)
    if os.path.exists(os.path.join(MOCK_DIR, "unreal_mock.py")):
        return True

    print("[WARN] mock_unreal module not detected, attempting to auto-generate...")

    # Find stub file
    stub_path = custom_stub_path or config.resolve_stub_path(PROJECT_ROOT)

    if not stub_path:
        return False

    # Validate custom path exists
    if custom_stub_path and not os.path.exists(custom_stub_path):
        print(f"[ERROR] Specified Stub file does not exist: {custom_stub_path}")
        return False

    print(f"[INFO] Found Stub file: {stub_path}")
    print(f"[INFO] Generating Mock module to: {MOCK_DIR}")

    try:
        os.makedirs(MOCK_DIR, exist_ok=True)
        # Pass custom stub path to converter
        cmd = [sys.executable, CONVERTER_SCRIPT]
        if custom_stub_path:
            cmd.extend(['--input', custom_stub_path, '--output', MOCK_DIR])
        subprocess.check_call(cmd)
        print("[OK] Mock module generated successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to generate Mock module: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
        return False

# Default definition to prevent NameError
class DeprecatedError(Exception):
    pass

# Global variable to store user specified stub path
_custom_stub_path = None

def init_unreal_module(custom_stub_path: Optional[str] = None):
    """Initialize unreal mock module

    Args:
        custom_stub_path: User specified unreal.py stub file path (via --input argument)

    Returns:
        unreal module or None
    """
    global DeprecatedError

    # Try to load mock_unreal
    if ensure_mock_module(custom_stub_path):
        # Directly add MOCK_DIR to path and import unreal_mock
        sys.path.insert(0, MOCK_DIR)
        try:
            import unreal_mock as unreal
            # Override default DeprecatedError
            if hasattr(unreal, 'DeprecatedError'):
                DeprecatedError = unreal.DeprecatedError
            return unreal
        except ImportError as e:
            # print(f"[ERROR] Failed to import mock_unreal: {e}")
            return None
    else:
        # print("[WARN] Will run in static analysis only mode (no runtime API checks)")
        return None

# Do not load at initialization, decide in main() based on arguments
unreal = None

class ValidationReport:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.infos = []
        self.stats = {"classes": 0, "methods": 0}

    def add_error(self, msg: str, line: int = 0):
        self.errors.append(f"[ERROR] Error (Line {line}): {msg}")

    def add_warning(self, msg: str, line: int = 0):
        self.warnings.append(f"[WARN] Warning (Line {line}): {msg}")

    def add_info(self, msg: str):
        self.infos.append(f"[INFO] Info: {msg}")

    def print_report(self):
        print("\n=== UE5 Python API Validation Report ===\n")
        
        for info in self.infos:
            print(info)
            
        if not self.errors and not self.warnings:
            print("[OK] Validation Passed! No issues found.")
        else:
            for warning in self.warnings:
                print(warning)
            for error in self.errors:
                print(error)
                
        print(f"\nStats: {self.stats['classes']} class references, {self.stats['methods']} method calls")

class AstValidator(ast.NodeVisitor):
    def __init__(self, report: ValidationReport):
        self.report = report
        self.imported_unreal_as = "unreal"
        self.variable_types = {}  # var_name -> class_name
        self.called_attributes = set()  # Track attribute nodes that are called as functions

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name == "unreal":
                self.imported_unreal_as = alias.asname or "unreal"
                self.report.add_info(f"Detected unreal import as '{self.imported_unreal_as}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module == "unreal":
            self.report.add_info("Detected import from unreal")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # Check unreal.Member access
        # But distinguish: function call (unreal.log()) vs class reference (unreal.Actor)
        if isinstance(node.value, ast.Name) and node.value.id == self.imported_unreal_as:
            member_name = node.attr
            # Only validate as class in non-function call context
            # Function calls will be handled in visit_Call
            if id(node) not in self.called_attributes:
                self._validate_unreal_class(member_name, node.lineno)
        self.generic_visit(node)

    def visit_Call(self, node):
        self.report.stats["methods"] += 1

        # Check if unreal.something() is called
        if isinstance(node.func, ast.Attribute):
            # Mark this attribute node as being called (so visit_Attribute won't validate it as a class)
            self.called_attributes.add(id(node.func))
            self._check_attribute_call(node)
        elif isinstance(node.func, ast.Name):
            # Check if it is a known class constructor
            if node.func.id in self.variable_types:
                # Might be some factory method
                pass

        self.generic_visit(node)

    def _check_attribute_call(self, node):
        # Handle unreal.something() call
        # Could be: unreal.SomeClass() or obj.some_method() or unreal.Class.method() or unreal.module_function()

        # Case 1: node.func.value is Name (unreal.something() or obj.method())
        if isinstance(node.func.value, ast.Name):
            obj_name = node.func.value.id
            member_name = node.func.attr

            # SubCase 1.1: unreal.something()
            if obj_name == self.imported_unreal_as:
                # Could be class constructor or module-level function
                self._validate_unreal_member_call(member_name, node)

            # SubCase 1.2: obj.method()
            elif obj_name in self.variable_types:
                class_name = self.variable_types[obj_name]
                self._validate_method(class_name, member_name, node.lineno)
                # TODO: Can also check method arguments

        # Case 2: node.func.value is Attribute (unreal.SomeClass.static_method())
        elif isinstance(node.func.value, ast.Attribute):
            sub_node = node.func.value
            # Check if sub_node is unreal.SomeClass
            if isinstance(sub_node.value, ast.Name) and sub_node.value.id == self.imported_unreal_as:
                class_name = sub_node.attr
                method_name = node.func.attr

                # Validate class existence (visit_Attribute will handle, but to validate method must confirm class first)
                # Validate method
                self._validate_method(class_name, method_name, node.lineno)
                # TODO: Check static method arguments

    def _validate_unreal_member_call(self, member_name: str, node: ast.Call):
        """Validate unreal.something() call, could be class constructor or module-level function"""
        if not unreal:
            return

        if not hasattr(unreal, member_name):
            self.report.add_error(f"'unreal.{member_name}' does not exist", node.lineno)
            return

        member = getattr(unreal, member_name)

        # Check if it is class or function
        if isinstance(member, type):
            # It is a class, may need to detect if deprecated (Runtime)
            try:
                # Try to instantiate to detect Runtime Deprecated
                # Note: Here we mainly detect if constructor raises DeprecatedError
                member()
            except DeprecatedError as e:
                self.report.add_warning(f"Class '{member_name}' is deprecated: {e}", node.lineno)
            except Exception:
                pass

            # Validate constructor arguments
            self._validate_constructor(member_name, node)
        else:
            # It is a module-level function or other callable
            # Module-level functions do not need special validation (they exist effectively available)
            pass

    def _validate_constructor(self, class_name: str, node: ast.Call):
        if not unreal or not hasattr(unreal, class_name):
            return
        
        cls = getattr(unreal, class_name)
        # Check __init__
        if not hasattr(cls, '__init__'):
            return
        
        try:
            init_method = cls.__init__
            self._validate_call_arguments(init_method, node, class_name)
        except Exception:
            pass

    def _validate_call_arguments(self, func, node: ast.Call, context_name: str):
        try:
            sig = inspect.signature(func)
        except (ValueError, TypeError):
            return

        params = list(sig.parameters.values())
        # Skip 'self' if it's the first parameter (unbound method)
        if params and params[0].name == 'self':
             params = params[1:]
        
        # Positional args
        for i, arg_node in enumerate(node.args):
            if i < len(params):
                param = params[i]
                # Skip *args
                if param.kind == inspect.Parameter.VAR_POSITIONAL:
                    continue
                self._check_arg_type(arg_node, param, context_name)
        
        # Keyword args
        for keyword in node.keywords:
            arg_name = keyword.arg
            arg_node = keyword.value
            param = next((p for p in params if p.name == arg_name), None)
            if param:
                 # Skip **kwargs
                if param.kind == inspect.Parameter.VAR_KEYWORD:
                    continue
                self._check_arg_type(arg_node, param, context_name)

    def _check_arg_type(self, arg_node, param, context_name):
        # Only check constant literals
        if not isinstance(arg_node, ast.Constant):
            return
            
        val = arg_node.value
        val_type = type(val) # <class 'str'>
        
        anno = param.annotation
        if anno == inspect.Parameter.empty:
            return
            
        # Parse Annotation
        target_type_name = None
        if isinstance(anno, type):
            target_type_name = anno.__name__
        elif isinstance(anno, str):
            target_type_name = anno
            # May contain module prefix, e.g., 'unreal.Name'
            if '.' in target_type_name:
                target_type_name = target_type_name.split('.')[-1]
        
        if not target_type_name or target_type_name == "Any":
            return
            
        actual_type_name = val_type.__name__
        
        # String type check enhancement
        if actual_type_name == "str":
            # Allowed types for strings in Unreal
            allowed_types_for_str = {
                "str", "String", "Name", "Text", 
                "SoftObjectPath", "SoftClassPath", 
                "FilePath", "DirectoryPath",
                "object", "Any"
            }
            
            if target_type_name not in allowed_types_for_str:
                 self.report.add_warning(
                     f"Argument type mismatch possible (Line {arg_node.lineno}): Argument '{param.name}' in '{context_name}' expects '{target_type_name}', but 'str' was provided.", 
                     arg_node.lineno
                 )

    def _validate_unreal_class(self, class_name: str, lineno: int):
        self.report.stats["classes"] += 1
        
        if not unreal:
            return

        # Check if class exists
        if not hasattr(unreal, class_name):
            self.report.add_error(f"Class 'unreal.{class_name}' does not exist", lineno)
            return

        cls = getattr(unreal, class_name)

        # Dynamic check: Try instantiate to detect Deprecated
        try:
            # Mock classes usually allow parameter-less instantiation
            _ = cls()
        except DeprecatedError as e:
            self.report.add_warning(f"Class '{class_name}' is deprecated: {e}", lineno)
        except Exception:
            # Ignore other instantiation errors (although mock classes usually don't raise error)
            pass

    def _validate_method(self, class_name: str, method_name: str, lineno: int):
        if not unreal:
            return
            
        if not hasattr(unreal, class_name):
            return # Already reported
            
        cls = getattr(unreal, class_name)
        
        # Check if method exists
        if not hasattr(cls, method_name):
            self.report.add_error(f"Method '{method_name}' does not exist in class '{class_name}'", lineno)
            return
            
        method = getattr(cls, method_name)
        
        # 1. Dynamic check: Try call to detect Deprecated
        try:
            # Determine if instance is needed
            is_bound = False
            try:
                # Try create instance to call instance method
                # If cls() raises error (e.g. class itself deprecated), we might not be able to test method
                # But if just for testing method, we can skip this step
                instance = cls()
                bound_method = getattr(instance, method_name)
                is_bound = True
                bound_method() # Mock method accepts any args
            except DeprecatedError as e:
                # Distinguish if it was raised by constructor or method
                # If we catch during cast/init, it might be class issue, but here testing method mainly
                # If is_bound is True, it means method call raised it
                if is_bound:
                    self.report.add_warning(f"Method '{class_name}.{method_name}' is deprecated (Runtime): {e}", lineno)
            except Exception:
                pass
                
            # If static method or class method, can call directly
            if not is_bound:
                 try:
                     method()
                 except DeprecatedError as e:
                     self.report.add_warning(f"Method '{class_name}.{method_name}' is deprecated: {e}", lineno)
                 except Exception:
                     pass

        except Exception:
            pass

    def visit_Assign(self, node):
        # Simple type inference: var = unreal.SomeClass()
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Attribute):
                if isinstance(node.value.func.value, ast.Name) and node.value.func.value.id == self.imported_unreal_as:
                    class_name = node.value.func.attr
                    # Mark left side variable as this type
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.variable_types[target.id] = class_name
                            
        self.generic_visit(node)


def validate_file(filepath: str):
    report = ValidationReport()
    report.add_info(f"Checking file: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        validator = AstValidator(report)
        validator.visit(tree)
        
    except SyntaxError as e:
        report.add_error(f"Python Syntax Error: {e}", e.lineno)
    except Exception as e:
        report.add_error(f"Analysis failed: {e}")
        
    report.print_report()

def query_api(query: str):
    print(f"\nQuerying API: {query}")

    # Argument Preprocessing: Reject queries containing spaces
    if ' ' in query:
        print("[ERROR] Error: Query argument cannot contain spaces")
        print("\nCorrect usage:")
        print("  - Query Class: unreal.<ClassName>")
        print("    Example: unreal.Actor, unreal.EditorLevelLibrary")
        print("  - Query Method: unreal.<ClassName>.<method_name>")
        print("    Example: unreal.Actor.set_actor_location")
        print("  - Query Module Function: unreal.<function_name>")
        print("    Example: unreal.log, unreal.log_warning")
        return

    # Auto add "unreal." prefix (if simple format and prefix missing)
    if not query.startswith('unreal.'):
        # Check basic format validity
        if not query or query.startswith('.') or query.endswith('.') or '..' in query:
            print("[ERROR] Error: Query format incorrect")
            print("\nCorrect format:")
            print("  - unreal.<name>")
            print("  - unreal.<ClassName>.<member_name>")
            return
        # Auto add prefix
        query = 'unreal.' + query
        print(f"Auto-completing to: {query}")

    # Remove "unreal." prefix to get actual query content
    query_without_prefix = query[7:]  # len("unreal.") = 7

    # Format validation
    if not query_without_prefix or query_without_prefix.endswith('.') or '..' in query_without_prefix:
        print("[ERROR] Error: Query format incorrect")
        print("\nCorrect format:")
        print("  - unreal.<name>")
        print("  - unreal.<ClassName>.<member_name>")
        return

    if not unreal:
        print("Error: Cannot load mock_unreal module, cannot query.")
        return

    parts = query_without_prefix.split('.')
    if len(parts) == 1:
        class_name = parts[0]
        if hasattr(unreal, class_name):
            cls = getattr(unreal, class_name)
            print(f"[OK] Class {class_name} exists")
            print(f"Doc: {cls.__doc__ or 'None'}")
        else:
            print(f"[ERROR] Class {class_name} does not exist")

    elif len(parts) == 2:
        class_name, member_name = parts
        if hasattr(unreal, class_name):
            cls = getattr(unreal, class_name)
            if hasattr(cls, member_name):
                member = getattr(cls, member_name)
                print(f"[OK] {class_name}.{member_name} exists")
                print(f"Doc: {member.__doc__ or 'None'}")
            else:
                print(f"[ERROR] {class_name}.{member_name} does not exist")
        else:
            print(f"[ERROR] Class {class_name} does not exist")

def main():
    global unreal

    parser = argparse.ArgumentParser(description="UE5 Python API Validator")
    parser.add_argument("path", nargs="?", help="Path to the script to validate")
    parser.add_argument("--query", "-q", help="Query API information")
    parser.add_argument("--input", "-i", help="Specify path to unreal.py stub file (for generating mock module)")

    args = parser.parse_args()

    # Initialize unreal module (use path if user specified --input)
    unreal = init_unreal_module(args.input)

    if args.query:
        query_api(args.query)
    elif args.path:
        validate_file(args.path)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
