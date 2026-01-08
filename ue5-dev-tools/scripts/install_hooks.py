#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Git Hooks Installation Script (Cross-platform)

This script installs git hooks from the hooks/ directory to .git/hooks/
Run this after cloning the repository to enable automatic version bumping.

The pre-commit hook will automatically increment the patch version in plugin.json
for commits that include non-auxiliary files. Auxiliary files (like .gitignore,
README.md, .github, etc.) do not trigger version bumping.

Works on Windows, macOS, and Linux
"""

import os
import sys
import io
import shutil
from pathlib import Path

# Ensure UTF-8 output on all platforms
if sys.version_info[0] >= 3:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class Colors:
    """ANSI color codes for terminal output (gracefully degrades on Windows)"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color

    @staticmethod
    def disable_on_windows():
        """Disable colors on Windows if not using ANSI-capable terminal"""
        if sys.platform == 'win32':
            # Try to enable ANSI escape sequences on Windows 10+
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.GetStdHandle(-11)
                mode = ctypes.c_ulong()
                if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                    mode.value |= 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
                    if kernel32.SetConsoleMode(handle, mode):
                        return  # ANSI support enabled
            except Exception:
                pass

            # Fallback: disable colors on older Windows
            Colors.RED = ''
            Colors.GREEN = ''
            Colors.YELLOW = ''
            Colors.NC = ''


def get_directories():
    """Get the source and target hook directories"""
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent.parent.resolve()
    subdir_root = script_dir.parent.resolve()

    source_hooks_dir = subdir_root / "hooks"
    target_hooks_dir = repo_root / ".git" / "hooks"

    return source_hooks_dir, target_hooks_dir, repo_root


def check_git_repo(repo_root):
    """Check if .git directory exists"""
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        print(f"{Colors.RED}Error: .git directory not found at {git_dir}{Colors.NC}")
        print("This script must be run from within a git repository")
        return False
    return True


def check_hooks_dir(source_hooks_dir):
    """Check if hooks directory exists"""
    if not source_hooks_dir.exists():
        print(f"{Colors.RED}Error: hooks directory not found at {source_hooks_dir}{Colors.NC}")
        return False
    return True


def create_symlink_or_copy(source, target):
    """
    Try to create a symlink, fall back to copying if that fails.

    Args:
        source: Path to the source hook file
        target: Path to the target hook file

    Returns:
        Tuple of (success, method) where method is 'symlink' or 'copy'
    """
    # Remove target if it already exists
    if target.exists():
        target.unlink()

    # Try creating a symlink
    try:
        # On Windows, this may fail if not running as admin
        if sys.platform == 'win32':
            # Use relative path for better portability
            relative_source = os.path.relpath(source, target.parent)
            os.symlink(relative_source, target)
        else:
            os.symlink(source, target)
        return True, 'symlink'
    except (OSError, NotImplementedError):
        # Fallback to copying if symlink fails
        try:
            shutil.copy2(source, target)
            # Make executable on Unix-like systems
            if sys.platform != 'win32':
                os.chmod(target, 0o755)
            return True, 'copy'
        except Exception as e:
            print(f"{Colors.RED}Error installing {target.name}: {e}{Colors.NC}")
            return False, None


def backup_existing_hook(target_file):
    """Backup existing hook file"""
    if target_file.exists():
        backup_file = target_file.with_suffix(target_file.suffix + '.backup')
        try:
            shutil.copy2(target_file, backup_file)
            print(f"{Colors.YELLOW}⚠ Backed up existing {target_file.name} to {backup_file.name}{Colors.NC}")
            return True
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ Warning: Could not backup {target_file.name}: {e}{Colors.NC}")
            return False
    return True


def install_hooks(source_hooks_dir, target_hooks_dir):
    """Install all hooks from source to target directory"""
    # Create target directory if it doesn't exist
    target_hooks_dir.mkdir(parents=True, exist_ok=True)

    installed_count = 0

    # Install each hook
    for hook_file in sorted(source_hooks_dir.iterdir()):
        if not hook_file.is_file():
            continue

        hook_name = hook_file.name

        # Skip .sample files
        if hook_name.endswith('.sample'):
            continue

        target_file = target_hooks_dir / hook_name

        # Backup existing hook if present
        if target_file.exists():
            backup_existing_hook(target_file)

        # Create symlink or copy
        success, method = create_symlink_or_copy(hook_file, target_file)
        if success:
            method_text = f"({method})"
            print(f"{Colors.GREEN}✓ Installed {hook_name} {method_text}{Colors.NC}")
            installed_count += 1

    return installed_count


def main():
    """Main function"""
    # Try to enable ANSI colors on Windows
    Colors.disable_on_windows()

    # Get directories
    source_hooks_dir, target_hooks_dir, repo_root = get_directories()

    print("Installing git hooks...")
    print(f"  Source: {source_hooks_dir}")
    print(f"  Target: {target_hooks_dir}")
    print()

    # Validation checks
    if not check_git_repo(repo_root):
        return 1

    if not check_hooks_dir(source_hooks_dir):
        return 1

    # Install hooks
    installed_count = install_hooks(source_hooks_dir, target_hooks_dir)

    print()
    if installed_count == 0:
        print(f"{Colors.YELLOW}No hooks found to install{Colors.NC}")
    else:
        print(f"{Colors.GREEN}Successfully installed {installed_count} hook(s){Colors.NC}")
        print()
        print("Available hooks:")
        print("  - pre-commit: Auto-increment version in plugin.json on every commit")

    print()
    print("Done!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
