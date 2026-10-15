# 2026-10-15 旧开发工作区归档

本目录记录清理前的来源审计，并将当前 `dev` 中缺少的历史诊断保存为非执行资料。产品开发仍暂停；本次清理不改变功能完成状态、生产准入或既有失败结论。

清理已完成，逐项目移除记录、磁盘空间前后值、保留边界和备份校验值见 [cleanup-result.json](cleanup-result.json)。唯一保留的冗余文件是约 74 MiB 的未完成 ZIP：自动审批拒绝删除，仅返回 `blocked by policy`；它不是有效恢复来源。

清理对象为 40 个旧 Git 工作树、43 个 `codex/*` 临时分支和 12 个普通测试副本。主工作区和 `dev`、`main`、`realm`、`render-dragon`、`uncomplete` 保留。

## 如何处理独有工作

- `retirement-index.json` 保存全部原分支头、159 个补丁独有提交及路径审计。补丁独有不等于功能尚未合入：当前 `dev` 中已有这些产品模块的后续版本。没有重新合并旧分支、制造重复提交或用旧实现覆盖现有代码。
- `recovered/` 保存 28 个缺少的历史诊断、计划和证据文件。它们不位于生效的源码、工具或测试目录，不能视为现版本的验证结果。逐文件原始及保存后 SHA256 见索引；本目录属性关闭这些文件的换行转换，以保留校验值。
- 77 个包含原始会话／调用资料的历史文件仅保留在本地私有 Git bundle；不发布原始凭据资料。
- 全部退休工作区的未提交变更、未跟踪文件和非缓存的 ignored 文件另有去重 ZIP 备份；工作树的索引与工作区补丁也保留。仅排除 `.git`、Python 字节码和可重建的 Python／测试缓存。

## 本地备份与恢复

备份位于主仓库的 `.runtime/cleanup-20261015/`，受忽略规则保护，不随本次提交发布。原始备份可能包含会话凭据，不应上传。

| 文件 | 用途 | SHA256 |
| --- | --- | --- |
| `retired-agent-branches.bundle` | 41 个含独有对象的原分支；另两个原分支头已在现有 `dev` 历史中 | `c3751645ce5ff2b6a49af0aab00f5b2b3664ac6600f55f0218859596c29c9b37` |
| `retired-workspace-deltas.zip` | 52 个工作区的 12,459 个去重内容对象及工作树补丁 | `648a40d19d2aac9b7b4d37844d3102f066ca25eed3b7f40ff8023891a2c7789a` |
| `workspace-backup-manifest.json` | 原路径、分支、提交、相对路径、对象校验值与重建来源 | `2999c9fb6d6808b139bc50a5d33e9c52019bb41593c6a81454c6ccbca82b24d3` |
| `clone-baseline-files.zip` | 4,505 个基线引用文件的精确工作区字节，避免换行转换及既有 WIP 影响重建 | `6f04e9479e772673b2d896025d12b1edb3c56c9645c6b281a0345c4173e4ea95` |

`workspace-backup-verification.json` 记录 ZIP 中每个内容对象解压后的大小和 SHA256 校验成功。bundle 为增量备份，恢复需要保留当前仓库的既有历史；不是一份独立的整仓库备份。

需要恢复原分支时，先在主仓库运行 `git bundle verify .runtime/cleanup-20261015/retired-agent-branches.bundle`，再以 `git fetch <bundle绝对路径> <原完整ref>:refs/heads/codex/recovered-<名称>` 显式导入所需分支；原 ref 和提交见索引。不应批量恢复所有旧分支。

ZIP 内外的 `manifest.json`／`workspace-backup-manifest.json` 使用相同内容：

1. 根据 `workspaces[].label` 选择原工作区。工作树先从记录的 `head` 创建新的 detached worktree；普通副本按清单重建目录。
2. 对 `source=archive-object`，从 `objects/<sha256>` 取出原字节，核对大小和 SHA256，再写到该工作区的相对路径。不要把 ZIP 内路径直接交给无校验的批量解压。
3. 普通副本中的 `source=dev-baseline` 从 `clone-baseline-files.zip` 的 `files/<相对路径>` 读取，核对清单 SHA256。它记录冻结基线 `feeb96344cc189245bec2de52e427d655c05ace0` 所在工作区的精确字节，包括原有换行风格与既有 WIP；不能简单用 Git blob 或现时 checkout 代替。
4. 工作树的 `deleted_tracked` 记录被删除的跟踪文件；`metadata/<label>/index.patch` 与 `worktree.patch` 可用于核对或恢复暂存状态。不要在已经覆盖快照后重复应用补丁。
5. 恢复必须限制相对路径在新目标目录内，拒绝绝对路径、`..` 和符号链接穿越。

今后工作树统一放在主仓库 `.runtime/worktrees/<名称>`，普通测试副本放在 `.runtime/projects/<名称>`；不再在 `D:/` 根目录堆放项目副本。

## 待继续的候选

后续书／台体、物品框边缘、水、折跃门等仍按 `docs/CONVERSATION_HANDOFF.md` 和统一待办继续。旧副本中的未准入候选已归档，不能因目录清理而改称验收通过。尤其是物品侧视 v6 的恢复未完成记录仍有效；旧进程现已退出，恢复开发需先检查对应世界状态及归档，不能调用失效 PID。
