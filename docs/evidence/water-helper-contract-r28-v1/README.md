# 下一窗口水 owner 合同扩展：显式绑定 scene_owner

结论：**可以按现有 schema 合法地从 39 个显式源扩展到 40 个源，但必须先更新正式生成器的 SOURCES，把实际执行的 `scene_owner.py` 纳入，再生成新合同和取得全部新源资格。** 本目录仅提供下一窗口的离线工具候选与真实 CLI 控制，没有改主仓、原封 owner／portal／combined 候选、旧合同或旧 metadata，没有运行任何 qualifier，也没有复制旧 gate。

本次输入为 root 已独立重放的 `scene-portal-combination-v1/combined/`。`scene.py` 实际导入 `.scene_owner.own_preview`，五种 owner effect 均调用它；水的 `own_liquid` 也直接调用该 helper。helper 当前只有函数与 `__future__` 导入，没有新增业务模块的传递依赖。

## 正式水合同的具体缺口

| 文件／规则 | 实际行为与结论 |
| --- | --- |
| `tools/generate_liquid_product_owner_contract.py:10`，SOURCES | 明确列举源文件；当前列 Scene，未列 scene_owner。它不分析 import 依赖。只改 helper 时，旧 owner 指纹不会变。 |
| 同文件 `:29`、`:30`、`:38` | 遍历 SOURCES 生成规范化源 hash、generator 自身 hash 和整体 owner 指纹；输出结构没有固定 39。新增一项不要求改变 schema_version=1。 |
| `tools/check_liquid_product_owner_contract.py:8`、`:33`、`:56` | 明示是“explicit SOURCES，not a transitive dependency closure”，动态遍历生成器清单；不会自行补 helper，也没有计数锁。 |
| `tests/test_liquid_product_owner_check.py:82` | 现有测试明确验证“未列 helper 的修改不在检查范围”。这是当前工具声明的边界，不是本次可以豁免实际依赖的理由。 |
| `tools/qualify_water_product_r16.py:22`、`:68`、`:295`、`:368` | 从正式生成器导入 SOURCES／generated；source_closure、生成结果比较和 qualification implementation map 都随清单动态扩展。无需为 40 改 qualifier；本次没有导入或执行它。 |
| `liquid_product_deployment.py:67` | 比较 qualification 与 owner 整体指纹，不检查源数。新 owner 指纹不能与旧 qualification 配对。 |
| `tools/probe_product_water.py:210`、`:215` | 对 behavior_pack／resource_pack 递归快照。实际纯函数离线调用已确认会收集 helper，正式 `source_file_sha256_before/after` 可绑定新源。 |
| 同文件 `:340` 的小 `source_sha256` | 只是另一个手工缩略字段，未列 helper；正式水 qualifier 使用完整 `source_file_sha256_before`，不能把此缩略字段当完整闭包。 |

已定点扫描生成器、checker、正式 qualifier、probe、freeze、历史 audit、runtime deployment 与 checker 测试共 8 个文件，没有发现比较源数量等于／不等于 39 的代码。此结论不声称穷尽历史 `.runtime` wrapper；旧 sealed 记录中的 39 是当时事实，不应改写。

## 最小补丁与真实控制

`generator.patch` 只在现有 SOURCES 的 Scene 后新增 `'scene_owner'`，不修改规范化、schema、比较规则或 gate。补丁 SHA-256：

`516d95f99d109f5c24f27b31c7e6c308cf89cd42b0f30388873968bab1288405`

`projects/baseline39/` 和 `projects/candidate40/` 都是新私有工程，输入为主仓 39 个当前源，加上只读复制的 combined Scene／portal profile／helper；两工程之间已有 39 项规范化源 hash 完全相同。它们没有拷贝 `liquid_product_qualification_data.py`。本次生成的 owner module／合同只存在这些新工程中，不是既有产品 metadata。

真实 CPython **3.13.13** 已执行 14 次独立 CLI 调用；每次完整 command／cwd／returncode／stdout／stderr 保存在 `calls/`。正式工具使用 pathlib，作为 Python3 host 工具运行，本记录不声称在 Py2 执行了生成 CLI。

| 实际控制 | 退出结果 |
| --- | --- |
| 旧清单新工程生成 39 项，再 `--check` | 0／0 |
| 只修改该工程未绑定的 helper，再运行旧 generator `--check`／checker | **0／0，实际演示漏检** |
| 新清单新工程生成 40 项，再 generator `--check`／checker | 0／0／0 |
| 修改被绑定 helper，运行新 generator `--check`／checker | **1／1**；checker 精确列出 helper changed |
| 恢复 helper | `--check` 0 |
| helper 仅 CRLF→LF | `--check` 0；既有规范化不变 |
| 暂时移走被绑定 helper，运行新 generator `--check`／checker | **1／1**；checker 列出 helper removed |
| 恢复 helper 后最终 `--check` | 0 |

所有 check 调用均未改写生成的合同／owner module。漂移、缺失负例没有运行生成覆盖旧结果；正例恢复使用保存的私有输入原字节。`controls-summary.json` 记录新合同 schema=1、精确多出 helper 一项、自身 generator hash 与 helper hash 一致。

私有 candidate40 合同 SHA-256：

`33f455ee6d334b13b4262eb991d44ca779f26654551533f0c983dba66a59d050`

这只是当前私有输入的离线指纹，不能直接移植到下一窗口。届时任何源或工具字节变化都须重新生成并绑定实际启动快照。新生成器自身也包含在合同 hash 中，因此只手工给 JSON 添一条、只复制 owner module 或仍用旧 host 生成器都不成立。

## 旧报告／归档工具的兼容缺口

`tools/audit_water_source_closure_r15.py:47–48` 对“当前合同的每项”直接执行旧 archive 的 `archive.read(relative)`。只读检查了它当前指定的两个真实 ZIP 中央目录：final 2,009 项、biome 2,024 项，均没有新 helper。若用 40 项当前合同再次读取这些旧 ZIP，会在 helper 上 KeyError；不能把新增源当作旧捕获已有内容。

`tools/summarize_water_checkpoint_r16.py:55` 同样把当前 owner 合同的每项直接索引到旧 report 的 `source_file_sha256_before`。旧报告没有 helper 时会 KeyError。它和上面的历史 audit 都没有写死 39，但对新增源缺少“历史未捕获”的结构化诊断。**本次不修成通过，也不补写旧报告；如后续改善，只能明确报告 added/unavailable，不能据此接受旧证据。**

`tools/verify_qualified_git_bytes.py:23` 从传入 qualification 的 implementation map 取文件，数量是动态的。旧 manifest 仍只代表旧源，下一窗口必须产生新的正式 manifest，才能使该校验覆盖 helper。

## 相关 owner 闭包也要同步审查

另有两个已确认的显式清单目前同样列 Scene 而未列 helper：

- portal：`tools/probe_portal_product_r16.py:15–18` 的 SOURCES；其 qualifier `qualify_portal_product_r16.py:9/28/40` 消费该清单。
- book：`tools/probe_book_native_r16.py:18–21` 的 OWNER_SOURCES；其 qualifier `qualify_book_product_r18.py:19/66` 消费该清单并核对 owner_files 集。

它们也实际经过新的 own_preview，下一窗口取得对应资格前必须审查并显式绑定 helper。**新的水 40 项合同不会自动替代 portal／book 的独立源清单。** 本次为遵守最小水工具准备范围，没有扩展这两套补丁或运行其 qualifier。

## 下一窗口执行边界与命令路径

先把已批准的 combined 源与 generator 候选放入新的独立完整项目，重新绑定 generator／checker／所有运行源和 host，随后在该项目执行：

```text
python -B -X utf8 <新项目>/tools/generate_liquid_product_owner_contract.py
python -B -X utf8 <新项目>/tools/generate_liquid_product_owner_contract.py --check
python -B -X utf8 <新项目>/tools/check_liquid_product_owner_contract.py --check
```

生成后需要重新取得与 40 项显式源及完整启动快照一致的 F/A/B/R/G/D 证据，**16 个正式水 gate 全部按原职责重新处理**：animation、biome、budgets、default_path、editor、geometry、lifecycle、neighbors、occupancy、projection_full、projection_missing、public_gallery、side_uv、transparency、transparent_overlap、visibility。不复制旧 true、不修改阈值／ROI、不以离线结构控制代替原生／冷启动验收。

正式入口仍是 `tools/qualify_water_product_r16.py`，由 root 在新证据、源审查和冷启满足后按既有 provisional／final 规则执行；本次没有调用它的任一函数。portal／book 的新 owner 资格亦须各自处理。

若只需只读重核本目录现有 candidate40 生成结果，可以在主仓根运行：

```text
python -B -X utf8 .runtime/round-20261023/water-owner-helper-contract-v1/projects/candidate40/tools/generate_liquid_product_owner_contract.py --check
python -B -X utf8 .runtime/round-20261023/water-owner-helper-contract-v1/projects/candidate40/tools/check_liquid_product_owner_contract.py --check
```

准备前后 47 项主仓保护文件、combined 的全部 3 份源码 hash 未变，收据在 `boundary-before/after.json`。本项是接续准备，**不计重构完成、不计新水／portal／book 验收、不增加人工关闭数。**
