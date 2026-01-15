# Phase 5: 视觉验证完整指南

## 何时使用视觉验证

在以下情况下使用此阶段:

脚本影响以下方面时:
- **视觉外观** - 材质、网格、光照、UI
- **游戏行为** - 角色移动、AI、游戏机制
- **关卡/世界状态** - 对象放置、生成、销毁

**跳过此阶段**当:
- 脚本仅处理数据/资产而无视觉影响
- 更改纯粹是组织性的(重命名、移动资产)
- 用户明确要求跳过视觉验证

## 分步过程

### Step 1: 准备截图捕获

确定要验证的内容:
- 应该加载哪个关卡/地图?
- 合适的分辨率是多少?
- 需要多少个截图?(默认: 3)
- 截图间隔是多少?(默认: 1.0 秒)

### Step 2: 执行截图工具

使用 ue5-screenshot 中的 `take_game_screenshot.py`:

```bash
python "ue5-screenshot/scripts/take_game_screenshot.py" \
  -p "<path-to-uproject>" \
  -l "<level-name-only>" \
  -n 3 \
  -i 1.0 \
  -o "verification_screenshot" \
  -r "1280x720" \
  --timeout 20 \
  --load-timeout 20
```

#### 参数详解

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `-p` | 项目文件路径(可自动检测) | 无(必需) | `MyProject.uproject` |
| `-l` | 关卡名称(仅名称,无路径) | 无(必需) | `MainMenu` |
| `-n` | 截图数量 | 3 | `-n 5` |
| `-i` | 截图间隔(秒) | 1.0 | `-i 0.5` |
| `-o` | 输出文件名前缀 | `screenshot` | `-o "verify"` |
| `-r` | 游戏分辨率 | `1280x720` | `-r "1920x1080"` |
| `--timeout` | 窗口等待超时(秒) | 20 | `--timeout 30` |
| `--load-timeout` | 游戏加载超时(秒) | 20 | `--load-timeout 40` |

#### 关键概念

**关卡参数格式:**
- ✅ 正确: `-l "MainMenu"` (仅名称)
- ❌ 错误: `-l "/Game/Maps/MainMenu"` (包含路径)
- ❌ 错误: `-l "MainMenu.umap"` (包含扩展名)

脚本内部使用 `-MapOverride` 来加载关卡。

**UE 引擎路径:**
- 默认: `C:\Program Files\Epic Games\UE_5.7`
- 使用 `--ue-root` 参数指定不同位置

#### 常见示例

```bash
# 示例 1: 简单捕获
python take_game_screenshot.py -p "MyProject.uproject" -l "Level1" -n 3

# 示例 2: 自定义分辨率和输出
python take_game_screenshot.py \
  -p "MyGame.uproject" \
  -l "MainMenu" \
  -n 5 \
  -r "1920x1080" \
  -o "results/menu_verification"

# 示例 3: 使用自定义 UE 路径
python take_game_screenshot.py \
  -p "MyProject.uproject" \
  -l "GameLevel" \
  --ue-root "D:/CustomUE5"
```

### Step 3: 分析截图

捕获完成后:

1. **读取并显示截图** - 使用 Read 工具查看
2. **分析视觉内容** - 查找:
   - 脚本产生的预期更改(材质、对象、UI 元素)
   - 意外问题(缺少对象、错误颜色、错误)
   - 视觉伪影或问题
3. **与需求比较** - 视觉结果是否匹配原始请求?

### Step 4: 报告发现

提供清晰的分析:

```markdown
## 视觉验证结果

### 捕获的截图
- verification_screenshot_1.png (1280x720)
- verification_screenshot_2.png (1280x720)
- verification_screenshot_3.png (1280x720)

### 分析
- ✓ 预期: [您期望看到的内容]
- ✓ 观察: [截图显示的内容]
- ⚠ 问题: [检测到的任何问题]

### 结论
[通过/失败] - [简要解释]
```

## 故障排除

### 游戏无法启动

**症状**: 超时或无窗口出现

**原因和解决方案**:
- 验证 UE 引擎路径(默认: `C:\Program Files\Epic Games\UE_5.7`)
- 检查 .uproject 文件是否有效
- 增加 `--timeout` (例如 `--timeout 30`)

### 黑色截图

**症状**: 所有截图都是黑色

**原因和解决方案**:
- 游戏仍在加载,增加 `--load-timeout`(例如 `--load-timeout 40`)
- 验证关卡名称是否正确(仅名称,无路径)
- 检查关卡是否存在于项目中

### 加载错误的关卡

**症状**: 加载了意外的关卡

**原因和解决方案**:
- 关卡参数必须是名称(例如 `"MainMenu"`)
- **不要**包含路径分隔符(/, \)
- **不要**包含 .umap 扩展名
- 脚本使用 `-MapOverride` 内部加载关卡

示例:
```bash
# 正确
-l "MyLevel"

# 错误
-l "/Game/Maps/MyLevel"
-l "MyLevel.umap"
-l "MyLevel/"
```

### 截图不显示更改

**症状**: 截图显示脚本执行前的状态

**原因和解决方案**:
- 验证脚本实际保存了资产(`save_loaded_asset()`)
- 检查更改是否需要编辑器重启
- 确认更改在游戏中可见(不仅是编辑器)

**调试步骤**:
```python
# 添加到脚本以验证保存
for asset in assets:
    asset.set_editor_property("my_property", new_value)
    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    # 验证保存是否成功
    reloaded = unreal.EditorAssetLibrary.load_asset(asset.get_path_name())
    actual_value = reloaded.get_editor_property("my_property")
    assert actual_value == new_value, f"Save failed! Got {actual_value}"
    unreal.log(f"✓ 已验证: {asset.get_path_name()}")
```

### 截图工具崩溃

**症状**: 脚本终止或给出错误

**常见原因**:
- 项目路径不存在
- 权限问题(无法访问项目)
- 缺少依赖(PIL, ctypes 等)

**解决**:
- 检查项目路径是否有效
- 确保有读取项目的权限
- 确保安装了 Pillow: `pip install Pillow`

## 工具功能

### 窗口管理

- 在屏幕外启动游戏(默认)
- 不中断用户工作
- 自动终止进程

### 加载检测

- 等待游戏窗口出现
- 检测黑屏(仍在加载)
- 只有在游戏完全加载后才开始截图

### 分辨率处理

- DPI 感知,获取物理分辨率
- 裁剪标题栏,保留客户区
- 支持自定义分辨率

## 集成到脚本流程

**完整工作流示例**:

```bash
#!/bin/bash

PROJECT_PATH="D:/MyUEProject/MyProject.uproject"
TEST_LEVEL="TestLevel"
SCRIPT_OUTPUT="test_results"

echo "1. 运行 UE5 Python 脚本..."
# (脚本已在 Phase 4 中执行)

echo "2. 捕获验证截图..."
python take_game_screenshot.py \
  -p "$PROJECT_PATH" \
  -l "$TEST_LEVEL" \
  -n 3 \
  -o "$SCRIPT_OUTPUT/screenshot"

echo "3. 验证截图..."
# Claude 分析输出的截图

echo "4. 生成报告..."
# 报告是否通过/失败
```

## 最佳实践

1. **选择合适的关卡** - 使用专用测试关卡以避免污染生产数据
2. **多个截图** - 捕获不同时刻以确保变化清晰可见
3. **一致的分辨率** - 使用与目标平台相同的分辨率
4. **清晰的命名** - 使用描述性的输出前缀以便识别
5. **自动化** - 将截图工具集成到 CI/CD 或测试脚本中

## 相关资源

- [Workflow Details](workflow-details.md) - Phase 5 在完整工作流中的位置
- [Best Practices](best-practices.md) - UE5 特有的模式和最佳实践
