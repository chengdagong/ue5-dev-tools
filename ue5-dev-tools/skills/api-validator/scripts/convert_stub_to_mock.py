#!/usr/bin/env python3
"""
将 Unreal Python 存根文件转换为可导入的 Mock 模块

功能：
1. 解析存根文件的类、方法、属性定义
2. 为每个方法生成返回 mock 值的实现
3. 为 @property 生成实际的 getter/setter
4. 在基类中实现 get_editor_property/set_editor_property
5. 检测 deprecated 标记并生成抛出异常的实现
"""

import re
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class PropertyInfo:
    """属性信息"""
    name: str
    type_hint: str
    docstring: str
    is_deprecated: bool = False
    deprecated_msg: str = ""


@dataclass
class MethodInfo:
    """方法信息"""
    name: str
    signature: str  # 完整签名行
    return_type: str
    docstring: str
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_deprecated: bool = False
    deprecated_msg: str = ""


@dataclass
class ClassInfo:
    """类信息"""
    name: str
    bases: str  # 父类字符串
    docstring: str
    init_signature: str = ""
    init_params: List[Tuple[str, str, str]] = field(default_factory=list)  # (name, type, default)
    methods: List[MethodInfo] = field(default_factory=list)
    properties: List[PropertyInfo] = field(default_factory=list)
    enum_values: List[Tuple[str, str]] = field(default_factory=list)  # (name, value) 枚举值
    is_deprecated: bool = False
    deprecated_msg: str = ""


def escape_docstring(text: str) -> str:
    """转义 docstring 中的特殊字符"""
    if not text:
        return text
    # 将嵌入的双引号替换为单引号，避免与三引号冲突
    text = text.replace('\\"', "'")
    text = text.replace('"', "'")
    return text


def escape_string(text: str) -> str:
    """转义字符串字面量中的特殊字符"""
    if not text:
        return text
    # 转义双引号和反斜杠
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    return text


def sanitize_default_value(default: str) -> str:
    """将复杂默认值（如枚举引用）转换为安全的 None"""
    if not default:
        return "None"
    
    # 保留简单的基本类型默认值
    safe_patterns = [
        # 数字
        lambda s: s.replace('.', '', 1).replace('-', '', 1).isdigit(),
        # 字符串
        lambda s: s.startswith('"') or s.startswith("'"),
        # 布尔值
        lambda s: s in ('True', 'False'),
        # None
        lambda s: s == 'None',
        # 空集合
        lambda s: s in ('[]', '{}', '()', 'set()'),
        # 列表/元组/字典字面量（简单情况）
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
    
    # 包含 . 的需要引用其他类型，不安全
    if '.' in default:
        return "None"
    
    # 其他情况如 Name("xxx") 需要判断
    if '(' in default:
        return "None"
    
    return default


def get_mock_return_value(return_type: str) -> str:
    """根据返回类型生成 mock 返回值"""
    if not return_type or return_type == "None":
        return "None"
    
    # 清理类型注解
    return_type = return_type.strip()
    
    # 处理 Optional 类型
    if return_type.startswith("Optional["):
        return "None"
    
    # 基本类型
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
    
    # 直接匹配
    if return_type in type_map:
        return type_map[return_type]
    
    # 处理泛型类型
    for key in type_map:
        if return_type.startswith(f"{key}["):
            return type_map[key]
    
    # Unreal 特定类型
    if return_type in ("Name", "Text"):
        return f'{return_type}("")' if return_type != "Name" else 'Name("None")'
    
    # Array 类型
    if return_type.startswith("Array["):
        return "Array(object)"
    
    # 其他类型返回 None
    return "None"


def check_deprecated(docstring: str) -> Tuple[bool, str]:
    """检查 docstring 中是否有 deprecated 标记"""
    if not docstring:
        return False, ""
    
    # 查找 deprecated 相关文本
    lines = docstring.split('\n')
    deprecated_lines = []
    in_deprecated = False
    
    for line in lines:
        line_lower = line.lower()
        if 'deprecated' in line_lower:
            in_deprecated = True
            deprecated_lines.append(line.strip())
        elif in_deprecated and line.strip() and not line.strip().startswith('-'):
            # 继续收集 deprecated 说明
            deprecated_lines.append(line.strip())
        elif in_deprecated and (not line.strip() or line.strip().startswith('-')):
            in_deprecated = False
    
    if deprecated_lines:
        return True, ' '.join(deprecated_lines)
    return False, ""


def parse_method_signature(sig_line: str) -> Tuple[str, str]:
    """解析方法签名，返回 (方法名, 返回类型)"""
    # 匹配 def method_name(...) -> ReturnType:
    match = re.match(r'\s*def\s+(\w+)\s*\([^)]*\)\s*(?:->\s*([^:]+))?\s*:', sig_line)
    if match:
        return match.group(1), (match.group(2) or "None").strip()
    return "", "None"


def parse_init_params(sig_line: str) -> List[Tuple[str, str, str]]:
    """解析 __init__ 方法的参数"""
    # 提取参数部分
    match = re.search(r'def\s+__init__\s*\(([^)]*)\)', sig_line)
    if not match:
        return []
    
    params_str = match.group(1)
    params = []
    
    # 简单分割参数（忽略嵌套的括号）
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
            continue
        
        # 解析 name: type = default
        match = re.match(r'(\w+)\s*:\s*([^=]+)(?:\s*=\s*(.+))?', param)
        if match:
            name = match.group(1)
            type_hint = match.group(2).strip()
            default = match.group(3).strip() if match.group(3) else None
            result.append((name, type_hint, default))
        else:
            # 只有名字
            result.append((param, "Any", None))
    
    return result


def parse_stub_file(file_path: str) -> List[ClassInfo]:
    """解析存根文件，提取所有类信息"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    classes = []
    
    # 匹配类定义
    class_pattern = re.compile(
        r'^class\s+(\w+)\s*(\([^)]*\))?\s*:\s*\n(.*?)(?=^class\s|\Z)',
        re.MULTILINE | re.DOTALL
    )
    
    for match in class_pattern.finditer(content):
        class_name = match.group(1)
        bases = match.group(2) or "()"
        class_body = match.group(3)
        
        # 提取类 docstring
        docstring_match = re.match(r'\s*r?"""(.*?)"""\s*', class_body, re.DOTALL)
        docstring = docstring_match.group(1) if docstring_match else ""
        
        # 检查类是否 deprecated
        is_deprecated, deprecated_msg = check_deprecated(docstring)
        
        class_info = ClassInfo(
            name=class_name,
            bases=bases,
            docstring=docstring,
            is_deprecated=is_deprecated,
            deprecated_msg=deprecated_msg
        )
        
        # 解析方法
        method_pattern = re.compile(
            r'((?:^    @(?:classmethod|staticmethod)\s*\n)?)'  # 装饰器
            r'^    def\s+(\w+)\s*\([^)]*\)(?:\s*->\s*[^:]+)?\s*:\s*\n'  # 方法签名
            r'((?:\s*r?""".*?"""\s*)?)',  # docstring
            re.MULTILINE | re.DOTALL
        )
        
        for m in method_pattern.finditer(class_body):
            decorator = m.group(1).strip() if m.group(1) else ""
            method_line = m.group(0)
            method_name, return_type = parse_method_signature(method_line)
            
            # 跳过解析失败的方法
            if not method_name:
                continue
            
            method_docstring = m.group(3) if m.group(3) else ""
            
            # 清理 docstring
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
                deprecated_msg=deprecated_msg
            )
            
            if method_name == '__init__':
                class_info.init_signature = method_line.strip()
                class_info.init_params = parse_init_params(method_line)
            else:
                class_info.methods.append(method_info)
        
        # 解析 @property
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
        
        # 解析枚举值 (如 GAUSSIAN: RBFKernelType = ... #: 0)
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
    
    # 扫描所有枚举引用，找出缺失的枚举值并补充
    # 首先收集所有已定义的枚举类及其值
    enum_classes = {}  # {类名: {已定义的枚举值名}}
    for cls in classes:
        if 'EnumBase' in cls.bases:
            enum_classes[cls.name] = set(name for name, _ in cls.enum_values)
    
    # 搜索整个文件中的枚举引用 (格式: EnumClassName.VALUE_NAME)
    enum_ref_pattern = re.compile(r'\b([A-Z][A-Za-z0-9_]+)\.([A-Z][A-Z0-9_]+)\b')
    referenced_values = {}  # {类名: {引用的枚举值名}}
    
    for match in enum_ref_pattern.finditer(content):
        enum_class = match.group(1)
        enum_value = match.group(2)
        if enum_class in enum_classes:
            if enum_class not in referenced_values:
                referenced_values[enum_class] = set()
            referenced_values[enum_class].add(enum_value)
    
    # 找出缺失的枚举值并添加到对应的类中
    missing_count = 0
    for cls in classes:
        if cls.name in enum_classes and cls.name in referenced_values:
            defined = enum_classes[cls.name]
            referenced = referenced_values[cls.name]
            missing = referenced - defined
            
            # 添加缺失的枚举值，使用类中最大值 + 1 作为起始
            if missing:
                max_value = max((int(v) for _, v in cls.enum_values), default=-1)
                for value_name in sorted(missing):
                    max_value += 1
                    cls.enum_values.append((value_name, str(max_value)))
                    missing_count += 1
    
    if missing_count > 0:
        print(f"  - 补充了 {missing_count} 个缺失的枚举值")
    
    return classes


def generate_mock_module(classes: List[ClassInfo], output_dir: str):
    """生成 mock 模块"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成 __init__.py
    init_content = '''"""
Unreal Engine Python Mock 模块

这是一个从 unreal.py 存根文件生成的 mock 模块，可以在没有 Unreal Engine 环境时使用。
支持通过 get_editor_property/set_editor_property 访问属性。
"""

from .unreal_mock import *
'''
    
    with open(os.path.join(output_dir, '__init__.py'), 'w', encoding='utf-8') as f:
        f.write(init_content)
    
    # 生成主模块
    lines = []
    
    # 文件头
    lines.append('"""')
    lines.append('Unreal Engine Python Mock 模块（自动生成）')
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
    lines.append('    """当使用已废弃的方法或属性时抛出"""')
    lines.append('    pass')
    lines.append('')
    lines.append('')
    
    # 分层处理类：基类 -> 枚举类 -> 其他类
    # 这样可以确保枚举类在被其他类引用之前已经定义
    base_classes = []  # 基类（如 _WrapperBase, EnumBase, StructBase 等）
    enum_classes = []  # 枚举类（继承自 EnumBase）
    other_classes = [] # 其他类
    
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
    
    # 按顺序生成
    lines.append('# ============== 基类 ==============')
    lines.append('')
    for cls in base_classes:
        lines.extend(generate_class_code(cls))
        lines.append('')
    
    lines.append('# ============== 枚举类 ==============')
    lines.append('')
    for cls in enum_classes:
        lines.extend(generate_class_code(cls))
        lines.append('')
    
    lines.append('# ============== 其他类 ==============')
    lines.append('')
    for cls in other_classes:
        lines.extend(generate_class_code(cls))
        lines.append('')
    
    with open(os.path.join(output_dir, 'unreal_mock.py'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"生成完成：{len(classes)} 个类")
    print(f"  - 基类：{len(base_classes)} 个")
    print(f"  - 枚举类：{len(enum_classes)} 个")
    print(f"  - 其他类：{len(other_classes)} 个")
    print(f"输出目录：{output_dir}")


def generate_class_code(cls: ClassInfo) -> List[str]:
    """生成单个类的代码"""
    lines = []
    
    # 类定义
    lines.append(f'class {cls.name}{cls.bases}:')
    
    # Docstring
    if cls.docstring:
        escaped_doc = escape_docstring(cls.docstring.strip())
        lines.append(f'    r"""')
        for line in escaped_doc.split('\n'):
            lines.append(f'    {line}')
        lines.append(f'    """')
    
    # 枚举值（如果是枚举类）
    if cls.enum_values:
        lines.append('')
        for enum_name, enum_value in cls.enum_values:
            lines.append(f'    {enum_name} = {enum_value}')
        lines.append('')
    
    # __init__ 方法
    if cls.is_deprecated:
        escaped_msg = escape_string(cls.deprecated_msg)
        lines.append(f'    def __init__(self, *args, **kwargs):')
        lines.append(f'        raise DeprecatedError("{escaped_msg}")')
    else:
        # 生成 __init__
        if cls.init_params:
            param_strs = ['self']
            sanitized_params = []  # 记录被安全化处理的参数
            for name, type_hint, default in cls.init_params:
                if default:
                    safe_default = sanitize_default_value(default)
                    param_strs.append(f'{name}={safe_default}')
                    if safe_default != default:
                        sanitized_params.append((name, default))
                else:
                    param_strs.append(f'{name}=None')
            
            # 如果有参数被安全化处理，添加 TODO 注释
            if sanitized_params:
                lines.append(f'    # TODO: 以下参数的默认值被安全化处理，原始值需要在 Unreal 环境中恢复:')
                for param_name, original_default in sanitized_params:
                    lines.append(f'    #   - {param_name}: {original_default}')
            
            lines.append(f'    def __init__({", ".join(param_strs)}):')
        else:
            lines.append(f'    def __init__(self, *args, **kwargs):')
        
        # 初始化属性存储
        lines.append(f'        self._properties = {{}}')
        
        # 设置参数为属性
        for name, type_hint, default in cls.init_params:
            lines.append(f'        self._properties["{name}"] = {name}')
        
        # 初始化所有 property
        for prop in cls.properties:
            if prop.name not in [p[0] for p in cls.init_params]:
                mock_val = get_mock_return_value(prop.type_hint)
                lines.append(f'        self._properties["{prop.name}"] = {mock_val}')
    
    # get_editor_property / set_editor_property
    if not cls.is_deprecated and ('_ObjectBase' in cls.bases or '_WrapperBase' in cls.bases or 'StructBase' in cls.bases or cls.name in ('_ObjectBase', 'StructBase', '_WrapperBase')):
        lines.append('')
        lines.append('    def get_editor_property(self, name: str) -> object:')
        lines.append('        """获取编辑器属性值"""')
        lines.append('        return self._properties.get(name, None)')
        lines.append('')
        lines.append('    def set_editor_property(self, name: str, value: object, notify_mode=None) -> None:')
        lines.append('        """设置编辑器属性值"""')
        lines.append('        self._properties[name] = value')
        lines.append('')
        lines.append('    def set_editor_properties(self, properties: dict) -> None:')
        lines.append('        """批量设置编辑器属性"""')
        lines.append('        self._properties.update(properties)')
    
    # 生成 properties
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
    
    # 生成方法
    for method in cls.methods:
        if method.name.startswith('_') and method.name != '__init__':
            continue  # 跳过私有方法（除了 __init__）
        
        lines.append('')
        
        if method.is_classmethod:
            lines.append('    @classmethod')
            lines.append(f'    def {method.name}(cls, *args, **kwargs) -> {method.return_type}:')
        elif method.is_staticmethod:
            lines.append('    @staticmethod')
            lines.append(f'    def {method.name}(*args, **kwargs) -> {method.return_type}:')
        else:
            lines.append(f'    def {method.name}(self, *args, **kwargs) -> {method.return_type}:')
        
        if method.docstring:
            # 简化 docstring
            first_line = escape_docstring(method.docstring.strip().split('\n')[0])
            lines.append(f'        """{first_line}"""')
        
        if method.is_deprecated:
            escaped_method_msg = escape_string(method.deprecated_msg)
            lines.append(f'        raise DeprecatedError("{escaped_method_msg}")')
        else:
            mock_val = get_mock_return_value(method.return_type)
            lines.append(f'        return {mock_val}')
    
    # 如果类体为空，添加 pass
    if len(lines) == 1 or (len(lines) == 2 and 'r"""' in lines[1]):
        lines.append('    pass')
    
    return lines


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='将 Unreal Python 存根文件转换为 Mock 模块')
    parser.add_argument('--input', '-i', default='Intermediate/PythonStub/unreal.py',
                       help='输入的存根文件路径')
    parser.add_argument('--output', '-o', default='mock_unreal',
                       help='输出目录')
    
    args = parser.parse_args()
    
    print(f"解析存根文件: {args.input}")
    classes = parse_stub_file(args.input)
    print(f"找到 {len(classes)} 个类定义")
    
    print(f"生成 Mock 模块...")
    generate_mock_module(classes, args.output)


if __name__ == '__main__':
    main()
