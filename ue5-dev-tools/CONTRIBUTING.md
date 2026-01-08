# Contributing to UE5 Dev Tools

## Setup for Development

After cloning the repository, set up your development environment:

### 1. Install Git Hooks

```bash
cd ue5-dev-tools
./scripts/install-hooks.sh
```

This installs:
- **pre-commit hook**: Auto-increments version in `.claude-plugin/plugin.json` on every commit

### 2. Verify Installation

```bash
# Check if hook is installed
ls -la ../.git/hooks/pre-commit

# Should show a symlink to ue5-dev-tools/hooks/pre-commit
```

## Development Workflow

### Version Management

Version numbers in `plugin.json` are **automatically managed**:

- **Format**: `x.y.z` (semantic versioning)
- **Auto-increment**: Patch version (+0.0.1) on every commit
- **Example**: `0.2.0` → `0.2.1` → `0.2.2`

You don't need to manually edit the version number!

### Making Changes

1. Make your changes to skills, commands, or scripts
2. Test your changes
3. Commit normally:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```
4. The pre-commit hook will automatically bump the version

### Testing Hooks

To test the pre-commit hook without committing:

```bash
# Navigate to repository root
cd /path/to/ue5-dev-tools

# Run the hook directly
.git/hooks/pre-commit
```

## Project Structure

```
ue5-dev-tools/
├── .claude-plugin/          # Plugin metadata
│   └── plugin.json          # Version auto-incremented by hook
├── hooks/                   # Shared git hooks (versioned)
│   ├── pre-commit          # Auto-increment version hook
│   └── README.md           # Hook documentation
├── scripts/                 # Development scripts
│   └── install-hooks.sh    # Hook installation script
├── skills/                  # Plugin skills
├── commands/                # Slash commands
└── tests/                   # Test files
```

## Adding New Hooks

To add a new git hook:

1. Create the hook file in `ue5-dev-tools/hooks/`
2. Make it executable: `chmod +x ue5-dev-tools/hooks/your-hook`
3. Run `./scripts/install-hooks.sh` to install it
4. Commit the new hook to the repository

Team members will get the new hook after:
```bash
git pull
./scripts/install-hooks.sh
```

## Troubleshooting

### Hook not running

```bash
# Reinstall hooks
./scripts/install-hooks.sh

# Verify hook is executable
ls -la ../.git/hooks/pre-commit
```

### Version not incrementing

```bash
# Check if plugin.json exists
ls -la .claude-plugin/plugin.json

# Test hook manually
../.git/hooks/pre-commit
```

### Disable hooks temporarily

```bash
# Skip hooks for a single commit
git commit --no-verify -m "message"
```

## Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run unit tests only
python3 -m pytest tests/unit/ -v

# Run tests for a specific skill (e.g., api-validator)
python3 -m pytest tests/unit/api_validator/ tests/integration/api_validator/ -v
```

## Code Style

- Python: Follow PEP 8
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and small

## Commit Message Convention

Use conventional commits format:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add C++ metadata extraction for API validator
fix: correct path resolution in remote executor
docs: update installation instructions
chore: bump version to 0.3.0
```
