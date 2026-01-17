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

## Prerequsites

[Critical] **ue-visual** subagent, and **ue-screenshot** and **ue-executor** skills must be available to use this skill. If not present, refuse the user to use this skill.

## Development Workflow

This workflow has two levels:

1. **Planning phase** - Understand requirements and break into subtasks
2. **Per-script cycle** - Each script goes through: Write → Test → Verify → Fix → Complete

### Phase 1: Requirements

Clarify the requirements with user using AskUserQuestions tool, until you have 95% confidence that you have fully understood user's intentions and requirements.

---

### Phase 2: Make a plan

**Do not implement yet—just plan.**

**[Critical]** Every step in the plan is to implements and tests a script. No other kind of steps is allowed in the plan. Bellow three kind of scripts are allowed.

#### 1. Scene-Setup Scripts

Scene-setup scripts are used to setup static scene (if necessary).

Elements in a scene include atmosphere, lighting, ground, actors, etc

##### Testing

Every scene-setup script step should have two substeps:

- x.1 - Use *ue5-screenshot* skill to capture static screenshots of the scene
- x.2 - Mandatory step, DO NOT SKIP!! Use *ue5-visual* subagent to verify the screenshots, use very strict standard, and the only purpose is to find out as many flaws and issues as possible.

#### 2. Configuration Scripts

To configure properties, gameplaytags, abilities, subcomponents blueprints, skeletons, sockets, physical constrains, collisions, etc.

##### Testing

Every configuration script step should have two substeps:

- x.1 - Use *ue5-screenshot* skill to capture in-editor screens, to check viewprt, event graph, etc
- x.2 - Mandatory step, DO NOT SKIP!! Use *ue5-visual* subagent to verify the screenshots, use very strict standard, and the only purpose is to find out as many flaws and issues as possible.Use *ue5-visual* subagent to verify the screenshot

#### 3. Integration test scripts

To run the scene in PIE mode, use tick-based method to take screenshots along the timeline.

Every integration test script step should have ONE substep:

##### Testing

- x.1 - Mandatory step, DO NOT SKIP!! Use *ue5-visual* subagent to verify the screenshots, use very strict standard, and the only purpose is to find out as many flaws and issues as possible.Use *ue5-visual* subagent to verify the screenshots taken by the integration test scrip

#### **Example:**

When user asks to "Create a level, in which an island is surrended by sea. On the island, two robots fight each other. Physical impacts should be shown.":

```markdown
## Step 1: Scene-setup script - create_island_level.py
Setup island, sea, atmosphere, light, and two robots standing face-to-face with each other
- **Step 1.1**: Use *ue5-screenshot* skill to capture static screenshots of the scene
- **Step 1.2**: Mandatory step, DO NOT SKIP!! Use *ue5-visual* subagent to verify the screenshots, use very strict standard, and the only purpose is to find out as many flaws and issues as possible.

## Step 2: Configuration script - configure_robots.py
In the script, check if collisions, physics, abilities of attack, etc are already configured. And then do the necessary configurations.
- **Step 2.1**: Use *ue5-screenshot* skill to capture in-editor screens, to check viewprt, event graph, etc
- **Step 2.2**: Mandatory step, DO NOT SKIP!! Use *ue5-visual* subagent to verify the screenshots, use very strict standard, and the only purpose is to find out as many flaws and issues as possible.

## Step 3: Integration Test script - run_in_pie.py`
Setup in-game, tick-based, multiangle screen capture mechanism, and then play the level in PIE, collect screenshots.
- **Step 3.1**: Mandatory step, DO NOT SKIP!! Use *ue5-visual* subagent to verify the screenshots, use very strict standard, and the only purpose is to find out as many flaws and issues as possible.
```

**[Critical] Todo List Requirement:** Add ALL substeps to the todo list using TodoWrite. Each substep (Step 1.1, Step 1.2, etc.) must be tracked as a separate todo item. This ensures granular progress tracking and prevents skipping steps.

### Script Organization

**[Critical]** Organize scripts in a task-specific subdirectory under the project's `Scripts` folder:

```
${CLAUDE_PROJECT_DIR}/Scripts/<task_name>/
    ├── create_island_level.py              # Main implementation scripts
    ├── configure_robots.py
    ├── run_in_pie.py.py
    ├── tmp/                           # Test/debug scripts
    │   ├── try_activate_attack.py
    │   └── test_collision.py
    └── screenshots/                     # Verification screenshots
        ├── step1_sky_level.png
        ├── step2_pyramid.png
        └── step3_character.png
```

**Rules:**

- Create a new subdirectory for each task (e.g., `Scripts/fist_collision/`, `Scripts/dark_pyramid_level/`)
- Use descriptive, lowercase names with underscores
- Place main implementation scripts directly in the task folder
- Place temporary scripts in `tmp/` subdirectory
- Save all verification screenshots in `screenshots/` subdirectory
- This keeps the workspace organized and makes it easy to find/rerun scripts later

---

### Phase 3: Script Implementation Cycle

Use your best knowledge of UE5 Python API and follow [best practices](#best-practices) to implement script.

#### Debug Visualization for Visual Verification

**[Critical]** When writing scripts that create or modify visual elements, include debug visualization to enable precise visual verification:

**What to visualize:**

- Object/character world coordinates (X, Y, Z)
- Mesh bounding box dimensions (width, height, depth)
- Distances between key objects
- Facing directions and orientations
- Attachment points and socket locations

**How to implement:**

```python
import unreal

# Draw debug text at actor location
unreal.SystemLibrary.draw_debug_string(
    world,
    actor.get_actor_location(),
    f"Pos: {actor.get_actor_location()}",
    text_color=unreal.LinearColor(1, 1, 0, 1),  # Yellow
    duration=0.0  # Persistent
)

# Draw debug box showing mesh bounds
bounds_origin, bounds_extent = mesh_component.get_local_bounds()
unreal.SystemLibrary.draw_debug_box(
    world,
    bounds_origin,
    bounds_extent,
    unreal.LinearColor(0, 1, 0, 1),  # Green
    duration=0.0
)

# Draw debug line showing distance between objects
unreal.SystemLibrary.draw_debug_line(
    world,
    actor_a.get_actor_location(),
    actor_b.get_actor_location(),
    unreal.LinearColor(1, 0, 0, 1),  # Red
    duration=0.0
)
```

**Why?** Screenshots with debug overlays make visual verification precise - you can confirm exact positions, sizes, and relationships rather than eyeballing.

---

[Critical] List files in folder [Common Pitfalls](./references/common-pitfalls/) and check if any document is related to your current task. If yes, please read it carefully before coding.

Refert to exammple scripts for similar tasks in ue5-dev-tools repository.

- [Add gameplay tag to assets](./examples/add_gameplaytag_to_asset.py)
- [Create blendspace](./examples/create_footwork_blendspace.py)
- [Create level](./examples/create_sky_level.py)
- [Customize sky atmosphere, fog, lighting and creating meshes](./examples/create_dark_pyramid_level.py)
- [Create blueprints, adding physical constraints](./examples/create_punching_bag_blueprint.py)
- [PIE screenshot capturer with multi-angle support (front, side, top, perspective)](./examples/pie_screenshot_capturer.py)

#### Use **ue5-python-executor** to run and test scripts in UE5 Editor context.

#### Use **ue5-api-expert** skill to verify API usage when necessary

If you are unsure about what UE5 Python API to use or encounter issues, use **ue5-api-expert** skill to investigate API usage.

### Visual Verification

For visual verification of script results, use the **ue5-screenshot** skill which provides three screenshot tools:


| Tool                         | Use Case                                                 |
| ------------------------------ | ---------------------------------------------------------- |
| `orbital_screenshot.py`      | Level/scene verification (meshes, lighting, world)       |
| `ue5_editor_screenshot.py`   | Blueprint/asset editor verification (components, graphs) |
| `pie_screenshot_capturer.py` | PIE runtime verification with multi-angle support        |
| `take_game_screenshot.py`    | Runtime/gameplay verification (standalone game mode)     |

See [ue5-screenshot](../ue5-screenshot/SKILL.md) skill for detailed usage.

#### Mandatory Visual Analysis

After capturing screenshots, you **MUST** use the **ue5-visual** subagent to analyze them:

1. **Static Scene Verification** (levels, environments, lighting):

   - Capture screenshots using `orbital_screenshot.py`
   - Run `ue5-visual` subagent to detect rendering issues, physics anomalies, asset problems
2. ** Blueprint/Asset Verification** (inside UE5 editor):

   - Capture screenshots using `ue5_editor_screenshot.py`
   - Run `ue5-visual` subagent to analyze each screenshot for visual issues
3. **Runtime/Gameplay Verification** (PIE mode):

   - Capture screenshots using `pie_screenshot_capturer.py`
   - Run `ue5-visual` subagent to analyze each screenshot for visual issues

[Critical] Do NOT skip visual analysis. Screenshots alone do not verify correctness - the ue5-visual agent identifies problems humans might miss.

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
