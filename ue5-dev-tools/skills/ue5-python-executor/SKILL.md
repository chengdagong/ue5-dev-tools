---
name: ue5-python-executor
description: Setup python support for UE5.x projects, execute Python scripts in UE5 editor instances. Use when users need to (1) run UE5.x python scripts (2) enable UE5 Python plugin and remote execution, (3) execute Python scripts in running UE5 editor with auto-launch capability, (4) verify UE5 project Python configuration
model: haiku
---

# UE5 Python Executor

Setup python support for UE5.x projects

Execute Python scripts and code in running Unreal Engine 5 editor instances via socket-based remote execution protocol. Supports automatic editor launching and configuration fixing.

## Quick Start

### Setup UE5 Project for Python Remote Execution

Enable Python plugin and remote execution in a UE5 project:

```bash
# Auto-detects project from CLAUDE_PROJECT_DIR (when run via Claude Code)
python scripts/check-config.py --auto-fix

# Or specify project path explicitly
python scripts/check-config.py --project /path/to/ue5/project --auto-fix
```

This automatically:

- Enables `PythonScriptPlugin` in `.uproject`
- Configures `bRemoteExecution=True` in `DefaultEngine.ini`
- Sets `bDeveloperMode=True` for development
- Configures multicast bind address

**Note:** `remote-execute.py` will also perform these checks and fixes automatically if it needs to launch the editor.

### Execute Python Scripts

Run Python scripts in a running UE5 instance (or auto-launch one):

```bash
# Auto-detects project name from CLAUDE_PROJECT_DIR
python scripts/remote-execute.py --file script.py

# Execute by project name
python scripts/remote-execute.py --file script.py --project-name MyProject

# Execute by project path (Recommended for auto-launch)
python scripts/remote-execute.py --file script.py --project-path /path/to/project.uproject

# Execute inline code
python scripts/remote-execute.py --code "import unreal; print('Hello UE5')"
```

## Core Workflows

### Workflow 1: Zero-Config Execution

For new or unconfigured projects:

1. **Run execution command directly:**

   ```bash
   python scripts/remote-execute.py --code "print('Hello')" --project-path /path/to/project.uproject
   ```

2. **The script will automatically:**
   - Detect that UE5 is not running.
   - Check and fix project configuration (enable plugin, set INI vars).
   - Launch `UnrealEditor.exe` with the project.
   - Wait for the editor to initialize.
   - Connect and execute the code.

### Workflow 2: Executing Scripts Without Debugging

For quick script execution:

```bash
# Execute specific file
python scripts/remote-execute.py \
  --file /path/to/script.py \
  --project-name MyProject \
  --timeout 10.0

# Execute with detached mode (fire and forget)
python scripts/remote-execute.py \
  --file script.py \
  --project-name MyProject \
  --detached

# Execute after delay (useful for timing-sensitive operations)
python scripts/remote-execute.py \
  --file script.py \
  --project-name MyProject \
  --wait 2.0
```

### Workflow 3: Verifying Configuration

Check if a project is correctly configured without making changes:

```bash
# Check only (auto-detects project)
python scripts/check-config.py --check-only

# Get JSON output for programmatic use
python scripts/check-config.py --json

# Check specific project
python scripts/check-config.py --project /path/to/ue5/project --check-only
```

## Bundled Tools

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
# Check current project (auto-detects project)
python scripts/check-config.py --check-only

# Auto-fix current project
python scripts/check-config.py --auto-fix

# Check specific project
python scripts/check-config.py --project /path/to/project --check-only
```

**Environment variables:**

- `CLAUDE_PROJECT_DIR` - Project root (auto-injected by Claude Code)

**Exit codes:**

- `0` - Configuration correct
- `1` - Error (e.g., no .uproject found)
- `2` - Configuration needs fixing

### remote-execute.py

Executes Python code or files in running UE5 instances using socket-based remote execution. Auto-launches editor if needed.

**Key features:**

- **Auto-Launch:** Locates and starts UE5 Editor if not running
- **Auto-Config:** Fixes project settings before auto-launch
- Auto-detects project name from `CLAUDE_PROJECT_DIR`
- Multicast discovery of UE5 instances
- Project name or path filtering
- Supports both code strings and file execution
- Detached mode for fire-and-forget execution

**Parameters:**

- `--code` - Python code string to execute
- `--file` - Python file to execute
- `--project-name` - Filter by project name (default: auto-detect from `CLAUDE_PROJECT_DIR`)
- `--project-path` - Filter by .uproject path (Required for reliable auto-launch)
- `--multicast-group` - Custom multicast address (default: 239.0.0.1:6766)
- `--timeout` - Command execution timeout (default: 5.0s)
- `--detached` - Run in background and exit immediately
- `--wait` - Delay before execution (useful with detached mode)
- `--no-launch` - Disable auto-launch behavior
- `-v, --verbose` - Enable debug logging

**Usage examples:**

```bash
# Execute file (auto-detects project, auto-launches if needed)
python scripts/remote-execute.py --file script.py --project-path /full/path/to/Project.uproject

# Execute with explicit project name (requires running instance)
python scripts/remote-execute.py --file script.py --project-name MyProject

# Explicitly prevent auto-launch
python scripts/remote-execute.py --file script.py --no-launch
```

**Environment variables:**

- `CLAUDE_PROJECT_DIR` - Project root, used to infer project name (auto-injected by Claude Code)

## Environment Variables

This skill uses Claude Code's auto-injected environment variables for seamless integration:

### CLAUDE_PROJECT_DIR

Auto-injected by Claude Code, pointing to the current project root.

**Used by:**

- `ue5_remote.config` - Auto-detects UE5 project location
- `remote-execute.py` - Infers project name/path from directory

**Example:**

```bash
# When CLAUDE_PROJECT_DIR=/Users/me/MyUE5Game
# These commands work without --project argument:
python scripts/check-config.py --auto-fix
python scripts/remote-execute.py --file script.py
```

### Fallback Behavior

When environment variables are not set (e.g., running scripts directly outside Claude Code):

1. **CLAUDE_PROJECT_DIR fallback:** Current working directory (`cwd`)

**Manual usage example:**

```bash
cd /path/to/ue5/project
python /path/to/plugin/skills/ue5-python-executor/scripts/remote-execute.py --file script.py
```

## Technical Details

### Remote Execution Protocol

The skill uses UE5's socket-based Python remote execution protocol:

1. **Discovery:** Multicast UDP ping/pong on `239.0.0.1:6766`
2. **Connection:** TCP connection on dynamically allocated port
3. **Execution:** JSON messages with commands
4. **Response:** JSON messages with results

### Project Requirements

**UE5 Configuration (Auto-handled by tools):**

- `PythonScriptPlugin` enabled in `.uproject`
- `bRemoteExecution=True` in `DefaultEngine.ini`
- `bDeveloperMode=True` in `DefaultEngine.ini`
- `RemoteExecutionMulticastBindAddress=0.0.0.0` in `DefaultEngine.ini`

**Python Requirements:**

- Python 3.x

## Troubleshooting

### "No UE5 instance found"

**Causes:**

- UE5 Editor not running and auto-launch disabled/failed
- Remote execution not enabled (and auto-fix failed)
- Firewall blocking multicast
- Wrong project name/path filter

**Solutions:**

```bash
# Verify configuration
python scripts/check-config.py --project /path/to/project

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
python scripts/remote-execute.py --file script.py --project-name MyProject --timeout 30.0

# Use detached mode for long scripts
python scripts/remote-execute.py --file script.py --project-name MyProject --detached
```

## Instance Discovery Behavior

When executing scripts, the tool discovers and connects to UE5 instances:

### Multiple Instances Running

If multiple UE5 editors are running, the script will show all discovered instances and select one:

```bash
# Without filter - shows all instances
python scripts/remote-execute.py --code "print('test')"
```

Output:
```
[INFO] Searching for UE5 instances...
[INFO] Discovered 3 UE5 instance(s):
[INFO]   1. MyProject (UE 5.4.0) [node: ue5_abc123]
[INFO]   2. OtherProject (UE 5.4.0) [node: ue5_xyz789]
[INFO]   3. TestProject (UE 5.3.2) [node: ue5_def456]
[WARNING] 3 instances discovered, selected first match
[INFO] Connecting to: MyProject (UE 5.4.0) [node: ue5_abc123]
```

### Filter by Project Name

To select a specific project when multiple editors are running:

```bash
python scripts/remote-execute.py --file script.py --project-name MyProject
```

Output:
```
[INFO] Searching for UE5 instances...
[INFO] Filter: project_name='MyProject'
[INFO] Discovered 3 UE5 instance(s):
[INFO]   1. MyProject (UE 5.4.0) [node: ue5_abc123]
[INFO]   2. OtherProject (UE 5.4.0) [node: ue5_xyz789]
[INFO]   3. TestProject (UE 5.3.2) [node: ue5_def456]
[INFO] Connecting to: MyProject (UE 5.4.0) [node: ue5_abc123]
```

## Troubleshooting

### "No UE5 instances discovered on network"

**Possible causes:**
- UE5 editor is not running
- Python plugin is not enabled
- Remote execution is not configured
- Firewall blocking multicast (239.0.0.1:6766)

**Solutions:**
1. Ensure UE5 editor is running
2. Run check-config to enable plugin and remote execution
3. Check firewall settings for multicast UDP on port 6766

### "Could not determine project name"

**Cause:** Script couldn't find a project name through any method

**Solutions:**
- Specify `--project-name <name>` explicitly
- Specify `--project-path /path/to/project.uproject` for auto-launch
- Run from a directory containing a `.uproject` file

### Multiple instances match filter

When multiple instances of the same project are running, the first discovered instance is selected. Check the log output to see which was selected.
