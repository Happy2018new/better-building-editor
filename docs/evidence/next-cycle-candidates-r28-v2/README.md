# R28 下一周期私有候选

本包保存可审阅的最小补丁、原始／候选源和离线控制。两项均未合入主程序，未启动游戏验证，不增加人工关闭，也不转授任何水或末地产品资格。

| 候选 | 内容 | 已执行的控制 | 仍须执行 |
| --- | --- | --- | --- |
| `portal/` | `PortalProfile.ui_offset_for_gui` 与 Scene 的可选分派，编辑器锚点改用实际 GUI 倍率 | 实际 Python 2.7.13／3.13.13，各编译4个源；8个公式、9个真实回调分派、12个非法 GUI、同一回调 GUI 变化及21个历史 V4 尺寸控制 | 新源默认冷启动、GUI2／3／4原图及原生读回、两投影路径和恢复；受影响的水16门与末地12门依原流程处理 |
| `scene/` | 五个 owner 的 Session 登记和 cleanup 机械抽为24行 helper，构造及 hook 仍留 Scene | 实际 Python 2.7.13／3.13.13，各8个真实 Scene 构造／hook 控制、50个真实 owner 闭包控制；其余完整 Scene AST 相同 | 合入最终源后的真实生命周期及显示、冷启动和受影响水合同重新绑定／验证 |

基准提交为 `b70ce7bf13ad6a4472f2b089ac812c162b174861`。`portal/index.json` 与 `scene/ready-index.json` 是代理原封索引，所有绑定字节已由 root 独立核对；`root-review.json` 记录独立 Git blob 和两解释器复跑。root 另读实际 helper AST，确认没有新增循环、异常吞错、finally 或幂等标志，仍先 `controls.close()` 再 `preview.close()`，之后按 preview 身份清理。

Scene 的 close 异常仍原样传播；旧 owner 迟到时先关旧资源再检查 Session；水／物品保留带默认值的 `getattr`，其他三族保留缺字段抛错；重复 cleanup 仍重复 close。这里保存的是机械重构候选，异常行为改善应单独讨论和验证。

两套控制执行实际候选函数及原 Scene 的真实函数／前缀，但 scheduler、Session／Theme、native factory 和资源 close 使用明确的离线边界对象。没有执行 SDK、实际 Pyreact 调度、Scene UI 或 GPU。历史 V4 图与公式只是设计依据，不是候选已取得真实显示资格。

原控制脚本完整保留原路径假设，**不能从本归档目录直接运行**。要复跑，可在新的工作副本将各目录恢复为原位置 `.runtime/round-20261023/portal-anchor-candidate-v1/` 和 `scene-owner-minimal-v2/`，并使用脚本要求的 fresh 输出路径；不要覆盖历史回执。portal 的历史尺寸对照还读取已提交的 `docs/evidence/portal-gui-anchor-r28-v4/raw/report.json.gz`。下一窗口如基准源变化，应先重新生成候选，不能盲目应用旧补丁。详细准入步骤见 [portal/NEXT_ROUND.md](portal/NEXT_ROUND.md) 和 [scene/README.md](scene/README.md)。

root 首次归档预检因错误要求 `cell.py` 的工作树字节等于 Git blob 而停止：Git 为 LF，`core.autocrlf=true` 的工作树为 CRLF；两份原始 SHA、长度及仅换行标准化后的相等分别列入回执。候选执行的是 Git 原字节的 `support/cell.py`，没有改任何产品文件或候选来消除差异。失败脚本和简要失败记录也在本包中；首次未完成目录留在本地，未当成功归档。

下一周期仍使用既定约6小时重构容量，其中约4小时为实施和真实验证安排；这些准备不重复计为产品重构完成。生命周期 helper 留主仓，不迁往纯规则库；两库最小接入仍排10-31—11-03。
