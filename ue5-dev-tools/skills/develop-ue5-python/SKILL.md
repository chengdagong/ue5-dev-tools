---
name: develop-ue5-python
description: Comprehensive guide for developing UE5 Editor Python scripts with proper workflow and best practices. Use when the user wants to (1) write a UE5 Python script, (2) mentions writing a script in a UE5 project context, or (3) has a requirement that Claude identifies can be fulfilled by a UE5 Python script (e.g., batch processing game assets, automating editor tasks).
hooks:
  PreToolUse:
    - python ${CLAUDE_SKILL_ROOT}/hooks/check_transaction.py
---

# UE5 Python Script Development Guide

A workflow-oriented guide for developing reliable UE5 Editor Python scripts, with emphasis on proper development cycles and common pitfalls.

## Development Workflow

Follow this 7-phase workflow when developing UE5 Python scripts:

### Phase 1: Requirements and Exploration

Understand the task before coding:
- Confirm script requirements
- Search for existing similar scripts
- Understand asset organization and naming conventions
- Review project-specific patterns


### Phase 2: API Validation and Exploration

Verify APIs exist before coding:
- Check if classes and methods are available in Python API
- Query class definitions using search-api
- Write exploratory scripts to validate approach

Use **ue5-api-expert** skill to query and explore available APIs.

Use **ue5-python-executor** skill to run exploratory scripts quickly without manual UE5 interaction.

### Phase 3: Write Formal Script

Implement complete logic with proper structure:
- Break script into logical functions
- Use proper error handling (let exceptions propagate)
- Always use transactions for asset modifications
- Log key milestones and results
- Track success/failure counts


### Phase 4: Validation and Testing

Verify script works correctly:
- Re-verify key APIs exist with search-api
- Test with single test asset first
- Then run on target assets
- Monitor console output and verify results


### Phase 5: Visual Confirmation

Verify visual results in-game when script affects:
- **Visual appearance** - materials, meshes, lighting, UI
- **Game behavior** - character movement, AI, game mechanics
- **Level/world state** - object placement, spawning, destruction

**Skip this phase** when changes are data-only, organizational (renaming, moving assets), or user explicitly requests to skip.

#### Screenshot Tool Usage

Use `take_game_screenshot.py` from ue5-dev-kit:

```bash
python "d:\Code\ue5-dev-tools\ue5-dev-tools\skills\ue5-dev-kit\take_game_screenshot.py" \
  -p "<path-to-uproject>" \
  -l "<level-name-only>" \
  -n 3 \
  -i 1.0 \
  -o "verification_screenshot" \
  -r "1280x720" \
  --timeout 20 \
  --load-timeout 20
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `-p` | Project file path | Required |
| `-l` | Level name (name only, no path) | Required |
| `-n` | Number of screenshots | 3 |
| `-i` | Interval between screenshots (seconds) | 1.0 |
| `-o` | Output filename prefix | `screenshot` |
| `-r` | Game resolution | `1280x720` |
| `--timeout` | Window wait timeout (seconds) | 20 |
| `--load-timeout` | Game load timeout (seconds) | 20 |

**Level parameter format:**
- Correct: `-l "MainMenu"` (name only)
- Wrong: `-l "/Game/Maps/MainMenu"` (includes path)
- Wrong: `-l "MainMenu.umap"` (includes extension)

#### Analyze Screenshots

1. **Read screenshots** - Use Read tool to view captured images
2. **Analyze visual content** - Check for expected changes, unexpected issues, visual artifacts
3. **Compare with requirements** - Do visual results match the original request?

#### Troubleshooting: Wrong Level Loaded

**Symptom**: Unexpected level loads instead of specified level

**Solution**:
- Level parameter must be name only (e.g., `"MainMenu"`)
- Do NOT include path separators (/, \)
- Do NOT include .umap extension

```bash
# Correct
-l "MyLevel"

# Wrong
-l "/Game/Maps/MyLevel"
-l "MyLevel.umap"
-l "MyLevel/"
```

#### Cleanup

**Very important**: Delete screenshot files for failed trails. Only keep successful ones. 

### Phase 6: Iteration and Fixing

When problems occur:
- Identify the problem from error messages
- Try alternative APIs if available
- Investigate C++ source if Python API is insufficient
- Consider custom C++ utility classes for bridging gaps
- Retry from Phase 4 after fixes


### Phase 7: Completion

Finalize and save script:
- Remove test mode flags
- Final verification on test asset
- Document script usage
- Save to appropriate project location


## Best Practices

### Core Interaction Patterns

#### 1. Use Subsystems Instead of Static Libraries

In UE4, we frequently used static function libraries such as `EditorAssetLibrary`. In UE5, Epic recommends using **Subsystems** - their lifecycle management is clearer and more aligned with object-oriented design.

- **Recommended:** `unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)`
- **Example:** Use `EditorActorSubsystem` instead of legacy LevelLibrary

```python
import unreal

# Recommended: Get subsystem instance
actor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
selected_actors = actor_subsystem.get_selected_level_actors()
```

#### 2. Must Handle Undo/Redo (Transaction Management)

If your script modifies the scene or assets without creating a Transaction, the user's `Ctrl+Z` will be ineffective. Always use `unreal.ScopedEditorTransaction`:

```python
# Wrap all modification operations in a with statement
with unreal.ScopedEditorTransaction("My Python Batch Rename"):
    for actor in selected_actors:
        actor.set_actor_label(f"Prefix_{actor.get_actor_label()}")
    # Users can now undo the entire loop's modifications with Ctrl+Z
```

#### 3. Use Asset Registry for Efficient Queries

Do not iterate through the Content directory and `load_asset` to find files - this is extremely slow. The **Asset Registry** is an in-memory database that stores metadata without loading files.

```python
asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

# Set up filter to find specific assets
filter = unreal.ARFilter(
    class_names=["MaterialInstanceConstant"],
    recursive_paths=True,
    package_paths=["/Game/Characters"]
)

# Get only metadata (AssetData) without loading actual assets
asset_data_list = asset_registry.get_assets(filter)

for data in asset_data_list:
    print(data.package_name)  # Extremely fast
    # Only load the asset when modification is necessary
    # asset = data.get_asset()
```

#### 4. Asset Loading vs Finding

Choose the right method for your use case:

- **`load_asset(path)`** - Load asset into memory for processing (slow)
- **`find_asset(path)`** - Quick check if asset exists (fast)
- **`list_assets(directory)`** - List asset paths without loading (fast)

Recommended workflow:
1. Use `list_assets()` to get paths
2. Use `find_asset()` to verify existence if needed
3. Only `load_asset()` when you need to modify the asset

### Additional Best Practices

5. **Verify APIs before coding** - Use search-api in Phase 2 and Phase 4
6. **Progressive testing** - Test exploratory scripts first, then single asset, then full set
7. **Don't over-handle errors** - Let exceptions propagate; fail loudly not silently
8. **Investigate C++ source when stuck** - Python API is derived from C++; C++ is the ground truth
9. **Consider C++ utilities** - Valid solution when Python API is insufficient
10. **Report results clearly** - Track success/failure counts; log meaningful progress
11. **Verify visual results** - Use Phase 5 screenshot verification for visual/gameplay changes
12. **Use ASCII-only output** - For cross-platform compatibility, use `[OK]`, `[ERROR]` instead of emojis

## Additional Resources

For comprehensive guidance on specific aspects of UE5 Python development:

- **workflow-details.md** - Detailed step-by-step workflow for each development phase
- **cpp-source-investigation.md** - Guide for investigating C++ source code when Python API is insufficient
