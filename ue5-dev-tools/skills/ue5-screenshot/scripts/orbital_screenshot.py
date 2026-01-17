# orbital_screenshot.py
# CLI wrapper for orbital screenshot capture
#
# This script provides command-line interface for the editor_capture.orbital module.
# Core functionality is in: site-packages/editor_capture/orbital.py
#
# Usage:
#   python orbital_screenshot.py --preset orthographic --level /Game/Maps/MyLevel
#   python orbital_screenshot.py --target 100+200+150 --distance 600

import unreal
import argparse
import sys

from editor_capture import orbital


def parse_resolution(value):
    """Parse resolution string like '1280x720' or '1920'."""
    if "x" in value.lower():
        parts = value.lower().split("x")
        if len(parts) != 2:
            raise argparse.ArgumentTypeError(f"Invalid resolution format: {value}")
        try:
            return (int(parts[0]), int(parts[1]))
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid resolution: {value}")
    else:
        try:
            size = int(value)
            return (size, size)
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid resolution: {value}")


def parse_target(value):
    """Parse target location string like '100+200+150'."""
    parts = value.split("+")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            f"Invalid target format: {value}. Expected X+Y+Z (e.g., 100+200+150)"
        )
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid target coordinates: {value}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Capture multi-angle screenshots for model validation in UE5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Presets:
  orthographic 6 orthographic views (front/back/left/right/top/bottom) [default]
  perspective  4 horizontal perspective views only
  birdseye     4 bird's eye views at 45-degree elevation
  all          All views (perspective + orthographic + birdseye)
  horizontal   Perspective + bird's eye views (no orthographic)
  technical    Same as orthographic (for technical drawings)

Examples:
  python orbital_screenshot.py --preset orthographic --level /Game/Maps/MyLevel
  python orbital_screenshot.py --target 100+200+150 --distance 600
  python orbital_screenshot.py --preset perspective --no-grid --no-gizmo
  python orbital_screenshot.py -r 1920x1080 -t 0+0+100
"""
    )

    parser.add_argument(
        "--preset", "-p",
        type=str,
        choices=list(orbital.VIEW_PRESETS.keys()),
        default="orthographic",
        help="View preset to use (default: orthographic)"
    )

    parser.add_argument(
        "--level", "-l",
        type=str,
        default="/Game/Maps/PunchingBagLevel",
        help="Level path to load (default: /Game/Maps/PunchingBagLevel)"
    )

    parser.add_argument(
        "--target", "-t",
        type=parse_target,
        default="200+150+250",
        help="Target location as X+Y+Z (default: 200+150+250)"
    )

    parser.add_argument(
        "--distance", "-d",
        type=float,
        default=400.0,
        help="Camera distance from target (default: 400)"
    )

    parser.add_argument(
        "--resolution", "-r",
        type=parse_resolution,
        default="800x600",
        help="Screenshot resolution as WIDTHxHEIGHT or single value (default: 800x600)"
    )

    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Output directory (default: <project>/Saved/Screenshots/Orbital)"
    )

    parser.add_argument(
        "--prefix",
        type=str,
        default="capture",
        help="Folder prefix for auto-incrementing capture folders (default: capture)"
    )

    parser.add_argument(
        "--ortho-width",
        type=float,
        default=600.0,
        help="Orthographic capture width in world units (default: 600)"
    )

    parser.add_argument("--no-grid", action="store_true", help="Disable reference grid")
    parser.add_argument("--grid-size", type=float, default=500.0, help="Grid size in units (default: 500)")
    parser.add_argument("--grid-divisions", type=int, default=10, help="Number of grid divisions (default: 10)")
    parser.add_argument("--no-gizmo", action="store_true", help="Disable axis gizmo indicator")
    parser.add_argument("--gizmo-size", type=float, default=80.0, help="Gizmo arrow length in units (default: 80)")
    parser.add_argument("--flat", action="store_true", help="Save all screenshots in single folder (no subfolders by type)")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Parse target
    if isinstance(args.target, str):
        target = parse_target(args.target)
    else:
        target = args.target
    TARGET = unreal.Vector(target[0], target[1], target[2])

    # Load level
    unreal.log(f"[INFO] Loading level: {args.level}")
    loaded_world = unreal.EditorLoadingAndSavingUtils.load_map(args.level)
    if not loaded_world:
        unreal.log_error(f"[ERROR] Failed to load level: {args.level}")
        sys.exit(1)

    unreal.log(f"[OK] Level loaded: {loaded_world.get_name()}")
    unreal.log(f"[INFO] Using preset: {args.preset}")

    # Parse resolution
    if isinstance(args.resolution, str):
        resolution = parse_resolution(args.resolution)
    else:
        resolution = args.resolution

    # Cleanup is handled internally by orbital.py via auto_cleanup=True (default)
    orbital.take_orbital_screenshots_with_preset(
        loaded_world=loaded_world,
        preset=args.preset,
        target_location=TARGET,
        distance=args.distance,
        output_dir=args.output_dir,
        folder_prefix=args.prefix,
        resolution_width=resolution[0],
        resolution_height=resolution[1],
        ortho_width=args.ortho_width,
        enable_grid=not args.no_grid,
        grid_size=args.grid_size,
        grid_divisions=args.grid_divisions,
        enable_gizmo=not args.no_gizmo,
        gizmo_size=args.gizmo_size,
        organize_by_type=not args.flat,
    )
