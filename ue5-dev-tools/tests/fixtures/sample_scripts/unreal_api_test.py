# Sample test script: Unreal API Test
# Used for E2E testing of unreal module access

import unreal

# Get engine version
version = unreal.SystemLibrary.get_engine_version()
print(f"Engine Version: {version}")

# Get project directory
project_dir = unreal.SystemLibrary.get_project_directory()
print(f"Project Directory: {project_dir}")

# Log a message
unreal.log("Test script executed successfully via remote execution")
