---
name: ue5-builder
description: Comprehensive guide for building UE5 projects from command line. Use when users need to (1) build UE5 project via command line, (2) locate UE5 build tools (UAT/RunUAT), (3) package UE5 projects for different platforms, (4) understand build configurations and parameters.
---

# UE5 Project Command Line Build Guide

A comprehensive guide for building, cooking, and packaging Unreal Engine 5 projects using command-line tools across different platforms.

## Overview

UE5 provides command-line tools for automated builds:

- **UAT (Unreal Automation Tool)**: Primary build automation tool
- **RunUAT**: Cross-platform wrapper for UAT
- **UBT (Unreal Build Tool)**: Lower-level C++ compilation tool (usually called via UAT)

This guide focuses on **UAT/RunUAT** as the recommended approach for project builds.

## Locating Build Tools

### Tool Locations by Platform

#### Windows

**Default Engine Installation (Epic Games Launcher):**

```
C:\Program Files\Epic Games\UE_5.X\Engine\Build\BatchFiles\RunUAT.bat
```

**Common paths by version:**
```
C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles\RunUAT.bat
C:\Program Files\Epic Games\UE_5.4\Engine\Build\BatchFiles\RunUAT.bat
C:\Program Files\Epic Games\UE_5.3\Engine\Build\BatchFiles\RunUAT.bat
```

**Custom/Source Build:**
```
<CustomEngineRoot>\Engine\Build\BatchFiles\RunUAT.bat
```

#### macOS

**Default Engine Installation (Epic Games Launcher):**

```bash
/Users/Shared/Epic Games/UE_5.X/Engine/Build/BatchFiles/RunUAT.sh
```

**Common paths by version:**
```bash
/Users/Shared/Epic Games/UE_5.5/Engine/Build/BatchFiles/RunUAT.sh
/Users/Shared/Epic Games/UE_5.4/Engine/Build/BatchFiles/RunUAT.sh
/Users/Shared/Epic Games/UE_5.3/Engine/Build/BatchFiles/RunUAT.sh
```

**Custom/Source Build:**
```bash
<CustomEngineRoot>/Engine/Build/BatchFiles/RunUAT.sh
```

#### Linux

**Custom/Source Build (typical):**

```bash
~/UnrealEngine/Engine/Build/BatchFiles/RunUAT.sh
# Or
<CustomEngineRoot>/Engine/Build/BatchFiles/RunUAT.sh
```

**Note:** Epic Games Launcher is not available on Linux. Linux users typically build from source.

### Auto-Detection Strategy

When you need to find RunUAT automatically:

**1. Check for engine association:**
```bash
# Windows
# Read .uproject file, look for "EngineAssociation" field
# Could be version like "5.5" or custom engine ID

# macOS/Linux
# Same approach - parse .uproject JSON
```

**2. Search common installation locations:**
```bash
# Windows - check all Epic Games installations
dir "C:\Program Files\Epic Games\UE_*\Engine\Build\BatchFiles\RunUAT.bat"

# macOS - check shared installations
ls "/Users/Shared/Epic Games/UE_"*/Engine/Build/BatchFiles/RunUAT.sh

# Linux - check typical source locations
ls ~/UnrealEngine/Engine/Build/BatchFiles/RunUAT.sh
```

**3. Use environment variables (if set):**
```bash
# Some users set UE_ROOT or UNREAL_ENGINE_ROOT
# Check: $UE_ROOT/Engine/Build/BatchFiles/RunUAT.sh
```

**4. Check registry (Windows only):**
```powershell
# Engine installations register here
# HKEY_LOCAL_MACHINE\SOFTWARE\EpicGames\Unreal Engine\<Version>
# Look for "InstalledDirectory" value
```

## Build Commands

### Basic Build Command Structure

```bash
RunUAT BuildCookRun \
  -project="<ProjectPath>" \
  -platform=<Platform> \
  -clientconfig=<Configuration> \
  [additional options]
```

### Build Configurations

UE5 supports these build configurations:

- **Debug**: Full debugging symbols, no optimization (very slow)
- **DebugGame**: Debugging for game code only, optimized engine
- **Development**: Balanced build with some debugging capability (default)
- **Shipping**: Fully optimized, no debugging (production)
- **Test**: Similar to Shipping but with some profiling/testing hooks

**Recommendation:**
- **Development** during active development
- **Shipping** for final production builds
- **DebugGame** when debugging specific game code issues

### Target Platforms

Common platform identifiers:

- `Win64` - Windows 64-bit
- `Mac` - macOS (Intel and Apple Silicon)
- `Linux` - Linux
- `Android` - Android devices
- `IOS` - iOS devices

## Common Build Scenarios

### Scenario 1: Build Game Code Only (No Cooking/Packaging)

Compile C++ code without cooking assets or packaging:

**Windows:**
```batch
"C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun ^
  -project="D:\MyProject\MyGame.uproject" ^
  -platform=Win64 ^
  -clientconfig=Development ^
  -build ^
  -nocompileeditor ^
  -skipstage
```

**macOS:**
```bash
"/Users/Shared/Epic Games/UE_5.5/Engine/Build/BatchFiles/RunUAT.sh" BuildCookRun \
  -project="/Users/me/MyProject/MyGame.uproject" \
  -platform=Mac \
  -clientconfig=Development \
  -build \
  -nocompileeditor \
  -skipstage
```

**Key flags:**
- `-build`: Compile the project
- `-nocompileeditor`: Skip editor compilation (faster)
- `-skipstage`: Don't stage files (no packaging)

### Scenario 2: Cook Assets Only (No Build/Package)

Cook game content without compiling or packaging:

**Windows:**
```batch
"C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun ^
  -project="D:\MyProject\MyGame.uproject" ^
  -platform=Win64 ^
  -cook ^
  -skipbuild ^
  -skipstage
```

**macOS:**
```bash
"/Users/Shared/Epic Games/UE_5.5/Engine/Build/BatchFiles/RunUAT.sh" BuildCookRun \
  -project="/Users/me/MyProject/MyGame.uproject" \
  -platform=Mac \
  -cook \
  -skipbuild \
  -skipstage
```

**Key flags:**
- `-cook`: Cook assets for target platform
- `-skipbuild`: Don't compile code
- `-skipstage`: Don't package

### Scenario 3: Full Build, Cook, and Package

Complete build pipeline producing a standalone game:

**Windows:**
```batch
"C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun ^
  -project="D:\MyProject\MyGame.uproject" ^
  -platform=Win64 ^
  -clientconfig=Shipping ^
  -build ^
  -cook ^
  -stage ^
  -package ^
  -pak ^
  -archive ^
  -archivedirectory="D:\MyProject\Builds\Windows"
```

**macOS:**
```bash
"/Users/Shared/Epic Games/UE_5.5/Engine/Build/BatchFiles/RunUAT.sh" BuildCookRun \
  -project="/Users/me/MyProject/MyGame.uproject" \
  -platform=Mac \
  -clientconfig=Shipping \
  -build \
  -cook \
  -stage \
  -package \
  -pak \
  -archive \
  -archivedirectory="/Users/me/MyProject/Builds/Mac"
```

**Key flags:**
- `-build`: Compile code
- `-cook`: Cook assets
- `-stage`: Stage files for distribution
- `-package`: Create distributable package
- `-pak`: Compress assets into .pak files
- `-archive`: Create final build archive
- `-archivedirectory`: Output location

### Scenario 4: Quick Iteration Build

Fast build for testing during development:

**Windows:**
```batch
"C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun ^
  -project="D:\MyProject\MyGame.uproject" ^
  -platform=Win64 ^
  -clientconfig=Development ^
  -build ^
  -cook ^
  -stage ^
  -pak ^
  -nocompileeditor ^
  -iterativecooking ^
  -unattended
```

**macOS:**
```bash
"/Users/Shared/Epic Games/UE_5.5/Engine/Build/BatchFiles/RunUAT.sh" BuildCookRun \
  -project="/Users/me/MyProject/MyGame.uproject" \
  -platform=Mac \
  -clientconfig=Development \
  -build \
  -cook \
  -stage \
  -pak \
  -nocompileeditor \
  -iterativecooking \
  -unattended
```

**Key flags:**
- `-iterativecooking`: Incremental cooking (faster subsequent builds)
- `-unattended`: Non-interactive mode
- `-nocompileeditor`: Skip editor build (faster)

### Scenario 5: Server Build

Build dedicated server:

**Windows:**
```batch
"C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun ^
  -project="D:\MyProject\MyGame.uproject" ^
  -platform=Win64 ^
  -serverconfig=Development ^
  -server ^
  -noclient ^
  -build ^
  -cook ^
  -stage ^
  -pak ^
  -archive ^
  -archivedirectory="D:\MyProject\Builds\Server"
```

**macOS:**
```bash
"/Users/Shared/Epic Games/UE_5.5/Engine/Build/BatchFiles/RunUAT.sh" BuildCookRun \
  -project="/Users/me/MyProject/MyGame.uproject" \
  -platform=Mac \
  -serverconfig=Development \
  -server \
  -noclient \
  -build \
  -cook \
  -stage \
  -pak \
  -archive \
  -archivedirectory="/Users/me/MyProject/Builds/Server"
```

**Key flags:**
- `-server`: Build server target
- `-serverconfig`: Configuration for server (Development/Shipping)
- `-noclient`: Don't build client

## Important Command-Line Flags Reference

### Build Control

- `-build`: Compile project code
- `-skipbuild`: Skip compilation
- `-clean`: Clean before building (full rebuild)
- `-nocompileeditor`: Don't compile editor binaries

### Cooking Control

- `-cook`: Cook content for target platform
- `-skipcook`: Skip cooking (use existing cooked content)
- `-iterativecooking`: Incremental cooking (faster)
- `-cookall`: Cook all content (including editor-only)

### Staging & Packaging

- `-stage`: Stage files for distribution
- `-skipstage`: Skip staging
- `-package`: Create standalone package
- `-pak`: Package assets into .pak files
- `-compressed`: Compress .pak files

### Output Control

- `-archive`: Create build archive
- `-archivedirectory="<Path>"`: Where to save build
- `-stagingdirectory="<Path>"`: Custom staging location

### Target Configuration

- `-platform=<Platform>`: Target platform (Win64, Mac, Linux, etc.)
- `-clientconfig=<Config>`: Client build config (Debug, Development, Shipping)
- `-serverconfig=<Config>`: Server build config
- `-target=<TargetName>`: Build specific target

### Server/Client Options

- `-server`: Build dedicated server
- `-noclient`: Don't build client
- `-client`: Build client (default)

### Automation & Logging

- `-unattended`: Non-interactive mode (no prompts)
- `-utf8output`: Use UTF-8 encoding for logs
- `-verbose`: Detailed logging
- `-log`: Custom log file path

### Advanced Options

- `-nop4`: Don't sync from Perforce
- `-compile`: Force recompile even if up to date
- `-allmaps`: Cook all maps (not just those in map list)
- `-distribution`: Create distribution build (enables additional optimizations)

## Build Workflow Best Practices

### 1. Pre-Build Validation

Before running a build:

```bash
# 1. Verify project compiles in editor
# Open in editor and ensure no compilation errors

# 2. Check .uproject integrity
# Ensure EngineAssociation matches installed engine

# 3. Verify UAT path exists
# Test: ls "<UAT_PATH>" or dir "<UAT_PATH>"
```

### 2. Incremental Development Builds

For rapid iteration during development:

```bash
# Use iterative cooking
-iterativecooking

# Use Development config (not Shipping)
-clientconfig=Development

# Skip editor compilation
-nocompileeditor

# Only build client (not server)
-noclient=false -noserver=true
```

### 3. Production Release Builds

For final production builds:

```bash
# Use Shipping configuration
-clientconfig=Shipping

# Full clean build
-clean

# Compress assets
-compressed -pak

# Distribution mode
-distribution

# Archive to specific location
-archive -archivedirectory="<Path>"
```

### 4. Multi-Platform Builds

Build for multiple platforms sequentially:

```bash
# Build Windows version
RunUAT BuildCookRun -project=<Project> -platform=Win64 ...

# Build macOS version
RunUAT BuildCookRun -project=<Project> -platform=Mac ...

# Build Linux version
RunUAT BuildCookRun -project=<Project> -platform=Linux ...
```

**Tip:** Each platform should use its own archive directory to avoid conflicts.

### 5. Parallel Builds (Advanced)

UAT supports parallel compilation:

```bash
# Enable parallel compilation (automatic, but can tune)
# Add to Engine/Saved/UnrealBuildTool/BuildConfiguration.xml:
# <MaxParallelActions>8</MaxParallelActions>
```

## Troubleshooting

### "RunUAT not found"

**Cause:** Incorrect path or engine not installed

**Solution:**
1. Verify engine installation exists
2. Check path matches installed version (e.g., UE_5.5 vs UE_5.4)
3. Use full absolute path, not relative path
4. On macOS/Linux, ensure .sh file has execute permissions: `chmod +x RunUAT.sh`

### "Project file not found"

**Cause:** Incorrect project path or path with spaces not quoted

**Solution:**
```bash
# WRONG - path with spaces not quoted
-project=D:\My Project\Game.uproject

# CORRECT - use quotes
-project="D:\My Project\Game.uproject"
```

### "Cook failed" errors

**Cause:** Asset errors, corrupted assets, or missing dependencies

**Solution:**
1. Try opening project in editor first
2. Fix any asset errors shown in Message Log
3. Try `-cook -skipcook` to use existing cooked data
4. Use `-clean` for fresh cook

### Build takes extremely long

**Cause:** Full rebuild, all maps cooking, or debug configuration

**Solution:**
1. Use `-iterativecooking` for subsequent builds
2. Avoid `-clean` unless necessary
3. Use Development config (not Debug)
4. Use `-nocompileeditor` if editor isn't needed
5. Specify maps to cook instead of cooking all: `-map=<MapName>`

### "Error: Missing precompiled manifest"

**Cause:** Editor hasn't been built with current engine version

**Solution:**
```bash
# Build editor first
RunUAT BuildCookRun -project=<Project> -build -nocompileeditor=false -skipstage
```

### Platform-specific issues

**macOS - "Operation not permitted":**
```bash
# Grant Terminal full disk access in System Preferences > Security & Privacy
```

**Windows - "Access denied" or script won't run:**
```batch
# Run Command Prompt as Administrator
```

**Linux - "Permission denied":**
```bash
# Ensure script is executable
chmod +x "/path/to/RunUAT.sh"
```

## Integration with CI/CD

### Example Jenkins Pipeline

```groovy
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                script {
                    if (isUnix()) {
                        sh '''
                            "/Users/Shared/Epic Games/UE_5.5/Engine/Build/BatchFiles/RunUAT.sh" \
                            BuildCookRun \
                            -project="${WORKSPACE}/MyGame.uproject" \
                            -platform=Mac \
                            -clientconfig=Shipping \
                            -build -cook -stage -package -pak \
                            -archive -archivedirectory="${WORKSPACE}/Builds" \
                            -unattended -utf8output
                        '''
                    } else {
                        bat '''
                            "C:\\Program Files\\Epic Games\\UE_5.5\\Engine\\Build\\BatchFiles\\RunUAT.bat" ^
                            BuildCookRun ^
                            -project="%WORKSPACE%\\MyGame.uproject" ^
                            -platform=Win64 ^
                            -clientconfig=Shipping ^
                            -build -cook -stage -package -pak ^
                            -archive -archivedirectory="%WORKSPACE%\\Builds" ^
                            -unattended -utf8output
                        '''
                    }
                }
            }
        }
    }
}
```

### Example GitHub Actions

```yaml
name: Build UE5 Project

on:
  push:
    branches: [ main ]

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Project
        run: |
          & "C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles\RunUAT.bat" `
            BuildCookRun `
            -project="${{ github.workspace }}\MyGame.uproject" `
            -platform=Win64 `
            -clientconfig=Shipping `
            -build -cook -stage -package -pak `
            -archive -archivedirectory="${{ github.workspace }}\Builds" `
            -unattended -utf8output

      - name: Upload Build
        uses: actions/upload-artifact@v3
        with:
          name: windows-build
          path: Builds/

  build-mac:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Project
        run: |
          "/Users/Shared/Epic Games/UE_5.5/Engine/Build/BatchFiles/RunUAT.sh" \
            BuildCookRun \
            -project="${{ github.workspace }}/MyGame.uproject" \
            -platform=Mac \
            -clientconfig=Shipping \
            -build -cook -stage -package -pak \
            -archive -archivedirectory="${{ github.workspace }}/Builds" \
            -unattended -utf8output

      - name: Upload Build
        uses: actions/upload-artifact@v3
        with:
          name: mac-build
          path: Builds/
```

## Quick Reference

### Minimal Commands

**Quick development build (Win64):**
```batch
RunUAT.bat BuildCookRun -project=<Project> -platform=Win64 -clientconfig=Development -build -cook -stage -pak
```

**Quick development build (Mac):**
```bash
RunUAT.sh BuildCookRun -project=<Project> -platform=Mac -clientconfig=Development -build -cook -stage -pak
```

**Full shipping build (Win64):**
```batch
RunUAT.bat BuildCookRun -project=<Project> -platform=Win64 -clientconfig=Shipping -build -cook -stage -package -pak -archive -archivedirectory=<OutputPath>
```

**Full shipping build (Mac):**
```bash
RunUAT.sh BuildCookRun -project=<Project> -platform=Mac -clientconfig=Shipping -build -cook -stage -package -pak -archive -archivedirectory=<OutputPath>
```

## Related Documentation

- **UE5 Official Documentation**: Build Operations (Automation)
- **UAT Commands**: Run `RunUAT.bat -list` to see all available commands
- **Build Configuration**: UnrealBuildTool documentation
- **Cooking & Packaging**: Content Cooking documentation

## Best Practices Summary

1. **Always use full absolute paths** for project and archive directories
2. **Quote paths with spaces** to avoid parsing errors
3. **Use iterative cooking** (`-iterativecooking`) for development builds
4. **Use Development config** during development, Shipping for production
5. **Verify builds locally** before pushing to CI/CD
6. **Clean builds** (`-clean`) when switching engine versions
7. **Test on target platform** - cooked content is platform-specific
8. **Monitor build logs** - UAT produces detailed logs in `<Project>/Saved/Logs/`
9. **Use `-unattended`** for automated/CI builds to avoid prompts
10. **Archive to version-controlled location** for build history tracking
