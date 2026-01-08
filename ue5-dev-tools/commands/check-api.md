---
description: Query UE5 class or function definitions
---

# /check-api

Query class or module-level function definitions from UE5 Python API.

## Usage

```
/check-api unreal.<ClassName>
/check-api unreal.<function_name>
```

**Important Notes:**
- **Must start with `unreal.`**
- **Must use exact class or function names** (e.g., `unreal.Actor`, `unreal.log`)
- **Supports class queries**: Returns full class definition including docstring, properties, and methods
- **Supports module-level function queries**: Returns function signature and docstring
- **Does NOT support**: Method queries (e.g., `unreal.Actor.set_actor_location`) - query the class instead to see its methods

## Steps

1. Run the API query script:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/skills/api-validator/scripts/api-search.py "$ARGUMENTS"
   ```

2. **Display the script's output directly**.

   > [!IMPORTANT]
   > Do not attempt to interpret, expand, or add additional API usage examples unless they are included in the script output.
   > Claude's internal knowledge may be inaccurate for UE5 Python APIs (many C++ APIs are not exposed to Python, e.g., `GameplayTagsManager`).
   > Only display the actual results returned by the tool.

## Examples

### Query Class Definition
```
/check-api unreal.InputMappingContext
```

Output includes class definition with docstring, properties, and methods.

### Query Module-Level Function
```
/check-api unreal.log
```

Output includes function signature and docstring.
