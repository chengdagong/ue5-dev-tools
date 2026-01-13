---
name: develop-ue5-python
description: Comprehensive guide for developing UE5 Editor Python scripts with proper workflow and best practices. Use when the user wants to (1) write a UE5 Python script, (2) mentions writing a script in a UE5 project context, or (3) has a requirement that Claude identifies can be fulfilled by a UE5 Python script (e.g., batch processing game assets, automating editor tasks).
allowedTools:
  - tool: Read
    path: "${CLAUDE_PROJECT_DIR}/**"
  - tool: Write
    path: "${CLAUDE_PROJECT_DIR}/**"
  - tool: Edit
    path: "${CLAUDE_PROJECT_DIR}/**"
  - tool: Glob
    path: "${CLAUDE_PROJECT_DIR}/**"
  - tool: Grep
    path: "${CLAUDE_PROJECT_DIR}/**"
allowedPrompts:
  - tool: Bash
    prompt: "run python scripts in project directory"
  - tool: Bash
    prompt: "execute UE5 remote python scripts"
  - tool: Bash
    prompt: "take game screenshots"
  - tool: Bash
    prompt: "delete temporary files in project"
hooks:
  PreToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: |
            python -c "
            import sys, json, re
            try:
                data = json.load(sys.stdin)
                tool = data.get('tool_name', '')
                if tool not in ['Write', 'Edit']: sys.exit(0)
                fp = data.get('tool_input', {}).get('file_path', '')
                if not fp.endswith('.py'): sys.exit(0)
                content = data.get('tool_input', {}).get('content', '') if tool == 'Write' else ''
                if not content or 'import unreal' not in content: sys.exit(0)
                ops = [r'\.set_editor_property\(', r'.*save.*\(', r'\.set_editor_properties\(', r'\.modify\(']
                has_ops = any(re.search(p, content) for p in ops)
                if not has_ops: sys.exit(0)
                has_tx = bool(re.search(r'with\s+unreal\.ScopedEditorTransaction\s*\(', content) or re.search(r'unreal\.ScopedEditorTransaction\(', content))
                if not has_tx:
                    print(f'Transaction Check Failed: {fp}\n\nThis UE5 Python script modifies assets but does NOT use transactions.\n\nREQUIRED: Wrap in transaction:\n  with unreal.ScopedEditorTransaction(\"Desc\"):\n      asset.set_editor_property(...)\n\nWhy: Enables undo and rollback on failure.', file=sys.stderr)
                    sys.exit(2)
            except: pass
            "
  Stop:
    - matcher: "*"
      hooks:
        - type: prompt
          prompt: |
            Based on the conversation transcript, verify if all of the user's requirements have been fully completed:

            1. **Review all user requests** - Look at the initial request and any follow-up requirements
            2. **Check task completion**:
               - All requested scripts written and saved?
               - All scripts tested and verified working?
               - Visual verification done if needed (screenshots taken)?
               - All API validations passed?
               - All errors fixed and resolved?
               - All user questions answered?
            3. **Verify workflow phases**:
               - Phase 1 (Requirements): Clarified ✓
               - Phase 2 (Write Script): Completed ✓
               - Phase 3 (Validation & Testing): Completed ✓
               - Phase 4 (Visual Confirmation): Done if needed ✓
               - Phase 5 (Iteration/Fixing): All issues resolved ✓
               - Phase 7 (Completion): Finalized ✓

            Return ONLY valid JSON with this format:
            {
              "decision": "approve" or "block",
              "reason": "Brief explanation of what's complete or what remains"
            }

            **Decision rules:**
            - Return "approve" ONLY if all requirements are fully complete
            - Return "block" if any required task is incomplete, unverified, or outstanding
            - If uncertain, return "block" to ensure nothing is skipped

            **Important cleanup reminder:**
            - Delete all temporary *-cmd and *-cwd files from the project root
            - Delete all failed screenshot attempts - only keep successful verification screenshots
            - Verify no temporary files remain before final approval
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

Refert to exammple scripts for similar tasks in ue5-dev-tools repository.
- [Add gameplay tag to assets](./examples/add_gameplaytag_to_asset.py)
- [Create blendspace](./examples/create_footwork_blendspace.py)
- [Create level](./examples/create_sky_level.py)
- [Customize sky atmosphere, fog, lighting and creating meshes](./examples/create_dark_pyramid_level.py)

### Phase 2： Write Script

Use your best knowledge of UE5 Python API to write the script.

#### 2.1 Try to break the task into smaller sub-tasks to be implemented as separate scripts. Only make a plan. Do not implement yet.

Always ask your self:
- Can I break this down further?
- Can I test this smaller piece first?

Even if user asks for a "sigle script", or "a script", don't take it literally. Always Break down the task into smaller logical steps.

For example, if the task is "Create a new level with a blue sky, a pyramid and a humaned character looking at the pyramid", break it down into:
1. Write a script to create a new level with blue sky `create_sky_level.py`
2. Write a script to add a pyramid mesh `add_pyramid.py`
3. Write a script to add a humanoid character `add_humanoid_character.py`


#### 2.2 Implement each sub-task script one by one.

Start from the first sub-task script, implmement it fully. Follow the following phases for each script:

##### For every script: Phase 3: Validation and Testing

Verify script works correctly:
- Re-verify key APIs exist with search-api
- Test with single test asset first
- Then run on target assets
- Monitor console output and verify results


##### For every script: Phase 4: Visual Confirmation

Verify visual results in-game when script affects:
- **Visual appearance** - materials, meshes, lighting, UI
- **Game behavior** - character movement, AI, game mechanics
- **Level/world state** - object placement, spawning, destruction

**Skip this phase** when changes are data-only, organizational (renaming, moving assets), or user explicitly requests to skip.

**Phase 4.1 Screenshot Tool Usage**

Use `take_game_screenshot.py` from ue5-dev-kit:

```bash
python "d:\Code\ue5-dev-tools\ue5-dev-tools\skills\ue5-dev-kit\take_game_screenshot.py" \
  -p "<path-to-uproject>" \
  -l "NewLevelName" \
  -n 3 \
  -i 1.0 \
  -o "screenshots/new_level" \
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

**Phase 4.2 Analyze Screenshots**

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

#### For every script: Phase 6: Iteration and Fixing

When problems occur:
- Identify the problem from error messages
- Try alternative APIs if available
- Investigate C++ source if Python API is insufficient
- Consider custom C++ utility classes for bridging gaps
- Retry from Phase 4 after fixes


#### For every script: Phase 7: Completion

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
