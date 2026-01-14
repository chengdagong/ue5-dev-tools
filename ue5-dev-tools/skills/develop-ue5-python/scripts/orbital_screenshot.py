# orbital_screenshot.py
# Captures multi-angle screenshots for model validation
# Supports perspective, orthographic, and bird's eye views
# Includes reference grid and axis indicator helpers
# Runs inside UE5 Editor via Python

import unreal
import math
import os


# ============================================
# VIEW CONFIGURATIONS
# ============================================

# Perspective horizontal views (original 4 views)
# Format: (yaw, pitch, view_name, display_name)
PERSPECTIVE_VIEWS = [
    (270, 0, "front", "正视图"),
    (180, 0, "left", "左视图"),
    (0, 0, "right", "右视图"),
    (90, 0, "back", "后视图"),
]

# Orthographic views (6 views for precise proportion checking)
ORTHOGRAPHIC_VIEWS = [
    (270, 0, "ortho_front", "正交正视图"),
    (90, 0, "ortho_back", "正交后视图"),
    (180, 0, "ortho_left", "正交左视图"),
    (0, 0, "ortho_right", "正交右视图"),
    (0, -90, "ortho_top", "正交俯视图"),
    (0, 90, "ortho_bottom", "正交仰视图"),
]

# Bird's eye views (4 views at 45-degree elevation)
BIRDSEYE_VIEWS = [
    (270, -45, "birdseye_front", "鸟瞰正视图"),
    (180, -45, "birdseye_left", "鸟瞰左视图"),
    (0, -45, "birdseye_right", "鸟瞰右视图"),
    (90, -45, "birdseye_back", "鸟瞰后视图"),
]


# ============================================
# UTILITY FUNCTIONS
# ============================================

def calculate_camera_transform(target, yaw_deg, pitch_deg, distance):
    """
    Calculate camera position and rotation from orbital parameters.

    Args:
        target: Target location (unreal.Vector)
        yaw_deg: Horizontal angle in degrees (0 = +X direction)
        pitch_deg: Vertical angle in degrees (0 = horizontal, -90 = looking down)
        distance: Distance from target

    Returns:
        tuple: (camera_location, camera_rotation)
    """
    yaw_rad = math.radians(yaw_deg)
    pitch_rad = math.radians(pitch_deg)

    # Calculate camera position
    # For pitch: cos(pitch) gives horizontal distance factor, sin(pitch) gives height
    horizontal_distance = distance * math.cos(pitch_rad)
    height_offset = distance * math.sin(-pitch_rad)  # Negative because -pitch = looking down = camera above

    cam_x = target.x + horizontal_distance * math.cos(yaw_rad)
    cam_y = target.y + horizontal_distance * math.sin(yaw_rad)
    cam_z = target.z + height_offset

    camera_location = unreal.Vector(cam_x, cam_y, cam_z)

    # Calculate rotation to look at target
    dir_x = target.x - cam_x
    dir_y = target.y - cam_y
    dir_z = target.z - cam_z

    # Yaw: horizontal direction
    calc_yaw = math.degrees(math.atan2(dir_y, dir_x))

    # Pitch: vertical angle
    horizontal_dist = math.sqrt(dir_x**2 + dir_y**2)
    calc_pitch = math.degrees(math.atan2(dir_z, horizontal_dist))

    camera_rotation = unreal.Rotator(roll=0, pitch=calc_pitch, yaw=calc_yaw)

    return camera_location, camera_rotation


# ============================================
# HELPER SPAWNING FUNCTIONS
# ============================================

def spawn_reference_grid(actor_subsystem, target_location, grid_size=500.0, divisions=10):
    """
    Spawn a temporary reference grid on the ground plane.

    Args:
        actor_subsystem: EditorActorSubsystem instance
        target_location: Center location for the grid
        grid_size: Total size of the grid
        divisions: Number of grid cells per axis

    Returns:
        list: List of spawned grid actors for cleanup
    """
    grid_actors = []
    cell_size = grid_size / divisions
    half_size = grid_size / 2.0

    # Grid at ground level (Z=0) or slightly below target
    grid_z = 0.5  # Slightly above ground to avoid z-fighting

    line_thickness = 2.0

    # Grid center
    center_x = target_location.x
    center_y = target_location.y

    # Spawn horizontal lines (along X axis)
    for i in range(divisions + 1):
        y_pos = center_y - half_size + (i * cell_size)

        line_actor = actor_subsystem.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(center_x, y_pos, grid_z)
        )

        if line_actor:
            line_actor.set_actor_label(f"OrbitalHelper_Grid_H_{i}")

            # Scale cube to make a line
            scale_x = grid_size / 100.0
            scale_y = line_thickness / 100.0
            scale_z = line_thickness / 100.0
            line_actor.set_actor_scale3d(unreal.Vector(scale_x, scale_y, scale_z))

            mesh_comp = line_actor.get_component_by_class(unreal.StaticMeshComponent)
            if mesh_comp:
                cube = unreal.load_asset("/Engine/BasicShapes/Cube")
                if cube:
                    mesh_comp.set_static_mesh(cube)

            grid_actors.append(line_actor)

    # Spawn vertical lines (along Y axis)
    for i in range(divisions + 1):
        x_pos = center_x - half_size + (i * cell_size)

        line_actor = actor_subsystem.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(x_pos, center_y, grid_z)
        )

        if line_actor:
            line_actor.set_actor_label(f"OrbitalHelper_Grid_V_{i}")

            # Scale cube to make a line (rotated 90 degrees)
            scale_x = line_thickness / 100.0
            scale_y = grid_size / 100.0
            scale_z = line_thickness / 100.0
            line_actor.set_actor_scale3d(unreal.Vector(scale_x, scale_y, scale_z))

            mesh_comp = line_actor.get_component_by_class(unreal.StaticMeshComponent)
            if mesh_comp:
                cube = unreal.load_asset("/Engine/BasicShapes/Cube")
                if cube:
                    mesh_comp.set_static_mesh(cube)

            grid_actors.append(line_actor)

    unreal.log(f"  [GRID] Spawned {len(grid_actors)} grid lines")
    return grid_actors


def spawn_axis_gizmo(actor_subsystem, target_location, arrow_length=80.0):
    """
    Spawn RGB axis indicator arrows at the target location.

    Args:
        actor_subsystem: EditorActorSubsystem instance
        target_location: Location for the gizmo origin
        arrow_length: Length of each axis arrow

    Returns:
        list: List of spawned gizmo actors for cleanup
    """
    gizmo_actors = []

    shaft_radius = arrow_length * 0.05  # 5% of length
    cone_length = arrow_length * 0.2    # 20% of length
    cone_radius = arrow_length * 0.1    # 10% of length
    shaft_length = arrow_length - cone_length

    # Gizmo origin (slightly offset from target to be visible)
    base = unreal.Vector(
        target_location.x - arrow_length * 0.5,
        target_location.y - arrow_length * 0.5,
        target_location.z - arrow_length * 0.5
    )

    # Axis definitions
    axes = [
        {"name": "X", "dir": (1, 0, 0), "rotation": unreal.Rotator(roll=0, pitch=0, yaw=90)},
        {"name": "Y", "dir": (0, 1, 0), "rotation": unreal.Rotator(roll=0, pitch=0, yaw=0)},
        {"name": "Z", "dir": (0, 0, 1), "rotation": unreal.Rotator(roll=0, pitch=-90, yaw=0)},
    ]

    for axis in axes:
        dx, dy, dz = axis["dir"]

        # Shaft center position
        shaft_center = unreal.Vector(
            base.x + dx * (shaft_length / 2),
            base.y + dy * (shaft_length / 2),
            base.z + dz * (shaft_length / 2)
        )

        # Spawn shaft (cylinder)
        shaft = actor_subsystem.spawn_actor_from_class(
            unreal.StaticMeshActor,
            shaft_center
        )

        if shaft:
            shaft.set_actor_label(f"OrbitalHelper_Gizmo_{axis['name']}_Shaft")
            shaft.set_actor_rotation(axis["rotation"], False)

            # Scale cylinder
            scale_xy = (shaft_radius * 2) / 100.0
            scale_z = shaft_length / 100.0
            shaft.set_actor_scale3d(unreal.Vector(scale_xy, scale_xy, scale_z))

            mesh_comp = shaft.get_component_by_class(unreal.StaticMeshComponent)
            if mesh_comp:
                cylinder = unreal.load_asset("/Engine/BasicShapes/Cylinder")
                if cylinder:
                    mesh_comp.set_static_mesh(cylinder)

            gizmo_actors.append(shaft)

        # Cone center position (at tip of shaft)
        cone_center = unreal.Vector(
            base.x + dx * (shaft_length + cone_length / 2),
            base.y + dy * (shaft_length + cone_length / 2),
            base.z + dz * (shaft_length + cone_length / 2)
        )

        # Spawn cone (arrowhead)
        cone = actor_subsystem.spawn_actor_from_class(
            unreal.StaticMeshActor,
            cone_center
        )

        if cone:
            cone.set_actor_label(f"OrbitalHelper_Gizmo_{axis['name']}_Cone")
            cone.set_actor_rotation(axis["rotation"], False)

            # Scale cone
            scale_xy = (cone_radius * 2) / 100.0
            scale_z = cone_length / 100.0
            cone.set_actor_scale3d(unreal.Vector(scale_xy, scale_xy, scale_z))

            mesh_comp = cone.get_component_by_class(unreal.StaticMeshComponent)
            if mesh_comp:
                cone_mesh = unreal.load_asset("/Engine/BasicShapes/Cone")
                if cone_mesh:
                    mesh_comp.set_static_mesh(cone_mesh)

            gizmo_actors.append(cone)

    unreal.log(f"  [GIZMO] Spawned {len(gizmo_actors)} gizmo parts (X/Y/Z axes)")
    return gizmo_actors


# ============================================
# CAPTURE FUNCTIONS
# ============================================

def capture_single_view(
    actor_subsystem,
    loaded_world,
    camera_location,
    camera_rotation,
    view_name,
    display_name,
    output_dir,
    filename_prefix,
    resolution,
    is_orthographic=False,
    ortho_width=600.0
):
    """
    Capture a single screenshot from the specified camera position.

    Returns:
        str or None: Path to saved file, or None if failed
    """
    unreal.log(f"\n[{view_name.upper()}] {display_name} Processing...")

    # Spawn SceneCapture2D actor
    capture_actor = actor_subsystem.spawn_actor_from_class(
        unreal.SceneCapture2D,
        camera_location
    )

    if not capture_actor:
        unreal.log_warning(f"  [WARNING] Failed to spawn SceneCapture2D")
        return None

    capture_actor.set_actor_rotation(camera_rotation, False)
    capture_actor.set_actor_label(f"OrbitalCapture_{view_name}")

    # Get the capture component
    capture_component = capture_actor.capture_component2d

    # Configure projection type
    if is_orthographic:
        capture_component.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
        capture_component.set_editor_property("ortho_width", ortho_width)

    # Create render target
    render_target = unreal.RenderingLibrary.create_render_target2d(
        loaded_world,
        resolution,
        resolution,
        unreal.TextureRenderTargetFormat.RTF_RGBA8
    )

    if not render_target:
        unreal.log_warning(f"  [WARNING] Failed to create render target")
        return None

    # Configure capture component
    capture_component.texture_target = render_target
    capture_component.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR

    # Capture the scene (synchronous)
    capture_component.capture_scene()

    # Export to file
    screenshot_filename = f"{filename_prefix}_{view_name}"
    unreal.RenderingLibrary.export_render_target(
        loaded_world,
        render_target,
        output_dir,
        screenshot_filename
    )

    # Handle file extension
    temp_path = os.path.join(output_dir, screenshot_filename)
    final_path = os.path.join(output_dir, f"{screenshot_filename}.png")

    saved_path = None
    if os.path.exists(temp_path):
        if os.path.exists(final_path):
            os.remove(final_path)
        os.rename(temp_path, final_path)
        saved_path = final_path
        unreal.log(f"  [OK] Saved: {screenshot_filename}.png")
    elif os.path.exists(final_path):
        saved_path = final_path
        unreal.log(f"  [OK] Saved: {screenshot_filename}.png")
    else:
        unreal.log_warning(f"  [WARNING] File not found: {screenshot_filename}")

    return saved_path


# ============================================
# MAIN CAPTURE FUNCTION
# ============================================

def take_orbital_screenshots(
    loaded_world,
    target_location=unreal.Vector(0, 0, 0),
    distance=500.0,
    output_dir=None,
    filename_prefix="screenshot",
    resolution=1920,
    # View group toggles
    enable_perspective_views=True,
    enable_orthographic_views=True,
    enable_birdseye_views=True,
    ortho_width=600.0,
    # Helper toggles
    enable_grid=True,
    grid_size=500.0,
    grid_divisions=10,
    enable_gizmo=True,
    gizmo_size=80.0,
    # Output organization
    organize_by_type=True,
):
    """
    Take multi-angle screenshots around a target location for model validation.

    Supports three view groups:
    - Perspective horizontal views (4 views)
    - Orthographic views (6 views: front, back, left, right, top, bottom)
    - Bird's eye views (4 views at 45-degree elevation)

    Can optionally spawn temporary helpers:
    - Reference grid on ground plane
    - RGB axis indicator (gizmo)

    Args:
        loaded_world: The loaded world/level to capture
        target_location: Center point to orbit around (unreal.Vector)
        distance: Distance from target in units (default: 500)
        output_dir: Directory to save screenshots (default: project's Saved/Screenshots/Orbital)
        filename_prefix: Prefix for screenshot filenames (default: "screenshot")
        resolution: Screenshot resolution (default: 1920)
        enable_perspective_views: Enable 4 horizontal perspective views (default: True)
        enable_orthographic_views: Enable 6 orthographic views (default: True)
        enable_birdseye_views: Enable 4 bird's eye views (default: True)
        ortho_width: Width of orthographic capture in world units (default: 600)
        enable_grid: Spawn reference grid during capture (default: True)
        grid_size: Size of reference grid in units (default: 500)
        grid_divisions: Number of grid divisions (default: 10)
        enable_gizmo: Spawn axis indicator during capture (default: True)
        gizmo_size: Size of gizmo arrows in units (default: 80)
        organize_by_type: Create subfolders for different view types (default: True)

    Returns:
        dict: Dictionary with view type keys and lists of saved file paths
    """

    if not loaded_world:
        unreal.log_error("[ERROR] loaded_world is required")
        return {}

    # Set default output directory
    if output_dir is None:
        project_dir = unreal.Paths.project_dir()
        output_dir = os.path.join(project_dir, "Saved", "Screenshots", "Orbital")

    # Get actor subsystem
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if not actor_subsystem:
        unreal.log_error("[ERROR] Failed to get EditorActorSubsystem")
        return {}

    # Count total views
    total_views = 0
    if enable_perspective_views:
        total_views += len(PERSPECTIVE_VIEWS)
    if enable_orthographic_views:
        total_views += len(ORTHOGRAPHIC_VIEWS)
    if enable_birdseye_views:
        total_views += len(BIRDSEYE_VIEWS)

    # Print configuration
    unreal.log("=" * 60)
    unreal.log("[INFO] Starting Multi-Angle Screenshot Capture")
    unreal.log(f"  Level: {loaded_world.get_name()}")
    unreal.log(f"  Target: ({target_location.x}, {target_location.y}, {target_location.z})")
    unreal.log(f"  Distance: {distance}")
    unreal.log(f"  Resolution: {resolution}x{resolution}")
    unreal.log(f"  Views: {total_views} total")
    unreal.log(f"    - Perspective: {'ON' if enable_perspective_views else 'OFF'}")
    unreal.log(f"    - Orthographic: {'ON' if enable_orthographic_views else 'OFF'}")
    unreal.log(f"    - Bird's Eye: {'ON' if enable_birdseye_views else 'OFF'}")
    unreal.log(f"  Helpers: Grid={'ON' if enable_grid else 'OFF'}, Gizmo={'ON' if enable_gizmo else 'OFF'}")
    unreal.log(f"  Output: {output_dir}")
    unreal.log("=" * 60)

    # Results dictionary
    results = {
        "perspective": [],
        "orthographic": [],
        "birdseye": []
    }

    # Spawn helpers (cleanup handled by transaction undo)
    if enable_grid:
        spawn_reference_grid(actor_subsystem, target_location, grid_size, grid_divisions)

    if enable_gizmo:
        spawn_axis_gizmo(actor_subsystem, target_location, gizmo_size)

    # Capture perspective views
    if enable_perspective_views:
        unreal.log("\n--- PERSPECTIVE VIEWS ---")

        if organize_by_type:
            persp_dir = os.path.join(output_dir, "perspective")
            os.makedirs(persp_dir, exist_ok=True)
        else:
            persp_dir = output_dir
            os.makedirs(persp_dir, exist_ok=True)

        for yaw, pitch, view_name, display_name in PERSPECTIVE_VIEWS:
            cam_loc, cam_rot = calculate_camera_transform(
                target_location, yaw, pitch, distance
            )

            saved_path = capture_single_view(
                actor_subsystem, loaded_world,
                cam_loc, cam_rot,
                view_name, display_name,
                persp_dir, filename_prefix, resolution,
                is_orthographic=False
            )

            if saved_path:
                results["perspective"].append(saved_path)

        # Capture orthographic views
        if enable_orthographic_views:
            unreal.log("\n--- ORTHOGRAPHIC VIEWS ---")

            if organize_by_type:
                ortho_dir = os.path.join(output_dir, "orthographic")
                os.makedirs(ortho_dir, exist_ok=True)
            else:
                ortho_dir = output_dir
                os.makedirs(ortho_dir, exist_ok=True)

            for yaw, pitch, view_name, display_name in ORTHOGRAPHIC_VIEWS:
                cam_loc, cam_rot = calculate_camera_transform(
                    target_location, yaw, pitch, distance
                )

                saved_path = capture_single_view(
                    actor_subsystem, loaded_world,
                    cam_loc, cam_rot,
                    view_name, display_name,
                    ortho_dir, filename_prefix, resolution,
                    is_orthographic=True,
                    ortho_width=ortho_width
                )

                if saved_path:
                    results["orthographic"].append(saved_path)

        # Capture bird's eye views
        if enable_birdseye_views:
            unreal.log("\n--- BIRD'S EYE VIEWS ---")

            if organize_by_type:
                bird_dir = os.path.join(output_dir, "birdseye")
                os.makedirs(bird_dir, exist_ok=True)
            else:
                bird_dir = output_dir
                os.makedirs(bird_dir, exist_ok=True)

            for yaw, pitch, view_name, display_name in BIRDSEYE_VIEWS:
                cam_loc, cam_rot = calculate_camera_transform(
                    target_location, yaw, pitch, distance
                )

                saved_path = capture_single_view(
                    actor_subsystem, loaded_world,
                    cam_loc, cam_rot,
                    view_name, display_name,
                    bird_dir, filename_prefix, resolution,
                    is_orthographic=False
                )

                if saved_path:
                    results["birdseye"].append(saved_path)

    # Summary
    total_saved = sum(len(v) for v in results.values())

    unreal.log("\n" + "=" * 60)
    unreal.log("[COMPLETE] Multi-Angle Screenshot Capture Finished")
    unreal.log(f"  Total screenshots: {total_saved}/{total_views}")
    unreal.log(f"    - Perspective: {len(results['perspective'])}")
    unreal.log(f"    - Orthographic: {len(results['orthographic'])}")
    unreal.log(f"    - Bird's Eye: {len(results['birdseye'])}")
    unreal.log(f"  Output directory: {output_dir}")
    unreal.log("=" * 60)

    return results


# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    # ============================================
    # CONFIGURATION - Modify these parameters
    # ============================================

    # Required: Level path
    LEVEL_PATH = "/Game/Maps/PunchingBagLevel"

    # Target location to orbit around
    TARGET = unreal.Vector(200, 150, 250)

    # Camera distance from target
    ORBIT_DISTANCE = 400.0

    # Output settings
    OUTPUT_PREFIX = "orbital"
    RESOLUTION = 1920

    # View group toggles (set to False to disable)
    ENABLE_PERSPECTIVE = True   # 4 horizontal views
    ENABLE_ORTHOGRAPHIC = True  # 6 orthographic views (front/back/left/right/top/bottom)
    ENABLE_BIRDSEYE = True      # 4 bird's eye views at 45 degrees

    # Orthographic capture width (world units visible in orthographic view)
    ORTHO_WIDTH = 600.0

    # Helper toggles
    ENABLE_GRID = True          # Reference grid on ground
    GRID_SIZE = 500.0           # Grid total size
    GRID_DIVISIONS = 10         # Number of grid cells

    ENABLE_GIZMO = True         # RGB axis indicator
    GIZMO_SIZE = 80.0           # Axis arrow length

    # Output organization
    ORGANIZE_BY_TYPE = True     # Create subfolders (perspective/, orthographic/, birdseye/)

    # ============================================

    # Load level BEFORE transaction (load_map resets transaction history)
    unreal.log(f"[INFO] Loading level: {LEVEL_PATH}")
    loaded_world = unreal.EditorLoadingAndSavingUtils.load_map(LEVEL_PATH)
    if not loaded_world:
        unreal.log_error(f"[ERROR] Failed to load level: {LEVEL_PATH}")
    else:
        unreal.log(f"[OK] Level loaded: {loaded_world.get_name()}")

        with unreal.ScopedEditorTransaction("Orbital Screenshot Capture") as trans:
            take_orbital_screenshots(
                loaded_world=loaded_world,
                target_location=TARGET,
                distance=ORBIT_DISTANCE,
                filename_prefix=OUTPUT_PREFIX,
                resolution=RESOLUTION,
                enable_perspective_views=ENABLE_PERSPECTIVE,
                enable_orthographic_views=ENABLE_ORTHOGRAPHIC,
                enable_birdseye_views=ENABLE_BIRDSEYE,
                ortho_width=ORTHO_WIDTH,
                enable_grid=ENABLE_GRID,
                grid_size=GRID_SIZE,
                grid_divisions=GRID_DIVISIONS,
                enable_gizmo=ENABLE_GIZMO,
                gizmo_size=GIZMO_SIZE,
                organize_by_type=ORGANIZE_BY_TYPE,
            )

        unreal.SystemLibrary.execute_console_command(None, "TRANSACTION UNDO")

