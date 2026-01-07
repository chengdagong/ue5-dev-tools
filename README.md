# UE5 Dev Tools (Claude Plugin)

用于辅助 Unreal Engine 5 Python 开发的 Claude 插件。提供 API 验证、查询和自动补全支持。

## 功能特性

*   **API 验证**: 检查 Python 脚本中的 UE5 API 调用是否正确，识别废弃 API 和参数错误。
*   **智能 Mock**: 首次运行时自动检测 UE5 项目生成的 Python Stub，并转换为运行时可用的 Mock 模块。
*   **元数据集成**: 自动扫描 UE5 源码（如果存在），提取 C++ 元数据以增强验证准确性。
*   **Anti-Hallucination**: 严格控制 `/check-api` 输出，防止 AI 编造不存在的 API。

## 安装

本插件设计为本地 Claude Plugin。

1.  **添加本地 Marketplace**
    在当前目录（`ue5-dev-tools` 根目录）下运行：
    ```bash
    claude plugin marketplace add .
    ```

2.  **安装插件**
    ```bash
    claude plugin install ue5-dev-tools
    ```

3.  **安装 Git Hooks（可选，用于开发）**
    如果你是插件开发者，安装 git hooks 可以自动管理版本号：
    ```bash
    cd ue5-dev-tools
    ./scripts/install-hooks.sh
    ```
    这会启用自动版本递增功能：每次 commit 时自动将 `plugin.json` 的版本号 +0.0.1

## 使用

在您的 UE5 项目目录中打开 Claude，即可使用以下命令：

*   **`/validate-script <file.py>`**: 验证指定脚本。首次运行时会自动生成 Mock 模块。
*   **`/check-api <ClassName>`**: 查询 UE5 类或方法的详细信息。

## 要求

*   Python 3.8+
*   Claude Code
*   (可选) UE5 源码 (用于增强元数据分析)
*   (可选) UE5 项目生成的 `Intermediate/PythonStub/unreal.py` (用于生成 Mock)
