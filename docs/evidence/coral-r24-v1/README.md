# R24 珊瑚：周末入口与冷启动预检审阅包

2026-10-20，正式自定义水默认启用后，已完成五张珊瑚／树苗测试卡的实际挂载控件语义导航，以及三个新画廊的 editor／full／missing 预检。所有成功检查均完成恢复且冻结源不变；本包保留原报告和两张总览的原字节副本。

- [五卡总览](five-cards.png)：从上到下为 R09 树苗与珊瑚、R10 十种珊瑚植物、R11 原生珊瑚块、R12 六扇状态与支撑对照、R13 十种植物与水层序。每行左侧为实际卡片、右侧为载入后的编辑器。
- [三个画廊与三条路径](three-galleries.png)：从上到下为块、扇、植物与水；从左到右为 editor、full、missing。植物 full／missing 各有 40 个 ready 水模型；missing 的 20／30／60 个目标均已知且与 rendered 状态匹配。

两张总览由原始 WGC 图缩放拼接，不能代替原始逐格图或精确像素验收。扇的合并远景只辨认出部分扇面；六态朝外方向的独立贡献应查阅本轮保留的 AIR／stone／fan 对照，不能根据总览判定全部扇通过或失败。其余 54 个合法扇态、含水扇、原生精确网格及全部变换仍待验证。

`ui-report.json` 与 `visual-report.json` 是原报告，`ui-reviewed.json` 与 `visual-reviewed.json` 绑定各报告的 SHA256。五卡检查使用正常控件的原载入和确认回调，明确记录 `native_mouse_clicked=False`；没有前台激活或桌面输入。三画廊预检复用既有确认载入辅助逻辑，与五卡 UI 检查分别记录。

`delivery.json` 为原 48 项交付索引，`source-binding.json` 从冻结的 4,464 项源合同提取三个 debug 源和正式水 gate 的哈希。冷源合同为 `e01636104fbf3f7bc3aede3834a31cca0de74a8a3944f13b345fc68b75ef6a42`；相对默认水 D-v2 仅这四路径变化，39 个水 owner 和全部资源不变。主仓后来修正的 R08 压力板分类不属于这次冷源，须在周五最终候选补冷启动检查。完整水准入另见[正式水审阅包](../water-product-r24-v1/README.md)。

保留 `failed-precheck.json` 和 `failure-classification.json`：初版宿主错误要求初始 missing 场景必须有增量 commits，已恢复，随后按逐目标 known／state／rendered 和无 pending／building／failed 的实际语义修正。原失败没有被成功结果覆盖。`stop.json` 与 `exact-exit.json` 记录正常关闭及宽限后仍未退出，再按身份强制终止，game 退出 1、MCDK 退出 0；所有 owned 辅助进程均已结束。

检查包内完整性、原报告绑定及计数：

```powershell
python -I docs/evidence/coral-r24-v1/verify.py
```

另外检查当前主仓的四个冻结来源仍一致：

```powershell
python -I docs/evidence/coral-r24-v1/verify.py --project .
```

本包不包含冷归档、全部原图、sidecar 或运行时脚本，不能独立重放 GPU 检查；这些继续保留于 `.runtime/round-20261020/coral-weekend-r24-v1` 及此前逐例珊瑚目录。详细结果见[本轮记录](../../WATER_CORAL_R24.md)，周末操作见[人工清单 R09—R13](../../acceptance/2026-10-24-r23-candidates.md)。**本次新增用户人工关闭 0 项。**
