---
description: 验证 UE5 Python 脚本的 API 使用是否正确
---

# /validate-script

验证指定的 Python 脚本是否正确使用了 UE5 API。

## 用法

```
/validate-script <script_path>
```

## 步骤

1. 运行验证脚本：
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/skills/api-validator/scripts/validate.py $ARGUMENTS
   ```

2. 分析验证报告输出

3. 如果发现错误或警告：
   - 对于 deprecated API：提供替代方案建议
   - 对于不存在的 API：建议正确的 API 名称
   - 对于参数错误：说明正确的参数类型/范围

## 示例

```
/validate-script Content/Python/my_script.py
```

输出：
```
=== UE5 Python API 验证报告 ===

检查文件: Content/Python/my_script.py

✅ 导入检查: import unreal - OK
✅ 类存在性: unreal.Actor - OK
⚠️ Deprecated: set_actor_hidden_in_game (第 15 行)
   原因: 此方法已废弃
   建议: 使用 set_hidden_in_game 代替
❌ 错误: 方法 'get_location' 不存在 (第 23 行)
   建议: 您是否想使用 'get_actor_location'?

总计: 2 个类, 5 个方法调用
错误: 1, 警告: 1, 通过: 4
```
