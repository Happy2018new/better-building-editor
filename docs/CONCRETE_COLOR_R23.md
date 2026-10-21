# OB-10：混凝土上方邻块色差调查（2026-10-19）

**10-22 接续：** 新的窄 context 副本候选已经取得白色／淡灰色、两种透明度的匹配冷源完整投影对照；它与下文未合入的 lever-owned 不同。[v2 匹配对照](verification/CONCRETE_CONTEXT_R27.md)保留原件；[v3 冻结专项及主仓整合](verification/CONCRETE_SUPPORT_R27_V3.md)补齐历史别名、三路径及湿层负控。红石线承托格仍亮，OB-10 的人工关闭数仍为 0。

OB-10 保持未关闭。本轮已在私有 C 材质和原样主材质的独立冷副本中复现白色混凝土的透明度相关邻块色差；随后，同源对照确认 aux 5 拉杆独立主体候选可消除这一个白色／完整投影样本的亮格，且本体保留。八项关键来源仅 `render_context` 不同，候选与对照的空场、不透明和恢复区域逐像素相同。编辑器、缺失投影、其他状态与上方方块仍未覆盖，本专项新增关闭数为 **0**。

## 原始证据及其限度

人工记录：[review.json](evidence/ordinary-manual-review-20261017/review.json)，用户第 12 条：“这些混凝土上方如果有方块，则这个混凝土的颜色会发生略微变化”。[图 7 原图](evidence/ordinary-manual-review-20261017/07-concrete-neighbor-color.png)中，拉杆和部分铁轨下方的浅色棋盘格呈局部较亮的一格方形。已实际查看原图；截图没有编辑器界面，也没有空／有／恢复序列，无法仅凭此图确认具体渲染路径和根因。

原图 SHA256 为 `839bb8d6176d88b3db0f3f8be2af4eecbcc35e1628f77d06c41d9d8439a4bc9e`；人工记录 SHA256 为 `8ec592a31518b7580c70f34481f532015eb6b699f2f3d377288a2b7f1c61e3ac`。16 色混凝土是保守留查范围，不能写成 16 色均已复现。原证据的全览布局来自登记时生成器，不是截图运行源码的精确绑定。

当前 `debug_blueprints.Fixture.floor()` 使用白色与淡灰色混凝土棋盘，`test.transforms.directions` 又包含拉杆、铁轨、楼梯、木门和紫色潜影盒；这与截图组合相似，仅作为复现入口线索。

## 当前代码中的颜色路径

审查对象为 `modern_projection_biome_blocks.vertex/.fragment`、`terrain.material`、`geometry_palette.py` 和 `render_context.py`。本轮没有查到按混凝土名称主动改色的业务逻辑，主资源包的 `blocks.json` 与 `terrain_texture.json` 也没有 16 个现代混凝土名称的覆盖项；这不替代实际加载资源包核对。

| 环节 | 已确认行为 | 对诊断的影响 |
| --- | --- | --- |
| vertex 的外部光照 | preview 或带 `19487` 标记的世界 actor 使用 `light=vec4(1)`；其他绘制使用 `TILE_LIGHT_COLOR` | 外部乘子固定不等于引擎生成的 `COLOR` 没有明暗差 |
| vertex 的顶点输入 | 初始 `color=COLOR`；非 SEASONS 的编辑器中，中性顶点色下限为 0.55 | 编辑器与世界投影可能保留不同的顶点色范围；尚未取得实际 `COLOR` |
| BLEND / FANCY | `color.a<0.95` 时可再次执行 `color=COLOR` | 必须记录实际材质 variant 与条件，不能只根据前面的 clamp 推断最终输入 |
| fragment 的草顶识别 | `g > r*0.85 && g > b*1.05` 时换为选定群系草色 | 完全中性的 `(k,k,k)` 不会通过；实际输入是否完全中性仍待确认 |
| fragment 的草侧恢复 | 根据采样 RGB 与 17 条颜色射线的误差识别，不检查方块名或 sprite ID；随后再乘 `inColor.rgb` | 可离线检查贴图直接误命中；它与顶点色是不同环节 |
| SEASONS | `inColor.xy`、`.b` 表示色图坐标和权重，`.a` 再参与亮度 | 不能把 SEASONS 的通道当 RGB 直接钳制或据此诊断 AO |
| 投影雾 | 产品世界标记将 fog alpha 设为 0 | 仍需确认目标实际带产品标记；不能套用到未标记绘制 |
| 邻域几何 | 缺失投影从文档源保留周围格烘焙并裁剪中心格 | 源邻域可能影响引擎几何／顶点输入；并非根据目标位置真实方块直接着色，具体机制未证实 |

已通过 mc-search 查阅 `CombineBlockPaletteToGeometry`、`RenderBlockGeometryModel`、`AddActorBlockGeometry`、相机及方块读写 API。资料确认几何来自 BlockPalette，但没有承诺此路径的 AO／顶点颜色语义，也未查得可直接读取该几何顶点 `COLOR` 的接口。`SetAmbientBrightness` 只改变天空亮度，不影响实体和方块照明，不能当作 AO 或方块光照开关。

另有一个需要优先分辨的**几何归属／重复合成候选**：fragment 的邻域中心裁剪使用含容差的闭边界 `[0.9999,2.0001]`。若某个上方目标的原生邻域 mesh 保留下方支撑的顶面，该面可恰好落在此 tile 的 `y=1` 边界，仍通过裁剪；支撑自身 tile 的顶面又在 `y=2` 边界通过，存在共面重复绘制的源码可能性。当前铁路独立主体分支已有“复制支撑会带入不归目标所有的边界面”的注释，但普通拉杆／非独立轨道实际是否生成并画出该面尚未验证，不能将该候选写成根因。

对同一颜色重复作标准 alpha 合成，等效透明度从 `a` 变为 `1-(1-a)^2`；当目标比背景亮时可形成较亮格面。应先核对症状路径是否真的使用邻域 tile、实际 `depthFunc`／深度写入／draw 顺序，再比较透明度 1 与默认透明度及面归属。透明度相关结果只提供定位线索，不能直接以提高不透明度当修复；也不能从两个共面数学位置推断 GPU 一定执行了两次合成。

## 安装包贴图的离线重放

来源为本机 NEMC `3.10.0.420447/data/resource_packs/vanilla`。通过 `blocks.json → textures key → terrain_texture.json → PNG` 精确解析；淡灰色实际映射到 `concrete_silver.png`，未靠文件名猜测。16 张均为 16×16、不透明 RGBA。详细记录含每张纹理的路径、SHA256、最近颜色射线和误差：[离线结果](evidence/concrete-r23/offline-texture-replay.json)。

数学重放保持产品 `light=1`，输入为 PNG RGB / 255，使用 NumPy float64，按当前 shader 的 `shade∈(0.25,0.9)` 及误差 `<0.000324` 原样判断。另在每个 2×2 邻域中，以 `u,v∈{0,0.25,0.5,0.75,1}` 生成局部双线性网格，边界按纹理自身循环；重复样本计入网格次数，不能视为独立纹素。

| 范围 | 原始纹素命中 | 局部双线性样本命中 |
| --- | ---: | ---: |
| 白色混凝土 | 0 / 256 | 0 / 6,400 |
| 淡灰色混凝土 | 0 / 256 | 0 / 6,400 |
| 其余 14 色 | 0 / 3,584 | 0 / 89,600 |
| 全部 16 色 | **0 / 4,096** | **0 / 102,400** |

所有输入中最接近有效射线的是绿色混凝土，误差约 `0.00061525456`，仍高于 `0.000324` 阈值。淡灰色最小有效误差约 `0.00986044719`；白色因 shade 区间不成立而未命中。这缩小了“上述混凝土原始贴图直接被误识别为草侧面”的嫌疑，**没有关闭 GPU、实际图集、mipmap、TexelAA、资源覆盖、实际 light／COLOR 或材质分支的问题**。也没有涵盖连续的所有双线性位置。

重放时的来源快照如下；这些仅绑定此次离线分析，不是任何 MC 进程加载证明，也不保证整轮最终集成后仍相同。

| 来源 | SHA256 |
| --- | --- |
| 产品 vertex | `0eae45cf748d5b70a18d4040a463a8b8e3746b1748ee6464ac4c54dcd65f8809` |
| 产品 fragment | `8c1c7a5f6bc17c9826085da7a0816aa64b910cb9068bdc0b34853f801c4f9077` |
| 产品 terrain.material | `b20079f22bb9272d036f1ca4c1c148ab2a0a9c05ad0cf894b644db93ebd5971b` |
| 原生 blocks.json | `cb3aad2d0d012bfb63a462ec9a5d8af54128c8afc26d74ac6f4ae074c9d50faa` |
| 原生 terrain_texture.json | `9ce3e389999a7aff19968a60fd21dad1811cf63ec3edd6afac0af0df649e212c` |

重放草侧数学不验证完整着色器。已有 `test_biome_shader.py` 的字符串契约通过同样不能代替混凝土实图或关闭 OB-10。可重放的私有脚本保存在本轮 ignored 运行目录 `.runtime/round-20261019/concrete-color/replay_texture_tint.py`，输入只读安装包及 shader，输出 JSON，不连接游戏。

## 下一次最小实机对照

第一步只做白色混凝土的 **3 路径 × 3 阶段，共 9 个状态**：真实世界原生方块、产品编辑器、产品完整投影；每一路依次为 `empty → above → restored`。每路先另取两张 `empty` 估计采样噪声，再进行状态序列；附加截图不另计功能覆盖。白色可复现后，再加淡灰色及石头对照，必要时扩到其余色与铁轨，避免一开始引入 16 色大矩阵。

1. 使用隔离测试存档中的 3×3 同材质台面，中央格为目标，旁格保留固定参照。在中央上方只放一个合法地面拉杆，使目标顶面仍有可见区域；实心上方块会遮住需比较的顶面。当前本地表的候选状态是 `lever_direction=up_north_south, open_bit=False`（aux 5）；表源仍为 3.9，实际 3.10 需通过状态转 aux、放置回读及外观确认，不凭 aux 算术断言合法。
2. 每一路固定目标坐标、相机、缩放、UI 姿态、群系、透明度和环境。世界与完整投影在同位置交替显示，确保另一来源隐藏；记录 actor 隐藏图以识别真实来源。编辑器为正交、世界为透视，跨三路不声称逐像素同机位，只有每路的三阶段保持同机位；比较各自的变化方向及区域。
3. 同时保存文档源与最终输入 BlockPalette、实际 states／aux、资源哈希、部署源码、进程、几何名字、actor 显示来源和相机读回。完整投影先用透明度 1，避免背景透出混入颜色差；再单独检查产品默认透明度。缺失投影在定位后另验，不能由完整路径通过替代。
4. 目标顶面中央无遮挡区、顶面边缘、侧面、邻格各设独立 ROI。排除拉杆／铁轨本体、鼠标、HUD、边缘抗锯齿及位置漂移；报告 RGB／亮度变化、方向、像素分布和恢复差，并与同路重复 empty 的噪声比较。不能用不同格的纹理花纹差冒充邻块因果。
5. 移除上方物后必须回读并确认 `restored` 回到 `empty` 的噪声范围；结束还原世界、文档、相机、时间、设置及 actor 可见性，保存恢复记录。`SetBlockNew` 返回 False 可能表示没有改变，需回读判定，不能直接当失败。不要触碰容器或用户存档内容。

只在主路径稳定复现后，才在独立诊断资源副本中逐一尝试：保留产品标记／裁剪／透明度而输出 `COLOR`；固定非 SEASONS 的 `inColor.rgb=1`；单独关闭草侧恢复；单独检查 editor clamp；最后检查邻域输入、实际 variant 和图集采样。每次只变一项，使用独立几何名并记录 bank／加载来源，避免缓存覆盖混淆。不能把诊断性“全部提亮”直接作为修复。

| 对照结果 | 后续判断 |
| --- | --- |
| 原生世界也有同方向、同区域变化且恢复成立 | 原生邻块关联的候选解释增强；还需判定是否符合产品显示预期，不能自动定名 AO |
| 原生世界稳定，编辑器与投影变化 | 优先缩小 Combine 输入、产品着色、材质与资源路径 |
| 仅编辑器变化 | 检查 UI 材质／顶点钳制／布局合成，保留相机和加载来源证据 |
| 固定 `inColor.rgb` 后差异消失 | 指向顶点色相关输入，但仍不等于已证明 AO |
| 只有关闭草侧恢复才消失 | 检查实际 GPU 采样、资源覆盖与识别条件；离线原图未命中不能否定此实机结果 |
| 差异只在非 1 透明度出现，并随透明度改变 | 优先检查邻域边界共面／重复 draw 及背景混合；仍需实际面归属、深度和顺序证据 |
| 移除后未恢复，或固定参照格也漂移 | 先调查来源／缓存／环境／相机／状态恢复，当前序列不用于关闭问题 |

以上三路径完整方案尚未执行，尚无真实世界、编辑器或缺失投影的颜色通过记录。下文登记的是随后缩小范围执行的首段完整投影对照；OB-10 与 16 色保守留查范围保持有效。

## 首段产品工具：先缩短定位序列

为先检验重复合成候选，已准备 [diagnose_concrete_color_r23.py](../tools/diagnose_concrete_color_r23.py)。第一段只走产品**完整投影**，不放置真实世界方块，也不动 shader；缺失投影、原生世界和编辑器仍由上面的完整方案后续补充。工具准备时保持离线，随后按 root 独占分配执行了下文八对实测。

默认矩阵为白色／淡灰色各 3×3 台面，按透明度 1 和从目标快照 `Session.__init__` 静态读取的产品默认透明度（当前为 0.45）分别执行 `empty → empty_repeat → above → restored`。`empty_repeat` 不重建文档或几何，用于同源采样噪声；`above` 只增加状态表合法的地面拉杆，`restored` 回到空场内容。默认共 16 个 shown／hidden 对，可先只选白色缩到 8 对。

工具使用现有产品 follow 保持 actor 在玩家已加载区域，不创建 raw actor；固定相机、顶面前条／左条和远角参照格的世界投影。统计全程使用第一帧的固定像素 ROI，屏幕投影读回漂移超过 0.05 像素则停止；三个 ROI 均须有足够实体可见／隐藏差分，才保留颜色分析。边界注释图与原图分别保存，ROI 仍需人工看图确认没有拉杆投影、HUD 或动态背景污染。

每阶段保存原始 shown／hidden、投影源／缓存归属、文档、nonce、相机、实体位置、原生提交和 RGB 均值，按 empty 计算变化；空场重复、移除恢复和恒定参照的数据单独保留。没有“色差小于某值即关闭”的自动判据。异常时恢复实体可见性，并尝试还原投影、相机、视觉字段、文档和工作区，所有清理错误写入报告。

仅生成离线计划的命令：

```powershell
python tools/diagnose_concrete_color_r23.py --plan-only --material white_concrete --opacity opaque --opacity default --output .runtime/round-20261019/concrete-color/product-plan-v1.json
```

运行采集必须另外提供 root 调度的受管 `--session`、`--owner` 和 `--project`；工具不启动实例，当前没有占用任何 MC。6 项离线回归覆盖合法增量、默认透明度、ROI 隔离、重复空场同源、隐藏截图失败后的可见性恢复，以及 plan-only 不创建客户端／解析 session。新增客户端片段与植物备用候选共 20 段由真实 Python 2.7.13 编译通过；这些都是离线工具资格，不是渲染或 OB-10 的关闭记录。

## 首次运行：C 材质下的白色最短序列

受管 `alpha-r23-cull-v1` 副本只选白色，按透明度 `1.0 / 0.45` 各跑 `empty → empty_repeat → above → restored`，共八组可见／隐藏对照、十六张 WGC 原始帧。原报告为 `.runtime/round-20261019/concrete-color/cull-white-product-v1.json`。程序逐帧核对 PNG 哈希、WGC 所属 PID／owner／后台捕获合同及三个固定 ROI，并实际查看不透明 above、默认透明度 empty／above 的全帧，以及完整八状态局部拼图。

| 固定顶面 ROI | 像素数 | opacity 1 增加上方物后的 RGB 均值变化 | opacity 0.45 增加上方物后的 RGB 均值变化 |
| --- | ---: | --- | --- |
| 中央格前条 | 1,198 | `(0,0,0)` | `(+35.8205,+33.3589,+42.9382)` |
| 中央格左条 | 1,101 | `(0,0,0)` | `(+35.8819,+33.3806,+42.9946)` |
| 固定远角参照 | 6,148 | `(0,0,0)` | `(0,0,0)` |

不仅均值相同：两种透明度的 `empty_repeat`／`restored`，以及不透明路线 `above` 的三个 ROI，均与各自 empty **逐像素完全相同**。默认透明度 above 的两个目标 ROI 全部像素发生变化，最大单通道差分别为 46 和 45；参照 ROI 仍为零变化。画面中只有中央白色顶面形成较亮格，移除上方物后消失，符合用户报告的外观。

用同机位不透明 empty 作为前景估计，在屏幕 RGB 字节上重放一次相同透明度的叠加，`预测 = 0.45 × opaque_empty + 0.55 × default_empty`：前条／左条平均绝对通道残差分别约 `0.2694 / 0.2686`，最大分别 `1.1 / 1.0`；实际新增亮度约占剩余不透明颜色距离的 `0.4512`。这使重复合成候选更强，但只是屏幕字节数学拟合，未读取 GPU 混合状态，也未验证线性色彩／sRGB 合同，不能据此宣称已观察到实际重复 draw。

**资源限度不能省略：**C 的 `terrain.material` 为 `de2291bd7e9a8db1acf11a9e1fbe76edd21c608830ca5fa6f5c4112c858eaa8f`，向三个原生 mesh 材质加过 culling 状态；它与主仓不同。文档和提交源中确有合法的地面 lever aux 5，但该候选资源的拉杆本体没有显示。因此本次只确立此副本中“上方源单元 → 透明顶面色差 → 移除恢复”的事实，不关闭主材质、拉杆外观、编辑器或任何其他路径。下一步优先在保持主 terrain 的独立副本重复同一最短八对。

精简完整来源及各 ROI 数据：[cull-white-product-20261019.json](evidence/concrete-r23/cull-white-product-20261019.json)；局部八状态拼图：[cull-white-product-sequence-20261019.png](evidence/concrete-r23/cull-white-product-sequence-20261019.png)。原帧、注释帧、相机／文档／缓存来源和原生提交保存在私有运行目录。该段 `completed=true`、`restored=true`、`cleanup_errors=[]`；独立只读恢复检查确认三个标记清除、实体为空、投影／busy／transition 均为 false、factory 恢复原生、玩家位置未变，随后交还 root 并停止访问。

不应全局把中心裁剪改为开边界：目标自己的底面和侧面同样位于 `1 / 2` 边界，会连正确几何一起删除。后续需先确认实际可用的法线输入／面归属，或用经过无支撑本体验证的 lever 独立主体分路进行隔离实验；当前没有把任何诊断改动应用到业务。

## 后续候选准备：先证明输入，保留单变量

主材质复验计划冻结于 `.runtime/round-20261019/concrete-color/main-terrain-plan-v1.json`；计划本身保留 `runtime_started=false`，真正实测另记于下文。独立 firefly 副本的八项混凝土相关来源与登记时主仓逐 SHA-256 相同，包括原样 terrain 与两份 shader；灌木 atlas／flipbook／strip 的候选改动不属于本段混凝土来源。不能由计划替代启动、所有权与采集证据。

已通过 mc-search 核对官方 `vertexFields` 中 `Normal ： 法线` 的定义，3.10 安装包 `netease_block_as_entity_mesh` 确实声明 `Position / Normal / Color / UV0 / UV1`，主材质保留同序列；但原生 block shader 与产品 shader 都没有读取 `NORMAL`，一般实体模型示例不能证明 Combine 方块网格实际填写了有效法线。

因此只准备 `.runtime/round-20261019/concrete-color/normal-input-v2` 的**纯法线颜色资格探针**，没有新增按法线丢面或开边界。它只在私有两份 shader overlay 中输出未经 normalize 的 `NORMAL.xyz * 0.5 + 0.5`，长度异常显示洋红，terrain 保持主仓哈希。六向空气／石头计划先把共用支撑移到旁格，露出目标六面；需实际核对 ±XYZ 的符号、幅值、面向和两路线一致性后，才能讨论 1 边界邻居正法线／2 边界邻居负法线的归属裁剪。

纯输入候选的 16 个独立 GLSL 阶段／变体中 12 个编译通过；4 个 ES100 fragment 因原有宏续行被独立 glslang 拒绝，未改基线具有相同错误，回执全部保留。它没有新增独立编译失败，但不能写成 16 项均通过，更不能替代原生引擎编译和实际 NORMAL 数据验证。

后续 v3 冷测遇到引擎 `Mesh missing vertex field NORMAL required by shader. Skipping draw.` 断言，六面有效采集为 0，NORMAL 资格未取得；没有将该输入用于产品面剔除。v2 门控修正、全局诊断的归因限制以及恢复失败／关闭记录详见 [NORMAL_INPUT_R23.md](NORMAL_INPUT_R23.md)。

另有 `.runtime/round-20261019/concrete-color/lever-owned-v1` 单文件 CPU 候选，只把合法 aux 5 的固定拉杆移到既有独立主体路径。真实 CPU 准备中，白色 above 的混凝土复制格由 58 减为 49，拉杆由十个 context 拷贝变为一个独立主体，empty 仍为 49；六个无关控制（含其他拉杆 aux、梯子和平／坡轨）逐数据不变，候选通过实际 Python 2.7 编译。准备当时原材质无支撑拉杆本体尚未验证；随后前置实测见下文，候选本身的 GPU、主产品和其他状态资格仍须另验。这两类候选只保存在 ignored 运行目录，没有据 CPU 结果修改或热覆盖业务、运行副本和共享生成器。

## 主材质复验：同样的透明度相关亮格

22:27—22:29 在受管 `firefly-r23-c-v1` 冷副本中完成原样主材质白色八对：完整投影，透明度 `1 / 0.45`，各自 `empty → empty_repeat → above → restored`。保存 16 张显示／隐藏原图；[精简证据](evidence/concrete-r23/main-white-product-20261019.json)与[固定裁切的八状态拼图](evidence/concrete-r23/main-white-product-sequence-20261019.png)绑定来源、精确进程和恢复读回。已实际检查 above 原图裁切，主材质下拉杆杆身与基座可见。

| 固定顶面 ROI | 像素数 | 不透明 above 相对 empty 的平均 ΔRGB | 默认透明度 above 相对 empty 的平均 ΔRGB |
| --- | ---: | --- | --- |
| target_front | 1,198 | 0, 0, 0 | +35.8205, +33.3589, +42.9382 |
| target_left | 1,101 | 0, 0, 0 | +35.8819, +33.3806, +42.9946 |
| reference_corner | 6,148 | 0, 0, 0 | 0, 0, 0 |

两种透明度下 `empty_repeat` 与 `restored` 的三个 ROI 都与各自 empty **逐像素相同**；不透明 above 也逐像素相同。默认透明度 above 的两个目标 ROI 全像素变化，最大通道差为 46 / 45，参照 ROI 不变。以上数值与 C 副本一致，缩小了“只由 C culling 材质造成此色差”的嫌疑。

主材质中的屏幕 RGB 重放仍为 `0.45 × opaque_empty + 0.55 × default_empty`，两个目标 ROI 平均绝对通道残差约 0.2694 / 0.2686、最大残差 1.1 / 1.0。它支持重复透明合成候选；实际 GPU blend state、重复 draw、线性／sRGB 和顶点色尚未直接测得，不能把屏幕字节拟合写成 GPU 根因证明。

这次只测白色完整投影；编辑器、缺失投影、原生真实世界、淡灰色与其他混凝土未覆盖。没有以提高透明度作为修复，OB-10 保持未关闭。

## 无支撑拉杆本体前置验证

22:30—22:32 在同一主材质冷副本完成 `air / stone / lever_supported / lever_unsupported × product / raw_loaded × north` 共八对。两个拉杆都通过本地注册表从 `lever_direction=up_north_south, open_bit=False` 解析为 `minecraft:lever, aux 5`；有支撑样本只加一个下方石头，无支撑样本的源只有拉杆本身。没有放置真实世界方块，也没有应用 lever-owned 候选。

两路线石头正控按原阈值通过。已实际检查[完整投影拼图](evidence/concrete-r23/main-lever-body-product-20261019.png)与[raw_loaded 拼图](evidence/concrete-r23/main-lever-body-raw_loaded-20261019.png)：有、无支撑源中的拉杆杆身和基座均可见；无支撑目标不是整块 fallback。[绑定证据](evidence/concrete-r23/main-lever-body-20261019.json)保留样本、原图哈希、两种差分数值与来源。

这个结果只支持**aux 5、北向、这两条路线的本体可生成**，不表示所有拉杆状态、所有视角、编辑器或缺失投影通过。目标 hull 与宽裁切差分含支撑移除、背景和生物变化，不能以非零计数代替外观判断。现在允许在独立冷副本验证该单状态的独立主体候选；尚未证明候选能修复色差。

两项采集均 `completed/restored=true`、`cleanup_errors=[]`。32 张原图的 SHA 与 WGC 回执一致，尺寸／精确进程／路径一致，帧 QPC 均不早于请求。两项之后的独立只读恢复确认四个诊断标记均清除，projection／busy／transition 为 false，entity／preparing 为 null，factory 恢复原生，玩家位置 `(0.5,-60,0.5)` 不变；22:34 交还实例，此后停止访问。

## 独立主体候选：精确样本亮格消失

经 root 授权，从当时新 main 冻结 `concrete-r23-owned-v1`，按候选 manifest 校验 base 与 overlay 后，只向该冷副本应用 aux 5 拉杆的单文件 CPU 改动；没有改主仓业务、材质或 shader。22:42 完成同样白色八对，`completed/restored=true`、`cleanup_errors=[]`。结果见[候选证据](evidence/concrete-r23/owned-white-product-20261019.json)和[八状态拼图](evidence/concrete-r23/owned-white-product-sequence-20261019.png)。已实际检查完整拼图与默认透明度 above 原图裁切，杆身与基座保留，中央亮格消失。

两种透明度下，三个固定 ROI 在 `empty_repeat / above / restored` 中均与 empty **逐像素相同**，包括两个目标 ROI。原图与 WGC 的哈希、尺寸、精确进程和非陈旧帧检查均通过。独立恢复读回确认四个标记清除、实体为空、projection／busy／transition=false、factory 原生、玩家位置不变。

需保留一项历史来源限制：最初主材质 A 来自 firefly，候选冷副本则包含随后主仓启用的三个植物代理，因此除了 `render_context`，其 `geometry_palette` 来源也发生了变化。夹具不含这些植物，empty 区域也相同，但不能把这两组直接称为严格单来源 A/B。随后同源补验见下文，原证据保持原有范围与内容。

正常 stop 首次在十秒内未结束；随后精确进程观察记录游戏 `0xC0000409`、MCDK `0`，均已退出。没有 force；确认两个精确进程已不存在后，第二次 stop 仅完成 registry bookkeeping，状态 stopped。异常游戏退出码如实保留，不称作干净退出，也不据此推断候选是退出原因。测试后的恢复检查与退出观察是两项独立证据，绑定见[实例结束记录](evidence/concrete-r23/owned-lifecycle-20261019.json)；原始 stderr 未另存的首次超时明确标为会话中观察，未伪装成独立原始回执。

候选目前只支持这一个 aux 5／白色／完整投影夹具的效果，未通过编辑器、缺失投影、其他拉杆状态或其他上方方块验证，OB-10 总体保持未关闭。

## 同源 A/B 补验：仅一个关键来源不同

root 授予 `ordinary-final-r23-v1` 独占后，先核对八项来源：该未补丁冷副本与 owned 候选只有 `render_context.py` 不同，分别精确匹配冻结 manifest 的 base `300bf6…` 与 candidate `6bc6d2…`；新植物 `geometry_palette`、注册表、bridge／session、terrain 和两份 shader 均一致。没有修改或热覆盖 ordinary-final 的资源与代码。

再次完成白色八对，结果仍与此前 A 相同；[未补丁组证据](evidence/concrete-r23/strict-a-white-product-20261019.json)与[完整八状态拼图](evidence/concrete-r23/strict-a-white-product-sequence-20261019.png)保存来源和恢复状态。[最终对比证据](evidence/concrete-r23/strict-ab-white-product-20261019.json)及[并排图](evidence/concrete-r23/strict-ab-white-product-20261019.png)进一步独立核对两组固定相机、源夹具、ROI 像素掩码和 24 项跨组比较：

- 所有不透明状态的三个 ROI，在 A／B 之间逐像素相同；
- 默认透明度的 empty、empty_repeat、restored 三个 ROI，在 A／B 之间逐像素相同；
- 默认透明度 above 仅两个目标 ROI 有差，A 比 B 平均亮 `35.8205,33.3589,42.9382` 与 `35.8819,33.3806,42.9946`，参照角仍逐像素相同。

已实际查看并排图：A 的中央亮格与 B 的恢复效果成立，A／B 的杆身和基座均保留。这个同源对照消除了最初 A/B 中新增植物映射的来源混杂；“单变量”仅指已绑定的八项关键来源，两个完整 pack 目录、进程和环境分别冻结，不声称全局逐字节相同。

补验 `completed/restored=true`、`cleanup_errors=[]`；独立只读恢复再次确认四个标记清除、实体为空、projection／busy／transition=false、原生 factory 与原玩家位置。随后交还 root 且停止访问，未自行关闭该共享后续测试实例。候选效果的验证没有扩大 OB-10 的整体关闭范围，也没有把实际 GPU blend state／draw count 写成已观测事实。

## 主线准入决定与后续门槛

本轮不合入 lever-owned。独立审查的 48 个 CPU 场景通过只能证明已列输入的准备行为，不能替代以下运行时门槛：

- 合法 aux 5 可与含水层组成完整格；当前候选以 common material 无条件选择独立主体，会改变未取得湿格资格的场景。需让产品准入明确到完整格／背景层，并验证水主体与拉杆主体的来源、遮挡和恢复。
- 普通编辑器走 `bridge.geometry → prepare_palette`，不经过这份投影 `render_context` 改动；完整投影候选通过不能宣称编辑器修复。编辑器仍需独立确认其现状和实际调用路径。
- 候选从邻域 context 抑制拉杆主体，可能改变邻格红石线的连接烘焙输入。需补红石线邻域对照，不能只看拉杆自身及下方混凝土。
- 缺失投影、过滤选取、其他朝向／通电状态及其他上方方块保留各自验证范围，不由精确样本通过推导。

主生产 `render_context.py` 保持 `300bf6bab79348deeeb457665c1f08904349b694ab14e52be7cbaed488310ab0`，候选只留在 ignored 运行目录。主仓本轮没有为此新增提交；renderer 来源同步仍按实际 host HEAD、WIP 来源哈希和资源绑定记录，不把私有候选纳入主线快照。
