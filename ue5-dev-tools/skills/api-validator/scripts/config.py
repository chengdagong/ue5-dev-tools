"""
UE5 Dev Tools 路径配置模块

集中管理 Stub 查找、Mock 生成路径等逻辑。
"""
import os
import sys

def get_project_root() -> str:
    """获取项目根目录"""
    # 优先使用 CLAUDE_PROJECT_DIR (由 Claude Code 注入)
    if "CLAUDE_PROJECT_DIR" in os.environ:
        return os.environ["CLAUDE_PROJECT_DIR"]
    # Fallback: 使用 CWD
    return os.getcwd()

def get_mock_dir(project_root: str = None) -> str:
    """获取 Mock 模块的缓存路径"""
    if not project_root:
        project_root = get_project_root()
    
    # 逻辑: ~/.claude/tmp/f{PROJECT_ROOT_ESCAPED}
    # 使用 - 替换 / 来生成扁平化的唯一目录名
    project_root_escaped = project_root.replace("/", "-")
    # 确保 expanduser (~ -> /Users/...)
    return os.path.expanduser(f"~/.claude/tmp/f{project_root_escaped}")

def get_metadata_path(project_root: str = None) -> str:
    """获取 metadata.json 路径 (与 Mock 在同一目录)"""
    mock_dir = get_mock_dir(project_root)
    return os.path.join(mock_dir, "metadata.json")

def get_stub_path(project_root: str = None) -> str:
    """获取 unreal.py stub 文件的默认路径"""
    if not project_root:
        project_root = get_project_root()
        
    # 优先匹配 Intermediate/PythonStub/unreal.py
    return os.path.join(project_root, "Intermediate", "PythonStub", "unreal.py")

def resolve_stub_path(project_root: str = None) -> str:
    """尝试查找 stub 文件，检查是否存在"""
    if not project_root:
        project_root = get_project_root()
    
    # 1. Intermediate
    path = get_stub_path(project_root)
    if os.path.exists(path):
        return path
        
    # 2. Saved (备用)
    alt_path = os.path.join(project_root, "Saved", "UnrealAPIGenerator", "unreal.py")
    if os.path.exists(alt_path):
        return alt_path
        
    return None
