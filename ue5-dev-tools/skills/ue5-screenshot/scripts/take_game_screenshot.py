"""
Launch Unreal Engine game and get window handle
"""

import subprocess
import time
import ctypes
import os
from ctypes import wintypes
from PIL import Image

# Windows API definitions
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Set DPI awareness to get physical resolution
ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE

EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
IsWindowVisible = user32.IsWindowVisible

# Windows constants
PW_RENDERFULLCONTENT = 0x00000002  # PrintWindow: render DirectX/GPU-accelerated content
SRCCOPY = 0x00CC0020               # BitBlt: direct copy source
BI_RGB = 0                         # Bitmap compression: no compression
DIB_RGB_COLORS = 0                 # GetDIBits: RGB color table


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ('bmiHeader', BITMAPINFOHEADER),
        ('bmiColors', wintypes.DWORD * 3),
    ]


def capture_window(hwnd: int, crop_titlebar: bool = True) -> Image.Image | None:
    """
    Capture window using PrintWindow API (supports background/offscreen windows)

    Args:
        hwnd: Window handle
        crop_titlebar: If True, crop titlebar and only keep client area

    Returns:
        PIL Image object, None if failed
    """
    # Get window size (including border and titlebar)
    window_rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(window_rect))

    # Get client area size
    client_rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(client_rect))

    # Calculate titlebar and border sizes
    point = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    titlebar_height = point.y - window_rect.top
    border_left = point.x - window_rect.left

    width = window_rect.right - window_rect.left
    height = window_rect.bottom - window_rect.top

    if width <= 0 or height <= 0:
        print(f"Error: Invalid window size ({width}x{height})")
        return None

    # Create device context and bitmap
    hwnd_dc = user32.GetWindowDC(hwnd)
    mfc_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
    old_bitmap = gdi32.SelectObject(mfc_dc, bitmap)

    # Use PrintWindow to capture
    result = user32.PrintWindow(hwnd, mfc_dc, PW_RENDERFULLCONTENT)
    if not result:
        print("Warning: PrintWindow failed, trying BitBlt...")
        gdi32.BitBlt(mfc_dc, 0, 0, width, height, hwnd_dc, 0, 0, SRCCOPY)

    # Prepare BITMAPINFO structure
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height  # Negative = top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = BI_RGB

    # Read bitmap data
    buffer = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(mfc_dc, bitmap, 0, height, buffer, ctypes.byref(bmi), DIB_RGB_COLORS)

    # Cleanup resources
    gdi32.SelectObject(mfc_dc, old_bitmap)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mfc_dc)
    user32.ReleaseDC(hwnd, hwnd_dc)

    # Convert to PIL Image (BGRA -> RGBA)
    img = Image.frombuffer('RGBA', (width, height), buffer, 'raw', 'BGRA', 0, 1)

    # Crop titlebar and border, keep only client area
    if crop_titlebar and (titlebar_height > 0 or border_left > 0):
        client_width = client_rect.right - client_rect.left
        client_height = client_rect.bottom - client_rect.top
        img = img.crop((border_left, titlebar_height, border_left + client_width, titlebar_height + client_height))

    return img


def is_image_black(img: Image.Image, threshold: int = 10) -> bool:
    """Check if image is black (max brightness below threshold)"""
    grayscale = img.convert('L')
    return grayscale.getextrema()[1] < threshold


def get_window_title(hwnd: int) -> str:
    """Get window title"""
    length = GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def get_window_pid(hwnd: int) -> int:
    """Get window process ID"""
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def find_windows_by_pid(pid: int) -> list[tuple[int, str]]:
    """Find all visible windows with titles for a given process ID"""
    windows = []

    def enum_callback(hwnd, _):
        if IsWindowVisible(hwnd) and get_window_pid(hwnd) == pid:
            title = get_window_title(hwnd)
            if title:
                windows.append((hwnd, title))
        return True

    EnumWindows(EnumWindowsProc(enum_callback), 0)
    return windows


def find_uproject_file(start_dir: str | None = None) -> str | None:
    """
    Find .uproject file by searching upward from start_dir.

    Args:
        start_dir: Starting directory (defaults to cwd)

    Returns:
        Path to .uproject file or None if not found
    """
    from pathlib import Path

    # Try to use ue5_utils if available
    try:
        import sys
        # Navigate from scripts/ up to skills/, then into lib/
        lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib")
        lib_path = os.path.normpath(lib_path)
        if lib_path not in sys.path:
            sys.path.insert(0, lib_path)
        from ue5_utils import find_ue5_project_root  # type: ignore  # noqa: E402

        project_root = find_ue5_project_root(Path(start_dir) if start_dir else None)
        if project_root:
            uprojects = list(project_root.glob("*.uproject"))
            if uprojects:
                return str(uprojects[0])
    except ImportError:
        pass

    # Fallback: manual search
    current = Path(start_dir or os.getcwd()).resolve()

    while True:
        uprojects = list(current.glob("*.uproject"))
        if uprojects:
            return str(uprojects[0])

        parent = current.parent
        if parent == current:
            return None
        current = parent


def run_game_and_get_hwnd(
    project_path: str | None = None,
    ue_root: str = r"C:\Program Files\Epic Games\UE_5.7",
    timeout: int = 60,
    window_x: int | None = None,
    window_y: int | None = None,
    width: int = 1280,
    height: int = 720,
    level: str | None = None,
) -> tuple[int, str, subprocess.Popen] | None:
    """
    Launch game and get window handle

    Args:
        project_path: Path to .uproject file (auto-detected if None)
        ue_root: UE engine root directory
        timeout: Timeout waiting for window to appear (seconds)
        window_x: Window initial X coordinate (None = offscreen)
        window_y: Window initial Y coordinate (None = 0)
        width: Game window width in pixels
        height: Game window height in pixels
        level: Map/level to load (e.g., "/Game/Maps/MainMenu" or just "MainMenu")

    Returns:
        (hwnd, title, process) or None
    """
    if project_path is None:
        project_path = find_uproject_file()
        if project_path:
            print(f"Auto-detected project: {project_path}")
        else:
            print("Error: No .uproject file found. Use -p to specify the path.")
            return None

    game_exe = os.path.join(ue_root, "Engine", "Binaries", "Win64", "UnrealEditor-Cmd.exe")

    if not os.path.exists(game_exe):
        print(f"Error: {game_exe} not found")
        return None

    if not os.path.exists(project_path):
        print(f"Error: Project file {project_path} not found")
        return None

    screen_width = user32.GetSystemMetrics(0)

    # Build command
    cmd = [
        game_exe,
        project_path,
        "-game",
        "-windowed",
        f"-ResX={width}",
        f"-ResY={height}",
        "-NoSplash",
        "-NoLogTimes",
        "-LogCmds=Global None, LogTemp Log",
        f"-WinX={window_x if window_x is not None else screen_width}",
        f"-WinY={window_y if window_y is not None else 0}",
    ]

    # Add level/map parameter if specified (using -MapOverride)
    if level:
        # Validate that level contains only the name, no path characters
        level = level.strip().strip('"\'')  # Remove quotes if any

        if '/' in level or '\\' in level or '.' in level:
            print("Error: Level parameter must be a name only (e.g., 'PyramidLevel', not '/Game/Maps/PyramidLevel')")
            return None

        cmd.extend(["-MapOverride", level])

    prev_foreground = user32.GetForegroundWindow()
    process = subprocess.Popen(cmd)

    print(f"Waiting for game window...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        print(".", end="", flush=True)
        time.sleep(0.2)

        windows = find_windows_by_pid(process.pid)
        if windows:
            hwnd, title = windows[0]
            print(f" OK")

            if prev_foreground:
                user32.SetForegroundWindow(prev_foreground)

            return hwnd, title, process

    print(f" timeout")
    return None


def wait_for_game_ready(hwnd: int, timeout: int = 120, check_interval: float = 0.1) -> bool:
    """
    Wait for game screen to finish loading (no longer black)

    Returns:
        True if game loaded, False if timeout
    """
    print(f"Waiting for game to load...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        img = capture_window(hwnd, crop_titlebar=True)
        if img and not is_image_black(img):
                return True

        print(".", end="", flush=True)
        time.sleep(check_interval)

    print(f" timeout")
    return False


def parse_resolution(res_str: str) -> tuple[int, int]:
    """Parse resolution string like '1280x720' into (width, height)"""
    try:
        parts = res_str.lower().split('x')
        if len(parts) != 2:
            raise ValueError()
        width, height = int(parts[0]), int(parts[1])
        if width <= 0 or height <= 0:
            raise ValueError()
        return width, height
    except (ValueError, IndexError):
        raise ValueError(f"Invalid resolution format: {res_str}. Use format like 1280x720")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Launch UE game and capture screenshots in background")
    parser.add_argument("-p", "--project", type=str, required=True, help="Path to .uproject file")
    parser.add_argument("-l", "--level", type=str, required=True, help="Level/map name only, without path (e.g., 'PyramidLevel'). Do not include '/Game/Maps/' or any path separators.")
    parser.add_argument("-n", "--count", type=int, default=3, help="Number of screenshots")
    parser.add_argument("-i", "--interval", type=float, default=1.0, help="Interval between screenshots (seconds)")
    parser.add_argument("-o", "--output", type=str, default="screenshot", help="Output filename prefix")
    parser.add_argument("-r", "--resolution", type=str, default="1280x720", help="Game resolution (e.g. 1920x1080)")
    parser.add_argument("--ue-root", type=str, default=r"C:\Program Files\Epic Games\UE_5.7")
    parser.add_argument("--timeout", type=int, default=20, help="Window wait timeout (seconds). Default to 20s. Should be enough.")
    parser.add_argument("--load-timeout", type=int, default=20, help="Load wait timeout (seconds). Default to 20s. Should be enough.")
    parser.add_argument("--wait", action="store_true", help="Wait for user input before closing game")

    args = parser.parse_args()

    try:
        width, height = parse_resolution(args.resolution)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    result = run_game_and_get_hwnd(
        project_path=args.project,
        ue_root=args.ue_root,
        timeout=args.timeout,
        width=width,
        height=height,
        level=args.level,
    )
    if not result:
        print("Launch failed")
        return 1

    hwnd, _, process = result

    wait_for_game_ready(hwnd, timeout=args.load_timeout)

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    print(f"\nCapturing {args.count} screenshots...")
    saved_count = 0
    skipped_count = 0

    for i in range(args.count):
        img = capture_window(hwnd, crop_titlebar=True)
        if img:
            if is_image_black(img):
                print(f"Screenshot {i+1}/{args.count}: skipped (black)")
                skipped_count += 1
            else:
                saved_count += 1
                filename = f"{args.output}_{saved_count}.png"
                img.save(filename)
                print(f"Screenshot {i+1}/{args.count} saved: {filename} ({img.width}x{img.height})")
        else:
            print(f"Screenshot {i+1}/{args.count} failed")

        if i < args.count - 1:
            time.sleep(args.interval)

    print(f"\nComplete! Saved: {saved_count}, skipped: {skipped_count}")

    if args.wait:
        input("Press Enter to close game...")

    process.terminate()
    return 0


if __name__ == "__main__":
    exit(main())
