#!/usr/bin/env python3
"""
为 Movement Ability 蓝图设置 AbilityTags

使用 export_text/import_text 方法来修改 GameplayTagContainer,
因为 gameplay_tags 属性是只读的。

Usage:
    通过 UE5 Python Remote Execution 运行:
    python3 remote-execute.py --file set_movement_ability_tags_final.py --project-name URF
"""

import unreal


def add_ability_tag_to_asset(asset_path, tag_name):
    """
    为单个 Ability 资产添加 AbilityTag

    Args:
        asset_path: UE5 资产路径 (如 "/Game/GAS/Abilities/Movement/GA_Step")
        tag_name: 要添加的 tag 名称 (如 "Ability.Move.Step")

    Returns:
        bool: 成功返回 True,失败返回 False
    """
    try:
        # 加载资产
        ability = unreal.load_asset(asset_path)
        if not ability:
            unreal.log_error(f"Failed to load asset: {asset_path}")
            return False

        # 获取 Blueprint Generated Class 和 CDO
        ability_class = ability.generated_class()
        if not ability_class:
            unreal.log_error(f"Failed to get generated class for: {asset_path}")
            return False

        cdo = unreal.get_default_object(ability_class)
        if not cdo:
            unreal.log_error(f"Failed to get CDO for: {asset_path}")
            return False

        # 获取当前的 ability_tags container
        current_container = cdo.get_editor_property("ability_tags")
        if current_container is None:
            unreal.log_error(f"Failed to get ability_tags for: {asset_path}")
            return False

        # 检查 tag 是否已存在
        current_tags = current_container.get_editor_property("gameplay_tags")
        for existing_tag in current_tags:
            existing_tag_name = str(existing_tag.get_editor_property("tag_name"))
            if existing_tag_name == tag_name:
                unreal.log(f"  Tag '{tag_name}' already exists, skipping")
                return True

        # 导出 container 为文本
        exported_text = current_container.export_text()

        # 修改文本以添加新 tag
        # 格式: (GameplayTags=((TagName="Tag1"),(TagName="Tag2")))
        # 或者: (GameplayTags=((TagName="Tag1")))
        # 或者: (GameplayTags=())
        if "(GameplayTags=(" in exported_text:
            # 找到最后的 ))
            parts = exported_text.rsplit('))', 1)
            if len(parts) == 2:
                # 检查是否为空 container
                if "(GameplayTags=())" in exported_text:
                    # 空 container,直接添加第一个 tag
                    new_text = f'(GameplayTags=((TagName="{tag_name}")))'
                else:
                    # 已有 tag,添加新的
                    new_text = f'{parts[0]},(TagName="{tag_name}")){parts[1]}'
            else:
                unreal.log_error(f"Unexpected container text format: {exported_text}")
                return False
        else:
            unreal.log_error(f"Unexpected container text format: {exported_text}")
            return False

        # 创建新 container 并导入修改后的文本
        new_container = unreal.GameplayTagContainer()
        new_container.import_text(new_text)

        # 设置到 CDO
        cdo.set_editor_property("ability_tags", new_container)

        # 保存资产
        unreal.EditorAssetLibrary.save_loaded_asset(ability, False)

        # 验证
        verify_container = cdo.get_editor_property("ability_tags")
        verify_tags = verify_container.get_editor_property("gameplay_tags")
        tag_found = False
        for tag in verify_tags:
            if str(tag.get_editor_property("tag_name")) == tag_name:
                tag_found = True
                break

        if tag_found:
            unreal.log(f"  ✓ Successfully added tag '{tag_name}'")
            return True
        else:
            unreal.log_error(f"  ❌ Tag '{tag_name}' not found after save")
            return False

    except Exception as e:
        unreal.log_error(f"  ❌ Exception adding tag to {asset_path}: {str(e)}")
        import traceback
        unreal.log_error(traceback.format_exc())
        return False


def main():
    """为所有 Movement Abilities 添加 AbilityTags"""

    unreal.log("=" * 80)
    unreal.log("=== Setting Movement Ability AbilityTags ===")
    unreal.log("=" * 80)

    # 定义需要配置的 Movement Abilities
    movement_abilities = [
        {
            "path": "/Game/GAS/Abilities/Movement/GA_Step",
            "name": "GA_Step",
            "tag": "Ability.Move.Step"
        },
        {
            "path": "/Game/GAS/Abilities/Movement/GA_Retreat",
            "name": "GA_Retreat",
            "tag": "Ability.Move.Retreat"
        },
        {
            "path": "/Game/GAS/Abilities/Movement/GA_SideStepLeft",
            "name": "GA_SideStepLeft",
            "tag": "Ability.Move.SideStepLeft"
        },
        {
            "path": "/Game/GAS/Abilities/Movement/GA_SideStepRight",
            "name": "GA_SideStepRight",
            "tag": "Ability.Move.SideStepRight"
        }
    ]

    unreal.log(f"\nProcessing {len(movement_abilities)} Movement Abilities...")
    unreal.log("")

    success_count = 0
    failed_list = []

    # 使用事务确保可以撤销
    with unreal.ScopedEditorTransaction("Set Movement Ability AbilityTags"):
        for ability_cfg in movement_abilities:
            unreal.log(f"Processing {ability_cfg['name']}...")

            if add_ability_tag_to_asset(ability_cfg["path"], ability_cfg["tag"]):
                success_count += 1
            else:
                failed_list.append(ability_cfg)

    # 总结
    unreal.log("")
    unreal.log("=" * 80)
    unreal.log("=== Summary ===")
    unreal.log("=" * 80)
    unreal.log(f"Success: {success_count}/{len(movement_abilities)}")

    if failed_list:
        unreal.log(f"Failed: {len(failed_list)}")
        for ability_cfg in failed_list:
            unreal.log(f"  - {ability_cfg['name']}: {ability_cfg['path']}")
    else:
        unreal.log("✓ All Movement Abilities configured successfully!")

    unreal.log("")
    unreal.log("Next steps:")
    unreal.log("1. Verify tags with: check_movement_ability_tags.py")
    unreal.log("2. Test in PIE mode (press W/S/A/D keys)")
    unreal.log("3. Use 'showdebug abilitysystem' command to debug")
    unreal.log("=" * 80)

    return len(failed_list) == 0


if __name__ == "__main__":
    result = main()
    exit(0 if result else 1)
