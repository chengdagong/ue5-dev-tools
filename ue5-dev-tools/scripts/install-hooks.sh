#!/bin/bash
###############################################################################
# Git Hooks Installation Script
#
# This script installs git hooks from the hooks/ directory to .git/hooks/
# Run this after cloning the repository to enable automatic version bumping
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the repository root (parent of ue5-dev-tools/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SUBDIR_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Hooks directories
SOURCE_HOOKS_DIR="$SUBDIR_ROOT/hooks"
TARGET_HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Installing git hooks..."
echo "  Source: $SOURCE_HOOKS_DIR"
echo "  Target: $TARGET_HOOKS_DIR"
echo ""

# Check if .git directory exists
if [ ! -d "$REPO_ROOT/.git" ]; then
    echo -e "${RED}Error: .git directory not found at $REPO_ROOT/.git${NC}"
    echo "This script must be run from within a git repository"
    exit 1
fi

# Check if hooks directory exists
if [ ! -d "$SOURCE_HOOKS_DIR" ]; then
    echo -e "${RED}Error: hooks directory not found at $SOURCE_HOOKS_DIR${NC}"
    exit 1
fi

# Create .git/hooks directory if it doesn't exist
mkdir -p "$TARGET_HOOKS_DIR"

# Install each hook
INSTALLED_COUNT=0
for hook_file in "$SOURCE_HOOKS_DIR"/*; do
    if [ -f "$hook_file" ]; then
        hook_name=$(basename "$hook_file")

        # Skip .sample files
        if [[ "$hook_name" == *.sample ]]; then
            continue
        fi

        target_file="$TARGET_HOOKS_DIR/$hook_name"

        # Backup existing hook if present
        if [ -f "$target_file" ]; then
            echo -e "${YELLOW}⚠ Backing up existing $hook_name to $hook_name.backup${NC}"
            mv "$target_file" "$target_file.backup"
        fi

        # Create symlink or copy
        if ln -sf "$hook_file" "$target_file" 2>/dev/null; then
            echo -e "${GREEN}✓ Installed $hook_name (symlink)${NC}"
        else
            # Fallback to copy if symlink fails
            cp "$hook_file" "$target_file"
            chmod +x "$target_file"
            echo -e "${GREEN}✓ Installed $hook_name (copy)${NC}"
        fi

        INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
    fi
done

echo ""
if [ $INSTALLED_COUNT -eq 0 ]; then
    echo -e "${YELLOW}No hooks found to install${NC}"
else
    echo -e "${GREEN}Successfully installed $INSTALLED_COUNT hook(s)${NC}"
    echo ""
    echo "Available hooks:"
    echo "  - pre-commit: Auto-increment version in plugin.json on every commit"
fi

echo ""
echo "Done!"
