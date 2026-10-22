# R28 水：既有 A 原图重放、F 水池就绪失败与几何候选

本记录覆盖 2026-10-22 晚／2026-10-23 凌晨的水专项。当前结论：原 R27 的 A 捕获在既有门限下同时满足可见动画与物理移动方向；本轮 F 编辑器在水池遇到可复现的 PaperDoll 就绪问题，尚未完成 F，也没有完成当前发布水产品资格。人工关闭数增加 **0**。

## A：复用原始捕获，完成已有可见动画门

R27 A 的 15 个 case 为编辑器／完整投影／缺失投影各 4 个水平方向及下落水。原始 30 张静态 PNG、15 段 burst 以及原始捕获报告保持原字节。本轮没有为此再开 MC，也没有重新采集 A；冻结源和辅助文件在准备 F 时分别核对 4,482／1,391 项。

沿用已复核的同会话石头标定、实际 GUI2 锚点分析与原门限，对原始 PNG 运行 `analyze_product_water.analyze`：

| 项目 | 结果 |
| --- | --- |
| 原捕获有效性 | 通过 |
| 可见动画 | 15／15 通过 |
| 物理移动方向 | 15／15 通过，复用冻结方向分析结果 |
| root 独立重放 | 完整分析与摘要逐值相等 |
| 实际速度幅值 | 未测量，保留限制 |
| 原生 RGB 完全一致 | 未作此主张 |
| 整套当前水产品发布资格 | 未完成 |

新动画分析 SHA256：`12ac7f1be48b1cc11f133cb23530692df036ded7672e4d6f029b28637467ba62`；摘要 SHA256：`7d411250f0e49beb03c1c283ccb1dd292370b0411a3e88a6067d735e94c07e95`。原 R27 旧编辑器 ROI 失败与 GUI 锚点修正分析均继续保留。此处没有新建原生速度／RGB 拟合矩阵。

## F：正常冷启动后在水池失败

F-editor v2 原计划覆盖 19 个公开 case、wet/dry、4 个含水本体的额外对照、剖切／恢复、池侧面、alpha 和 owner 预算。实际正常冷启动、普通会话初始化、GUI2、世界只读基线均通过；先完成 source、low、diagonal、drop_north 的 wet/dry，共 **8 行、14 张原始 PNG**。随后 `pool_wet` 的 liquid owner 报：

> Liquid skeleton model ID did not become ready

8 个水组中，6 个已取得独立 native ID，另外 2 个同属批次原点 `(4, 0, 4)`，native ID 持续为 `-1`。该运行没有原样重试。原始失败报告保持不变，不能把已完成的 8 行当作 19 个 case 通过。

独立恢复检查为 true：Scene、profile、timing、世界、相机锁与旋转、源文件恢复；自有 marker 和 actor 清空。普通 stop 首次报告未关闭，exact-handle 观察随后记录游戏退出码 `0xC0000409`、MCDK 退出码 0；最终两个 creation identity 均消失，helpers 退休。未触发 handle／modal 资源门。退出码异常保留为实测事实，不把进程消失写成正常退出码。

## 离线根因与最小候选

`group_view()` 先调用 `render_bounds()`，使未加锚点偏移的 UI 矩形覆盖 viewport。Scene 随后给产品水加 `min(size)/GUI` 的竖向偏移，会破坏这一覆盖关系。

失败组的实际 geometry 读回为：position `(0, 183.3057)`，size `(366.6114, 413.8420)`。以已 ready 的 6 组当前 `scale × min(size)=52.9092`、冻结 `Scene.unit()` 和 `render_bounds()` 推导 native viewport 为 `340.625 × 159.75`；**该 viewport 是源码与实际读回的推导值，原失败 host 没有直接读回 canvas／clip 大小**。失败组的偏移后矩形与此 viewport 的交集为零，6 个成功组均有交集。失败两组的 pending pose 来自更早布局，不能用它们代替已 ready 组推导当前像素单位。

仅产品水的新 geometry 回调候选为：

```text
W' = W
H' = max(W, H + 2W / GUI)
P'x = Px
P'y = Py + (H - H') / 2 + W / GUI
```

这里 `(P, size)` 为尚未加水锚点偏移的 `group_view` 结果。新矩形包含旧的未偏移矩形。新 `min(size)=W`，按现有 `ui_pose` 对新尺寸重新计算 scale 后，`scale × min(size)` 和目标模型屏幕中心不变。**raw scale 数值通常会改变**；保持不变的是有效像素单位和投影。对失败的两组，新矩形为 position `(0, 0)`、size 约 `(366.6114, 780.4534)`。

候选限定于 `ProductLiquidProfile`，Scene 优先采用可选几何回调；没有该回调的 profile 保留原回调逻辑。没有全局修改 `group_view()`，没有延长 readiness timeout。书本独立 GUI 锚点问题另有记录，水的矩形原因不能代替书本旧 GUI4 缺画的结论。

离线验证包括：实际 8 组／216 个投影点、GUI1／2／3／4／8／16／256 共 3,500 组几何、11 个非法 GUI 输入、4 个负控；全部达到预期。执行实际 Scene 回调 AST，24 个旧 profile 对照逐值相同，新回调 12 个对照逐值相同。这些是解析与离线检查，尚不证明候选在 native 中成功。

候选已准备为私有冷源：原 119,618,244B ZIP 基档复用，2 个精确文件的 overlay 为 11,976B，逐字重构核对全部 5,873 项。没有修改原冻结源或共享正式源。下一步仅运行正常冷启动的 pool wet/dry，加实际 canvas／clip 读回；通过后再决定是否扩展 F。候选 owner、资格与旧接受数据不转写为新接受。

## 可提交证据

[证据索引](../evidence/water-A-replay-F-pool-r28-v1/index.json) 包含 A 新重放、root 重放结果、F 原始失败、14 张原 PNG、恢复／退出记录、host、实际失败 state、候选和负控。A 的 30 张原静态 PNG 按 SHA256 引用已提交 R27 bundle，不重复复制；burst 原档及大源 ZIP 保留于原 runtime。

索引 SHA256：`3c9a596cb02e2b8350bed2fc7fa81127b0c4ed8a9f56ea22dbf192a771161180`。94 个对象、98 个存储文件，总 3,385,629B，单文件不超过 240,000B。原始与脱敏重构 SHA 分列，递归 JSON／base64／转义及本地凭据扫描未发现待处理项；提交前由 root 独立重构与扫描。

剩余范围仍包括完成 F 编辑器／投影矩阵、B 群系与占位恢复、R 反向邻接、G 公开全览以及当前源的冷启动默认路径／最终资格。此次没有因为 A 已通过而关闭这些门。
