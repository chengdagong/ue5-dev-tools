"""
UE5 Dev Tools Path Configuration Module

Centralizes logic for Stub lookup, Mock generation paths, etc.
"""
import os
import sys

def get_project_root() -> str:
    """Get the project root directory"""
    # Prefer using CLAUDE_PROJECT_DIR (injected by Claude Code)
    if "CLAUDE_PROJECT_DIR" in os.environ:
        return os.environ["CLAUDE_PROJECT_DIR"]
    # Fallback: Use CWD
    return os.getcwd()

def get_mock_dir(project_root: str = None) -> str:
    """Get the cache path for the Mock module"""
    if not project_root:
        project_root = get_project_root()
    
    # Logic: ~/.claude/tmp/f{PROJECT_ROOT_ESCAPED}
    # Use - to replace / to generate a flattened unique directory name
    project_root_escaped = project_root.replace("/", "-")
    # Ensure expanduser (~ -> /Users/...)
    return os.path.expanduser(f"~/.claude/tmp/f{project_root_escaped}")

def get_metadata_path(project_root: str = None) -> str:
    """Get metadata.json path (same directory as Mock)"""
    mock_dir = get_mock_dir(project_root)
    return os.path.join(mock_dir, "metadata.json")

def get_stub_path(project_root: str = None) -> str:
    """Get the default path for unreal.py stub file"""
    if not project_root:
        project_root = get_project_root()
        
    # Prefer matching Intermediate/PythonStub/unreal.py
    return os.path.join(project_root, "Intermediate", "PythonStub", "unreal.py")

def resolve_stub_path(project_root: str = None) -> str:
    """Try to find the stub file, check if it exists"""
    if not project_root:
        project_root = get_project_root()
    
    # 1. Intermediate
    path = get_stub_path(project_root)
    if os.path.exists(path):
        return path
        
    # 2. Saved (Alternative)
    alt_path = os.path.join(project_root, "Saved", "UnrealAPIGenerator", "unreal.py")
    if os.path.exists(alt_path):
        return alt_path
        
    return None
