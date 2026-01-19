---
name: ue5-python-executor
description: Execute Python scripts in UE5 editor using the UE-MCP server.
---

# UE5 Python Executor (via UE-MCP)

Execute Python scripts and code in running Unreal Engine 5 editor instances using the `ue-mcp` server.

## Overview

This skill utilizes the `ue-mcp` server to communicate with the Unreal Editor. It allows you to:
- Execute Python code directly in the editor (`editor.execute`).
- Launch the editor if it's not running (`editor.launch`).
- Check editor status (`editor.status`).

## Usage

### executing Scripts

To run a python script, read the file content and pass it to `editor.execute`.

```python
# Example of using editor.execute
result = editor.execute(code="print('Hello from UE5')")
```

### Tools

The `ue-mcp` server provides the following tools:

- **`editor.execute(code: str) -> str`**: Executes Python code in the UE5 editor. Returns the output.
- **`editor.launch()`**: Launches the UE5 editor for the current project.
- **`editor.status()`**: Checks if the editor is running and connected.
- **`editor.configure()`**: Checks and fixes the UE5 project configuration for remote execution.

## Workflow

1.  **Check Status**: Use `editor.status()` to see if UE5 is running.
2.  **Launch (if needed)**: If not running, use `editor.launch()`.
3.  **Execute**: Use `editor.execute(code=...)` to run your scripts.

## Troubleshooting

- If `editor.execute` fails because the editor is not running, try `editor.launch()`.
- If connection fails, ensure the project has `PythonScriptPlugin` enabled and `bRemoteExecution=True` (the `editor.configure()` tool can help with this).
