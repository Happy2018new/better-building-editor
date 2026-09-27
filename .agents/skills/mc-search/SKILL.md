---
name: mc-search
description: 在处理我的世界 MOD、Bedrock、网易版、JSON UI、模型、动画、原版资源等任务时，优先通过 MCP 资料库检索接口、字段、路径、格式规则和示例，避免编造事实。
---

# 先查资料库

本项目使用 mcdk-assistant v0.2.7 LITE 的统一工具入口，先以 `minecraft_docs(command="help")` 确认当前 schema。这里的命令示例已适配上游旧的独立工具名；来源与本地差异见 [同步记录](../../../docs/MCDK_ASSISTANT_UPSTREAM.md)。

涉及以下内容时，先检索再回答：

- ModAPI 接口、事件、枚举、回调参数
- 网易版差异、教程、独占规则
- JSON UI 属性、绑定、命名空间、补丁规则
- 原版资源路径、命名、示例文件
- QuMod 相关内容
- 实体、方块、物品、地物、群系、粒子、合成等json组件结构与格式

工具选择：

- `minecraft_docs(command="api <关键词>")` / `minecraft_docs(command="event <关键词>")` / `minecraft_docs(command="enum <关键词>")` / `minecraft_docs(command="all <关键词>")`：ModAPI
- `minecraft_docs(command="netease <关键词>")`：网易资料
- `minecraft_docs(command="wiki <关键词>")`：Bedrock Wiki
- `minecraft_docs(command="dev <关键词>")`：json组件结构与格式
- `minecraft_docs(command="qumod <关键词>")`：QuMod
- `minecraft_docs(command="assets <关键词>")`：原版资源
- `minecraft_docs(command="netease diff")` / `minecraft_docs(command="netease jsonui")`：网易差异与内置 UI 控件速查。
- `minecraft_docs(command="read NeteaseGuide/mcguide/18-界面与交互/30-UI说明文档.md")`：JSON UI 说明。
- `minecraft_docs(command="read BedrockDev/02_Animations.md")`：动画格式。
- `minecraft_docs(command="read BedrockWiki/visuals/bedrock-modeling.md")`：模型说明。

要求：

- 先检索，再下结论
- 资料不足时直接说明，不要硬猜
- 生成代码或 JSON 前，凡涉及字段、事件、路径、格式，先查资料
- 文本润色、纯重构、纯创意讨论可不检索
- `read` 使用搜索结果中的真实路径，可用 `--start` / `--end` 限制行数；不要猜测文件名。
- 文档库已更新到 ModSDK 3.10 Beta，调用 API 前仍需核对项目实际使用的游戏版本，不能假定旧客户端具备新接口。
