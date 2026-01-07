# Git Hooks

This directory contains git hooks that can be shared across the team.

## Installation

After cloning this repository, run the installation script to activate the hooks:

```bash
# From the ue5-dev-tools directory
./scripts/install-hooks.sh
```

This will install all hooks from this directory to `.git/hooks/`.

## Available Hooks

### pre-commit

Automatically increments the version number in `.claude-plugin/plugin.json` on every commit.

- **Version format**: `x.y.z` (semantic versioning)
- **Increment**: Patch version (last digit) +1
- **Example**: `0.2.0` → `0.2.1` → `0.2.2`

The modified `plugin.json` is automatically staged and included in the commit.

## Manual Installation

If the installation script doesn't work, you can manually create a symlink:

```bash
# From the repository root
ln -sf ../../ue5-dev-tools/hooks/pre-commit .git/hooks/pre-commit
```

## Uninstallation

To disable a hook, simply remove it from `.git/hooks/`:

```bash
rm .git/hooks/pre-commit
```

## Why Use Shared Hooks?

- **Consistency**: Ensures all team members follow the same processes
- **Automation**: Reduces manual work (like version bumping)
- **Quality**: Can enforce code quality checks before commits
- **Version Control**: Hooks are tracked in git, so everyone gets updates
