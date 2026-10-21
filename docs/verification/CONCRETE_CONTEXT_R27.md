# R27 混凝土邻接颜色与上下文副本

本记录接续 [OB-10 旧记录](../CONCRETE_COLOR_R23.md)。2026-10-22 的新候选仅移除**干燥、地面拉杆 aux5 自己的 context tile 中，正下方干混凝土的多余副本**；混凝土本身的 tile、其他目标的邻域、shader、透明度及边界裁剪均保留。此前 lever-owned 候选仍未合入。

## 匹配冷源：base 与候选 v2

两个独立冷副本从 `7015c9c4` 冻结，各有 3,709 项 runtime 输入。root 在归档时逐文件重新读回，两者仅 `render_context.py` 不同：base 为 `6989fda1…f0fcf84c`，v2 为 `5452d30b…81c8e4c4`。完整清单与原始报告分别压缩保留于[证据索引](../evidence/concrete-context-r27-v2/index.json)。目录 `candidate-*-product-v3` 中的 v3 是宿主尝试编号，实际产品仍是 **v2**，不与后续产品 v3 混用。

白色、淡灰色各在透明度 `1 / 0.45` 下完成 `empty → empty_repeat → above → restored`，共 32 个状态、64 张显示／隐藏原 PNG。原诊断工具、固定 ROI 与相机漂移门保持原值。root 独立重放原 PNG 的长度、SHA、文档／缓存／提交后来源和固定投影检查，并直接打开四张无损裁切拼图。

| 对照 | 原始像素结果 | 可见外观 |
| --- | --- | --- |
| base 默认透明度的 above | 两色的两个目标 ROI 全部像素变化，远角参照不变；白色前条／左条平均 ΔRGB 约 `(35.97,33.32,42.91)`／`(36.07,33.42,43.06)` | 混凝土中央出现亮格，拉杆仍可见 |
| v2 两色、两种透明度的 repeat／above／restored | 三个固定 ROI 相对各自 empty 逐像素相同 | 亮格消失，拉杆杆身和基座保留 |
| 两副本间的 empty／repeat／restored 及全部 opaque 状态 | 相同色的三个 ROI 逐像素相同 | 不透明与原有底色保持一致 |

四张拼图：[白色默认](../evidence/concrete-context-r27-v2/white_concrete-default.png)、[淡灰默认](../evidence/concrete-context-r27-v2/light_gray_concrete-default.png)、[白色不透明](../evidence/concrete-context-r27-v2/white_concrete-opaque.png)、[淡灰不透明](../evidence/concrete-context-r27-v2/light_gray_concrete-opaque.png)。精确数值来自原 PNG，拼图仅作外观复核；没有从 JPEG 推导精确像素结果，也没有据屏幕颜色宣称已测得 GPU draw count 或 blend state。

每组诊断均完成恢复。另一个独立观察器在工具前保存原 session／editor／document／factory、七个 profile 对象、工作区和玩家状态，之后确认 changed keys、actors、jobs、markers 均为空，并显式移除自身标记。两个实例均先普通 stop，精确句柄观察均记录 game `0xC0000409`、MCDK `0`，watcher 在创建身份核对后单独回收；不能称正常引擎退出。

首次 v2 宿主因默认截图程序旧路径不存在，在派发测试客户端前失败；失败原件也已归档。后续使用已审查的显式截图程序路径，没有删除或改写失败。

## 范围与下一门槛

v2 基于完整 logical 前／背景层判定干燥，避免自定义水准备阶段抑制水层后误判。其 896 组合独审覆盖 16 色、完整双层格、内区／跨 16 边界及 native／custom-water 的 CPU 准备；但发现历史 `minecraft:concrete` aux0–15 名称未获修复。因此 v2 **不合生产**，也不把两色 full 结果推导为所有名称与三路径通过。

产品 v3 使用现有注册表将原 logical 名称 canonicalize，仍要求背景为 AIR，且解析后的前层精确等于实际 prepared common 才授予标记。它保留另一冻结冷副本与自己的实机记录；v2 的截图不替代 v3 的实测。编辑器、缺失投影、红石线邻域、历史名称和含水负控须按实际结果另记。

本页归档不修改生产代码，**新增用户人工关闭 0 项，OB-10 总体仍开放**。其他颜色的实机外观、其他上方方块、其他拉杆状态、真实世界占用和自定义水 GPU 资格均不由本次结果扩大。
