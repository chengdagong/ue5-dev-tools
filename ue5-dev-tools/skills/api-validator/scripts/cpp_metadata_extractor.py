#!/usr/bin/env python3
"""
UE5 C++ Metadata Extractor
"""

import os
import re
import json
import argparse
from typing import Dict, Any

def scan_ue5_source(source_path: str) -> Dict[str, Any]:
    metadata = {}
    print(f"Scanning UE5 source directory: {source_path}")
    
    # Regular expressions
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
                print(f"  Processed {file_count} files...", end='\r')
            
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Simple class parsing
                # This is not a full parser, just extracting basic info
                class_matches = class_pattern.finditer(content)
                current_classes = {}
                
                for match in class_matches:
                    cpp_class_name = match.group(1)
                    # Try to infer Python class name (remove prefix U/A/F)
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
                
                # Extract UFUNCTION
                func_matches = ufunction_pattern.finditer(content)
                for f_match in func_matches:
                    specifiers = f_match.group(1)
                    func_name = f_match.group(2)
                    
                    # Only BlueprintCallable might be visible to Python
                    if 'BlueprintCallable' in specifiers or 'BlueprintPure' in specifiers:
                        # Determine which class it belongs to (very simplified, just finds the nearest one)
                        # In reality, this should be judged based on file position
                        if current_classes:
                            # Assume the function belongs to the first class defined in the file (this is inaccurate, but enough for example)
                            target_class = list(current_classes.keys())[0]
                            
                            current_classes[target_class]["functions"][func_name] = {
                                "specifiers": specifiers,
                                "blueprint_pure": 'BlueprintPure' in specifiers
                            }
                            
                            # Parse meta
                            meta_match = meta_pattern.search(specifiers)
                            if meta_match:
                                meta_str = meta_match.group(1)
                                if 'Deprecated' in meta_str or 'DeprecationMessage' in meta_str:
                                    current_classes[target_class]["functions"][func_name]["deprecated"] = True
                                    
                # Merge into main data
                for name, data in current_classes.items():
                    if data["functions"]: # Only keep classes with functions
                        metadata[name] = data
                        
            except Exception as e:
                pass
                
    print(f"\nScan complete. Extracted metadata for {len(metadata)} classes.")
    return metadata

def main():
    parser = argparse.ArgumentParser(description="UE5 C++ Metadata Extractor")
    parser.add_argument("--output", "-o", default="metadata.json", help="Output JSON path")
    parser.add_argument("--ue5-path", "-u", default="/Users/Shared/Epic Games/UE_5.7/Engine/Source", help="UE5 Source Path")
    
    args = parser.parse_args()
    
    metadata = scan_ue5_source(args.ue5_path)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"Metadata saved to: {args.output}")

if __name__ == "__main__":
    main()
