# R29 末地编辑器 GUI 锚点修正

2026-10-26，本地 dev 已接入上一轮实机对照确定的锚点修正：末地传送门与末地折跃门的编辑器表面，使用当前原生 GUI 倍率计算骨骼锚点补偿。原先固定 `min(size)/4` 会在 GUI2、GUI3 下产生偏移；现在通过 `PortalProfile.ui_offset_for_gui` 使用 `min(size)/actualGUI`，GUI4 与原公式相同。

Scene 在每次回调读取 `Theme.native_gui_scale`，因此同一场景内 GUI 倍率改变也能更新位置。旧 profile 没有此 hook 或明确设为 None 时继续调用其既有 `ui_offset`；非法或未初始化的原生 GUI 倍率明确拒绝。此次只改 profile 与 Scene 的末地回调，不调整模型、shader、星点参数、世界姿态或 Scene owner 生命周期。

诊断依据是 [R28 V4 原生位置与 A/B/A 实图](PORTAL_GUI_ANCHOR_R28_V4.md)。该历史实验不是本次新源冷启动，也不关闭星点密度、亮度、速度、完整／缺失投影或其余外观问题。

`tests/test_portal_gui_anchor.py` 的四项回归覆盖 GUI2／3 修正、GUI4 恒等、输入边界、同一实际 Scene 回调的 2→3→4→2 切换和旧 profile 兼容；与五项既有书本锚点回归共同通过。其余 35 项末地定点测试通过。真实 Python2／3 的完整候选编译及 profile／实际回调控制通过；root 已逐字核对主仓两文件等于该候选，完整 Scene AST 只有末地回调体变化。结构审查保留 Scene 原有长函数和参数提示，没有新增依赖或端侧调用。

本次 Scene 改动会使水 41 项显式实现来源及书本 19 项 owner 来源中的 Scene 指纹改变；末地 19 项来源另含 profile。新源必须单独冻结和验证，不能复制旧门或资格。新源实机与用户人工接受仍待完成，新增人工关闭为 0。内部离线控制留在 `.runtime/portal-anchor-r29-v1/`；产品及永久测试由 Git 提交保存。
