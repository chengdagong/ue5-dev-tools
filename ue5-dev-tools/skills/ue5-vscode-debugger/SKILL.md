---
name: ue5-vscode-debugger
description: Setup VSCode for F5 Python debugging in UE5 editor. Use when users need to (1) configure VSCode for UE5 Python debugging, (2) setup debugpy remote debugging workflow, (3) enable breakpoint debugging in UE5 Python scripts, or (4) create VSCode launch/task configurations for UE5.
---

# UE5 VSCode Debugger

Configure VSCode for F5 debugging of Python scripts running in Unreal Engine 5 editor via debugpy remote debugging.

## Dependencies

**Required Skill**: [ue5-python-executor](../ue5-python-executor/SKILL.md)

This skill depends on ue5-python-executor for:
- UE5 Python plugin configuration verification
- Remote script execution to start debugpy server
- Shared library for path resolution utilities

Ensure ue5-python-executor skill is installed before using this skill.

## Quick Start

### Setup VSCode for UE5 Debugging

Configure VSCode with debugging launch and task configurations:

```bash
# Auto-detects project from CLAUDE_PROJECT_DIR
python scripts/setup-vscode.py

# Or specify project path explicitly
python scripts/setup-vscode.py --project /path/to/ue5/project

# Force overwrite existing configurations
python scripts/setup-vscode.py --force
```

This automatically creates:
- `.vscode/launch.json` - Debug configurations for attaching to UE5
- `.vscode/tasks.json` - Tasks for starting debugpy server and executing scripts

**Note:** Requires debugpy installed in UE5's Python environment.

### Start Debugging

1. Open any Python file in VSCode
2. Press **F5** (or Run → Start Debugging)
3. Select **"UE5 Python: Debug Current File"**
4. VSCode will:
   - Start debugpy server in UE5 editor (port 19678)
   - Execute your Python file in UE5
   - Attach debugger and hit breakpoints

## Core Workflows

### Workflow 1: First-Time VSCode Setup

For new UE5 projects that need VSCode debugging:

1. **Ensure ue5-python-executor is configured:**
   ```bash
   # From ue5-python-executor skill
   python ../ue5-python-executor/scripts/check-config.py --auto-fix
   ```

2. **Setup VSCode configurations:**
   ```bash
   python scripts/setup-vscode.py
   ```

3. **Install debugpy in UE5's Python:**
   - Open UE5 Editor
   - Execute via ue5-python-executor:
     ```bash
     python ../ue5-python-executor/scripts/remote-execute.py \
       --code "import subprocess; subprocess.run(['pip', 'install', 'debugpy'])"
     ```

4. **Test debugging:**
   - Open a Python file in VSCode
   - Set a breakpoint
   - Press F5

### Workflow 2: Using F5 Debugging

For interactive Python development with breakpoints:

1. **Open Python file** in VSCode
2. **Set breakpoints** by clicking left of line numbers
3. **Press F5** to start debugging:
   - Task "ue5-start-debug-server" starts debugpy in UE5
   - Task "ue5-execute-python" sends your file to UE5
   - Debugger attaches and pauses at breakpoints
4. **Use debugging controls**: Step over, step into, inspect variables

### Workflow 3: Attach-Only Debugging

For debugging already-running debugpy servers:

1. **Manually start debugpy server** in UE5:
   ```bash
   python ../ue5-python-executor/scripts/remote-execute.py \
     --file scripts/start_debug_server.py
   ```

2. **In VSCode**, select **"UE5 Python: Attach Only"** configuration
3. **Press F5** - debugger attaches without executing a script

## Bundled Scripts

### setup-vscode.py

Generates VSCode debugging configurations for UE5 Python.

**Key features:**
- Auto-detects project from `CLAUDE_PROJECT_DIR`
- Auto-detects plugin root from `CLAUDE_PLUGIN_ROOT`
- Creates launch.json with debugpy attach configurations
- Creates tasks.json with debugpy server startup and script execution
- Merges with existing configurations to preserve user customizations
- References ue5-python-executor's remote-execute.py for execution

**Usage examples:**

```bash
# Setup current project (auto-detected)
python scripts/setup-vscode.py

# Setup specific project
python scripts/setup-vscode.py --project /path/to/ue5/project

# Force overwrite existing configurations
python scripts/setup-vscode.py --force
```

**Environment variables:**
- `CLAUDE_PROJECT_DIR` - Project root (auto-injected by Claude Code)
- `CLAUDE_PLUGIN_ROOT` - Plugin root (auto-injected by Claude Code)

**Generated Configurations:**

**launch.json:**
- **"UE5 Python: Debug Current File"** - Starts debugpy and executes current file
- **"UE5 Python: Attach Only"** - Attaches to existing debugpy server

**tasks.json:**
- **"ue5-start-debug-server"** - Starts debugpy server in UE5 (via remote-execute.py)
- **"ue5-execute-python"** - Executes current file in UE5 (detached mode)
- **"ue5-start-debug-and-execute"** - Sequential combination of above tasks

### start_debug_server.py

Python script executed in UE5 editor to start debugpy remote debugging server.

**Key features:**
- Starts debugpy server on port 19678
- Waits for debugger attachment
- Outputs structured logging for VSCode task matcher

**Execution:**
```bash
# Via ue5-python-executor
python ../ue5-python-executor/scripts/remote-execute.py \
  --file scripts/start_debug_server.py
```

**Output format:**
```
[UE5-DEBUG] Starting debug server setup
[UE5-DEBUG] debugpy server listening on 127.0.0.1:19678
[UE5-DEBUG] Waiting for debugger attachment...
[UE5-DEBUG] READY
```

## VSCode Configuration

### Debug Port

- **Default Port:** 19678
- **Protocol:** debugpy (Debug Adapter Protocol)
- **Connection:** localhost attachment

**To change port:**
1. Edit `scripts/start_debug_server.py` (modify port number)
2. Edit `.vscode/launch.json` (update "port" field in configurations)

### Path Mappings

By default, local and remote paths are identical:
```json
"pathMappings": [
  {
    "localRoot": "${workspaceFolder}",
    "remoteRoot": "${workspaceFolder}"
  }
]
```

**When to customize:**
- UE5 Python scripts are in different location than VSCode workspace
- Using symbolic links or mounted directories
- Network path differences

## Environment Variables

This skill leverages Claude Code environment variables for seamless integration:

### CLAUDE_PROJECT_DIR

Auto-injected by Claude Code, pointing to the current project root.

**Used by:**
- `setup-vscode.py` - Auto-detects project location for VSCode config generation

**Example:**
```bash
# When CLAUDE_PROJECT_DIR=/Users/me/MyUE5Game
python scripts/setup-vscode.py
# Creates .vscode/ in /Users/me/MyUE5Game
```

### CLAUDE_PLUGIN_ROOT

Auto-injected by Claude Code, pointing to the plugin root directory.

**Used by:**
- `setup-vscode.py` - Locates executor skill's scripts for task configuration

**Fallback:**
- Script location inference (assumes `skills/ue5-vscode-debugger/scripts/setup-vscode.py`)

## Technical Details

### Debug Protocol

Uses debugpy (Python's Debug Adapter Protocol implementation):

1. **Server Start:** `start_debug_server.py` runs in UE5, starts debugpy on port 19678
2. **Debugger Attach:** VSCode debugpy extension connects to port 19678
3. **Breakpoint Sync:** VSCode sends breakpoints to debugpy server
4. **Script Execution:** UE5 executes Python, pauses at breakpoints
5. **Interactive Debugging:** Step through code, inspect variables

### Requirements

**VSCode Extensions:**
- Python extension (ms-python.python)
- Debugpy support (included in Python extension)

**Python Packages in UE5:**
- `debugpy` - Install via pip in UE5's Python environment

**UE5 Configuration:**
- Python plugin enabled (handled by ue5-python-executor)
- Remote execution enabled (handled by ue5-python-executor)

## Troubleshooting

### "Failed to attach to debugpy"

**Causes:**
- debugpy not installed in UE5's Python
- debugpy server not running
- Port 19678 already in use
- Firewall blocking localhost connections

**Solutions:**
```bash
# Install debugpy in UE5
python ../ue5-python-executor/scripts/remote-execute.py \
  --code "import subprocess; subprocess.run(['pip', 'install', 'debugpy'])"

# Verify debugpy server starts
python ../ue5-python-executor/scripts/remote-execute.py \
  --file scripts/start_debug_server.py

# Check port availability
lsof -i :19678
```

### Breakpoints not hitting

**Causes:**
- Path mappings incorrect
- Code not executing (execution bypassed)
- Debugger attached after code execution

**Solutions:**
- Verify `localRoot` and `remoteRoot` in launch.json match actual paths
- Use "UE5 Python: Debug Current File" to ensure execution
- Check debugpy server logs for attachment confirmation

### "Task ue5-start-debug-server failed"

**Causes:**
- ue5-python-executor skill not found
- UE5 editor not running
- Remote execution not configured

**Solutions:**
```bash
# Verify ue5-python-executor installed
ls ../ue5-python-executor/scripts/remote-execute.py

# Check UE5 configuration
python ../ue5-python-executor/scripts/check-config.py --check-only

# Test remote execution
python ../ue5-python-executor/scripts/remote-execute.py \
  --code "print('test')"
```

## Common Use Cases

### Case 1: Interactive Script Development

Develop complex UE5 Python scripts with full debugging:

```bash
# Setup VSCode once
python scripts/setup-vscode.py

# Then develop iteratively:
# 1. Edit Python file
# 2. Set breakpoints
# 3. Press F5
# 4. Inspect variables, step through logic
# 5. Fix issues and repeat
```

### Case 2: Debugging Asset Processing

Debug complex asset processing logic:

```python
# process_assets.py
import unreal

def process_asset(asset_path):
    # Set breakpoint here to inspect asset
    asset = unreal.load_asset(asset_path)

    # Step through processing
    # Inspect asset properties in VSCode
    pass

# Press F5 to debug
process_asset("/Game/MyAsset")
```

### Case 3: Editor Automation Debugging

Debug editor automation workflows:

```python
# automation.py
import unreal

def generate_thumbnails():
    # Breakpoint to verify editor state
    editor_lib = unreal.EditorLevelLibrary()

    # Step through automation
    # Watch variables in VSCode
    pass

# F5 debug to verify each step
```

## Integration with Other Tools

### Custom VSCode Tasks

Extend tasks.json for project-specific workflows:

```json
{
  "label": "ue5-run-tests",
  "type": "shell",
  "command": "python",
  "args": [
    "${env:CLAUDE_PLUGIN_ROOT}/skills/ue5-python-executor/scripts/remote-execute.py",
    "--file",
    "${workspaceFolder}/tests/run_all.py"
  ]
}
```

### Multiple Debug Configurations

Add custom debug configurations to launch.json:

```json
{
  "name": "UE5 Python: Debug Tests",
  "type": "debugpy",
  "request": "attach",
  "connect": {
    "host": "127.0.0.1",
    "port": 19678
  },
  "preLaunchTask": "ue5-run-tests"
}
```

## Best Practices

1. **Use F5 debugging for complex logic** - Breakpoints and variable inspection save time

2. **Start debugpy server manually for long sessions** - Use "Attach Only" to reconnect

3. **Verify debugpy installation** before first debugging session

4. **Keep VSCode workspace at UE5 project root** for correct path mappings

5. **Use structured logging** in production scripts, F5 debugging for development

## Related Skills

- **ue5-python-executor**: Remote Python script execution (required dependency)
