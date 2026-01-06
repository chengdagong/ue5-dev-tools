#!/bin/bash

# 获取脚本所在目录
# 假设脚本位于 plugin/ue5-python-validator/scripts/install.sh
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"
SKILL_API_DIR="$PLUGIN_ROOT/skills/api-validator"

echo "安装 UE5 Python API Validator Plugin..."

# 1. 准备 C++ 元数据
# 尝试生成元数据（如果 UE5 路径存在）
UE5_PATH="/Users/Shared/Epic Games/UE_5.7/Engine/Source"
if [ -d "$UE5_PATH" ]; then
    echo "检测到 UE5 源码，正在提取元数据..."
    # 限制扫描范围以加快演示速度
    python3 "$SKILL_API_DIR/scripts/cpp_metadata_extractor.py" \
        --ue5-path "$UE5_PATH/Runtime/Engine/Classes/GameFramework" \
        --output "$SKILL_API_DIR/references/metadata.json"
else
    echo "未检测到 UE5 源码，跳过元数据提取。"
fi

# 2. 触发 mock_unreal 自动生成
echo "检查并生成 mock_unreal 模块..."
# 运行验证脚本一次，不带参数，它会尝试加载 mock 模块，如果不存在则自动生成
# 我们使用一个不存在的文件路径作为参数，或者使用 --query 参数来触发加载
python3 "$SKILL_API_DIR/scripts/validate.py" --query "Actor"

echo "=========================================="
# 3. 配置本地 Marketplace (当前目录的父目录即为 Marketplace 根目录)
MARKET_DIR="$(dirname "$PLUGIN_ROOT")"
mkdir -p "$MARKET_DIR/.claude-plugin"

# 在嵌套结构方案中，无需创建软链接，ue5-dev-tools 已经是 MARKET_DIR 的子目录

echo "{
  \"name\": \"ue5-local-market\",
  \"owner\": {
    \"name\": \"Local User\",
    \"email\": \"user@local\"
  },
  \"plugins\": [
    {
      \"name\": \"ue5-dev-tools\",
      \"description\": \"UE5 Development Tools\",
      \"source\": \"./ue5-dev-tools\"
    }
  ]
}" > "$MARKET_DIR/.claude-plugin/marketplace.json"

echo "注册本地 Marketplace..."
# 注意：这需要 Claude CLI 支持 plugin 命令
try_install() {
    if command -v claude &> /dev/null; then
        echo "尝试添加 Marketplace..."
        # 先尝试移除旧的同名市场（如果存在）
        claude plugin marketplace remove ue5-local-market &> /dev/null || true
        
        if claude plugin marketplace add "$MARKET_DIR"; then
            echo "尝试安装插件..."
            claude plugin install ue5-dev-tools || echo "⚠️ 安装插件失败"
        else
            echo "⚠️ 添加 Marketplace 失败"
        fi
    else
        echo "未找到 'claude' 命令，请手动执行以下步骤："
        echo "1. claude plugin marketplace add \"$MARKET_DIR\""
        echo "2. claude plugin install ue5-dev-tools"
    fi
}
try_install

# 即使上述命令失败，我们之前的 settings.local.json 修改也能保证插件加载
# 但为了响应用户 Explicit 的 install 请求，我们尝试上面的步骤

echo "=========================================="
echo "Plugin 安装脚本执行完毕！"
echo ""
echo "如果在上方看到安装失败的错误，您可以尝试手动运行："
echo "1. claude plugin marketplace add ./local_marketplace"
echo "2. claude plugin install ue5-dev-tools"
echo ""
echo "或者，该插件已通过 .claude/settings.local.json 自动配置，"
echo "您可以直接重启 Claude Code 即可生效。"
echo "=========================================="
