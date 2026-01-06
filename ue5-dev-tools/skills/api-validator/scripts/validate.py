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
from typing import List, Dict, Optional, Any, Tuple

# 路径定义
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(CURRENT_DIR)
LIB_DIR = os.path.join(SKILL_ROOT, "lib")
MOCK_DIR = os.path.join(LIB_DIR, "mock_unreal")
CONVERTER_SCRIPT = os.path.join(CURRENT_DIR, "convert_stub_to_mock.py")

# 获取项目根目录 (假设 skill 位于 <project>/ue5-python-validator/skills/api-validator/scripts)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SKILL_ROOT))
PROJECT_ROOT = os.path.dirname(os.path.dirname(PLUGIN_ROOT))

def ensure_mock_module():
    """确保 mock_unreal 模块存在，如果不存在则尝试生成"""
    if os.path.exists(os.path.join(MOCK_DIR, "__init__.py")):
        return True
        
    print("⚠️ 未检测到 mock_unreal 模块，尝试自动生成...")
    
    # 查找 stub 文件
    stub_path = os.path.join(PROJECT_ROOT, "Intermediate", "PythonStub", "unreal.py")
    if not os.path.exists(stub_path):
        # 尝试其他常见位置
        potential_paths = [
            os.path.join(PROJECT_ROOT, "Intermediate", "PythonStub", "unreal.py"),
            os.path.join(PROJECT_ROOT, "Saved", "UnrealAPIGenerator", "unreal.py"), # 假设路径
            os.path.join(PLUGIN_ROOT, "..", "Intermediate", "PythonStub", "unreal.py")
        ]
        found = False
        for p in potential_paths:
            if os.path.exists(p):
                stub_path = p
                found = True
                break
        
        if not found:
            print(f"❌ 无法找到 unreal.py stub 文件。请确保项目已生成 Python stub。搜索路径: {stub_path}")
            return False
            
    print(f"ℹ️ 找到 Stub 文件: {stub_path}")
    print(f"ℹ️ 生成 Mock 模块到: {MOCK_DIR}")
    
    try:
        os.makedirs(LIB_DIR, exist_ok=True)
        subprocess.check_call([
            sys.executable, 
            CONVERTER_SCRIPT, 
            "--input", stub_path, 
            "--output", MOCK_DIR
        ])
        print("✅ Mock 模块生成成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 生成 Mock 模块失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False

# (Empty - Remove duplicate code)

# 尝试加载 mock_unreal
if ensure_mock_module():
    sys.path.insert(0, LIB_DIR)
    try:
        import mock_unreal as unreal
    except ImportError as e:
        print(f"❌ 导入 mock_unreal 失败: {e}")
        unreal = None
else:
    print("⚠️ 将在仅静态分析模式下运行 (无运行时 API 检查)")
    unreal = None

# ... rest of the file ...

# 尝试加载元数据
METADATA = {}
metadata_path = os.path.join(os.path.dirname(PLUGIN_ROOT), "references", "metadata.json")
if os.path.exists(metadata_path):
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            METADATA = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load metadata: {e}")

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

    def visit_Call(self, node):
        self.report.stats["methods"] += 1
        
        # 检查是否调用了 unreal.Class()
        if isinstance(node.func, ast.Attribute):
            self._check_attribute_call(node)
        elif isinstance(node.func, ast.Name):
            # 检查是否是已知的类构造函数
            if node.func.id in self.variable_types:
                # 可能是某种工厂方法
                pass
                
        self.generic_visit(node)

    def _check_attribute_call(self, node):
        # 处理 unreal.SomeClass() 或 obj.some_method()
        if isinstance(node.func.value, ast.Name):
            obj_name = node.func.value.id
            method_name = node.func.attr
            
            # Case 1: unreal.SomeClass()
            if obj_name == self.imported_unreal_as:
                self._validate_unreal_class(method_name, node.lineno)
            
            # Case 2: obj.method() - 需要类型推断
            elif obj_name in self.variable_types:
                class_name = self.variable_types[obj_name]
                self._validate_method(class_name, method_name, node.lineno)

    def _validate_unreal_class(self, class_name: str, lineno: int):
        self.report.stats["classes"] += 1
        
        if not unreal:
            return

        # 检查类是否存在
        if not hasattr(unreal, class_name):
            self.report.add_error(f"类 'unreal.{class_name}' 不存在", lineno)
            return

        # 检查是否 Deprecated
        cls = getattr(unreal, class_name)
        try:
            # 尝试实例化以检查 deprecated (这在静态分析中有点难，只能检查属性)
            # 这里我们主要依赖 mock_unreal 中的实现
            pass
        except Exception:
            pass
            
        # 检查 C++ 元数据中的 Deprecated 标记
        if class_name in METADATA and METADATA[class_name].get("deprecated", False):
            msg = METADATA[class_name].get("deprecation_message", "此类已废弃")
            self.report.add_warning(f"类 '{class_name}' 已废弃: {msg}", lineno)

    def _validate_method(self, class_name: str, method_name: str, lineno: int):
        if not unreal:
            return
            
        if not hasattr(unreal, class_name):
            return # 之前已经报过错了
            
        cls = getattr(unreal, class_name)
        
        # 检查方法是否存在
        if not hasattr(cls, method_name):
            # 可能是父类方法？mock_unreal 应该包含继承关系
            # 所有的 Python 方法在 mock 中都应该存在
            self.report.add_error(f"方法 '{method_name}' 不存在于类 '{class_name}'", lineno)
            return
            
        # 检查 Deprecated
        method = getattr(cls, method_name)
        # 在 mock 中，deprecated 方法会抛出异常，但我们在静态分析。
        # 我们需要检查 mock 源码或元数据
        
        # 使用元数据检查
        if class_name in METADATA:
            methods = METADATA[class_name].get("functions", {})
            if method_name in methods:
                func_data = methods[method_name]
                if func_data.get("deprecated", False):
                    msg = func_data.get("deprecation_message", "此方法已废弃")
                    self.report.add_warning(f"方法 '{class_name}.{method_name}' 已废弃: {msg}", lineno)

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
