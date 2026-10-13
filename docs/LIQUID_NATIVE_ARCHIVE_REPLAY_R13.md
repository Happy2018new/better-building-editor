# R13 原生液体证据离线重放

R13 V2 原始的 palette/direct 对照报告现在可以在冷检出目录复算。新的宿主工具只重定位原始证据中的文件位置，保留原始源码和截图字节、SHA256、固定像素区域、阈值、背景截图门控、原生读取结果以及每个判定条件。它不会启动 Minecraft、调用 ModSDK 或访问网络。

该工作解决的是证据可维护性。复算得到的原始总结果仍为 `FAIL`：H/L 两个原生 palette/direct 路径均没有水包络像素；完整投影对照的水包络可见。原始 `side_uv_qualified`、`transparency_qualified`、`animation_qualified`、`production_qualified` 均为 `false`，不能据此宣布水侧面、透明度或动画已经通过。

## 重放方式

在任意检出根目录执行，三个归档目录可迁移到任意位置。需宿主 Python、NumPy、Pillow；本次实际验证环境为 CPython 3.13.13、NumPy 2.3.4、Pillow 12.0.0。

```powershell
python -X utf8 tools/replay_liquid_native_archive.py `
  --archive docs/evidence/liquid-native-write-r13-v2 `
  --source-archive docs/evidence/liquid-native-write-r13-v2-source-closure `
  --source-archive docs/evidence/liquid-native-write-r13-v2-source-closure-extra `
  --closure archive-index.json `
  --output .runtime/liquid-native-v2-replay-fresh.json
```

输出必须是尚未存在的文件。命令返回成功表示原始报告已精确复算，原始渲染判定单独保留在 `recomputed.status`。如果源码、截图、归档索引绑定、依赖闭包或任何判定结果不符，命令拒绝执行并不写出重放结果。

工具读取并校验全部归档原字节，然后用 `python -I` 子进程把冻结源码复制到临时目录。子进程仅把该目录的 tools、projection 包和冻结宿主 scripts 加入导入路径，工作目录也切换到临时目录。原始 scorer 会继续根据自己的临时根目录检查原始的九项源码绑定。原始绝对路径只作为归档查找 key；不存在对原开发机的源码、`.runtime` 或兄弟工作树的回退。

三个原始归档和其索引均保持不变。108 个冻结源码组成导入闭包，本次实际导入的 46 个源码逐个校验原始 SHA；源码导入审计也要求主要 scorer 依赖确实位于冻结树内。原始报告中的 session/owner/进程身份和 WGC 可靠性字段保留，只有 detached 截图校验副本的 `path` 被定位到归档文件。

结果比较仅允许最外层 `source`、`geometry_plan`、`analyzer` 三个引用的 `path` 因迁移而不同。这三项 SHA，以及所有其他字段、像素数、边界、阈值、readback/source gate、会话绑定门控和最终判定必须与原始报告完全一致；不做换行归一化或语义替代。

## 已保存验证

`docs/evidence/liquid-native-archive-replay-r13-v1/` 保存冷复制验证的原始输出、两个拒绝栈、测试输出及当次 helper/test/script 原字节快照。13 个文件共 60,552 bytes；索引 SHA256 为 `3b2afc30ff41f13a0d8391213b4816496730344bed28afd87bfd8c2896fcb4fb`。`.gitattributes` 对该目录禁用文本转换。

实际冷复制根最初只有一个 `replay.py` 和三个原始归档目录，没有行为包、开发 tools、游戏实例或原 `.runtime`。冷复制的完整结果与原始报告一致；其 helper SHA256 为 `268e8bd26ac753aea817e30a38f1a36b78b6ff360bed8d4586318bfeeeea2484`。

两个故意破坏实验只修改一次性冷副本：将冻结 `analyze_liquid_sides.py` 的 CRLF 改为 LF，以及翻转原生 palette H 截图的一字节。两次均在归档原字节检查阶段拒绝，退出码 1，没有输出结果。原始三个索引在实验前后相同。

14 个宿主测试通过，其中四个使用真实归档：完整失败结果复算、换行拒绝、截图篡改拒绝，以及移除冻结 `projection.block_traits` 后必须导入失败。最后一项证明即使当前开发树仍有该模块，也不能回退到它。集成测试只在三份归档尚未整合时明确跳过；可以用 `BBE_LIQUID_REPLAY_EVIDENCE_ROOT` 指定 staging 证据目录，它只提供归档字节。

```powershell
python -X utf8 -m unittest discover -s tests -p 'test_liquid_archive_replay*.py'
```

这是一条原始观察的可重放路径；不新增渲染认可，也不扩展原六路径 H/L 试验范围。未来大版本升级应保留旧归档，新增新版本的原始截图、读取结果、源码闭包和索引，不能用新源码替换旧绑定来让旧证据通过。

## V4b 收尾兼容检查

15:37 对已完成的 V4b 归档进行一次只读冷复制重放，无新游戏、SDK 或网络调用。原 193 条索引含 117 个源码记录；原索引 SHA256 为 `d43ed2405aa85ce8cc184e39134a41d89a914088672ca1144d9866ecf6cde342`，检查前后相同。当前 helper 原字节不改，实际导入 46 个冻结源码，复算与原 `native-write-analysis.json` 全字段一致（仅三个路径不同）：`status=OBSERVED`、`native_visibility_observed=true`，UV、透明度、动画、生产认可仍为 `false`。

直接把 V4b 混合索引传作 `--closure` 尚不支持：76 个非源码记录没有 `project_relative_path`；源码记录的两个原路径均指向冻结 `.runtime/sources`，缺少原计划绑定的项目路径别名。此次只在冷副本新增派生源码清单，按已有 `frozen_project + project_relative_path` 得到项目别名，并保留冻结原别名和所有原 SHA/bytes。每个源仍须通过完整原索引和原计划的双重检查，没有归一化或门槛降低。输出及派生规则的原始工件保存于 `docs/evidence/liquid-native-archive-replay-r13-v4b/`。

下轮待办：为 V4b 补充不可变的 117 源码清单及项目路径别名，或在 host helper 中明确支持从混合索引派生并测试这一规则。需要同时覆盖非源码记录过滤、重复别名冲突、原索引不可改、原计划 SHA 不可替换，以及 `--expected native-write-analysis.json`；不能把此次一次性兼容验证误报为已完成默认 CLI 接入。统一待办和交接应引用本条。
