---
name: develop-ue5-python
description: Comprehensive guide for developing UE5 Editor Python scripts with proper workflow and best practices. Use when the user wants to (1) write a UE5 Python script, (2) mentions writing a script in a UE5 project context, or (3) has a requirement that Claude identifies can be fulfilled by a UE5 Python script (e.g., batch processing game assets, automating editor tasks).
---
# UE5 Python Script Development Guide

A workflow-oriented guide for developing reliable UE5 Editor Python scripts, with emphasis on proper development cycles and common pitfalls.

## Development Workflow

Follow this 6-phase workflow when developing UE5 Python scripts:

### Phase 1: Start - Requirements and Exploration

**Both steps required:**

#### a) Requirement Analysis

- Confirm the requirement of this script

#### b) Project Structure Exploration

- Refer to [example scripts](./examples/) for reference implementations
- Search for existing similar scripts in the project
- Understand asset organization and naming conventions
- Check for existing utility functions or helper modules
- Review project-specific patterns and conventions

**Example:**

```
User request: "Batch set montages for all melee abilities"

Analysis:
- Task: Set Animation Montage property on Gameplay Ability assets
- Scope: Filter assets by "melee" tag or naming pattern
- Location: Likely in /Game/Abilities/Melee/ directory
- Check: Are there existing batch processing scripts?
```

### Phase 2: Preparation - API Validation and Exploration

**Both steps required:**

#### a) Use check-api Skill

Before writing code, verify APIs exist and understand their usage:

```bash
# Query class definitions
Use check-api skill to query:
- unreal.GameplayAbility
- unreal.EditorAssetLibrary
- unreal.AnimMontage
```

Verify:

- Classes exist in Python API
- Available methods and properties (from class definition output)
- Return types from docstrings

**Note**: check-api supports class and module-level function queries only. To check a method, query the class and look for the method in the output.

#### b) Write Exploratory Scripts

Use **ue5-python-executor** skill for rapid iteration in an open UE5 Editor:

```python
# exploratory_test.py - Quick validation script
import unreal

# Test 1: Can we access target assets?
abilities = unreal.EditorAssetLibrary.list_assets("/Game/Abilities/Melee")
unreal.log(f"Found {len(abilities)} assets")

# Test 2: Can we load and inspect them?
if abilities:
    asset = unreal.EditorAssetLibrary.load_asset(abilities[0])
    unreal.log(f"Loaded: {asset}, Type: {type(asset)}")

# Test 3: Can we access the property we need to set?
if hasattr(asset, 'montage'):
    unreal.log(f"Current montage: {asset.montage}")
```

Execute with ue5-python-executor to verify approach works before writing formal script.

### Phase 3: Write Formal Script

Now implement the complete logic with proper structure.

#### Code Quality Guidelines

**Modularization**

- Break script into logical functions
- Separate concerns: asset discovery, filtering, processing, reporting
- Keep functions focused and testable

**Error Handling Philosophy**

- **Don't over-handle errors** - let exceptions propagate
- Avoid hiding important errors with generic try-except blocks
- Only catch specific exceptions when you can meaningfully handle them
- Let UE5 and Python error messages surface naturally

**Why?** Over-handling errors can mask bugs. Better to fail loudly than succeed silently with wrong behavior.

```python
# BAD - Hides all errors
try:
    asset.set_editor_property("montage", montage)
except:
    pass  # Silent failure - user has no idea what went wrong

# GOOD - Let exceptions propagate
asset.set_editor_property("montage", montage)  # Will raise clear error if fails
```

**Logging**

- Use `unreal.log()` for basic progress tracking
- Log key milestones: start, major steps, completion
- Log summary statistics

```python
unreal.log(f"Processing {len(assets)} assets...")
unreal.log(f"Completed: {success_count} succeeded, {fail_count} failed")
```

**Transactions for Asset Operations**

- **Always use transactions when modifying assets**
- Enables automatic rollback on failure
- Provides undo functionality in editor

```python
with unreal.ScopedEditorTransaction("Batch Set Montages") as trans:
    for asset in assets:
        asset.set_editor_property("montage", target_montage)
        unreal.EditorAssetLibrary.save_loaded_asset(asset)
```

**Result Reporting**

- Track success/failure counts
- Report which assets succeeded/failed
- Provide actionable summary

```python
results = {"success": [], "failed": []}

for asset_path in asset_paths:
    try:
        # ... process asset ...
        results["success"].append(asset_path)
    except Exception as e:
        results["failed"].append((asset_path, str(e)))

unreal.log(f"Success: {len(results['success'])}, Failed: {len(results['failed'])}")
for path, error in results["failed"]:
    unreal.log_warning(f"Failed {path}: {error}")
```

### Phase 4: Validation and Testing

#### a) API Verification with check-api

Before testing, verify key APIs used in your script:

```bash
# Query classes used in your script
Use check-api skill to verify:
- Main classes your script depends on
- Module-level functions like unreal.log
```

This helps catch:

- Non-existent classes
- Misspelled class names

#### b) Dynamic Testing with Progressive Approach

Use **ue5-python-executor** skill:

1. **First: Single test asset**

   - Create or identify a test asset
   - Run script on just this one asset
   - Verify behavior is correct
   - Inspect asset manually in editor
2. **Then: Target assets**

   - After single-asset test passes, run on real target assets
   - Monitor console output during execution
   - Verify results

```python
# Add a test mode to your script
TEST_MODE = True  # Set to False for production run

if TEST_MODE:
    # Process only first asset
    assets_to_process = assets[:1]
    unreal.log_warning("TEST MODE: Processing only 1 asset")
else:
    assets_to_process = assets
```

### Phase 5: Iteration and Fixing

When problems occur, follow this systematic approach:

#### Step 1: Identify the Problem

- Review error messages from testing
- Check if the error is due to API misuse, missing class, wrong parameters, etc.
- If yes, think about other possible APIs or methods to achieve the same goal
- If alternative methods could be found, go back to Phase 1 and start over again
- If alternatives are exhausted, proceed to Step 2

#### Step 2: Deep Dive into C++ Source if needed

After exhausting Python API options, investigate C++ source code. This is crucial.

**Why?** UE5 Python API is generated from C++ via reflection. The C++ source is the ground truth.

You may find possible alternative methods, factory functions, or understand constructor visibility. For example, when you want to set gamplay tag for some asset, the intuitive way is to create a unreal.GameplayTag using its constructor, but it cannot be instantiated directly because its constructor is private. But if you look into C++ source code, C++ source reveals that you can use export_text and import_text of GameplayTagContainer to set gameplay tag, and these two methods are exposed to Python.

**Engine Source Locations:**

- **macOS**: `/Users/Shared/Epic Games/UE_5.X/Engine/Source`
- **Windows**: `C:\Program Files\Epic Games\UE_5.X\Engine\Source`
- **Linux**: `~/UnrealEngine/Engine/Source` (or custom install location)

**How to investigate:**

```bash
# Find C++ implementation
cd "/Users/Shared/Epic Games/UE_5.5/Engine/Source"

# Search for class definition
grep -r "class.*GameplayTag" --include="*.h"

# Search for method implementation
grep -r "RequestGameplayTag" --include="*.cpp"

# Look at the header file to understand:
# - Constructor signatures (public vs private)
# - Static factory methods
# - Parameter types and defaults
```

**Step 3: Custom C++ Utility Class Solution**

If C++ has easy APIs but Python lacks proper bindings:

**When to use:**

- C++ provides simple functions for a task
- Python API is missing or awkward
- Example: GameplayTag creation might have easy C++ helpers but limited Python access

**Solution:** Create a custom C++ utility class to expose functionality to Python

```cpp
// MyPythonUtils.h
UCLASS()
class UMyPythonUtils : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

    UFUNCTION(BlueprintCallable, Category="Python Utilities")
    static FGameplayTag CreateGameplayTag(FName TagName);
};

// MyPythonUtils.cpp
FGameplayTag UMyPythonUtils::CreateGameplayTag(FName TagName)
{
    // Use C++ API that works
    return FGameplayTag::RequestGameplayTag(TagName);
}
```

After compiling, this becomes available in Python:

```python
import unreal
tag = unreal.MyPythonUtils.create_gameplay_tag(unreal.Name("Ability.Melee"))
```

**This bridges the gap when Python API is insufficient.**

#### Retry Strategy

After fixing issues:

1. **Restart from Phase 4a** - Run validate-script again
2. Re-run dynamic testing on single test asset
3. Verify fix works before proceeding

#### Escalation Path

**After multiple failed attempts:**

- If you've tried 2-3 fixes and issues persist
- Suggest user manually debug using **ue5-vscode-debug** skill
- Provide clear description of:
  - What was attempted
  - What failed
  - Current hypothesis about the problem

### Phase 6: Completion

Once testing succeeds:

1. **Remove test mode flags** - Clean up debug code if any
2. **Final verification** - One more run on test asset
3. **Document usage** - Add docstring or comments explaining how to run the script
4. **Save to project** - Place in appropriate location (e.g., `Content/Python/` or project scripts folder)

## Common Pitfalls

### Pitfall 1: C++-Only APIs

**Problem:** Some UE5 features exist only in C++, not exposed to Python.

**Example:**

```python
# This will fail - GameplayTagManager is C++-only
import unreal
manager = unreal.GameplayTagManager.get()  # AttributeError: no such class
```

**Detection:**

- check-api will show "No match found" for non-existent classes
- Runtime AttributeError when trying to use

**Solutions:**

1. Use check-api to verify class exists
2. Check if there's a Python alternative API
3. Use Blueprint Function Library approach (expose via C++)
4. Inform user the feature isn't available in Python

### Pitfall 2: Private Constructors

**Problem:** Some classes have private constructors - you can't call `ClassName(args)`.

**Example:**

```python
# WRONG - Constructor is private
tag = unreal.GameplayTag(unreal.Name("Ability.Melee"))  # Fails at runtime

# Possible solutions (check API):
# Option 1: Use factory method
tag = unreal.GameplayTagContainer.create_gameplay_tag(unreal.Name("Ability.Melee"))

# Option 2: Request from tag manager
tag = unreal.GameplayTagsManager.request_gameplay_tag(unreal.Name("Ability.Melee"))

# Option 3: Custom C++ utility (see Phase 5, Step 3)
```

**Detection:**

- Runtime error when trying to instantiate
- C++ source investigation reveals private/public constructors

**Solution:**

1. Use check-api to find factory methods
2. Search C++ source for `static` factory methods
3. Create custom C++ utility class if needed

### Pitfall 3: Asset Path Formats

**Problem:** Confusion between UE5 asset paths and filesystem paths.

```python
# WRONG - Filesystem path
asset = unreal.EditorAssetLibrary.load_asset(
    "/Users/me/Project/Content/MyAsset.uasset"
)

# CORRECT - UE5 asset path
asset = unreal.EditorAssetLibrary.load_asset(
    "/Game/MyAsset"
)
```

**Asset path rules:**

- Start with `/Game/` for project content
- Start with `/Engine/` for engine content
- Start with `/PluginName/` for plugin content
- No file extension in path
- No `Content/` folder in path

### Pitfall 4: Forgetting to Save Assets

**Problem:** Modifications not persisted to disk.

```python
# Asset is modified in memory but not saved
asset.set_editor_property("montage", new_montage)

# CORRECT - Save the asset
asset.set_editor_property("montage", new_montage)
unreal.EditorAssetLibrary.save_loaded_asset(asset)
```

**Best practice:** Use transactions (see Phase 3) which handle saving automatically in many cases, but explicitly save when needed.

### Pitfall 5: Asset Loading vs Finding

**Difference:**

- `load_asset()` - Loads asset into memory (slow, use for processing)
- `find_asset()` - Checks if asset exists (fast, use for validation)
- `list_assets()` - Returns asset paths, doesn't load them

```python
# List doesn't load - just returns paths
asset_paths = unreal.EditorAssetLibrary.list_assets("/Game/Abilities")

# Must load each asset to inspect or modify
for path in asset_paths:
    asset = unreal.EditorAssetLibrary.load_asset(path)  # Now it's in memory
    # ... process asset ...
```

## Engine Source Investigation Reference

### When to Investigate C++ Source

Use this approach when:

- Python API exists but behaves unexpectedly
- Documentation is unclear
- Need to understand parameter constraints
- Looking for alternative methods
- Investigating constructor availability

### Quick Investigation Workflow

```bash
# 1. Navigate to Engine source
cd "/Users/Shared/Epic Games/UE_5.5/Engine/Source"

# 2. Find class header file
grep -r "class GAMEPLAYABILITIES_API UGameplayAbility" --include="*.h"

# 3. Read the header to understand:
#    - Public vs private members
#    - UFUNCTION declarations (exposed to Python/Blueprints)
#    - Parameter types and defaults
#    - Static factory methods

# 4. Find implementation details
grep -r "UGameplayAbility::MethodName" --include="*.cpp"
```

### Understanding UFUNCTION Macros

In C++ headers, look for these macros - they control Python exposure:

```cpp
// Exposed to Python and Blueprints
UFUNCTION(BlueprintCallable)
void MyMethod();

// Exposed to Blueprints (and usually Python)
UFUNCTION(BlueprintPure)
int32 GetValue() const;

// NOT exposed - won't be in Python API
void PrivateMethod();
```

## Related Skills

This skill orchestrates the following supporting skills:

### check-api (from api-validator skill)

**When to use:** Phase 2 and Phase 5

- Query class definitions before writing code
- Verify classes exist and see their available methods
- Re-check when encountering API errors

**Limitations:**

- Only supports class and module-level function queries
- To check a method, query the parent class

### ue5-python-executor

**When to use:** Phase 2b, Phase 4b

- Execute exploratory scripts during preparation
- Run formal scripts for testing
- Rapid iteration without manual UE5 interaction

### ue5-vscode-debug

**When to use:** Phase 5 escalation

- Manual debugging when automated fixes fail
- Step-through debugging of complex issues
- User-initiated deep investigation

## Best Practices Summary

1. **Always verify APIs before using**

   - Phase 2a: check-api before writing
   - Phase 4a: verify key classes with check-api
2. **Progressive testing approach**

   - Exploratory scripts first (Phase 2b)
   - Single test asset (Phase 4b)
   - Then full target set
3. **Use transactions for asset modifications**

   - Enables rollback on failure
   - Provides undo in editor
   - Safer for batch operations
4. **Don't over-handle errors**

   - Let exceptions propagate
   - Fail loudly rather than silently
   - Easier debugging
5. **Investigate C++ source when stuck**

   - Python API is derived from C++
   - C++ source is ground truth
   - Reveals private constructors, factory methods, alternatives
6. **Consider custom C++ utilities**

   - Valid solution when Python API is insufficient
   - Exposes C++ functionality cleanly
   - Better than awkward workarounds
7. **Report results clearly**

   - Track success/failure counts
   - Log meaningful progress
   - Provide actionable summaries

## Additional Resources

### Best Practices Reference

For comprehensive guidance on UE5 Python development patterns, see [best-practices.md](references/best-practices.md). Key topics include:

- Core interaction mechanisms (subsystems vs static libraries)
- Transaction management for undo/redo support
- Asset Registry usage for efficient queries
- And more proven patterns for production scripts

### Example Scripts

Reference implementations are available in [scripts/examples/](../../../scripts/examples/):

- `add_gameplaytag_to_asset.py` - Demonstrates batch asset modification with transactions, error handling, and verification
- Use these as templates for your own scripts
