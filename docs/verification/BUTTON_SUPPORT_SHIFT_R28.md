# R28：T02 支撑块 Y+4 位移诊断

本次在精确 `2ab5a29a21f68bac607637b10d4afb42ac9caaa6` 冻结冷源完成一次支撑块 A／B／A 诊断，三个阶段均有实际原图、同会话来源与校准记录。结论仅为隔离支撑模型的位置随输入变化符合预测，**不关闭按钮附着、厚度、遮挡或 T02 全矩阵**；新增人工关闭 **0**。

## 实际范围与结果

从真实公开 T02 卡正常清除 58 格，保留原 Document／editor／尺寸与两格逻辑内容；诊断私有模型使用固定原生 volume `(16,16,10)`。创建 combined、button-only、support-only、shifted-support 四个独立模型，但本次三个显示阶段只绘制支撑，**没有绘制按钮**。固定 yaw 35°、pitch −80°、zoom 12，依次显示 support_before → support_Y+4 → support_after。

| 观察 | 实际结果 |
| --- | --- |
| 原生输入 | 原支撑 index 1083，移动后 2107；差值对应逻辑 Y+4，原逻辑文档未变 |
| 校准预测 | 画面位移 `(0, −59.91904018575101)` px |
| 三张原 PNG 的有限 ROI 轮廓 | 原位 `[586,309,706,442]`；移动后 `[586,249,706,382]`；恢复原位相同 |
| 实测中心位移 | `(0, −60)` px，与预测差约 0.081 px |
| 恢复对照 | 首尾 ROI 的 RGB 逐像素相同 |

root 已逐张打开三张原图，并独立复算上述轮廓、位移及首尾 RGB；同时核对包内 12 项索引、5 份原始报告指纹、26 份绑定 host 和 14 份 base64 内容长度。扫描未发现 API key 格式的凭据。有限 ROI 和可见轮廓测量不等于 GPU vertices／WORLDVIEW／tint uniform 原生读回，也不证明按钮与支撑同时显示时的深度关系。

## 失败历史、恢复与退出

旧 constructor 缺 Theme 字段的尝试、后续 v3 对合法 list／tuple 尺寸误拒绝均保留。v4 只将尺寸合同收窄为恰好两个正整数的 list／tuple，并通过 21 项负控；没有放松像素或校准门，也没有以重复相同输入覆盖旧失败。

诊断 native slots 恢复、60 格撤销恢复、原草稿恢复、两次独立只读恢复审计与冻结来源检查完成。owner `r28-button-shift-v4` 普通停止后 registry 为 stopped、watcher 已退役，没有强杀游戏。game PID 40720／creation `134371713006819645` 退出 **0xC0000409**，MCDK PID 69080／creation `134371713004953982` 退出 **0**；因此正常引擎退出资格仍为 false。

## 可审材料与后续

后续只读复核在原位移 ROI `[577,242,714,452]` 比较了同轮 combined baseline／support-only：有 **264 个非零差异像素，82 个最大通道差大于12，最大差22**，全部差异位于 `[626,365,665,403]`。82 个较强差异均落在 R27 单按钮的758像素轮廓内；combined baseline 与 original source restored、support before 与 after 各自在该 ROI 逐 RGB 完全相同。这支持存在可重复的微弱按钮贡献，不能把完整场景描述成完全无按钮输出。这里的差异指标只定位贡献，未新增外观通过阈值，也不与 R27 另一组261像素的不同原图／比较口径混用。

[按钮贡献小包](../evidence/button-visible-contribution-r28-v1/index.json) 保留5张原 PNG 和各自原 capture／host 元数据、完整原生输入与原证书、分析源码及明确标注的4倍最近邻衍生图。31文件合计995,492 B，逐文件小于240,000 B；大 JSON 用标准 xz 无损压缩，5份敏感 JSON 的原始、脱敏内容和存储指纹分别登记。root 独立逐项核对原始来源与包内指纹、5份声明的敏感字段修改，并确认402份 typed native wire 值不变；便携 verifier 在无 MC 条件下复算原生输入、264／82／82指标通过。索引 SHA256 为 `8aa4f97c31f43b6fa45ec181713b1b48f6d136469306f30482f6aba4cafa0a98`。

下一最小区分实验只考虑把原位置的石头支撑换成不透明白色混凝土，保持按钮 index827／aux0、支撑 index1083、native volume／pose／slot 不变，各自与对应 support-only 比较，并回到原石头对照。当前仅完成离线草案，没有新的实机结果；材料变化可能同时影响原生照明／剔面，因此即使对比更清楚，也不能单独证明安装、厚度或原版几何一致。人工关闭仍为0。

[精简证据索引](../evidence/button-support-shift-r28-v4/evidence-index.json) SHA256 为 `f165c1dec038225ef0d4665799fa00ea9d9c1402fe3ba74a15af64dddaa7d0e0`。13 文件合计 514,244 B，含三张原 PNG／metadata、来源链、轮廓测量、恢复审计及摘要；单文件均小于 240,000 B。完整生命周期和 UI 树留在原始 `.runtime/round-20261023/button-shift-lifecycle-v4`，其报告 SHA 在包内固定。

当前只缩小了支撑定位的排查范围。若继续研究按钮，需要在原生参照有效的条件下单独测按钮与支撑同时显示时的轮廓、原生 bounds／depth 及全部方向；本次不转授这些通过结论，也不要求用户重复验收已知无新修复的 T02。
