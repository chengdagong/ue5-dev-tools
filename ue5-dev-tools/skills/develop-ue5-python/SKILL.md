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

Use **ue5-python-executor** to run and test scripts in UE5 Editor context.

#### Use *ue5-api-expert* skill wisely

If you are unsure about what UE5 Python API to use or encounter issues, use **ue5-api-expert** skill to investigate API usage.

### How to do Visual Confirmation based on screenshot

**Required when script affects:**

- Visual appearance (materials, meshes, lighting, UI)
- Game behavior (character movement, AI, mechanics)
- Level/world state (object placement, spawning)
- Blueprint structure (components, event graph, variables)

**Skip when:** Changes are data-only, organizational, or user requests to skip.

**Choose the right screenshot tool:**

| Tool | Use Case |
|------|----------|
| `orbital_screenshot.py` | Level/scene verification (meshes, lighting, world) |
| `ue5_editor_screenshot.py` | Blueprint/asset editor verification (components, graphs) |

---

#### Level/Scene Screenshots

Use *ue5-python-executor* skill to run [./scripts/orbital_screenshot.py](./scripts/orbital_screenshot.py) to capture multi-angle screenshots of the scene. orbital_screenshots accepts the following arguments:

``
  --args "level=//Game/Path/To/Level,preset=orthographic,target=0+0+100,resolution=800x600,distance=500,output=screenshots,prefix=capture"
``

| Parameter    | Description                                                                             | Default       |
| -------------- | ----------------------------------------------------------------------------------------- | --------------- |
| `level`      | Level path (use`//Game/...` format to avoid path conversion)                            | Required      |
| `preset`     | View preset:`all`, `perspective`, `orthographic`, `birdseye`, `horizontal`, `technical` | `orthographic`         |
| `target`     | Target location as`X+Y+Z` format (e.g., `100+200+150`)                                  | `0+0+100`     |
| `resolution` | Screenshot resolution as`WIDTHxHEIGHT` (e.g., `1280x720`)                               | `800x600`     |
| `distance`   | Camera distance from target                                                             | `500`         |
| `output`     | Output directory for screenshots                                                        | `screenshots` |
| `prefix`     | Folder prefix (creates`output/prefix_1`, `prefix_2`, etc.)                              | `capture`     |

**View presets:**

- `all` - All angles (perspective + orthographic + birdseye) - 14 screenshots
- `perspective` - 8 perspective angles around target
- `orthographic` - 6 orthographic views (front, back, left, right, top, bottom)
- `birdseye` - Bird's eye view from above
- `horizontal` - Perspective + birdseye views
- `technical` - Orthographic views only (same as `orthographic`)

**Level path format:**

- Use double slash prefix: `//Game/ThirdPerson/Maps/ThirdPersonMap`
- This prevents MSYS/Git Bash path conversion issues

**Analyze screenshots:**

1. Read captured images from the auto-incremented folder
2. Check for expected changes and any visual artifacts
3. Verify results match original requirements

---

#### Blueprint/Asset Editor Screenshots

Use *ue5-python-executor* skill to run [./scripts/ue5_editor_screenshot.py](./scripts/ue5_editor_screenshot.py) to capture screenshots of Blueprint editors, Animation Blueprints, or other asset editors.

**When to use:**

- Verify Blueprint component changes (added/removed components)
- Verify Animation Blueprint graph modifications
- Verify material/texture asset changes
- Any asset editor visual verification

**Arguments:**

```
--args "asset=//Game/Path/To/Asset,output=C://Screenshots//screenshot.png,delay=2.0,tab=1"
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `asset` | Asset path (use `//Game/...` format) | **Required** |
| `output` | Output file path (use `//` for path separators) | **Required** |
| `delay` | Seconds to wait for editor to render | `3.0` |
| `tab` | Tab number to switch to (1-9) | `1` (Viewport) |
| `no-tab` | Set to `true` to skip tab switching | `false` |
| `no-capture-ue5-only` | Set to `true` to capture full screen | `false` |

**Tab numbers in Blueprint Editor:**

- `1` - Viewport (3D preview)
- `2` - Construction Script
- `3` - Event Graph

**Example usage:**

```bash
# Capture Blueprint viewport (default)
python remote-execute.py --file scripts/ue5_editor_screenshot.py \
    --args "asset=//Game/Blueprints/BP_MyActor,output=C://Screenshots//bp_viewport.png"

# Capture Event Graph (tab 3)
python remote-execute.py --file scripts/ue5_editor_screenshot.py \
    --args "asset=//Game/Blueprints/BP_MyActor,output=C://Screenshots//bp_eventgraph.png,tab=3"

# Capture Animation Blueprint
python remote-execute.py --file scripts/ue5_editor_screenshot.py \
    --args "asset=//Game/Animations/ABP_Character,output=C://Screenshots//abp.png,tab=2"
```

**Workflow:**

1. Script opens the asset editor
2. Moves UE5 window to extended display (for high-resolution capture)
3. Switches to specified tab
4. Captures screenshot
5. Closes the editor automatically
6. Restores window position

**Then proceed to the next script in your plan.**

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

## Additional Resources

For comprehensive guidance on specific aspects of UE5 Python development:

- **cpp-source-investigation.md** - Guide for investigating C++ source code when Python API is insufficient
