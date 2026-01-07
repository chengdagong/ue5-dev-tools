"""
UE5 Remote Execution Library

Shared library for UE5 Python remote execution protocol and utilities.
Used by ue5-python-executor and ue5-vscode-debugger skills.
"""

from .executor import UE5RemoteExecution
from .utils import (
    get_plugin_root,
    get_project_root,
    get_default_project_name,
    get_default_project_path,
)

__all__ = [
    "UE5RemoteExecution",
    "get_plugin_root",
    "get_project_root",
    "get_default_project_name",
    "get_default_project_path",
]
