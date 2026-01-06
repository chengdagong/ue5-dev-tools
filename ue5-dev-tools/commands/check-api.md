---
description: 查询 UE5 API 的详细信息
---

# /check-api

查询指定 UE5 类或方法的详细信息，包括参数约束、废弃状态、使用示例等。

## 用法

```
/check-api <ClassName>
/check-api <ClassName.method_name>
/check-api <ClassName.property_name>
```

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
/check-api Actor
```

输出：
```
=== UE5 API 信息: Actor ===

类型: UObject 派生类
模块: Engine
C++ 类名: AActor

常用方法:
- get_actor_location() -> Vector
- set_actor_location(new_location: Vector, sweep: bool, teleport: bool) -> bool
- get_actor_rotation() -> Rotator
- destroy_actor() -> None

常用属性:
- root_component: SceneComponent [读写]
- actor_label: str [读写]
```

### 查询方法信息
```
/check-api Actor.set_actor_location
```

输出：
```
=== UE5 API 信息: Actor.set_actor_location ===

签名: set_actor_location(new_location: Vector, sweep: bool = False, teleport: bool = False) -> bool

参数:
- new_location: Vector - 新的位置坐标
- sweep: bool = False - 是否进行碰撞检测
- teleport: bool = False - 是否作为瞬移（忽略物理）

返回值: bool - 是否成功设置位置

C++ Blueprint 特性:
- BlueprintCallable: ✅
- Category: "Transformation"
```
