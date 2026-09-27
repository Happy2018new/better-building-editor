# mcdk-assistant 同步记录

本项目使用 [GitHub-Zero123/mcdk-assistant](https://github.com/GitHub-Zero123/mcdk-assistant) 提供资料检索、原版资源查询和 Python MOD 结构审查。它与 Pyreact 调试技能使用的 MCDevTool 是两个独立工具；本次更新不涉及 MCDevTool v1.6.1 或 Pyreact 的本地补丁。

## 当前基准

同步日期：2026-09-26。

| 内容 | 版本与位置 |
| --- | --- |
| 上游源码、原版资料 | commit `172b3bc8289912e58a096349f568d1b921005d8c`，`.tools/mcdk-assistant` |
| Windows x64 程序 | 官方发布版 `v0.2.7`，`.tools/mcdk-runtime/v0.2.7` |
| 下载包 SHA-256 | `7f27c2e9df48a57e3df726d5b5f740d5f25c37f6567bc9091b7dfb037f20b497`，已与 GitHub release asset digest 核对 |
| 索引资料源 | 程序旁的 `knowledge` 是指向 `.tools/mcdk-assistant/knowledge` 的 Windows 目录联接 |
| 项目 MCP 配置 | `.codex/config.toml`，使用新版 `mcdk-asst-lite.exe --stdio` |
| 命令行入口 | `python -X utf8 tools/mcdk.py`，指向同一新版程序 |

此前源码为 `481f461d589847b9dceed762a9d8557bcd278e81`，程序为 `v0.2.6`。本次源码前进 6 个提交，涵盖 Python 审查规则、ModSDK 3.10 Beta／PhysX 资料、Bedrock 文档与原版资源更新，以及 `corner_and_cardinal_direction` 文档格式修正。

`v0.2.7` 发布之后还有 4 个资料提交，程序源码和 skills 没有进一步变化。因此继续使用官方发布程序，并通过其知识库指纹机制重建索引，使搜索也能使用最新源码资料。重建后的 `mcdk_index_cache.bin` 为 9,838,318 字节；不是沿用发布包中的 9,339,695 字节索引。实际读取的 Bedrock Addons／Animations 文档版本为 `1.21.130.3`。工具帮助中的 Bedrock 版本文字仍是上游旧描述，资料版本以读取结果为准。

资料更新不代表本项目运行的客户端已升级。使用 ModSDK 3.10 Beta 的新 API 前，仍需确认实际引擎版本。

## 项目技能

通过 skill-installer 按固定 commit 安装到 `.agents/skills/`，没有写入用户全局技能目录。安装后逐份核对上游内容，移除文件开头的 UTF-8 BOM，使技能解析器能直接识别 YAML 起始分隔符，再进行下列本地适配。下表的“与上游一致”指正文一致，不含 BOM／换行规范化。

| 技能 | 用途 | 本地差异 |
| --- | --- | --- |
| `ffi-cache` | 减少高频跨语言接口调用 | 与上游一致 |
| `hash-key` | 字典／集合键设计 | 与上游一致 |
| `mc-search` | 查询 ModSDK、资源和格式文档 | 旧独立工具名改为 `minecraft_docs`，修正文档读取入口，补充引擎版本核对 |
| `mod-workflow` | MOD 结构、端侧边界与改动验证 | 旧工具名改为 `minecraft_py`／`minecraft_docs`；按当前工具帮助限制全局扫描；补充按范围 review，并明确已有用户授权优先 |
| `next-opt` | 生成器／迭代器推进 | 与上游一致 |
| `py-except` | 避免用异常驱动热路径 | 与上游一致 |
| `py-init` | 模块初始化与线程／端侧边界 | 与上游一致 |

上游的 `skills/` 在这 6 个提交中未修改；本项目此前未安装这些技能，本次补齐。保留 [上游 BSD 3-Clause 许可](vendor/mcdk-assistant.LICENSE.txt)，归属见根目录 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

## 使用与后续更新

- 新技能在下一轮对话中可用。已运行的 MCP 进程不会因修改配置自动换成新版；重新连接 MCP 或重启 Codex 后会按新路径启动。本地 CLI 已直接使用新版。
- 旧 `.tools/mcdk-runtime` 中的 v0.2.6 文件保留，避免替换正在使用的 Windows 可执行文件。没有停止其他会话的工具或游戏进程。
- 更新前先检查 `.tools/mcdk-assistant` 是否有本地改动，使用快进合并同步上游，记录固定 commit；技能仅覆盖上游部分，保留本记录列出的本地适配。
- 更新程序时下载官方 Windows x64 release，并核对 GitHub 提供的 SHA-256。按版本并存安装，同步修改 `.codex/config.toml` 与 `tools/mcdk.py`，随后验证 `tools/list`、两个工具的 `help`、真实检索及指定模块分析。
- 如需发布后最新资料，让新程序相邻的 `knowledge` 指向源码库，再运行一次 CLI；程序会校验知识库指纹并在变化时重建索引。先等待重建完成，再接入其他客户端，避免多个进程同时写索引。
- `.tools/` 和 `.runtime/` 都是忽略的本地缓存。技能和版本记录可以提交，程序、索引、下载包与验证产物不提交。本次更新不生成 `dist/astral_survey_v1.zip`。

## 验证范围

验证新版程序的工具枚举、帮助、ModAPI 和 Bedrock 检索、实际知识库文件读取，以及 Python 引用链与定向审查。核对 7 份技能的 YAML 元数据、引用路径、保留的上游内容和工具入口。证据保存于忽略目录 `.runtime/`。

实际检索到 `CombineBlockPaletteToGeometry`、3.10 PhysX 的 `AddForceAtPos`，并逐行核对最新提交修正的 `corner_and_cardinal_direction` 文档。定向审查 `camera` 模块实际解析 1 个文件，无解析失败，返回 2 个已有参数数量提示；本次仅验证审查入口，没有将这些提示当作新问题修改业务代码。`--scope` 必须使用不带 `.py` 的模块名，错误范围可能返回 `files=0`，不能将其视为通过。

这些检查验证开发工具的安装与连接；本次没有修改模组业务代码，也没有启动游戏或执行手机回归。
