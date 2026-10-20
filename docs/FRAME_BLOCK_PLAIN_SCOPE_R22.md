# R22 普通方块的有限部署范围

本轮产品 WIP 只准备部署 `minecraft:stone:0`、`minecraft:quartz_block:0`、
`minecraft:grass_block:0` 的 opaque 完整立方体内容。普通内容和人工附魔独立验收，
当前全部资格门仍关闭。生产门不能将这三个名称直接扩大成所有展示框方向、
旋转和发光框，也不能用 48 姿态 GLES 数学检查替代原生像素。

`frame_block_measured_profile.production_items()` 要求每个接受的精确物品都有
非空 `QUALIFIED_FRAME_POSES`，当前允许申请的范围限于普通 `minecraft:frame`、
`facing_direction=2`、`ItemRotation=0`。`sprite_content()` 在解析真实展示框材质
和 typed NBT 旋转后执行该名单；其他姿态返回不支持，原文档不变。
显式 candidate profile 不带这些限制，后续可以按授权测试其他姿态。

这是 Root 产品文件的增量。已经冻结并获准运行的 v2 冷项目继续保持原字节，
用于测量新 namespace 的默认资源。v2 candidate 原图不能宣称验证了后来加入的
生产资格路由；正式部署前还需新的生产 profile 冷启动最短三路确认。

新增离线测试遍历两个展示框类型、六个朝向和八个旋转，确认只生成一个接受的
普通 frame 内容；编辑器及世界模型各自使用正确名称，typed 文档完整不变。
另验证空、缺失、扩展及含布尔值的 pose 名单被拒绝。
与既有 sprite planner 一起共 22 个测试通过，三文件范围审查 0 findings。
生成器已增加空 `QUALIFIED_FRAME_POSES={}`；除生成配置外，新资源输出逐字节不变。

## 默认光照的来源边界

原生 `entityVertexUtil.h` 标准 FANCY 分支与候选 `frameIntensity` 表达式相同，
尚不能将既有约 1.07 倍亮度差异归因于公式系数。原生实际 frame draw 的材质、
宏定义、`TILE_LIGHT_COLOR`、vertex COLOR 和 fog 输入没有被原采集记录。
`COLOR_BASED`/`ITEM_IN_HAND` 可引入顶点色与 tint，原生片元还在 glint 前应用 fog；
这些不同项必须依据实际路径核实，不能直接假定任意一项就是成因。

Item 世界路线复用 `WorldLiquidRenderer`：`CreateModel(level)` 创建自由模型，
锚点使用 `anchor + group.origin + 2`，四格内的实际内容位置由 shader 解码。
整组自由模型的 `TILE_LIGHT_COLOR` 与原生 frame 所在位置的取光输入无法仅由
当前 Python 源码证明相同。不能把“复制了原生方向公式”当成光照输入也等价。

MCP 文档确认 `SetBrightness` 只支持替换骨骼模型的实体，没有确立可用于本路线
的自由模型 light setter；`GetAmbientBrightness` 只影响天空，明确不影响实体或
方块光照。`GetBlockLightLevel` 返回已加载位置的等级，但它不是 shader 原始
`TILE_LIGHT_COLOR`。这些 API 不能被写成已验证的亮度修复。

本轮先实测无 `0.93` 的默认石头新资源，若重复偏亮则保留失败并停止无关扩展。
原来的 scalar 是经验实验，不能作为原生光照因果或正式产品资格。
