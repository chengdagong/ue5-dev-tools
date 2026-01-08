---
description: Validates whether UE5 Python script API usage is correct
---

# /validate-script

Validates whether the specified Python script correctly uses UE5 API.

## Usage

```
/validate-script <script_path>
```

## Steps

1. Run the validation script:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/skills/api-validator/scripts/validate.py $ARGUMENTS
   ```

2. Analyze the validation report output

3. If errors or warnings are found:
   - For deprecated APIs: provide alternative suggestions
   - For non-existent APIs: suggest the correct API name
   - For parameter errors: explain the correct parameter types/ranges

## Example

```
/validate-script Content/Python/my_script.py
```

Output:
```
=== UE5 Python API Validation Report ===

Checking file: Content/Python/my_script.py

✅ Import check: import unreal - OK
✅ Class existence: unreal.Actor - OK
⚠️ Deprecated: set_actor_hidden_in_game (line 15)
   Reason: This method is deprecated
   Suggestion: Use set_hidden_in_game instead
❌ Error: Method 'get_location' does not exist (line 23)
   Suggestion: Did you mean 'get_actor_location'?

Total: 2 classes, 5 method calls
Errors: 1, Warnings: 1, Passed: 4
```
