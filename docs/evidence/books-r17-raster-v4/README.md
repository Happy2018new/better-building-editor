# 书本薄面光栅修复及原生页面对照

2026-10-15，NEMC 3.10.0.420447。此目录是候选书外观的专项证据，**不授予生产资格**。树叶等真实方块选框穿透的修复另见`../render-depth-r17-v1`。

## 原因与修改

薄封面是有两面的极薄盒体。深度写入修复后，双面绘制使前后表面在部分旋转姿态竞争同一深度，形成密集碎点。先统一所有盒底的三角形绕序，再在实际NEMC UI／世界骨架坐标下选择外表面：当前这套几何需要`InvertCulling`，保持深度写入并关闭`DisableCulling`。普通默认剔除虽没有碎点，却会显示封面内侧、页体内部和错误明暗，因此被否决。

诊断alias仅修改剔除状态，保持原有状态继承；早期添加`states: []`的对照有干扰，不能用于本结论。shader保留`highp`，四个正式资源使用相同修复，生成器与几何版本一并保存。

| 对照 | 动态候选帧 | 碎点检查 | 原生封面图案分布 | 结论 |
| --- | ---: | --- | --- | --- |
| `double-negative` | 16 | 失败，多姿态密集异常 | 失败 | 有效旧错误负控 |
| `inside-negative` | 16 | 通过 | 失败，内侧暗色区域过多 | 防止“没碎点就算修好” |
| `exterior-control` | 16 | 通过 | 通过 | 明确外表面方向 |
| `final-reference` | 16，加6帧原生与attached视图 | 通过 | 通过 | 最终资源名冷启动，无alias |

前3组各19帧完成恢复；最终`final-reference`23帧完成恢复。`final-reference-v1`还包含真实有书讲台与候选的重复近景；其中附魔台原生仅有一个足够宽的封面样本，故没有用它授予封面分布通过，而是补拍了6帧原生的v2。

封面分析器同时检查原图指纹、可靠截图、恢复、来源不变、时间跨度、样本数和目标大小。薄面指标检测均匀棕色区域内的孤立异常像素；图案指标将足够宽的封面暗色占比与原生同机位参照比较，容许整体曝光变化。两者都只覆盖这里明确的缺陷，不代替整体姿态与各视角验收。

## 讲台及三路径复验

`final-reference-v1/lectern-analysis.json`验证真实放书所得typed NBT、同位置／同相机、静止原生双帧；页面主体中值RGB为原生(211,200,157)、候选(213,201,158)。3像素边界容差下precision 0.99826、recall 0.99075；没有通过平移、缩放或调色获得分数。这是固定正面页面的有限通过，不能宣称所有面逐像素相同。

`final-product`23帧及4张review已实际检查，覆盖编辑器正反视角、常驻旋转、切面、图层隐藏／恢复、空／有书讲台、full和missing。所有运行completed/restored/source_unchanged，cleanup_errors为空。`crops.json`保留原图／精确裁切SHA256，`report.json`保留完整回执与实际模型名；原图在相应本地`.runtime`目录。正式资源快照现在包括实际注册模型和材质entry，不再只依赖可能过期的生成contract。

## 仍未完成

- 附魔台本体低0.125格并与支撑相交，证据在`../enchanting-body-offset-r17-v1`；不能通过移动书pivot掩盖。
- 书仍使用隔离候选注入，尚需独立产品owner及完整普通入口生命周期／占用／透明度矩阵。
- 本轮没有因此开启书、物品或水的生产gate，也没有替换既有banner／portal等资格。

工具：`prepare_book_raster_controls_r17.py`、`probe_book_reference_r17.py`、`probe_book_native_r16.py`、`analyze_book_surface_r17.py`、`analyze_lectern_book_r17.py`、`pack_book_diagnostics_r17.py`。14项书专项测试通过，包括绕序、atlas、状态继承、实际材质指纹、碎点和内外图案负控、页面缺失／变暗／位移负控。
