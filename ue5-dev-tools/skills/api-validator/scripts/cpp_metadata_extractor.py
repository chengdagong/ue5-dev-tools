#!/usr/bin/env python3
"""
UE5 C++ 元数据提取器
"""

import os
import re
import json
import argparse
from typing import Dict, Any

def scan_ue5_source(source_path: str) -> Dict[str, Any]:
    metadata = {}
    print(f"扫描 UE5 源码目录: {source_path}")
    
    # 正则表达式
    class_pattern = re.compile(r'class\s+\w+_API\s+(\w+)\s*:')
    ufunction_pattern = re.compile(r'UFUNCTION\s*\(([^)]*)\)\s*(?:virtual\s+)?[\w<>*&]+\s+(\w+)\s*\(')
    meta_pattern = re.compile(r'meta\s*=\s*\(([^)]*)\)')
    
    file_count = 0
    for root, dirs, files in os.walk(source_path):
        for file in files:
            if not file.endswith('.h'):
                continue
                
            filepath = os.path.join(root, file)
            file_count += 1
            if file_count % 100 == 0:
                print(f"  已处理 {file_count} 个文件...", end='\r')
            
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # 简单解析类
                # 这不是完整的解析器，只是提取基本信息
                class_matches = class_pattern.finditer(content)
                current_classes = {}
                
                for match in class_matches:
                    cpp_class_name = match.group(1)
                    # 尝试推断 Python 类名 (去掉前缀 U/A/F)
                    if cpp_class_name[0] in ['U', 'A', 'F']:
                        py_class_name = cpp_class_name[1:]
                    else:
                        py_class_name = cpp_class_name
                        
                    current_classes[py_class_name] = {
                        "cpp_name": cpp_class_name,
                        "file": file,
                        "functions": {},
                        "properties": {}
                    }
                
                # 提取 UFUNCTION
                func_matches = ufunction_pattern.finditer(content)
                for f_match in func_matches:
                    specifiers = f_match.group(1)
                    func_name = f_match.group(2)
                    
                    # 只有 BlueprintCallable 才有可能是 Python 可见的
                    if 'BlueprintCallable' in specifiers or 'BlueprintPure' in specifiers:
                        # 确定属于哪个类（非常简化，只找最近的一个）
                        # 实际上这里应该根据文件位置来判断
                        if current_classes:
                            # 假设函数属于文件中定义的第一个类（这很不准确，但作为示例足够）
                            target_class = list(current_classes.keys())[0]
                            
                            current_classes[target_class]["functions"][func_name] = {
                                "specifiers": specifiers,
                                "blueprint_pure": 'BlueprintPure' in specifiers
                            }
                            
                            # 解析 meta
                            meta_match = meta_pattern.search(specifiers)
                            if meta_match:
                                meta_str = meta_match.group(1)
                                if 'Deprecated' in meta_str or 'DeprecationMessage' in meta_str:
                                    current_classes[target_class]["functions"][func_name]["deprecated"] = True
                                    
                # 合并到主数据
                for name, data in current_classes.items():
                    if data["functions"]: # 只保留有函数的类
                        metadata[name] = data
                        
            except Exception as e:
                pass
                
    print(f"\n完成扫描。提取了 {len(metadata)} 个类的元数据。")
    return metadata

def main():
    parser = argparse.ArgumentParser(description="UE5 C++ 元数据提取器")
    parser.add_argument("--output", "-o", default="metadata.json", help="输出 JSON 路径")
    parser.add_argument("--ue5-path", "-u", default="/Users/Shared/Epic Games/UE_5.7/Engine/Source", help="UE5 源码路径")
    
    args = parser.parse_args()
    
    metadata = scan_ue5_source(args.ue5_path)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"元数据已保存至: {args.output}")

if __name__ == "__main__":
    main()
