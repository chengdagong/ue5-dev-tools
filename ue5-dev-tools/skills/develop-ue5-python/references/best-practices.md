When developing UE5 Editor scripts using Python, following these best practices is crucial to ensure code **stability, performance, and maintainability**.

The UE5 Python API is essentially a wrapper around the C++ reflection system, which means many logic patterns are similar to C++ development, though there are considerations unique to Python.

---

### 1. Core Interaction Mechanisms (The Unreal Way)

#### 1.1 Use Subsystems instead of Static Libraries

In UE4, we frequently used static function libraries such as `EditorAssetLibrary`. In UE5, Epic recommends using **Subsystems**. Their lifecycle management is clearer and more aligned with object-oriented design.

- **Recommended:** `unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)`
- **Example:** Use `EditorActorSubsystem` instead of the legacy LevelLibrary.

```python
import unreal

# Recommended: Get subsystem instance
actor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
selected_actors = actor_subsystem.get_selected_level_actors()
```

#### 1.2 Must handle Undo/Redo (Transaction Management)

This is the most easily overlooked but most important point. If your script modifies the scene or assets without creating a Transaction, the user's `Ctrl+Z` will be ineffective, which is disastrous in a production environment.

- **Use:** `unreal.ScopedEditorTransaction` (Context Manager)

```python
# Wrap all modification operations in a with statement
with unreal.ScopedEditorTransaction("My Python Batch Rename"):
    for actor in selected_actors:
        actor.set_actor_label(f"Prefix_{actor.get_actor_label()}")
        # Users can now undo the entire loop's modifications with a single Ctrl+Z
```

#### 1.3 Use Asset Registry Wisely

Do not iterate through the Content directory and `load_asset` to find files. Loading assets is extremely slow and memory-intensive. The **Asset Registry** is an in-memory database that stores asset metadata (paths, class names, tags), allowing queries without loading the files themselves.

- **Scenario:** Find all Material Instances.
- **Practice:** Use `AssetRegistryHelpers`.

```python
asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

# Set up filter
filter = unreal.ARFilter(
    class_names=["MaterialInstanceConstant"],
    recursive_paths=True,
    package_paths=["/Game/Characters"]
)

# Get only data summaries (AssetData) without loading actual assets
asset_data_list = asset_registry.get_assets(filter)

for data in asset_data_list:
    print(data.package_name) # Extremely fast
    # Only load the asset when modification is strictly necessary
    # asset = data.get_asset()
```
