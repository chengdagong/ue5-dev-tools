---
name: api-validator
description: Validate UE5 Python scripts for correctness, check for deprecated APIs, and verify parameter constraints.
---

# UE5 API Validator

Query class or function definitions from UE5 unreal.py stub files.

## Usage

```bash
# Query a class definition
python scripts/api-search.py unreal.InputMappingContext

# Query a module-level function
python scripts/api-search.py unreal.log

# Specify stub file explicitly
python scripts/api-search.py --input /path/to/unreal.py unreal.Actor
```

## Arguments

| Argument | Short | Required | Description |
|----------|-------|----------|-------------|
| `query` | | Yes | Query string (e.g., `unreal.ClassName` or `unreal.function_name`) |
| `--input` | `-i` | No | Path to unreal.py stub file. Auto-detects from `$CLAUDE_PROJECT_DIR/Intermediate/PythonStub/unreal.py` if not provided |

## Output

- **Class query**: Returns full class definition including docstring, properties, and methods
- **Function query**: Returns function signature and docstring
- **No match**: Exits with code 1 and prints error to stderr

## Examples

### Query a class
```bash
$ python scripts/api-search.py unreal.InputMappingContext

class InputMappingContext(DataAsset):
    r"""
    UInputMappingContext : A collection of key to action mappings...
    """
    ...
```

### Query a function
```bash
$ python scripts/api-search.py unreal.log

def log(arg: Any) -> None:
    r"""
    log(arg: Any) -> None -- log the given argument as information in the LogPython category
    """
    ...
```
