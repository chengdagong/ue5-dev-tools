"""
PIE Screenshot Capturer - UE5 Python Script
基于tick回调在PIE运行时自动截图

使用方法:
    import pie_screenshot_capturer

    # 启动抓拍器并自动启动PIE (默认每1秒截图一次)
    capturer = pie_screenshot_capturer.start(auto_start_pie=True)

    # 或自定义参数
    capturer = pie_screenshot_capturer.start(
        output_dir="C:/Screenshots",
        interval_seconds=2.0,
        resolution=(1920, 1080),
        auto_start_pie=True
    )

    # 手动启动/停止PIE
    pie_screenshot_capturer.start_pie()
    pie_screenshot_capturer.stop_pie()

    # 停止抓拍器
    pie_screenshot_capturer.stop()
"""

import unreal
import os
from datetime import datetime


class PIEScreenshotCapturer:
    """基于tick回调的PIE截图抓拍器"""

    def __init__(self, output_dir=None, interval_seconds=1.0, resolution=(1920, 1080)):
        """
        初始化抓拍器

        Args:
            output_dir: 截图输出目录，默认为项目Screenshots目录
            interval_seconds: 截图间隔秒数
            resolution: 截图分辨率 (width, height)
        """
        # 设置输出目录
        if output_dir is None:
            project_dir = unreal.Paths.project_dir()
            output_dir = os.path.join(project_dir, "Screenshots", "PIE_Captures")

        self.output_dir = output_dir
        self.interval_seconds = interval_seconds
        self.resolution = resolution

        # 状态变量
        self._tick_handle = None
        self._accumulated_time = 0.0
        self._screenshot_count = 0
        self._is_running = False
        self._pending_task = None
        self._was_in_pie = False

        # 确保输出目录存在
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            unreal.log(f"[PIE Capturer] Created output directory: {self.output_dir}")

    def start(self):
        """启动抓拍器"""
        if self._is_running:
            unreal.log_warning("[PIE Capturer] Already running")
            return

        self._is_running = True
        self._accumulated_time = 0.0
        self._screenshot_count = 0
        self._was_in_pie = False

        # 注册tick回调
        self._tick_handle = unreal.register_slate_post_tick_callback(self._on_tick)

        unreal.log(f"[PIE Capturer] Started - Interval: {self.interval_seconds}s, Resolution: {self.resolution}")
        unreal.log(f"[PIE Capturer] Output: {self.output_dir}")

    def stop(self):
        """停止抓拍器"""
        if not self._is_running:
            unreal.log_warning("[PIE Capturer] Not running")
            return

        self._is_running = False

        # 取消注册tick回调
        if self._tick_handle is not None:
            unreal.unregister_slate_post_tick_callback(self._tick_handle)
            self._tick_handle = None

        unreal.log(f"[PIE Capturer] Stopped - Total screenshots: {self._screenshot_count}")

    def _on_tick(self, delta_time):
        """Tick回调函数"""
        if not self._is_running:
            return

        # 检查是否有待完成的截图任务
        if self._pending_task is not None:
            if self._pending_task.is_task_done():
                self._pending_task = None
            else:
                # 任务未完成，跳过本tick
                return

        # 检查PIE状态
        pie_worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        is_in_pie = len(pie_worlds) > 0

        # PIE状态变化检测
        if is_in_pie and not self._was_in_pie:
            unreal.log("[PIE Capturer] PIE started - beginning capture")
            self._accumulated_time = 0.0
        elif not is_in_pie and self._was_in_pie:
            unreal.log("[PIE Capturer] PIE ended - pausing capture")

        self._was_in_pie = is_in_pie

        # 如果不在PIE中，不截图
        if not is_in_pie:
            return

        # 累计时间
        self._accumulated_time += delta_time

        # 检查是否达到截图间隔
        if self._accumulated_time >= self.interval_seconds:
            self._accumulated_time = 0.0
            self._take_screenshot()

    def _take_screenshot(self):
        """执行截图"""
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            self.output_dir,
            f"PIE_Screenshot_{timestamp}_{self._screenshot_count:04d}.png"
        )

        # 确保在截图前完成加载
        unreal.AutomationLibrary.finish_loading_before_screenshot()

        # 执行高分辨率截图
        self._pending_task = unreal.AutomationLibrary.take_high_res_screenshot(
            res_x=self.resolution[0],
            res_y=self.resolution[1],
            filename=filename,
            camera=None,  # 使用当前视角
            mask_enabled=False,
            capture_hdr=False,
            comparison_tolerance=unreal.ComparisonTolerance.LOW,
            comparison_notes="",
            delay=0.0,
            force_game_view=True
        )

        self._screenshot_count += 1
        unreal.log(f"[PIE Capturer] Screenshot #{self._screenshot_count}: {os.path.basename(filename)}")


# 全局实例
_capturer_instance = None


def start(output_dir=None, interval_seconds=1.0, resolution=(1920, 1080), auto_start_pie=False):
    """
    启动PIE截图抓拍器

    Args:
        output_dir: 截图输出目录
        interval_seconds: 截图间隔秒数
        resolution: 截图分辨率 (width, height)
        auto_start_pie: 是否自动启动PIE

    Returns:
        PIEScreenshotCapturer实例
    """
    global _capturer_instance

    if _capturer_instance is not None:
        _capturer_instance.stop()

    _capturer_instance = PIEScreenshotCapturer(
        output_dir=output_dir,
        interval_seconds=interval_seconds,
        resolution=resolution
    )
    _capturer_instance.start()

    # 自动启动PIE
    if auto_start_pie:
        start_pie()

    return _capturer_instance


def stop():
    """停止PIE截图抓拍器"""
    global _capturer_instance

    if _capturer_instance is not None:
        _capturer_instance.stop()
        _capturer_instance = None


def get_capturer():
    """获取当前抓拍器实例"""
    return _capturer_instance


def start_pie():
    """启动PIE"""
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if subsystem.is_in_play_in_editor():
        unreal.log_warning("[PIE Capturer] PIE is already running")
        return False

    subsystem.editor_request_begin_play()
    unreal.log("[PIE Capturer] PIE start requested")
    return True


def stop_pie():
    """停止PIE"""
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not subsystem.is_in_play_in_editor():
        unreal.log_warning("[PIE Capturer] PIE is not running")
        return False

    subsystem.editor_request_end_play()
    unreal.log("[PIE Capturer] PIE stop requested")
    return True


def is_pie_running():
    """检查PIE是否正在运行"""
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    return subsystem.is_in_play_in_editor()


# 如果直接运行此脚本，启动抓拍器并自动启动PIE
if __name__ == "__main__":
    start(auto_start_pie=True)
