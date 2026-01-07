---
name: ue5-python-executor
description: Execute Python scripts in running UE5 editor instances using remote execution protocol. Use when users need to (1) enable UE5 Python plugin and remote execution, (2) execute Python scripts in running UE5 editor, (3) verify UE5 project Python configuration, or (4) run Python code remotely in UE5 without debugging.
---

# UE5 Python Executor

Execute Python scripts and code in running Unreal Engine 5 editor instances via socket-based remote execution protocol.

## Quick Start

### Setup UE5 Project for Python Remote Execution

Enable Python plugin and remote execution in a UE5 project:

```bash
# Auto-detects project from CLAUDE_PROJECT_DIR (when run via Claude Code)
python3 scripts/check-config.py --auto-fix

# Or specify project path explicitly
python3 scripts/check-config.py --project /path/to/ue5/project --auto-fix
```

This automatically:
- Enables `PythonScriptPlugin` in `.uproject`
- Configures `bRemoteExecution=True` in `DefaultEngine.ini`
- Sets `bDeveloperMode=True` for development
- Configures multicast bind address

**Note:** Restart UE5 Editor after running this command.

### Execute Python Scripts

Run Python scripts in a running UE5 instance:

```bash
# Auto-detects project name from CLAUDE_PROJECT_DIR
python3 scripts/remote-execute.py --file script.py

# Execute by project name
python3 scripts/remote-execute.py --file script.py --project-name MyProject

# Execute by project path
python3 scripts/remote-execute.py --file script.py --project-path /path/to/project.uproject

# Execute inline code
python3 scripts/remote-execute.py --code "import unreal; print('Hello UE5')"
```

## Core Workflows

### Workflow 1: First-Time Project Setup

For new UE5 projects that need Python remote execution:

1. **Check and fix project configuration:**
   ```bash
   # Auto-detects project from CLAUDE_PROJECT_DIR
   python3 scripts/check-config.py --auto-fix
   ```

2. **Restart UE5 Editor** to apply configuration changes

3. **Test the setup:**
   ```bash
   python3 scripts/remote-execute.py --code "import unreal; print('Hello from UE5')"
   ```

### Workflow 2: Executing Scripts Without Debugging

For quick script execution:

```bash
# Execute specific file
python3 scripts/remote-execute.py \
  --file /path/to/script.py \
  --project-name MyProject \
  --timeout 10.0

# Execute with detached mode (fire and forget)
python3 scripts/remote-execute.py \
  --file script.py \
  --project-name MyProject \
  --detached

# Execute after delay (useful for timing-sensitive operations)
python3 scripts/remote-execute.py \
  --file script.py \
  --project-name MyProject \
  --wait 2.0
```

### Workflow 3: Verifying Configuration

Check if a project is correctly configured without making changes:

```bash
# Check only (auto-detects project)
python3 scripts/check-config.py --check-only

# Get JSON output for programmatic use
python3 scripts/check-config.py --json

# Check specific project
python3 scripts/check-config.py --project /path/to/ue5/project --check-only
```

## Bundled Scripts

### check-config.py

Validates and optionally fixes UE5 Python configuration.

**Key features:**
- Auto-detects project from `CLAUDE_PROJECT_DIR`
- Checks `.uproject` for `PythonScriptPlugin` enabled
- Verifies `DefaultEngine.ini` remote execution settings
- Can automatically fix configuration issues
- Provides JSON output for automation

**Usage examples:**

```bash
# Check current project (auto-detected)
python3 scripts/check-config.py --check-only

# Auto-fix current project
python3 scripts/check-config.py --auto-fix

# Check specific project
python3 scripts/check-config.py --project /path/to/project --check-only

# Get machine-readable output
python3 scripts/check-config.py --json
```

**Environment variables:**
- `CLAUDE_PROJECT_DIR` - Project root (auto-injected by Claude Code)

**Exit codes:**
- `0` - Configuration correct
- `1` - Error (e.g., no .uproject found)
- `2` - Configuration needs fixing

### remote-execute.py

Executes Python code or files in running UE5 instances using socket-based remote execution.

**Key features:**
- Auto-detects project name from `CLAUDE_PROJECT_DIR`
- Multicast discovery of UE5 instances
- Project name or path filtering
- Supports both code strings and file execution
- Detached mode for fire-and-forget execution
- Configurable timeout and wait delays

**Parameters:**
- `--code` - Python code string to execute
- `--file` - Python file to execute
- `--project-name` - Filter by project name (default: auto-detect from `CLAUDE_PROJECT_DIR`)
- `--project-path` - Filter by .uproject path
- `--multicast-group` - Custom multicast address (default: 239.0.0.1:6766)
- `--timeout` - Command execution timeout (default: 5.0s)
- `--detached` - Run in background and exit immediately
- `--wait` - Delay before execution (useful with detached mode)
- `-v, --verbose` - Enable debug logging

**Usage examples:**

```bash
# Execute file (auto-detects project)
python3 scripts/remote-execute.py --file script.py

# Execute with explicit project name
python3 scripts/remote-execute.py --file script.py --project-name MyProject

# Execute inline code
python3 scripts/remote-execute.py --code "import unreal; print(unreal.EditorLevelLibrary.get_editor_world())"

# Detached execution
python3 scripts/remote-execute.py --file long_running.py --detached

# With delay (useful for timing)
python3 scripts/remote-execute.py --file script.py --wait 2.0 --detached
```

**Environment variables:**
- `CLAUDE_PROJECT_DIR` - Project root, used to infer project name (auto-injected by Claude Code)

## Environment Variables

This skill uses Claude Code's auto-injected environment variables for seamless integration:

### CLAUDE_PROJECT_DIR

Auto-injected by Claude Code, pointing to the current project root.

**Used by:**
- `check-config.py` - Auto-detects UE5 project location
- `remote-execute.py` - Infers project name from directory basename

**Example:**
```bash
# When CLAUDE_PROJECT_DIR=/Users/me/MyUE5Game
# These commands work without --project argument:
python3 scripts/check-config.py --auto-fix
python3 scripts/remote-execute.py --file script.py
```

### Fallback Behavior

When environment variables are not set (e.g., running scripts directly outside Claude Code):

1. **CLAUDE_PROJECT_DIR fallback:** Current working directory (`cwd`)

**Manual usage example:**
```bash
cd /path/to/ue5/project
python3 /path/to/plugin/skills/ue5-python-executor/scripts/check-config.py --auto-fix
```

## Technical Details

### Remote Execution Protocol

The skill uses UE5's socket-based Python remote execution protocol:

1. **Discovery:** Multicast UDP ping/pong on `239.0.0.1:6766`
2. **Connection:** TCP connection on dynamically allocated port
3. **Execution:** JSON messages with commands
4. **Response:** JSON messages with results

**Message format:**
```json
{
  "version": 1,
  "magic": "ue_py",
  "source": "python_executor",
  "dest": "node_id",
  "type": "command",
  "data": {
    "command": "script.py or code",
    "exec_mode": "ExecuteFile|ExecuteStatement|EvaluateStatement",
    "unattended": true
  }
}
```

### Project Requirements

**UE5 Configuration:**
- `PythonScriptPlugin` enabled in `.uproject`
- `bRemoteExecution=True` in `DefaultEngine.ini`
- `bDeveloperMode=True` in `DefaultEngine.ini`
- `RemoteExecutionMulticastBindAddress=0.0.0.0` in `DefaultEngine.ini`

**Python Requirements:**
- Python 3.x

## Troubleshooting

### "No UE5 instance found"

**Causes:**
- UE5 Editor not running
- Remote execution not enabled
- Firewall blocking multicast
- Wrong project name/path filter

**Solutions:**
```bash
# Verify configuration
python3 scripts/check-config.py --project /path/to/project

# Try without project filter
python3 scripts/remote-execute.py --code "print('test')" --project-name ""

# Check firewall allows UDP on port 6766
```

### Script execution timeout

**Causes:**
- Script takes longer than timeout
- UE5 frozen or busy
- Network issues

**Solutions:**
```bash
# Increase timeout
python3 scripts/remote-execute.py --file script.py --project-name MyProject --timeout 30.0

# Use detached mode for long scripts
python3 scripts/remote-execute.py --file script.py --project-name MyProject --detached
```

## Common Use Cases

### Case 1: Asset Batch Processing

Process multiple assets without debugging overhead:

```bash
python3 scripts/remote-execute.py \
  --file batch_process_assets.py \
  --project-name MyGame \
  --timeout 60.0
```

### Case 2: Editor Automation

Automate editor workflows:

```bash
python3 scripts/remote-execute.py \
  --file automation/generate_thumbnails.py \
  --project-name MyGame \
  --detached
```

### Case 3: Development Workflow Integration

Integrate into build/test scripts:

```bash
#!/bin/bash

# Ensure UE5 is configured
python3 scripts/check-config.py --project ./MyProject --auto-fix

# Run validation scripts
python3 scripts/remote-execute.py \
  --file tests/validate_assets.py \
  --project-name MyProject \
  --timeout 60.0
```

## Integration with Other Tools

### CI/CD Integration

```yaml
# .github/workflows/ue5-validation.yml
- name: Validate UE5 Assets
  env:
    CLAUDE_PROJECT_DIR: ${{ github.workspace }}
  run: |
    # Scripts auto-detect project from CLAUDE_PROJECT_DIR
    python3 skills/ue5-python-executor/scripts/check-config.py --json
    python3 skills/ue5-python-executor/scripts/remote-execute.py \
      --file validation/check_assets.py \
      --timeout 120
```

## Best Practices

1. **Always verify configuration** before first use: `check-config.py --check-only`

2. **Use project name filtering** when multiple UE5 instances are running

3. **Set appropriate timeouts** for long-running scripts

4. **Use detached mode** for background tasks that don't need immediate results

5. **Restart UE5 Editor** after configuration changes

## Related Skills

- **ue5-vscode-debugger**: Setup VSCode for F5 Python debugging in UE5 (requires this skill)
