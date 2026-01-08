---
description: Query detailed information about UE5 APIs
---

# /check-api

Query detailed information about a specified UE5 class or method, including parameter constraints, deprecation status, usage examples, etc.

## Usage

```
/check-api unreal.<ClassName>
/check-api unreal.<ClassName>.<method_name>
/check-api unreal.<function_name>
```

**Important Notes:**
- **Must start with `unreal.`**
- **Must use exact class or method names** (e.g., `unreal.Actor`, `unreal.Actor.set_actor_location`)
- **Format requirement**: Only accepts `unreal.<name>` or `unreal.<ClassName>.<member_name>` format
- **Supports module-level function queries** (e.g., `unreal.log`, `unreal.log_warning`)

## Steps

1. Run the API query script:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/skills/api-validator/scripts/validate.py --query "$ARGUMENTS"
   ```

2. **Display the script's output directly**.

   > [!IMPORTANT]
   > Do not attempt to interpret, expand, or add additional API usage examples unless they are included in the script output.
   > Claude's internal knowledge may be inaccurate for UE5 Python APIs (many C++ APIs are not exposed to Python, e.g., `GameplayTagsManager`).
   > Only display the actual results returned by the tool.

## Examples

### Query Class Information
```
/check-api unreal.Actor
```

Output:
```
Query API: unreal.Actor
✅ Class Actor exists
Documentation: ...
```

### Query Method Information
```
/check-api unreal.Actor.set_actor_location
```

Output:
```
Query API: unreal.Actor.set_actor_location
✅ Actor.set_actor_location exists
Documentation: ...
```

### Query Module-Level Functions
```
/check-api unreal.log
```

Output:
```
Query API: unreal.log
✅ Function log exists
Documentation: ...
```
