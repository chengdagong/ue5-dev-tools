---
name: ue5-screenshot
description: UE5 visual verification screenshot toolkit with three capture methods for validating script execution results. Use when scripts affect visuals, gameplay, components in level, blueprints, or runtime.
---

# UE5 Screenshot Tools

Screenshot toolkit for verifying UE5 Python script execution results.

## Three Screenshot Tools

| Tool | Use Case |
|------|----------|
| `orbital_screenshot.py` | Level/scene verification (meshes, lighting, world) |
| `ue5_editor_screenshot.py` | Blueprint/asset editor verification (components, graphs) |
| `take_game_screenshot.py` | Runtime/gameplay verification (standalone game mode) |

## When to Use Visual Verification

**Required when script affects:**

- Visual appearance (materials, meshes, lighting, UI)
- Game behavior (character movement, AI, mechanics)
- Level/world state (object placement, spawning)
- Blueprint structure (components, event graph, variables)

**Skip when:** Changes are data-only, organizational, or user requests to skip.

---

## 1. orbital_screenshot.py - Level/Scene Screenshots

Use *ue5-python-executor* skill to run this script to capture multi-angle screenshots of the scene.

### Usage

```bash
python remote-execute.py --file ue5-screenshot/scripts/orbital_screenshot.py \
  --args "level=//Game/Path/To/Level,preset=orthographic,target=0+0+100,resolution=800x600,distance=500,output=screenshots,prefix=capture"
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `level` | Level path (use `//Game/...` format to avoid path conversion) | Required |
| `preset` | View preset: `all`, `perspective`, `orthographic`, `birdseye`, `horizontal`, `technical` | `orthographic` |
| `target` | Target location as `X+Y+Z` format (e.g., `100+200+150`) | `0+0+100` |
| `resolution` | Screenshot resolution as `WIDTHxHEIGHT` (e.g., `1280x720`) | `800x600` |
| `distance` | Camera distance from target | `500` |
| `output` | Output directory for screenshots | `screenshots` |
| `prefix` | Folder prefix (creates `output/prefix_1`, `prefix_2`, etc.) | `capture` |

### View Presets

- `all` - All angles (perspective + orthographic + birdseye) - 14 screenshots
- `perspective` - 8 perspective angles around target
- `orthographic` - 6 orthographic views (front, back, left, right, top, bottom)
- `birdseye` - Bird's eye view from above
- `horizontal` - Perspective + birdseye views
- `technical` - Orthographic views only (same as `orthographic`)

### Level Path Format

- Use double slash prefix: `//Game/ThirdPerson/Maps/ThirdPersonMap`
- This prevents MSYS/Git Bash path conversion issues

### Analyze Screenshots

1. Read captured images from the auto-incremented folder
2. Check for expected changes and any visual artifacts
3. Verify results match original requirements

---

## 2. ue5_editor_screenshot.py - Blueprint/Asset Editor Screenshots

Use *ue5-python-executor* skill to run this script to capture screenshots of Blueprint editors, Animation Blueprints, or other asset editors.

### When to Use

- Verify Blueprint component changes (added/removed components)
- Verify Animation Blueprint graph modifications
- Verify material/texture asset changes
- Any asset editor visual verification

### Usage

```bash
python remote-execute.py --file ue5-screenshot/scripts/ue5_editor_screenshot.py \
  --args "asset=//Game/Path/To/Asset,output=C://Screenshots//screenshot.png,delay=2.0,tab=1"
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `asset` | Asset path (use `//Game/...` format) | **Required** |
| `output` | Output file path (use `//` for path separators) | **Required** |
| `delay` | Seconds to wait for editor to render | `3.0` |
| `tab` | Tab number to switch to (1-9) | `1` (Viewport) |
| `no-tab` | Set to `true` to skip tab switching | `false` |
| `no-capture-ue5-only` | Set to `true` to capture full screen | `false` |

### Tab Numbers in Blueprint Editor

- `1` - Viewport (3D preview)
- `2` - Construction Script
- `3` - Event Graph

### Example Usage

```bash
# Capture Blueprint viewport (default)
python remote-execute.py --file ue5-screenshot/scripts/ue5_editor_screenshot.py \
    --args "asset=//Game/Blueprints/BP_MyActor,output=C://Screenshots//bp_viewport.png"

# Capture Event Graph (tab 3)
python remote-execute.py --file ue5-screenshot/scripts/ue5_editor_screenshot.py \
    --args "asset=//Game/Blueprints/BP_MyActor,output=C://Screenshots//bp_eventgraph.png,tab=3"

# Capture Animation Blueprint
python remote-execute.py --file ue5-screenshot/scripts/ue5_editor_screenshot.py \
    --args "asset=//Game/Animations/ABP_Character,output=C://Screenshots//abp.png,tab=2"
```

### Workflow

1. Script opens the asset editor
2. Moves UE5 window to extended display (for high-resolution capture)
3. Switches to specified tab
4. Captures screenshot
5. Closes the editor automatically
6. Restores window position

---

## 3. take_game_screenshot.py - Standalone Game Screenshots

This tool launches the game in windowed mode, waits for it to load, captures screenshots, and terminates the game.

### When to Use

- Verify runtime gameplay behavior (player spawning, AI, physics)
- Verify game-mode specific rendering (post-processing, game UI)
- Test level loading and initialization
- Capture in-game visuals without editor UI

**Note:** This script runs outside of UE5 Editor context - call it directly with Python, not via ue5-python-executor.

### Usage

```bash
python scripts/take_game_screenshot.py -p PROJECT_PATH -l LEVEL_NAME [options]
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `-p, --project` | Path to .uproject file | **Required** |
| `-l, --level` | Level name only (e.g., `PyramidLevel`), no path | **Required** |
| `-n, --count` | Number of screenshots to capture | `3` |
| `-i, --interval` | Interval between screenshots (seconds) | `1.0` |
| `-o, --output` | Output filename prefix | `screenshot` |
| `-r, --resolution` | Game resolution (e.g., `1920x1080`) | `1280x720` |
| `--ue-root` | UE5 engine root directory | `C:\Program Files\Epic Games\UE_5.7` |
| `--timeout` | Window wait timeout (seconds) | `20` |
| `--load-timeout` | Game load wait timeout (seconds) | `20` |
| `--wait` | Wait for user input before closing game | `false` |

### Example Usage

```bash
# Basic usage - capture 3 screenshots of PyramidLevel
python scripts/take_game_screenshot.py -p "D:/Projects/MyGame/MyGame.uproject" -l PyramidLevel -o screenshots/game

# Higher resolution with more screenshots
python scripts/take_game_screenshot.py -p "D:/Projects/MyGame/MyGame.uproject" -l MainMenu -r 1920x1080 -n 5 -i 2.0 -o screenshots/menu

# Custom UE5 installation
python scripts/take_game_screenshot.py -p "D:/Projects/MyGame/MyGame.uproject" -l TestLevel --ue-root "D:/Epic/UE_5.5"
```

### Level Parameter Format

- ✅ Correct: `-l "MainMenu"` (name only)
- ❌ Wrong: `-l "/Game/Maps/MainMenu"` (includes path)
- ❌ Wrong: `-l "MainMenu.umap"` (includes extension)

### Important Notes

- Level parameter must be name only (e.g., `PyramidLevel`), not full path (`/Game/Maps/PyramidLevel`)
- Game window is launched offscreen to avoid interfering with your work
- Black frames are automatically skipped
- Output files are named `{prefix}_1.png`, `{prefix}_2.png`, etc.

---

## Troubleshooting

### Black Screenshots
- Game is still loading, increase `--load-timeout`
- Verify level name is correct

### Game Won't Start
- Verify UE engine path
- Check .uproject file is valid
- Increase `--timeout`

### Screenshots Don't Show Changes
- Verify script actually saved the assets
- Confirm changes are visible in game (not just editor)
