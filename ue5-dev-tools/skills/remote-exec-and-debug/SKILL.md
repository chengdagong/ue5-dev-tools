---
name: remote-exec-and-debug
description: Setup and automate UE5 Python remote debugging and script execution. Use when users need to (1) enable UE5 Python plugin and remote execution, (2) configure VSCode for F5 Python debugging in UE5, (3) execute Python scripts in running UE5 editor, (4) setup debugpy remote debugging workflow, or (5) automate UE5 project Python development environment setup.
---

# UE5 Remote Execution and Debugging

Automates the setup and execution of Python scripts in Unreal Engine 5, including VSCode debugging configuration.

## Quick Start

### Setup UE5 Project for Python Development

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

### Setup VSCode Debugging (F5 to Debug)

Configure VSCode for one-click Python debugging in UE5:

```bash
# Auto-generates correct paths using CLAUDE_PLUGIN_ROOT and CLAUDE_PROJECT_DIR
python3 scripts/setup-vscode.py

# Or specify project path explicitly
python3 scripts/setup-vscode.py --project /path/to/ue5/project

# Force overwrite existing configurations
python3 scripts/setup-vscode.py --force
```

This automatically:
- Creates or merges `.vscode/launch.json` with debug configurations
- Creates or merges `.vscode/tasks.json` with UE5 tasks
- Uses correct plugin paths from environment variables
- Preserves existing VSCode configurations

**Then:** Open Python file in VSCode and press F5 to:
- Start debugpy server in UE5
- Execute the current Python file in UE5
- Attach VSCode debugger to UE5

### Execute Python Scripts Directly

Run Python scripts in a running UE5 instance without debugging:

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

For new UE5 projects that need Python development:

1. **Check and fix project configuration:**
   ```bash
   # Auto-detects project from CLAUDE_PROJECT_DIR
   python3 scripts/check-config.py --auto-fix
   ```

2. **Restart UE5 Editor** to apply configuration changes

3. **Setup VSCode debugging:**
   ```bash
   # Auto-generates correct configurations
   python3 scripts/setup-vscode.py
   ```

4. **Test the setup:**
   - Open any Python file in VSCode
   - Press F5
   - Verify debugger attaches and script executes

### Workflow 2: Debugging Python Scripts

For debugging Python code running in UE5:

1. **Ensure UE5 Editor is running** with the target project

2. **Set breakpoints** in your Python file

3. **Choose debug configuration:**
   - **"UE5 Python: Debug Current File"** - Starts debug server, executes current file, and attaches
   - **"UE5 Python: Attach Only"** - Only attaches to existing debug server

4. **Press F5** to start debugging

5. **Debug normally** - Use VSCode debugging features (step, inspect variables, etc.)

### Workflow 3: Executing Scripts Without Debugging

For quick script execution without debugging overhead:

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

### Workflow 4: Verifying Configuration

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

### setup-vscode.py

Automatically generates VSCode configurations with correct plugin paths.

**Key features:**
- Auto-detects plugin root from `CLAUDE_PLUGIN_ROOT`
- Auto-detects project root from `CLAUDE_PROJECT_DIR`
- Creates or merges `.vscode/launch.json` and `.vscode/tasks.json`
- Preserves existing configurations when merging
- Uses absolute paths to plugin scripts for reliability

**Usage examples:**

```bash
# Auto-detect all paths from environment
python3 scripts/setup-vscode.py

# Specify project path
python3 scripts/setup-vscode.py --project /path/to/ue5/project

# Force overwrite existing configurations
python3 scripts/setup-vscode.py --force
```

**Environment variables:**
- `CLAUDE_PROJECT_DIR` - Project root (auto-injected by Claude Code)
- `CLAUDE_PLUGIN_ROOT` - Plugin root (auto-injected by Claude Code)

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

### start_debug_server.py

Executed **inside UE5** to start debugpy server. Not called directly by users.

**What it does:**
- Checks if debugpy is installed, installs if needed
- Configures debugpy to use UE5's Python interpreter
- Starts listening on `127.0.0.1:19678`
- Handles already-running server gracefully

**Called by:** VSCode task `ue5-start-debug-server` via `remote-execute.py`

## VSCode Configuration

### Launch Configurations

**"UE5 Python: Debug Current File"**
- Starts debug server in UE5
- Executes current file
- Attaches debugger
- Uses `preLaunchTask: "ue5-start-debug-and-execute"`

**"UE5 Python: Attach Only"**
- Only attaches to existing debug server
- Useful when debug server is already running
- No preLaunchTask

**Configuration details:**
- Debug adapter: `debugpy`
- Host: `127.0.0.1`
- Port: `19678`
- Path mapping: `${workspaceFolder}` ↔ `${workspaceFolder}`
- `justMyCode: false` - Allows debugging into UE5 Python modules

### Tasks

**ue5-start-debug-server**
- Executes `start_debug_server.py` in UE5 via `remote-execute.py`
- Waits for `[UE5-DEBUG] READY` message
- Problem matcher detects errors

**ue5-execute-python**
- Executes current file (`${file}`) in UE5
- Runs detached with 1-second wait
- Background task

**ue5-start-debug-and-execute**
- Sequential composite task
- Runs `ue5-start-debug-server` then `ue5-execute-python`
- Used by "Debug Current File" launch config

## Environment Variables

This skill uses Claude Code's auto-injected environment variables for seamless integration:

### CLAUDE_PROJECT_DIR

Auto-injected by Claude Code, pointing to the current project root.

**Used by:**
- `check-config.py` - Auto-detects UE5 project location
- `remote-execute.py` - Infers project name from directory basename
- `setup-vscode.py` - Determines where to create `.vscode/` configs

**Example:**
```bash
# When CLAUDE_PROJECT_DIR=/Users/me/MyUE5Game
# These commands work without --project argument:
python3 scripts/check-config.py --auto-fix
python3 scripts/remote-execute.py --file script.py
python3 scripts/setup-vscode.py
```

### CLAUDE_PLUGIN_ROOT

Auto-injected by Claude Code, pointing to the plugin installation directory.

**Used by:**
- `setup-vscode.py` - Finds plugin scripts to reference in VSCode tasks
- All scripts (fallback) - Locates plugin resources when environment variable not set

**Example:**
```bash
# When CLAUDE_PLUGIN_ROOT=/Users/me/.claude/plugins/ue5-dev-tools
# setup-vscode.py generates absolute paths like:
# /Users/me/.claude/plugins/ue5-dev-tools/skills/remote-exec-and-debug/scripts/remote-execute.py
```

### Fallback Behavior

When environment variables are not set (e.g., running scripts directly outside Claude Code):

1. **CLAUDE_PROJECT_DIR fallback:** Current working directory (`cwd`)
2. **CLAUDE_PLUGIN_ROOT fallback:** Inferred from script location using relative paths

**Manual usage example:**
```bash
cd /path/to/ue5/project
python3 /path/to/plugin/skills/remote-exec-and-debug/scripts/check-config.py --auto-fix
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

### Debug Port

Default debugpy port: `19678`

To change:
- Update `DEBUG_PORT` in `start_debug_server.py`
- Update `port` in `vscode-launch-template.json`

### Project Requirements

**UE5 Configuration:**
- `PythonScriptPlugin` enabled in `.uproject`
- `bRemoteExecution=True` in `DefaultEngine.ini`
- `bDeveloperMode=True` in `DefaultEngine.ini`
- `RemoteExecutionMulticastBindAddress=0.0.0.0` in `DefaultEngine.ini`

**Python Requirements:**
- `debugpy` (auto-installed by `start_debug_server.py`)
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

### "debugpy client already connected" or "already in use"

This is normal - debug server is already running. Use "UE5 Python: Attach Only" configuration instead.

### Debugger doesn't stop at breakpoints

**Causes:**
- File path mismatch
- Code already executed before attach
- `justMyCode: true` (should be `false`)

**Solutions:**
- Verify `pathMappings` in `launch.json`
- Use "Attach Only" and manually execute script
- Ensure `justMyCode: false` in `launch.json`

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

### VSCode tasks not found

**Cause:** `.vscode/tasks.json` not configured

**Solution:**
```bash
# Run setup-vscode.py to generate proper configuration
python3 scripts/setup-vscode.py
```

## Common Use Cases

### Case 1: Asset Batch Processing

Process multiple assets with debugging support:

```python
# batch_process_assets.py
import unreal

asset_paths = ["/Game/Assets/Asset1", "/Game/Assets/Asset2"]

for path in asset_paths:
    asset = unreal.EditorAssetLibrary.load_asset(path)
    # Set breakpoint here to inspect each asset
    process_asset(asset)
```

Execute with debugging: **Press F5** in VSCode

### Case 2: Editor Automation

Automate editor workflows without debugging:

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

### Case 4: Interactive Development

Rapid iteration with auto-reload:

1. Edit Python file
2. Press F5 to execute in UE5 with debugging
3. Fix issues and repeat

## Integration with Other Tools

### CI/CD Integration

```yaml
# .github/workflows/ue5-validation.yml
- name: Validate UE5 Assets
  env:
    CLAUDE_PROJECT_DIR: ${{ github.workspace }}
  run: |
    # Scripts auto-detect project from CLAUDE_PROJECT_DIR
    python3 skills/remote-exec-and-debug/scripts/check-config.py --json
    python3 skills/remote-exec-and-debug/scripts/remote-execute.py \
      --file validation/check_assets.py \
      --timeout 120
```

### Custom VSCode Tasks

After running `setup-vscode.py`, customize or add tasks to `.vscode/tasks.json`:

```json
{
  "label": "UE5: Run Tests",
  "type": "shell",
  "command": "python3",
  "args": [
    "/absolute/path/to/plugin/skills/remote-exec-and-debug/scripts/remote-execute.py",
    "--file",
    "${workspaceFolder}/tests/run_all_tests.py"
  ],
  "problemMatcher": []
}
```

**Note:** Use the absolute path generated by `setup-vscode.py` for reliability across different environments.

## Best Practices

1. **Always verify configuration** before first use: `check-config.py --check-only`

2. **Use project name filtering** when multiple UE5 instances are running

3. **Set appropriate timeouts** for long-running scripts

4. **Use detached mode** for background tasks that don't need immediate results

5. **Restart UE5 Editor** after configuration changes

6. **Keep debug server running** during active development to avoid setup overhead

7. **Use path mappings carefully** to ensure breakpoints work correctly
