---
name: ue5-python
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
            Examining $ARGUMENTS, verify if all of the user's requirements have been fully completed:

            1. **Review all user requests** - Look at the initial request and any follow-up requirements
            2. **Check task completion**:
               - All requested scripts written and saved?
               - All scripts tested and verified working?
               - Visual verification done if needed (screenshots taken)?
               - All API validations passed?
               - All errors fixed and resolved?
               - All user questions answered?
            3. **Final cleanup** - Delete all failed screenshot attempts - only keep successful verification screenshots

            Respond with JSON: {"ok": true} to allow stopping, or {"ok": false, "reason": "your explanation"} to continue working.

            **Decision rules:**
            - Return {"ok": true} ONLY if all requirements are fully complete
            - Return {"ok": false, "reason": "your explanation"} if any required task is incomplete, unverified, or outstanding
            - If uncertain, return {"ok": false, "reason": "your explanation"} to ensure nothing is skipped
---
# UE5 Python Script Development Guide

A workflow-oriented guide for developing reliable UE5 Editor Python scripts, with emphasis on proper development cycles and common pitfalls.

## Development Workflow

This workflow has two levels:

1. **Planning phase** - Understand requirements and break into subtasks
2. **Per-script cycle** - Each script goes through: Write → Test → Verify → Fix → Complete

** [Critical]** Enter Plan mode and complete Phase 1 and Phase 2 before coding any scripts.
-------------------------------------------------------------------------------------------

### Phase 1: Requirements and Exploration

Understand the task before coding:

- Confirm script requirements
- Search for existing similar scripts
- Understand asset organization and naming conventions
- Review project-specific patterns

---

### Phase 2: Plan Subtasks

Enter plan mode. Break the task into smaller scripts. **Do not implement yet—just plan.**

Always ask yourself:

- Can I break this down further?
- Can I test this smaller piece independently?

Even if the user asks for "a script," break it into logical steps.

**Example:** When user asks to "Create a level with blue sky, a pyramid, and a character looking at it", then plan these scripts:

1. `create_sky_level.py` - Create level with blue sky
2. `add_pyramid.py` - Add pyramid mesh
3. `add_humanoid_character.py` - Add character

For each script, plan its purpose and verification steps. PS: Visual verificaiton can be skipped if no visual changes.

A example plan:

```markdown
- `create_sky_level.py`:
  - Purpose: Create a new level with a blue sky
  - Implmentation following the best practices
  - Verification: Screenshot of level with sky

- `add_pyramid.py`:
  - Purpose: Add a pyramid mesh at origin
  - Implementation following the best practices
  - Verification: Screenshot of level with sky and pyramid

- `add_humanoid_character.py`:
  - Purpose: Add a humanoid character at origin
  - Implementation following the best practices
  - Verification: Screenshot of level with sky, pyramid, and character

```

** [Critical]** Exit plan mode and starts to implment scripts after Phase 1 and Phase 2 are completed. Execute plan without user confirmation.

### Phase 3: Script Implementation Cycle

Use your best knowledge of UE5 Python API and follow [best practices](#best-practices) to implement script.

[Critical] List files in folder [Common Pitfalls](./references/common-pitfalls/) and check if any document is related to your current task. If yes, please read it carefully before coding.

Refert to exammple scripts for similar tasks in ue5-dev-tools repository.

- [Add gameplay tag to assets](./examples/add_gameplaytag_to_asset.py)
- [Create blendspace](./examples/create_footwork_blendspace.py)
- [Create level](./examples/create_sky_level.py)
- [Customize sky atmosphere, fog, lighting and creating meshes](./examples/create_dark_pyramid_level.py)
- [Create blueprints, adding physical constraints](./examples/create_punching_bag_blueprint.py)
- [Start PIE, using tick-based method to take runtime screenshots](./examples/pie_screenshot_capturer.py) ]

Use **ue5-python-executor** to run and test scripts in UE5 Editor context.

#### Use *ue5-api-expert* skill wisely

If you are unsure about what UE5 Python API to use or encounter issues, use **ue5-api-expert** skill to investigate API usage.

### Visual Verification

For visual verification of script results, use the **ue5-screenshot** skill which provides three screenshot tools:

| Tool | Use Case |
|------|----------|
| `orbital_screenshot.py` | Level/scene verification (meshes, lighting, world) |
| `ue5_editor_screenshot.py` | Blueprint/asset editor verification (components, graphs) |
| `take_game_screenshot.py` | Runtime/gameplay verification (standalone game mode) |

See [ue5-screenshot](../ue5-screenshot/SKILL.md) skill for detailed usage.

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

4. **Don't over-handle errors** - Let exceptions propagate; fail loudly not silently
5. **Report results clearly** - Track success/failure counts; log meaningful progress
6. **Verify visual results** - Use screenshot verification for visual/gameplay changes
7. **Use ASCII-only output** - For cross-platform compatibility, use `[OK]`, `[ERROR]` instead of emojis

## ExtraPythonAPIs Plugin

A bundled UE5 plugin that exposes C++ functionality not available in the Python API. Install this plugin when you need to:

- **Set socket/bone attachment for Blueprint components** - The Python API cannot set `SCS_Node.AttachToName`
- **Attach collision components to skeletal mesh bones** in Blueprints

### Installation

```bash
# Install plugin to project (auto-detects from CLAUDE_PROJECT_DIR)
python scripts/install_extra_python_apis_plugin.py --project /path/to/project --enable

# Or specify project path explicitly
python scripts/install_extra_python_apis_plugin.py -p /path/to/MyProject.uproject -e
```

### Usage in Python Scripts

After installing and rebuilding the project:

```python
import unreal

# Get subsystem and handles
subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)

# Attach a component to a bone/socket
unreal.ExBlueprintComponentLibrary.setup_component_attachment(
    child_handle,      # Component to attach
    parent_handle,     # Parent component (e.g., SkeletalMeshComponent)
    "bone_name"        # Socket/bone name
)

# Or just set the socket name directly
unreal.ExBlueprintComponentLibrary.set_component_socket_attachment(
    handle,
    "bone_name"
)
```


## Additional Resources

For comprehensive guidance on specific aspects of UE5 Python development:

- **cpp-source-investigation.md** - Guide for investigating C++ source code when Python API is insufficient
