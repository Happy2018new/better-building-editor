# R25 恢复批次：整合回归与库来源

记录时间：2026-10-21 12:57，北京时间。首次全量来源为 `7c7c32f05fbc6d4eb0e7e9895f060f1f39b8860c`，修正后第二次全量来源为 `900100aa402f7442b1f1cf6cf1554f1f3d76fd14`；两批结果独立保存。

## 恢复后首次全量

09:43:27—09:55:48 使用 Python 3.13.13 执行 `python -B -X utf8 -m unittest discover -s tests -q`：**3,429 项，ERROR 1，跳过 1，整体未通过**。unittest 报告730.932秒，子进程墙钟741.706秒。这是恢复后的实际新执行，没有复用中断前3,358项的结果。

运行前后 HEAD 均为 `7c7c32f0…`，`behavior_pack`／`resource_pack`／`tests`／`tools` 共6,297个文件、259,195,599字节的逐源SHA256无变化。输入包含10个历史未跟踪测试及其他未跟踪工具，因此这是该时点的当前工作树回归，不能宣称仅检出干净HEAD即可重现。

唯一错误位于 `test_botanical_neighbor_snapshots.BotanicalNeighborSnapshotTests.test_partial_projection_retains_original_hidden_neighbor_and_both_layers` 的 `kelp_wet_chain` 子例：旧断言查找原生 `('minecraft:kelp', 0)`，而已提交实现按完整源邻域使用茎／顶代理，触发KeyError。原失败日志、前后来源与汇总完整保留于 `.runtime/round-20261021/resumed-integration-v1/`，未覆盖或改写为通过。

## 唯一错误的定点续验

仅修正 `tests/test_botanical_neighbor_snapshots.py` 的海带期望。对只选择中段的三格含水海带柱，明确检查隐藏下段为茎、中段仍为茎、隐藏上段为顶；三格背景水均保留在extra，逻辑文档仍是原生海带，渲染common不残留原生海带。其他植物的原断言和完整源快照不变断言保留，没有删除或跳过海带子例。

10:00:23—10:01:31，Python3对以下9个模块执行**99项，全部通过**：`test_botanical_neighbor_snapshots`、`test_kelp_render`、`test_kelp_blueprints`、`test_kelp_resources`、`test_render_context`、`test_context_batches`、`test_water_interactions`、`test_water_native_projection`、`test_complete_cells`。随后真实Python2.7对 `test_kelp_render` 执行**13项，全部通过**。18个聚焦源码／测试文件在该定点运行前后哈希不变。

定点命令、起止时间、原测试备份和最小diff记录在同批次的 `kelp-assertion-followup.json`、`kelp-assertion-focused-py3.log`、`kelp-assertion-focused-py2.log` 与 `botanical-neighbor-test-fix.patch`。这99／13项是错误修正后的定点证据，没有把先前失败的3,429项改记为全量通过。最小测试修正随后保存为 `374136c6`。

## 修正后第二次全量

在测试修正和T02公开变换卡 `900100aa` 均提交后，使用同一解释器与同一discovery命令另起一次全量：**3,431项，跳过1项，整体通过**。前后HEAD均为 `900100aa402f7442b1f1cf6cf1554f1f3d76fd14`，6,297个输入文件共259,203,560字节，逐源哈希无变化。第二批仍包含前述历史未跟踪测试／工具，不能标为干净HEAD独立回归。

原始时间为10:17:02至12:57:04，进程墙钟9,604.070秒，unittest计时9,588.098秒；中间包含用户说明的会话中断／挂起时段。这些是原样保留的进程计时，不能据此计算有效开发工时或额度，不能改写成连续有效运行约160分钟。

第二次结果独立保存于 `.runtime/round-20261021/resumed-integration-v2/` 的 `unittest-summary.json`、`unittest-discover.log`、`source-before.json` 和 `source-after.json`。相对第一次输入只改了三个文件：`debug_transform_acceptance.py`、`test_transform_acceptance.py`、`test_botanical_neighbor_snapshots.py`，差异记录为 `source-delta-v1.json`；其他6,294个输入相同。原先的ERROR记录和定点修正记录均保留。本批只是CPU整合回归，不取得T02或其他产品路径的实机／人工资格。

## 独立库续接

renderer在09:44通过正常生成器刷新，保存本地main提交 `4e4f0b2d1d4b0faf0e3ca0caf53e323bc817e531`，未推送。来源绑定为 `7c7c32f0…`，绑定路径没有工作区修改；只有 `geometry_palette`／`render_context` 两个边界哈希变化。布局、3个资源、另外6个边界、owner和states绑定不变。

库内 `docs/verification/2026-10-21-layout-parity-r25-resumed.json` 记录新执行的66,249次布局调用、8个边界、3个资源和状态清单检查，全部通过。真实Python2.7／Python3.13各7项重新通过。原manifest、生成模块和说明文件在本批次 `renderer-before/` 备份，原报告保留。

states保持干净提交 `58534dc5956848b4e6e5bcba97ad7112e2802388`，manifest SHA256为 `36a7a2ad36dfdaa948474daf086a5716a2fbd0fc6c46dc810c5e30e6f04626ae`；未修改或提交该库。主仓仍使用原实现，未切换两个库的生产依赖。

本摘要只记录CPU整合与来源维护，不授予GPU资格，不改变水profile准入，不关闭未检查的组合；新增用户人工关闭为0。T02变换卡及其定点验证见[方向卡记录](TRANSFORM_DIRECTIONS_R25.md)：它进入第二次CPU全量，未进入第一次来源；实机资格仍由对应专项持有。

两次全量、首次错误及定点修正的15项原bytes记录已保存为[整合小包](../evidence/integration-resumed-r25-v1/index.json)，四份大来源清单使用gzip，全部单件小于300KB。[最终三包独立审核](../evidence/r25-final-packs-review.json)复核raw、压缩和解码hash，仍保留首次ERROR。包内 `second-evidence-document-readonly-review.json` 是共同冷源包token脱敏前的只读快照，其中旧index hash不代表当前27份原件＋1份脱敏派生件；当前包以各自index及最终审核为准。

此后 `adafea2f` 只修正catalog内90°／270°旋转的两条提示及对应手册，将“围绕选区中心”改成实际的最小坐标锚定语义。真Python2.7／Python3.13已确认64个工具的ID、分组、标题、参数、图标、材质不变，MCP定点review扫描1文件无发现。3431项全量仍归属900100aa的输入，不冒称已在新提示来源重跑。
