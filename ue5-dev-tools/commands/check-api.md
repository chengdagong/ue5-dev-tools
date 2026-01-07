---
description: 查询 UE5 API 的详细信息
---

# /check-api

查询指定 UE5 类或方法的详细信息，包括参数约束、废弃状态、使用示例等。

## 用法

```
/check-api unreal.<ClassName>
/check-api unreal.<ClassName>.<method_name>
/check-api unreal.<function_name>
```

**注意事项:**
- **必须以 `unreal.` 开头**
- **必须使用精确的类名或方法名**（如 `unreal.Actor`, `unreal.Actor.set_actor_location`）
- **格式要求**: 只接受 `unreal.<name>` 或 `unreal.<ClassName>.<member_name>` 格式
- **支持模块级函数查询**（如 `unreal.log`, `unreal.log_warning`）

## 步骤

1. 运行 API 查询脚本：
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/skills/api-validator/scripts/validate.py --query "$ARGUMENTS"
   ```

2. **直接显示脚本的输出内容**。

   > [!IMPORTANT]
   > 不要尝试解释、扩展或添加额外的 API 用法示例，除非脚本输出中包含这些信息。
   > Claude 的内部知识对于 UE5 Python API 来说可能是不准确的（很多 C++ API 并未暴露给 Python，例如 `GameplayTagsManager`）。
   > 只展示工具返回的真实结果。

## 示例

### 查询类信息
```
/check-api unreal.Actor
```

输出：
```
查询 API: unreal.Actor
✅ 类 Actor 存在
文档: ...
```

### 查询方法信息
```
/check-api unreal.Actor.set_actor_location
```

输出：
```
查询 API: unreal.Actor.set_actor_location
✅ Actor.set_actor_location 存在
文档: ...
```

### 查询模块级函数
```
/check-api unreal.log
```

输出：
```
查询 API: unreal.log
✅ 函数 log 存在
文档: ...
```
