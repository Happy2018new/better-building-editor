# R27 混凝土与地面拉杆：v3 冻结源码实机专项

2026-10-22，owner `concrete-r27-support-candidate-v3`。本记录支持一个窄范围候选修复：干燥混凝土承托地面拉杆时，避免在拉杆目标的邻居副本里重复绘制承托体；完整逻辑文档和承托体自己的目标不删除。它不代表 OB-10 整项关闭，也不新增人工验收关闭。

## 源码与冻结边界

- matched base HEAD：`7015c9c470f5cbb1144b2565a8eb740ac8f3e7e0`。
- 从原 matched manifest 精确复制 3,709 个 runtime 文件，只 overlay `projection/render_context.py`；未复制旧世界或缓存，关闭自动热重载。
- v3 源码 SHA-256：`966e2f35cba67d7810854fdcde7aed970dc2cea7c35ed1e26c497376ac17a1c0`。
- 原 matched manifest SHA-256：`5a3c99bd1ef306d95aa98b2de6b9aaac9305da8fa25722e61c94227f0685acc5`。
- 每条 RPC／截图的资源、进程身份、来源和时序门保持开启；完成后再次校验 runtime 文件集合和内容。

v3 在 v2 上补齐历史别名判断。先检查完整逻辑 background 为 AIR，再用现有 registry canonical 规则解析 foreground，且必须与实际 prepared common 一致，才写入仅供准备阶段使用的标记。水层被自定义渲染抑制不构成“干燥”的证明。

宿主行为测试共 5 个方法通过；同一测试在 v2 上有 34 个失败、0 个 error。包括 16 色历史别名 × 2 位置，224 个含水、反层、双 solid 和其他 lever aux 负控，以及继承的 896 项 canonical 矩阵。真 Python 2 AST 检查通过。这些 CPU 结果不单独授予实机资格。

## 本次实机结果

| 路径 | 覆盖 | 结果和边界 |
| --- | --- | --- |
| 完整投影 | 白／淡灰 canonical，历史 `minecraft:concrete` aux 0／8；各透明度 1.0／0.45；empty、empty_repeat、above、restored | 四份报告 completed/restored=true。target front、target left、reference corner 的 216 个 RGB 通道均值比较差值全为 0；参考 actor signal 为 2,558 像素。64 张 shown/hidden 原图。 |
| 编辑器 | blank、empty、above、restored、白色历史别名 | completed/restored=true；同一实际 viewport crop／相机，非 blank 四阶段均存在实际场景差异，超过 12 的像素数分别为 10,754／10,763／10,753／10,763。5 张原图。空白负控与 above 原图已实际打开检查。 |
| 受控 missing 投影 | canonical、白色历史别名、wet lever、wet support；各 air→support occupied→support restored→lever occupied→lever restored，含四向 wire | completed/restored=true；20 个 published 状态、40 张 shown/hidden 原图。source、current cache、origin、ready、occupancy idle 与相机／ROI 门均通过。此路径仅替换 fixture 范围的 `CreateBlockInfo.GetBlock` 读值，其他读取 delegate；未在真实世界放置方块。 |

受控读值只在 3×2×3 fixture 内返回 air 或指定 stone occupied，不改变原始文档两层数据。它验证了本候选在占用变化时的提交和目标保留，**不能替代真实世界放置／移除的验收**。

## 原生调用完整输入复核

六个运行报告共导出 76 对真实 `DeserializeBlockPalette`／`CombineBlockPaletteToGeometry`。每对记录绑定 fixture、nonce、editor、document 和同一个原生 palette 对象，并在宿主核验完整 base64、长度和 SHA-256。`IntegerBuffer` 导出全部整数值，没有把对象地址当作内容。

canonical 白／灰首次完整投影使用 observer v1：数值、布尔和文字完整，但 observer 将 list 与 tuple 都转为 tuple。因此这两组保留“容器类型被合并”的局限，不能称完整 typed raw。原 raw 没有改写，也没有以重跑结果替换它。

编辑器、受控 missing 和两组历史别名完整投影使用 observer v2，保留 list／tuple 各自类型。observer v2 SHA-256：`be5bad6bdac99c61658500e6922df6059b4fe9b125c32ab23e58c8fd3c728c61`。记录了 Deserialize 的完整实际输入、原 palette 在 Deserialize 后的 Serialize 结果，以及同一 palette 在 Combine 前的完整 Serialize 结果；后两份 wire 逐字节相同。

缺失路径的独立复核由 `analyze_missing_v4.py` 完成：

- 24 对真实调用包含 4 次 `OccupancyShader.bind` 的 spare 单目标 seed，以及 20 次 published 状态提交。seed 单独核对，未丢弃。
- 期望值由**冻结项目**的 `prepare_context_batches`、宿主专用 `candidate_profile()` 以及从冻结 `bridge.py` 提取的原样 `native`／`_native_tree`／`_native_palette` AST 函数生成。宿主创建该对象没有 RPC，也没有向运行中的 session 赋值。
- 实际 native input 与上述期望值全部一致。比较只显式统一 Py2 字节文本与宿主文本，并排序 common／extra 的等价索引顺序；其他容器、数值与状态仍保留。
- 完整 logical palette／chunk 整数缓冲逐格还原，匹配 fixture 的所有单元；五个状态的完整逻辑来源保持一致。四向 wire 自己的 target center 均保留。
- 结果 SHA-256：`fc19c918de86c541acd7d43c10b6451aedce8f14685fdfe057abf82d3769dabc`。

这些代理只拦截原生 palette Deserialize／Combine。自定义水使用的 `CreateModel`／`CreateFreeModel`／uniform 调用由 factory 正常委托，**没有被本次 observer 完整导出或逐调用核验**；本记录不能授予新的自定义水 GPU 资格。

## 流体来源纠正与失败保留

初版 `OCCUPANCY_STATE` 导出的是 `getattr(s.liquid_profile, 'identity', None)`。`ProductLiquidProfile` 没有此属性；字段为 null 不能证明 profile 对象为空。此前据此作出的“默认 profile=None／wet 仅原生路径”推断错误。

所有测试恢复后，执行一次只读核查，既没有调用 `production_profile` 重新创建，也没有赋值：

- `profile_is_none=false`；对象类型为 `modern_projection.projection.liquid_product_profile.ProductLiquidProfile`，与全部测试前保存的是同一对象。
- renderer 为 `modern_projection.projection.liquid_product_render.ProductWorldLiquidRenderer`。
- supported names 和 `liquid_render_ownership.identity` 都是 flowing water／water。
- bridge、`api.GetEngineVersion()` 和 target 版本均为 `3.10.0.420447`。
- `PRODUCT_QUALIFIED=True`，legacy native `PRODUCTION_QUALIFIED=False`；完整 qualification 常量已经导出。

因此 wet 用例应描述为**默认自定义水 profile 下，保持完整逻辑水层的混凝土原生几何负控**。它们不是 native-only 水效果测试，也不新增水验收。

保留的分析失败链没有改写：v1 错以为每 fixture 只有 5 对调用，漏计 spare seed；v2 仍用了 None profile 假设，因此 wet 期望多出了原生水层；v3 已加入真实水归属，但遗漏 native boundary 对私有 profile metadata 的过滤；v4 按冻结生产边界修正后通过。旧脚本、原报告、失败记录和原始截图均仍在 `.runtime/round-20261022/concrete-support-v3-runtime`。

## 剩余问题与生命周期

四向 wire 本体可见、自己 target 保留，但它们承托的混凝土格仍有偏亮现象。此次窄修只处理地面拉杆的 copied support，不能把 wire 亮格算作已解决，不能宣布所有“上方有方块导致色差”的组合已经关闭。含水负控也不构成含水外观验收。

独立 audit 在完整测试前保存 editor、document 完整数据、factory、fields、profiles、workspace 与 player foot；各专项后均恢复。最终检查 actor=0、jobs=false、ready=true、无 `_concrete_v3_*` 残留，保存的 profile 均为原对象，随后显式 retire 独立 audit 标记。

随后执行普通 `instances stop`：通道返回 0，没有 force。精确 PID／创建身份核验游戏和 MCDK 均已退出，assert watcher 也只按本 owner 的精确 PID／身份回收。游戏实际退出码为 **`0xC0000409`**，MCDK 为 0；普通停止命令成功不等于游戏正常退出，此生命周期异常仍然开放，不能据本轮称生命周期通过。

## 证据入口

小包位于 `docs/evidence/concrete-support-r27-v3-v1/`，入口为 `index.json`。17 个文件共 1,455,427 字节，最大单文件 186,144 字节，无需 LFS。5 个 ZIP 均解包往返校验，含精确 manifest、完整原生调用和报告、源／工具／生命周期记录；11 张 PNG 是原图的无缩放、无改色、逐像素校验裁剪。109 张原始截图保留在 runtime，并列出原路径、字节数与 SHA。

建议先查看 `editor-empty.png`／`editor-above.png`，再看 `missing-support-occupied.png`／`missing-lever-occupied.png`／`missing-restored.png`，最后看两张 wet 负控和 `full-gray-alias-above.png`。wire 亮格在 missing 图中直接可见。

本专项没有自行修改共享生产源码、stage、commit 或 push；由 root 根据独立复核结果统一整合。人工关闭数仍为 **0**。

## 主仓整合复核

root 已将上述 v3 原始字节复制到生产 `projection/render_context.py`，SHA 仍为 `966e2f35cba67d7810854fdcde7aed970dc2cea7c35ed1e26c497376ac17a1c0`，没有混入旧版本；5 个行为测试也复制到 `tests/test_concrete_floor_context.py`。当前工作区的 89 项 context／door／chest／occupancy／native actor／kelp／copper chest／concrete 专项均通过，使用实际生产模块，没有注入候选替代。

结构审查实际扫描 3 个相关生产文件，parse 失败和 error 均为 0。保留的四条建议是原有 `build` 分发函数、`material` 方法长度，以及 `prepare_context_batches`／`Fixture.put` 的现有参数数量；本次没有扩大这些公开接口，暂不在窄修中重构。`bridge`、`occupancy`、`world_projection` 三个直接调用方无需改接口。root 另逐字节核验全部 109 张原图、11 张裁剪、5 个 ZIP 的 55 个成员及源文件；无凭据匹配，单件均小于 300,000 字节，并实际打开编辑器空例、missing restored 和灰色别名 above 图。完整中间回执保留在 `.runtime/round-20261022/root-concrete-production-review/`。

公共 OB-10 比较卡另行整合，最终共同提交的冷启资格需重新取得；本专项冷源的范围仍限于上文冻结的 3,709 个文件和一个 overlay。
