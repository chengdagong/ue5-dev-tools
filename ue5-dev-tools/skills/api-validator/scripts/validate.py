#!/usr/bin/env python3
"""
UE5 Python API 验证工具
"""

import os
import sys
import argparse
import ast
import json
import importlib.util
import subprocess
import subprocess
from typing import List, Dict, Optional, Any, Tuple

# 确保能导入同目录下的 config 模块
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import config

# 路径定义
# 优先使用 CLAUDE_PLUGIN_ROOT (由 Claude Code 注入)
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT")
if not PLUGIN_ROOT:
    # Fallback: 假设脚本位置 <root>/skills/api-validator/scripts/validate.py
    PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))

# 定义插件内部路径
SKILL_ROOT = os.path.join(PLUGIN_ROOT, "skills", "api-validator")
CONVERTER_SCRIPT = os.path.join(SKILL_ROOT, "scripts", "convert_stub_to_mock.py")
EXTRACTOR_SCRIPT = os.path.join(SKILL_ROOT, "scripts", "cpp_metadata_extractor.py")

# 获取项目根目录和Mock路径 (via config)
PROJECT_ROOT = config.get_project_root()
MOCK_DIR = config.get_mock_dir(PROJECT_ROOT)
LIB_DIR = MOCK_DIR

# 常见的 UE5 源码路径 (MacOS)
POTENTIAL_UE5_SOURCE_PATHS = [
    "/Users/Shared/Epic Games/UE_5.7/Engine/Source",
    "/Users/Shared/Epic Games/UE_5.6/Engine/Source",
    "/Users/Shared/Epic Games/UE_5.5/Engine/Source",
    "/Users/Shared/Epic Games/UE_5.4/Engine/Source",
    "/Users/Shared/Epic Games/UE_5.3/Engine/Source",
]

def ensure_mock_module():
    """确保 mock_unreal 模块存在，如果不存在则尝试生成"""
    # 检查是否存在 (检查 unreal_mock.py)
    if os.path.exists(os.path.join(MOCK_DIR, "unreal_mock.py")):
        return True
        
    print("⚠️ 未检测到 mock_unreal 模块，尝试自动生成...")
    
    # 查找 stub 文件 (via config)
    stub_path = config.resolve_stub_path(PROJECT_ROOT)
    
    if not stub_path:
        return False
            
    print(f"ℹ️ 找到 Stub 文件: {stub_path}")
    print(f"ℹ️ 生成 Mock 模块到: {MOCK_DIR}")
    
    try:
        os.makedirs(MOCK_DIR, exist_ok=True)
        subprocess.check_call([
            sys.executable, 
            CONVERTER_SCRIPT
        ])
        print("✅ Mock 模块生成成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 生成 Mock 模块失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False

def ensure_metadata(output_path: str):
    """确保 C++ 元数据存在，如果不存在则尝试从 UE5 源码提取"""
    if os.path.exists(output_path):
        return

    print("⚠️ 未检测到 C++ 元数据，尝试自动提取...")
    
    ue5_source = None
    # 1. 尝试从环境变量获取 UE5_ENGINE_DIR
    env_ue5 = os.environ.get("UE_ENGINE_DIR")
    if env_ue5 and os.path.exists(os.path.join(env_ue5, "Engine/Source")):
        ue5_source = os.path.join(env_ue5, "Engine/Source")
    
    # 2. 尝试常见路径
    if not ue5_source:
        for p in POTENTIAL_UE5_SOURCE_PATHS:
            if os.path.isdir(p):
                ue5_source = p
                break
    
    if not ue5_source:
        print("ℹ️ 未检测到 UE5 源码路径，跳过元数据提取。")
        return

    print(f"ℹ️ 检测到 UE5 源码: {ue5_source}")
    target_scan_path = os.path.join(ue5_source, "Runtime/Engine/Classes/GameFramework")
    
    if not os.path.exists(target_scan_path):
        print(f"ℹ️ 源码路径中未找到 Engine/Classes/GameFramework，跳过。")
        return

    print("⏳ 正在提取元数据 (可能需要几秒钟)...")
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        subprocess.check_call([
            sys.executable,
            EXTRACTOR_SCRIPT,
            "--ue5-path", target_scan_path,
            "--output", output_path
        ])
        print("✅ 元数据提取成功！")
    except Exception as e:
        print(f"❌ 元数据提取失败: {e}")

# 默认定义，防止 NameError
class DeprecatedError(Exception):
    pass

# 尝试加载 mock_unreal
if ensure_mock_module():
    # 直接将 MOCK_DIR 加入 path，并导入 unreal_mock
    sys.path.insert(0, MOCK_DIR)
    try:
        import unreal_mock as unreal
        # 覆盖默认的 DeprecatedError
        if hasattr(unreal, 'DeprecatedError'):
             DeprecatedError = unreal.DeprecatedError
    except ImportError as e:
        # print(f"❌ 导入 mock_unreal 失败: {e}")
        unreal = None
else:
    # print("⚠️ 将在仅静态分析模式下运行 (无运行时 API 检查)")
    unreal = None

# C++ 元数据处理
METADATA_PATH = os.path.join(MOCK_DIR, "metadata.json")
ensure_metadata(METADATA_PATH)

METADATA = {}
if os.path.exists(METADATA_PATH):
    try:
        with open(METADATA_PATH, 'r', encoding='utf-8') as f:
            METADATA = json.load(f)
    except Exception as e:
        print(f"⚠️ 加载元数据失败: {e}")

class ValidationReport:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.infos = []
        self.stats = {"classes": 0, "methods": 0}

    def add_error(self, msg: str, line: int = 0):
        self.errors.append(f"❌ 错误 (Line {line}): {msg}")

    def add_warning(self, msg: str, line: int = 0):
        self.warnings.append(f"⚠️ 警告 (Line {line}): {msg}")

    def add_info(self, msg: str):
        self.infos.append(f"ℹ️ 信息: {msg}")

    def print_report(self):
        print("\n=== UE5 Python API 验证报告 ===\n")
        
        for info in self.infos:
            print(info)
            
        if not self.errors and not self.warnings:
            print("✅ 验证通过！未发现问题。")
        else:
            for warning in self.warnings:
                print(warning)
            for error in self.errors:
                print(error)
                
        print(f"\n统计: {self.stats['classes']} 个类引用, {self.stats['methods']} 个方法调用")

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
                self.report.add_info(f"检测到 unreal 导入为 '{self.imported_unreal_as}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module == "unreal":
            self.report.add_info("检测到从 unreal 导入具体内容")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # 检查 unreal.Member 访问
        # 但要区分：函数调用 (unreal.log()) vs 类引用 (unreal.Actor)
        if isinstance(node.value, ast.Name) and node.value.id == self.imported_unreal_as:
            member_name = node.attr
            # 只在非函数调用上下文中验证为类
            # 函数调用会在 visit_Call 中处理
            if id(node) not in self.called_attributes:
                self._validate_unreal_class(member_name, node.lineno)
        self.generic_visit(node)

    def visit_Call(self, node):
        self.report.stats["methods"] += 1

        # 检查是否调用了 unreal.something()
        if isinstance(node.func, ast.Attribute):
            # Mark this attribute node as being called (so visit_Attribute won't validate it as a class)
            self.called_attributes.add(id(node.func))
            self._check_attribute_call(node)
        elif isinstance(node.func, ast.Name):
            # 检查是否是已知的类构造函数
            if node.func.id in self.variable_types:
                # 可能是某种工厂方法
                pass

        self.generic_visit(node)

    def _check_attribute_call(self, node):
        # 处理 unreal.something() 调用
        # 可能是：unreal.SomeClass() 或 obj.some_method() 或 unreal.Class.method() 或 unreal.module_function()

        # Case 1: node.func.value 是 Name (unreal.something() 或 obj.method())
        if isinstance(node.func.value, ast.Name):
            obj_name = node.func.value.id
            member_name = node.func.attr

            # SubCase 1.1: unreal.something()
            if obj_name == self.imported_unreal_as:
                # 可能是类构造函数或模块级函数
                self._validate_unreal_member_call(member_name, node)

            # SubCase 1.2: obj.method()
            elif obj_name in self.variable_types:
                class_name = self.variable_types[obj_name]
                self._validate_method(class_name, member_name, node.lineno)
                
                # Check for editor property access
                if member_name in ("get_editor_property", "set_editor_property"):
                    self._validate_editor_property_access(class_name, node)
                
                # TODO: 也可以检查方法参数

        # Case 2: node.func.value 是 Attribute (unreal.SomeClass.static_method())
        elif isinstance(node.func.value, ast.Attribute):
            sub_node = node.func.value
            # 检查 sub_node 是否是 unreal.SomeClass
            if isinstance(sub_node.value, ast.Name) and sub_node.value.id == self.imported_unreal_as:
                class_name = sub_node.attr
                method_name = node.func.attr

                # 验证类存在性 (visit_Attribute 会处理，但为了验证方法必须先确认类)
                # 验证方法
                self._validate_method(class_name, method_name, node.lineno)
                # TODO: 检查静态方法参数

    def _validate_unreal_member_call(self, member_name: str, node: ast.Call):
        """验证 unreal.something() 调用，可能是类构造函数或模块级函数"""
        if not unreal:
            return

        if not hasattr(unreal, member_name):
            self.report.add_error(f"'unreal.{member_name}' 不存在", node.lineno)
            return

        member = getattr(unreal, member_name)

        # 检查是类还是函数
        if isinstance(member, type):
            # 这是一个类，可能需要检测是否已废弃 (Runtime & Metadata)
            try:
                # 尝试实例化以检测 Runtime Deprecated
                # 注意：这里我们主要检测构造函数是否抛出 DeprecatedError
                member()
            except DeprecatedError as e:
                self.report.add_warning(f"类 '{member_name}' 已废弃(Runtime): {e}", node.lineno)
            except Exception:
                pass
                
            # 同时也检查 Metadata (因为 visit_Attribute 被跳过了)
            if member_name in METADATA and METADATA[member_name].get("deprecated", False):
                msg = METADATA[member_name].get("deprecation_message", "此类已废弃")
                self.report.add_warning(f"类 '{member_name}' 已废弃(Metadata): {msg}", node.lineno)
                
            # 验证构造函数参数
            self._validate_constructor(member_name, node)
        else:
            # 这是一个模块级函数或其他可调用对象
            # 模块级函数不需要特殊验证（它们存在即可用）
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
        # 仅检查常量字面量
        if not isinstance(arg_node, ast.Constant):
            return
            
        val = arg_node.value
        val_type = type(val) # <class 'str'>
        
        anno = param.annotation
        if anno == inspect.Parameter.empty:
            return
            
        # 解析 Annotation
        target_type_name = None
        if isinstance(anno, type):
            target_type_name = anno.__name__
        elif isinstance(anno, str):
            target_type_name = anno
            # 可能包含 module 前缀，如 'unreal.Name'
            if '.' in target_type_name:
                target_type_name = target_type_name.split('.')[-1]
        
        if not target_type_name or target_type_name == "Any":
            return
            
        actual_type_name = val_type.__name__
        
        # 字符串类型检查增强
        if actual_type_name == "str":
            # 定义允许接受字符串的 Unreal 类型白名单
            allowed_types_for_str = {
                "str", "String", "Name", "Text", 
                "SoftObjectPath", "SoftClassPath", 
                "FilePath", "DirectoryPath",
                "object", "Any"
            }
            
            if target_type_name not in allowed_types_for_str:
                 self.report.add_warning(
                     f"参数类型可能不匹配(Line {arg_node.lineno}): '{context_name}' 的参数 '{param.name}' 期望 '{target_type_name}', 但提供了 'str'。", 
                     arg_node.lineno
                 )

    def _validate_unreal_class(self, class_name: str, lineno: int):
        self.report.stats["classes"] += 1
        
        if not unreal:
            return

        # 检查类是否存在
        if not hasattr(unreal, class_name):
            self.report.add_error(f"类 'unreal.{class_name}' 不存在", lineno)
            return

        cls = getattr(unreal, class_name)
        
        # 1. 动态检查: 尝试实例化以检测 Deprecated
        try:
            # Mock 类通常允许无参实例化
            _ = cls()
        except DeprecatedError as e:
            self.report.add_warning(f"类 '{class_name}' 已废弃(Runtime): {e}", lineno)
        except Exception:
            # 忽略其他实例化错误（虽然 mock 类通常不会报错）
            pass
            
        # 2. 静态检查: C++ 元数据
        if class_name in METADATA and METADATA[class_name].get("deprecated", False):
            msg = METADATA[class_name].get("deprecation_message", "此类已废弃")
            self.report.add_warning(f"类 '{class_name}' 已废弃(Metadata): {msg}", lineno)

    def _validate_method(self, class_name: str, method_name: str, lineno: int):
        if not unreal:
            return
            
        if not hasattr(unreal, class_name):
            return # 之前已经报过错了
            
        cls = getattr(unreal, class_name)
        
        # 检查方法是否存在
        if not hasattr(cls, method_name):
            self.report.add_error(f"方法 '{method_name}' 不存在于类 '{class_name}'", lineno)
            return
            
        method = getattr(cls, method_name)
        
        # 1. 动态检查: 尝试调用以检测 Deprecated
        try:
            # 判断是否需要实例
            is_bound = False
            try:
                # 尝试创建实例来调用实例方法
                # 如果 cls() 报错 (例如类本身 deprecated), 我们可能无法测试方法
                # 但如果只是为了测试方法，我们可以跳过这一步
                instance = cls()
                bound_method = getattr(instance, method_name)
                is_bound = True
                bound_method() # Mock 方法接受任意参数
            except DeprecatedError as e:
                # 区分是类构造函数抛出的还是方法抛出的
                # 如果我们在调用 cast/init 时捕获到，那可能是类的问题，但这里主要是测方法
                # 如果 is_bound 为 True，说明是方法调用抛出的
                if is_bound:
                    self.report.add_warning(f"方法 '{class_name}.{method_name}' 已废弃(Runtime): {e}", lineno)
            except Exception:
                pass
                
            # 如果是静态方法或类方法，可以直接调用
            if not is_bound:
                 try:
                     method()
                 except DeprecatedError as e:
                     self.report.add_warning(f"方法 '{class_name}.{method_name}' 已废弃(Runtime): {e}", lineno)
                 except Exception:
                     pass

        except Exception:
            pass
        
        # 2. 静态检查: 使用元数据
        if class_name in METADATA:
            methods = METADATA[class_name].get("functions", {})
            if method_name in methods:
                func_data = methods[method_name]
                if func_data.get("deprecated", False):
                    msg = func_data.get("deprecation_message", "此方法已废弃")
                    self.report.add_warning(f"方法 '{class_name}.{method_name}' 已废弃(Metadata): {msg}", lineno)

    def visit_Assign(self, node):
        # 简单的类型推断： var = unreal.SomeClass()
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Attribute):
                if isinstance(node.value.func.value, ast.Name) and node.value.func.value.id == self.imported_unreal_as:
                    class_name = node.value.func.attr
                    # 将左侧变量标记为该类型
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.variable_types[target.id] = class_name
                            
        self.generic_visit(node)

    def _validate_editor_property_access(self, class_name: str, node: ast.Call):
        """Validates calls to get_editor_property and set_editor_property."""
        if not node.args:
            return

        # First argument is the property name
        prop_arg = node.args[0]
        if not isinstance(prop_arg, ast.Constant) or not isinstance(prop_arg.value, str):
            return # Runtime expression, cannot validate statically

        prop_name = prop_arg.value
        
        # Check Metadata
        if class_name in METADATA:
            properties = METADATA[class_name].get("properties", {})
            if prop_name not in properties:
                # Some properties might be dynamic or missing from metadata, treat as warning or error?
                # For now, if we have metadata for the class but not the property, it's suspicious.
                self.report.add_error(f"属性 '{prop_name}' 不存在于类 '{class_name}' (Editor Property)", node.lineno)
            else:
                prop_data = properties[prop_name]
                if prop_data.get("deprecated", False):
                    msg = prop_data.get("deprecation_message", "此属性已废弃")
                    self.report.add_warning(f"属性 '{class_name}.{prop_name}' 已废弃: {msg}", node.lineno)


def validate_file(filepath: str):
    report = ValidationReport()
    report.add_info(f"检查文件: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        validator = AstValidator(report)
        validator.visit(tree)
        
    except SyntaxError as e:
        report.add_error(f"Python 语法错误: {e}", e.lineno)
    except Exception as e:
        report.add_error(f"分析失败: {e}")
        
    report.print_report()

def query_api(query: str):
    print(f"\n查询 API: {query}")
    
    if not unreal:
        print("错误: 无法加载 mock_unreal 模块，无法查询。")
        return

    parts = query.split('.')
    if len(parts) == 1:
        class_name = parts[0]
        if hasattr(unreal, class_name):
            cls = getattr(unreal, class_name)
            print(f"✅ 类 {class_name} 存在")
            print(f"文档: {cls.__doc__ or '无'}")
            
            # 显示 C++ 元数据
            if class_name in METADATA:
                print("\n[C++ 元数据]")
                print(json.dumps(METADATA[class_name], indent=2, ensure_ascii=False))
        else:
            print(f"❌ 类 {class_name} 不存在")
            
    elif len(parts) == 2:
        class_name, member_name = parts
        if hasattr(unreal, class_name):
            cls = getattr(unreal, class_name)
            if hasattr(cls, member_name):
                member = getattr(cls, member_name)
                print(f"✅ {class_name}.{member_name} 存在")
                print(f"文档: {member.__doc__ or '无'}")
            else:
                print(f"❌ {class_name}.{member_name} 不存在")
        else:
            print(f"❌ 类 {class_name} 不存在")

def main():
    parser = argparse.ArgumentParser(description="UE5 Python API 验证器")
    parser.add_argument("path", nargs="?", help="要验证的脚本路径")
    parser.add_argument("--query", "-q", help="查询 API 信息")
    
    args = parser.parse_args()
    
    if args.query:
        query_api(args.query)
    elif args.path:
        validate_file(args.path)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
