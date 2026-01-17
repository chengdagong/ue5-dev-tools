# ue5_editor_screenshot.py
# UE5 编辑器截图工具
# 功能：资产编辑器操作、窗口管理、截图
# 支持：蓝图、骨架、材质、动画等资产类型

import unreal
import time
import os
import ctypes
import argparse
from ctypes import wintypes

# Windows API constants
_PW_RENDERFULLCONTENT = 0x00000002
_SRCCOPY = 0x00CC0020
_BI_RGB = 0
_DIB_RGB_COLORS = 0
_INPUT_TYPE_KEYBOARD = 1
_INPUT_TYPE_MOUSE = 0
_KEYEVENTF_KEYUP = 0x0002
_MOUSEEVENTF_LEFTDOWN = 0x0002
_MOUSEEVENTF_LEFTUP = 0x0004

# Virtual key codes
_VK_CONTROL = 0x11
_VK_SHIFT = 0x10
_VK_MENU = 0x12  # Alt key

# Number keys (1-9) for tab switching
_VK_NUMBERS = {
    1: 0x31,  # '1' key
    2: 0x32,  # '2' key
    3: 0x33,  # '3' key
    4: 0x34,  # '4' key
    5: 0x35,  # '5' key
    6: 0x36,  # '6' key
    7: 0x37,  # '7' key
    8: 0x38,  # '8' key
    9: 0x39,  # '9' key
}

# Windows API handles
_user32 = ctypes.windll.user32
_gdi32 = ctypes.windll.gdi32


# ============================================
# Windows API Structures
# ============================================

class _BITMAPINFOHEADER(ctypes.Structure):
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


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ('bmiHeader', _BITMAPINFOHEADER),
        ('bmiColors', wintypes.DWORD * 3),
    ]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', wintypes.WORD),
        ('wScan', wintypes.WORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong)),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ('dx', wintypes.LONG),
        ('dy', wintypes.LONG),
        ('mouseData', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT_KEYBOARD(ctypes.Structure):
    _fields_ = [
        ('type', wintypes.DWORD),
        ('ki', _KEYBDINPUT),
        ('padding', ctypes.c_ubyte * 8),
    ]


class _INPUT_MOUSE(ctypes.Structure):
    _fields_ = [
        ('type', wintypes.DWORD),
        ('mi', _MOUSEINPUT),
        ('padding', ctypes.c_ubyte * 8),
    ]


# ============================================
# Asset Loading and Validation Helpers
# ============================================

def _load_asset(asset_path, expected_type=None):
    """
    Load and validate an asset.

    Args:
        asset_path: The asset path to load
        expected_type: Optional type to validate against (e.g., unreal.Blueprint)

    Returns:
        tuple: (asset, error_message) - asset is None if failed
    """
    if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        return None, f"Asset does not exist: {asset_path}"

    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not asset:
        return None, f"Failed to load asset: {asset_path}"

    if expected_type and not isinstance(asset, expected_type):
        return None, f"Asset is not a {expected_type.__name__}: {asset_path}"

    return asset, None


def _get_editor_subsystem():
    """
    Get the AssetEditorSubsystem.

    Returns:
        tuple: (subsystem, error_message) - subsystem is None if failed
    """
    subsystem = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
    if not subsystem:
        return None, "Failed to get AssetEditorSubsystem"
    return subsystem, None


def _ensure_directory(path):
    """Ensure the directory for a file path exists."""
    output_dir = os.path.dirname(path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)


# ============================================
# Asset Editor Functions
# ============================================

def open_asset_editor(asset_path):
    """
    Open the editor for a single asset.

    Args:
        asset_path: The asset path (e.g., "/Game/Blueprints/BP_MyBlueprint")

    Returns:
        bool: True if successful, False otherwise
    """
    asset, error = _load_asset(asset_path)
    if error:
        unreal.log_error(f"[ERROR] {error}")
        return False

    subsystem, error = _get_editor_subsystem()
    if error:
        unreal.log_error(f"[ERROR] {error}")
        return False

    subsystem.open_editor_for_assets([asset])
    unreal.log(f"[OK] Opened editor for: {asset_path}")
    return True


def open_blueprint_editor(blueprint_path):
    """
    Open the Blueprint editor for a Blueprint asset.

    Args:
        blueprint_path: The Blueprint asset path

    Returns:
        bool: True if successful, False otherwise
    """
    asset, error = _load_asset(blueprint_path, unreal.Blueprint)
    if error:
        unreal.log_error(f"[ERROR] {error}")
        return False

    subsystem, error = _get_editor_subsystem()
    if error:
        unreal.log_error(f"[ERROR] {error}")
        return False

    subsystem.open_editor_for_assets([asset])
    unreal.log(f"[OK] Opened Blueprint editor for: {blueprint_path}")
    return True


def open_multiple_asset_editors(asset_paths):
    """
    Open editors for multiple assets at once.

    Args:
        asset_paths: List of asset paths to open

    Returns:
        dict: {"success": [paths], "failed": [paths]}
    """
    results = {"success": [], "failed": []}

    if not asset_paths:
        unreal.log_warning("[WARNING] No asset paths provided")
        return results

    assets_to_open = []
    for path in asset_paths:
        asset, error = _load_asset(path)
        if error:
            unreal.log_error(f"[ERROR] {error}")
            results["failed"].append(path)
        else:
            assets_to_open.append((path, asset))

    if assets_to_open:
        subsystem, error = _get_editor_subsystem()
        if subsystem:
            subsystem.open_editor_for_assets([asset for _, asset in assets_to_open])
            for path, _ in assets_to_open:
                unreal.log(f"[OK] Opened editor for: {path}")
                results["success"].append(path)
        else:
            unreal.log_error(f"[ERROR] {error}")
            for path, _ in assets_to_open:
                results["failed"].append(path)

    unreal.log("=" * 50)
    unreal.log(f"[SUMMARY] Opened: {len(results['success'])}, Failed: {len(results['failed'])}")
    return results


def close_asset_editor(asset_path):
    """
    Close the editor for a specific asset.

    Args:
        asset_path: The asset path to close

    Returns:
        bool: True if successful, False otherwise
    """
    asset, error = _load_asset(asset_path)
    if error:
        unreal.log_error(f"[ERROR] {error}")
        return False

    subsystem, error = _get_editor_subsystem()
    if error:
        unreal.log_error(f"[ERROR] {error}")
        return False

    subsystem.close_all_editors_for_asset(asset)
    unreal.log(f"[OK] Closed editor for: {asset_path}")
    return True


def close_all_asset_editors():
    """
    Close all open asset editors.

    Returns:
        bool: True if successful, False otherwise
    """
    subsystem, error = _get_editor_subsystem()
    if error:
        unreal.log_error(f"[ERROR] {error}")
        return False

    subsystem.close_all_asset_editors()
    unreal.log("[OK] Closed all asset editors")
    return True


# ============================================
# Window Management Functions
# ============================================

def _find_ue5_window():
    """
    Find the UE5 Editor window by current process ID.

    Returns:
        int: Window handle (hwnd) if found, None otherwise
    """
    pid = os.getpid()
    found_hwnd = []

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def enum_callback(hwnd, lparam):
        if not _user32.IsWindowVisible(hwnd):
            return True

        window_pid = ctypes.c_ulong()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))

        if window_pid.value == pid:
            length = _user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                _user32.GetWindowTextW(hwnd, buff, length + 1)
                found_hwnd.append((hwnd, buff.value))
                return False
        return True

    _user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

    if found_hwnd:
        hwnd, title = found_hwnd[0]
        unreal.log(f"[INFO] Found UE5 window (PID={pid}): {title}")
        return hwnd
    return None


def _get_window_rect(hwnd):
    """Get window rectangle as (left, top, right, bottom)."""
    rect = wintypes.RECT()
    _user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect


# ============================================
# Input Simulation Functions
# ============================================

def _send_key(vk_code, flags=0):
    """
    Send a single key press using Windows API.

    Args:
        vk_code: Virtual key code
        flags: Key event flags (0=down, KEYEVENTF_KEYUP=up)
    """
    inp = _INPUT_KEYBOARD()
    inp.type = _INPUT_TYPE_KEYBOARD
    inp.ki.wVk = vk_code
    inp.ki.wScan = 0
    inp.ki.dwFlags = flags
    inp.ki.time = 0
    inp.ki.dwExtraInfo = None
    _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT_KEYBOARD))


def _press_key_combo(modifiers, key_vk):
    """
    Press a key combination (e.g., Shift+F1).

    Args:
        modifiers: List of modifier virtual key codes
        key_vk: Main key virtual key code
    """
    for mod in modifiers:
        _send_key(mod, flags=0)
        time.sleep(0.02)

    _send_key(key_vk, flags=0)
    time.sleep(0.02)
    _send_key(key_vk, flags=_KEYEVENTF_KEYUP)
    time.sleep(0.02)

    for mod in reversed(modifiers):
        _send_key(mod, flags=_KEYEVENTF_KEYUP)
        time.sleep(0.02)


def _click_at(x, y):
    """
    Simulate a mouse click at the given screen coordinates.

    Args:
        x: Screen X coordinate
        y: Screen Y coordinate
    """
    _user32.SetCursorPos(x, y)
    time.sleep(0.05)

    inp = _INPUT_MOUSE()
    inp.type = _INPUT_TYPE_MOUSE
    inp.mi.dx = 0
    inp.mi.dy = 0
    inp.mi.mouseData = 0
    inp.mi.time = 0
    inp.mi.dwExtraInfo = None

    inp.mi.dwFlags = _MOUSEEVENTF_LEFTDOWN
    _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT_MOUSE))
    time.sleep(0.05)

    inp.mi.dwFlags = _MOUSEEVENTF_LEFTUP
    _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT_MOUSE))
    time.sleep(0.05)


def _switch_to_tab(hwnd=None, tab_number=1):
    """
    Switch to a specific tab in Blueprint Editor using keyboard shortcut.
    Clicks window center to ensure focus, then sends Ctrl+Shift+Alt+<number>.

    Args:
        hwnd: Window handle (optional, will find UE5 window if not provided)
        tab_number: Tab number to switch to (1-9, default: 1 for Viewport)

    Returns:
        bool: True if key combo was sent, False otherwise
    """
    if tab_number not in _VK_NUMBERS:
        unreal.log_error(f"[ERROR] Invalid tab number: {tab_number} (must be 1-9)")
        return False

    if hwnd is None:
        hwnd = _find_ue5_window()

    if not hwnd:
        unreal.log_error("[ERROR] Cannot switch tab: UE5 window not found")
        return False

    _user32.SetForegroundWindow(hwnd)
    time.sleep(0.2)

    window_rect = _get_window_rect(hwnd)
    center_x = (window_rect.left + window_rect.right) // 2
    center_y = (window_rect.top + window_rect.bottom) // 2

    unreal.log(f"[INFO] Clicking window center at ({center_x}, {center_y}) to ensure focus...")
    _click_at(center_x, center_y)
    time.sleep(0.3)

    unreal.log(f"[INFO] Sending Ctrl+Shift+Alt+{tab_number} to switch to tab {tab_number}...")
    _press_key_combo([_VK_CONTROL, _VK_SHIFT, _VK_MENU], _VK_NUMBERS[tab_number])
    time.sleep(0.5)
    return True


# Legacy alias for backward compatibility
def _switch_to_viewport_tab(hwnd=None):
    """Switch to viewport tab (tab 1). Legacy wrapper for _switch_to_tab."""
    return _switch_to_tab(hwnd, tab_number=1)


# ============================================
# Screenshot Functions
# ============================================

def _capture_window_printwindow(hwnd, crop_titlebar=True):
    """
    Capture window using PrintWindow API (works for background/hidden windows).

    Args:
        hwnd: Window handle
        crop_titlebar: If True, crop titlebar and keep only client area

    Returns:
        PIL Image object, None if failed
    """
    from PIL import Image

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    window_rect = _get_window_rect(hwnd)
    client_rect = wintypes.RECT()
    _user32.GetClientRect(hwnd, ctypes.byref(client_rect))

    point = wintypes.POINT(0, 0)
    _user32.ClientToScreen(hwnd, ctypes.byref(point))
    titlebar_height = point.y - window_rect.top
    border_left = point.x - window_rect.left

    width = window_rect.right - window_rect.left
    height = window_rect.bottom - window_rect.top
    unreal.log(f"[DEBUG] Capture window rect: ({window_rect.left}, {window_rect.top}) size: {width}x{height}")

    if width <= 0 or height <= 0:
        unreal.log_error(f"[ERROR] Invalid window size ({width}x{height})")
        return None

    hwnd_dc = _user32.GetWindowDC(hwnd)
    mfc_dc = _gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = _gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
    old_bitmap = _gdi32.SelectObject(mfc_dc, bitmap)

    result = _user32.PrintWindow(hwnd, mfc_dc, _PW_RENDERFULLCONTENT)
    if not result:
        unreal.log_warning("[WARNING] PrintWindow failed, trying BitBlt...")
        _gdi32.BitBlt(mfc_dc, 0, 0, width, height, hwnd_dc, 0, 0, _SRCCOPY)

    bmi = _BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = _BI_RGB

    buffer = ctypes.create_string_buffer(width * height * 4)
    _gdi32.GetDIBits(mfc_dc, bitmap, 0, height, buffer, ctypes.byref(bmi), _DIB_RGB_COLORS)

    _gdi32.SelectObject(mfc_dc, old_bitmap)
    _gdi32.DeleteObject(bitmap)
    _gdi32.DeleteDC(mfc_dc)
    _user32.ReleaseDC(hwnd, hwnd_dc)

    img = Image.frombuffer('RGBA', (width, height), buffer, 'raw', 'BGRA', 0, 1)

    if crop_titlebar and (titlebar_height > 0 or border_left > 0):
        client_width = client_rect.right - client_rect.left
        client_height = client_rect.bottom - client_rect.top
        img = img.crop((border_left, titlebar_height, border_left + client_width, titlebar_height + client_height))

    return img


def _capture_ue5_window(output_path, crop_titlebar=True):
    """
    Capture the UE5 Editor window using PrintWindow API.

    Args:
        output_path: Path to save the screenshot
        crop_titlebar: If True, crop titlebar and keep only client area

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        _ensure_directory(output_path)

        hwnd = _find_ue5_window()
        if not hwnd:
            unreal.log_error("[ERROR] Could not find UE5 Editor window")
            return False

        img = _capture_window_printwindow(hwnd, crop_titlebar)
        if img is None:
            unreal.log_error("[ERROR] Failed to capture window")
            return False

        img.save(output_path)
        unreal.log(f"[OK] UE5 window screenshot saved to: {output_path} ({img.width}x{img.height})")
        return True

    except Exception as e:
        unreal.log_error(f"[ERROR] Failed to capture UE5 window: {e}")
        return False


def _capture_screen(output_path):
    """
    Capture the entire screen using PIL.

    Args:
        output_path: Path to save the screenshot

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from PIL import ImageGrab
    except ImportError:
        unreal.log_error("[ERROR] PIL/Pillow not installed. Run: pip install Pillow")
        return False

    try:
        _ensure_directory(output_path)
        screenshot = ImageGrab.grab()
        screenshot.save(output_path)
        unreal.log(f"[OK] Full screen screenshot saved to: {output_path}")
        return True
    except Exception as e:
        unreal.log_error(f"[ERROR] Failed to capture screenshot: {e}")
        return False


# ============================================
# Main Screenshot Functions
# ============================================

def open_asset_editor_with_screenshot(asset_path, output_path, delay=3.0, capture_ue5_only=True, tab_number=None):
    """
    Open an asset editor and take a screenshot after a delay.

    Flow when capture_ue5_only=True:
    1. Open blueprint editor
    2. Switch to specified tab (if tab_number is set)
    3. Take screenshot

    Args:
        asset_path: The asset path to open
        output_path: Path to save the screenshot
        delay: Seconds to wait before taking screenshot (default: 3.0)
        capture_ue5_only: If True, capture only UE5 window; if False, capture full screen
        tab_number: Tab number to switch to (1-9, None to skip switching)

    Returns:
        dict: {"opened": bool, "screenshot": bool, "screenshot_path": str}
    """
    result = {"opened": False, "screenshot": False, "screenshot_path": None}

    if capture_ue5_only:
        prev_active_hwnd = _user32.GetForegroundWindow()
        unreal.log(f"[INFO] Recorded original active window: {prev_active_hwnd}")

        hwnd = _find_ue5_window()
        if not hwnd:
            unreal.log_error("[ERROR] Could not find UE5 Editor window")
            return result

        try:
            if not open_asset_editor(asset_path):
                return result
            result["opened"] = True

            unreal.log(f"[INFO] Waiting {delay}s for editor to render...")
            time.sleep(delay)

            if tab_number is not None:
                _switch_to_tab(hwnd, tab_number)
                time.sleep(0.5)

            _ensure_directory(output_path)
            img = _capture_window_printwindow(hwnd, crop_titlebar=True)
            if img:
                img.save(output_path)
                unreal.log(f"[OK] UE5 window screenshot saved to: {output_path} ({img.width}x{img.height})")
                result["screenshot"] = True
                result["screenshot_path"] = output_path
            else:
                unreal.log_error("[ERROR] Failed to capture window")

        finally:
            if prev_active_hwnd:
                _user32.SetForegroundWindow(prev_active_hwnd)
                unreal.log(f"[INFO] Restored original active window: {prev_active_hwnd}")
                time.sleep(0.1)
    else:
        if not open_asset_editor(asset_path):
            return result
        result["opened"] = True

        unreal.log(f"[INFO] Waiting {delay}s for editor to render...")
        time.sleep(delay)

        if tab_number is not None:
            hwnd = _find_ue5_window()
            if hwnd:
                _switch_to_tab(hwnd, tab_number)
                time.sleep(0.5)

        success = _capture_screen(output_path)
        result["screenshot"] = success
        if success:
            result["screenshot_path"] = output_path

    return result


def open_and_screenshot_assets(asset_paths, output_dir, delay=3.0, capture_ue5_only=True):
    """
    Open multiple asset editors one by one and take screenshots of each.

    Args:
        asset_paths: List of asset paths to open
        output_dir: Directory to save screenshots
        delay: Seconds to wait before each screenshot (default: 3.0)
        capture_ue5_only: If True, capture only UE5 window

    Returns:
        dict: {"success": [(path, screenshot_path)], "failed": [path]}
    """
    results = {"success": [], "failed": []}

    if not asset_paths:
        unreal.log_warning("[WARNING] No asset paths provided")
        return results

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for asset_path in asset_paths:
        asset_name = asset_path.split("/")[-1]
        screenshot_path = os.path.join(output_dir, f"{asset_name}.png")

        result = open_asset_editor_with_screenshot(
            asset_path, screenshot_path, delay, capture_ue5_only
        )

        if result["opened"] and result["screenshot"]:
            results["success"].append((asset_path, result["screenshot_path"]))
            unreal.log(f"[OK] {asset_path} -> {result['screenshot_path']}")
        else:
            results["failed"].append(asset_path)
            unreal.log_error(f"[ERROR] Failed: {asset_path}")

        close_asset_editor(asset_path)
        time.sleep(0.5)

    unreal.log("=" * 50)
    unreal.log(f"[SUMMARY] Success: {len(results['success'])}, Failed: {len(results['failed'])}")
    return results


# ============================================
# Command Line Interface
# ============================================

def _create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='UE5 编辑器截图工具 - 打开资产编辑器，截图，自动关闭',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s -a /Game/BP/BP_Robot -o C:/Screenshots/robot.png
  %(prog)s -a /Game/BP/BP_Robot -o C:/Screenshots/robot.png -d 2.0
  %(prog)s -a /Game/BP/BP_Robot -o C:/Screenshots/robot.png -t 2
  %(prog)s -a /Game/BP/BP_Robot -o C:/Screenshots/robot.png --no-tab
'''
    )
    parser.add_argument('-a', '--asset', required=True,
                        help='资产路径 (例如: /Game/Blueprints/Robot/BP_RobotBase)')
    parser.add_argument('-o', '--output', required=True,
                        help='输出文件路径 (例如: C:/Screenshots/robot.png)')
    parser.add_argument('-d', '--delay', type=float, default=3.0,
                        help='截图前延迟秒数 (默认: 3.0)')
    parser.add_argument('--no-capture-ue5-only', action='store_true',
                        help='捕获全屏而非仅UE5窗口')
    parser.add_argument('-t', '--tab', type=int, default=1,
                        help='切换到指定标签页 (1-9, 默认: 1=视口)')
    parser.add_argument('--no-tab', action='store_true',
                        help='不切换标签页')
    return parser


if __name__ == "__main__":
    parser = _create_parser()
    args = parser.parse_args()

    unreal.log("=" * 60)
    unreal.log("[INFO] UE5 编辑器截图工具")
    unreal.log("=" * 60)
    # 确定要切换的标签页
    tab_number = None if args.no_tab else args.tab

    unreal.log(f"[INFO] 资产: {args.asset}")
    unreal.log(f"[INFO] 输出: {args.output}")
    unreal.log(f"[INFO] 延迟: {args.delay}s")
    unreal.log(f"[INFO] 标签: {tab_number if tab_number else '不切换'}")

    # 执行截图
    result = open_asset_editor_with_screenshot(
        args.asset,
        args.output,
        delay=args.delay,
        capture_ue5_only=not args.no_capture_ue5_only,
        tab_number=tab_number
    )

    # 自动关闭编辑器
    close_asset_editor(args.asset)

    # 输出结果
    unreal.log("=" * 60)
    if result["screenshot"]:
        unreal.log(f"[OK] 截图完成: {result['screenshot_path']}")
    else:
        unreal.log_error("[ERROR] 截图失败")
    unreal.log("=" * 60)
