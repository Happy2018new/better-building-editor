# 铁轨投影衔接：2026-10-19 开发记录

关联用户人工反馈为 **OB-04b**；原图见 [补充图 9](evidence/ordinary-manual-review-20261017/09-rail-projection-connection.png)。**OB-04a 的铁轨像素异常仍独立留查**，不能用连接修复代替其验收。

当前状态：**root 已接受窄准入并默认启用当前注册表中 28 个已知坡轨的 owned-body 分支**，针对中心格裁剪造成的坡轨高端缺口。最终收紧实现已完成 7 条有效运行时短测，覆盖四类轨道／四个坡向代表、XYZ 分块角、隔离／生产两种模型名以及缺失隐藏／重建／恢复；每条均 `completed/restored=True`。这只关闭本项实现与运行时阻塞，不改变此前人工验收计数，也不宣布全部铁轨的所有状态／组合通过。OB-04a 继续留查。

## 当前定位与改动范围

编辑器的普通有界调色板路径直接使用原生几何；完整投影和缺失投影则由 `ContextBatchBuilder` 把每个目标及 26 格邻居放进独立的 4 格间距 tile，再由 `modern_projection_biome_blocks.fragment` 仅保留中心格 XYZ phase `[1,2]`。超出所属格高度的表面会在这里被截断，即使调色板中的状态和支撑均完整。第二组同相机三路对照支持：用户同类的激活铁轨高端缺口与中心格裁剪有关；完整原生表面由 owned-body 路线保留。实际表面高度尚未导出为顶点数字，不把猜测的 `1/16` 高度当作已测量值。

候选将四种原生铁轨中 `rail_direction=2,3,4,5` 的 **28 个合法 name/aux** 作为目标格自身的独立主体，复用已有讲台／桌体的独立几何分支：

- `rail_render_profile.py` 只枚举当前方块表中的坡轨，保留通电位和原生状态；不改文档、世界身份、邻域连接算法或旋转／镜像规则。
- `render_context.py` 把这些坡轨从邻域复制体剔除，并且仅在该格本身是可见目标时输出一次主体。无 secondary 的坡轨目标不再复制自己的 27 邻域；有 secondary 时继续为这一层保留邻域。其他目标仍可从完整快照读取坡轨格的 secondary 及支撑。沿用现有缺失投影双缓冲、透明度、深度、所属分块和销毁流程。
- 平轨、弯轨及其他方块继续原有分支。没有放宽全体方块的中心格裁剪范围。

`render_context.py` 在本轮之前已包含讲台等未提交修改。本轮增加坡轨判定及现有两个通用独立主体 helper 中的条件，并用 `_requires_context_tile` 同步收紧小型参考、增量和分块三条规划路径；保留原有修改。没有修改 `geometry_palette.py`、`scene.py`、`world_projection.py`、`block_neighbors.py` 或 `rail_neighbor_data.py`。

当前来源：`NEMC 3.9.0.401155` 方块表，SHA-256 `6b2d9e961e934a745f5ab30d697cf22fb463fd3792d371a6dd42cb4342062f01`。枚举条件基于当前注册表的语义状态，未依赖 aux 的数值算术。

## 已完成验证

2026-10-19 运行结果：

| 验证 | 结果 | 实际覆盖 |
| --- | --- | --- |
| `tests/test_rail_render_profile.py` | 10 项通过 | 28 个坡轨 aux、四方向、所有已有通电位、XYZ 的 16 格分块角、只发出一个主体、已占据坡轨不从邻域残留、视图隐藏与缺失隐藏分别处理、secondary 水层保留、小型与增量 context 输出一致、旧路由负对照、关闭开关可回退；三条规划器分别检查无 secondary 坡轨不复制支撑平面、含水保留完整邻域、普通邻轨仍有支撑来源 |
| `tests/test_render_context.py` | 14 项通过 | 原有调色板上下文回归 |
| `tests/test_occupancy_neighbor_context.py` | 8 项通过 | 原有完整／缺失邻域输入边界回归 |
| 诊断夹具离线执行及片段编译 | 112 组通过 | 28 个原生坡轨状态 × 两个中心位置 × 完整／缺失两种模式；均为 6 格夹具，状态及初始隐藏集合一致；包含 `unique-models` 的六种路由参数均可编译，未连接或启动游戏 |
| 新模块结构审查 | 1 文件，0 项发现 | 纯注册表依赖，没有 SDK、端侧初始化或事件注册 |
| `render_context.py` 结构审查 | 1 文件，1 项既有签名参数过多警告 | 本轮未改接口签名；依赖链复核无跨端导入或循环依赖 |

以上 32 项离线通过仅证明路由／状态／生命周期输入契约，不等价于 GPU 像素或原生世界对照通过。新增的所有权回归先在收紧前产生 6 个子用例失败，再由三条路径的一致修改转为通过。

第一组运行时记录 `.runtime/round-20261019/rail-full-v1.json` 已完整生成并恢复；root 与铁路专项代理均阅读三张原图。窗口 1994×1105，`golden_rail`、坡向 2、通电、相机偏移 `(4,2.8,-5)`。原生调用证明确实切换了输入：旧路由 context 有 26 格、其中坡轨 6 份；候选 context 20 格加独立坡轨 1 份；裸原生参考 6 格。三个版本都能生成对应几何，排除了“诊断没有切换输入”；但同名 native GPU 资源是否复用仍需 `--unique-models` 独立对照，不能只凭提交记录排除。

固定物体 ROI `(790,525,1165,800)` 中旧／候选仅 147 个像素的最大通道差大于 16，RGB 平均绝对差约 `(0.068,0.050,0.074)`；变化集中在少量轨面采样边缘，未出现用户图 9 的大间隙。窗口其他区域的 HUD 时钟和生物变化不参与此数字。此对照没有形成产品修复证据，不能仅凭成功提交及离线通过启用候选。

第二组 `.runtime/round-20261019/rail-activator-close-v2.json` 使用原生贴图匹配后的 `activator_rail`、坡向 2、未通电、相机偏移 `(0,1.8,-3.2)`，已完成并恢复。三张图在高端接头给出了明确区别：旧路由缺一段，候选与裸原生保持连续。接头静态 ROI `(865,465,935,590)`，共 8,750 像素，最大通道差大于 16 的像素数分别为旧／候选 **517**、旧／裸原生 **526**、候选／裸原生 **7**；后者平均绝对 RGB 差约 `(0.0231,0.0197,0.0383)`。此 ROI 排除 HUD 和远处会动的马，不用全屏差异计数宣称几何修复。

第二组捕获早于“无 secondary 坡轨目标跳过自身邻域 tile”的后续收紧，不能直接当作最终候选源码的像素验收。收紧消除的是输入中不属于该目标的支撑边界平面及重复邻域；未声称运行时已经观察到另一处支撑残影。

离线可重放命令如下，输入图像 SHA-256 与同一相机首先通过检查，输出原始差值及 nearest 放大三列，不自动判定问题关闭：

```text
python tools/analyze_rail_context_r23.py .runtime/round-20261019/rail-activator-close-v2.json .runtime/round-20261019/rail-activator-close-v2-joint.json --roi 865 465 935 590
```

## 最终实现的 7 条有效运行时短测

最终短测绑定独立 `ordinary-r23-v2` 实例，在游戏 `3.10.0.420447`／运行时 `1.21.130.0` 中串行执行；注册表仍是上文记录的 `NEMC 3.9.0.401155` 来源。五条原计划完成后，按 root 要求追加生产模型命名的两条复核；没有自行启动／停止游戏，没有写世界或持久化文档。完整原始记录在 `.runtime/round-20261019/`，可长期保留的小型审阅材料及真实输入摘要位于 [专项证据目录](evidence/rail-slope-ownership-r23/shortset-summary.json)，合计约 510 KiB。

| 记录名／条件 | 模型命名 | 结果与静态接头 ROI |
| --- | --- | --- |
| `rail-activator-unique-v3`，未通电、坡向 2 | 每次构建独立名 | 旧路由高端断口，候选／裸原生连续；ROI `(865,475,920,590)`，旧／候选 >16 像素 **533**，旧／裸 **526**，候选／裸 **23** |
| `rail-activator-missing-v3`，同姿态缺失模式 | 每次构建独立名 | 全空显示 → 动态占据坡轨 → 保持占据重新生成 → 恢复显示，四阶段实图及观测状态一致；两端平轨与支撑保留 |
| `rail-detector-reversed-v3`，通电、坡向 3 | 每次构建独立名 | 反方向高端接续恢复；ROI `(1070,475,1135,590)`，旧／候选 **543**，旧／裸 **529**，候选／裸 **37** |
| `rail-golden-corner-v3`，通电、坡向 4，中心 `(15,15,15)` | 每次构建独立名 | 另一水平轴及分块角接续恢复；ROI `(1070,475,1135,590)`，旧／候选 **697**，旧／裸 **688**，候选／裸 **34** |
| `rail-other-axis-v3`，普通铁轨、坡向 5 | 每次构建独立名 | 另一轴反向接续恢复；ROI `(865,475,920,590)`，旧／候选 **356**，旧／裸 **351**，候选／裸 **28** |
| `rail-activator-production-v3`，未通电、坡向 2 | 生产双缓冲名称 | 与独立名首条相同的接头结果；旧／候选 **533**，旧／裸 **526**，候选／裸 **23** |
| `rail-activator-production-missing-v3`，同姿态缺失模式 | 生产双缓冲名称 | 四阶段显示与隐藏恢复均正常，与独立名缺失模式结果一致 |

以上 7 条逐条检查完成与恢复标记、真实 native 调色板输入、源文档／投影快照保持、拍摄期间相机／玩家／模型稳定。每组三路相机完全相同，图像 SHA-256 通过重放校验。所有全图和接头放大图均已实际查看；ROI 由图中静态接头人工选择，排除 HUD 和移动生物。首条实测发现原 ROI 边缘会纳入移动猪，因而收窄右边界至 920，未沿用受污染的 ROI。

候选与裸原生之间剩余的 23–37 个阈值像素集中在采样边缘，ROI 平均绝对 RGB 差的各通道均低于 0.21；这里记录的是测量和实图判断，不把阈值数字自动映射成“所有像素完全一致”。例如 [生产命名激活铁轨接头三列图](evidence/rail-slope-ownership-r23/rail-activator-production-v3-joint.png) 和 [分块角动力铁轨接头三列图](evidence/rail-slope-ownership-r23/rail-golden-corner-v3-joint.png) 直接保留旧／候选／裸原生的区别。

两条缺失模式另在坡面中部静态 ROI `(935,570,1060,660)` 比较四阶段：显示／恢复显示、动态隐藏／初始隐藏均为逐像素 RGB **0 差**；显示／动态隐藏有 **6,270** 个最大通道差大于 16 的像素。坡轨占据观测依次为 `1→2→2→1`，两端邻轨始终为 `1`，动态隐藏和恢复各完成一次提交。该结果同时出现在隔离名和生产名路径，不依赖为每次重建更换名称。见 [生产缺失模式四阶段裁图](evidence/rail-slope-ownership-r23/production-missing-four-phases.png)。

最后只读恢复确认结果为 `candidate_enabled=False`、`projection_active=False`、`preparing=False`、`saved_probes=[]`，随后释放运行时给其他专项。此处的 `False` 是诊断结束时恢复原默认值；root 后来接受资格后才将生产默认值改为 `True`。

### 实测与启用后的源码指纹

七条实测使用同一份最终实现，`fixed` 路由在运行时内存中打开 gate；`legacy` 路由在内存中关闭 gate，`raw_native` 使用同组有界原生输入。root 启用生产默认值后，只改变 gate 值和资格说明注释；把 gate 常量规范化为相同值后，新旧源码的 Python AST 完全相同，没有另改几何规划逻辑。

| 文件 | 实测时 SHA-256 | root 启用后 SHA-256 |
| --- | --- | --- |
| `rail_render_profile.py` | `3b4fe2c5a59f51c895e453981945bd0a8f8707b450940c667c12aae8f417344e` | `2b644ba748025e3ca5e5218767e24d9222df835e8b0119cd3b10da944f3088da` |
| `render_context.py` | `300bf6bab79348deeeb457665c1f08904349b694ab14e52be7cbaed488310ab0` | 相同 |

`render_layout.py`、顶点／片元 shader 的散列亦记录在 [完整短测摘要](evidence/rail-slope-ownership-r23/shortset-summary.json)；7 条捕获记录中的五个宿主源码散列完全相同。root 负责生产启用后的受影响回归与共享资格文档整合，本专项没有再次修改业务源码。

### 窄准入判断与仍保留的边界

当前证据足以默认启用已知 28 个坡轨的独立主体分支：定位有旧路由负对照，四类轨道／四个坡向代表可见修复，分块角与缺失生命周期可用，生产名称复核没有额外依赖。离线枚举确认 28 个状态及全部已有通电位保留原生状态；运行时覆盖代表例，不称为 28 状态逐项 GPU 验收。

仍保留以下边界，不计为本次人工验收关闭项：

- **OB-04a 铁轨像素异常**独立留查；平轨、弯轨没有切换本轮分支。
- secondary 含水组合已完成纯规划回归，尚无对应运行时图像验收。
- 已有缺失短测占据的是坡轨自身；上／下邻轨分别占据、所有邻接组合、真实世界原生摆放对照仍未逐项完成。
- 最大尺寸文档的 native 内存／显存峰值没有实测；本记录只给出有界分块的静态规划上限。
- 方块表来源仍为 3.9，不能把此修复扩大表述为完整 3.10 适配。

## 最小运行时诊断

工具 `tools/diagnose_rail_context_r23.py` 创建临时的三格轨道坡面及支撑，在同一位置和相机下依次捕获：

1. `legacy`：临时关闭坡轨独立体，重现本轮以前的中心格裁剪路线。
2. `fixed`：本轮候选原样走生产投影流程。
3. `raw_native`：同一组目标单元直接生成有界原生调色板，取消中心格裁剪，用于区别裁剪与状态／本体问题。这个对照不等于真实世界原生摆放验收。

每次捕获保留 shown／actor-hidden 两张图及差分信号，检查编辑器文档、投影源快照、相机、玩家位置和模型来源在拍摄前后保持一致。只操作临时客户端投影／相机／内存文档，不写真实世界或持久化建筑。模块替换、观察器、编辑器和相机在 finally 中恢复。应使用拥有该游戏的 session/owner 路由；禁止直接使用未绑定默认端口。

已执行的精简验证集如下，可供后续复现。每行均为工具参数，必须通过绑定实际游戏 session/owner 的路由执行：

```text
diagnose_rail_context_r23.py <activator-unique.json> --name minecraft:activator_rail --unpowered --shape 2 --offset 0 1.8 -3.2 --unique-models --native-resolution --refresh-render-context
diagnose_rail_context_r23.py <activator-missing.json> --name minecraft:activator_rail --unpowered --shape 2 --offset 0 1.8 -3.2 --missing --variant fixed --exercise-occupancy --unique-models --native-resolution --refresh-render-context
diagnose_rail_context_r23.py <detector-reversed.json> --name minecraft:detector_rail --shape 3 --offset 0 1.8 -3.2 --unique-models --native-resolution --refresh-render-context
diagnose_rail_context_r23.py <golden-corner.json> --name minecraft:golden_rail --shape 4 --cell 15 15 15 --offset 3.2 1.8 0 --unique-models --native-resolution --refresh-render-context
diagnose_rail_context_r23.py <rail-other-axis.json> --name minecraft:rail --shape 5 --offset 3.2 1.8 0 --unique-models --native-resolution --refresh-render-context
```

`--native-resolution` 使用已有 `SignCheck` 和 `capture_native_window.py`，不需要前台窗口输入。第一条在第二组的已复现姿态隔离同名资源缓存；第二条覆盖全空显示 → 动态占据坡轨 → 保持占据重新生成 → 恢复显示；其余三条覆盖反方向、另一水平轴、XYZ 的 16 格分块角及另外三种轨道。每条均保存提交状态和真实 native 输入，不能仅以截图存在宣布通过。可再用 `--occupied upper` 检查坡轨在上端邻轨隐藏后是否保留。`--cell` 最大 60，以保证裸原生参考输入仍低于 64。新源码必须实际同步到独立实例，不能只看主仓库文件名推断运行版本。

`--unique-models` 在每次异步构建开始前，为该次 shader buffer 使用带 `projection_serial` 的新名称；其余输入与变换不变，用于区别同名几何资源复用。默认不加该参数，先保留实际生产名称策略；有差异时再成对运行，而非默默改变所有基线。

本轮已完成本项实现准入要求的同视角三路对照、反方向及另一水平轴、四轨代表例、缺失初始／动态隐藏和恢复。人工复验及未覆盖组合仍按上述边界保留，像素异常 OB-04a 继续独立核验。

## 所属权与内存边界

候选只新增 28 项的材料集合，不复制第二份源文档、目标集合或世界数据。坡轨主体与同分块已有的讲台等独立主体共用 overlay 调色板；每个含坡轨的 16³ 逻辑分块最多因此增加一项 overlay draw，而非每格创建一个模型。以 64×128×64 文档为例，静态分块上限为 128 个；这只是规划器的 draw 数上限，不是 native 内存或显存实测。

无 secondary 的坡轨目标现在不生成自己的邻域引用，也不会为了这一目标把支撑块的共面边界送入中心裁剪。含水等 secondary 的目标仍保留邻域，以让该层的原生几何获得完整上下文。旁边的普通方块目标照常查询同一只读源快照，缺失目标集合不修改源快照或邻域来源；动态隐藏时主体随目标集合消失，恢复时重新发出。离线回归确认这三个契约，最终短测也覆盖了代表性发布／隐藏／恢复及生产名称复用；长期反复重建和最大尺寸的显存峰值没有实测。

## 与 renderer 拆库直接相关的最小边界

此次问题暴露的是“几何所属单元”与“为原生补全形状的邻域单元”两个契约的区别。renderer 的首版接口应明确这两个概念，不让几何裁剪隐式决定所属权。

推荐先抽一个小型纯规划接口：`plan_draws(snapshot, targets, visibility, profiles)`。输入只含规范化的前／后景、已解码可见内容、只读邻域和目标集合；返回带 `origin`、`kind`、native palette、`owners` 的有限 draw 计划，`kind` 至少区分 `neighbor_context` 和 `owned_body`。宿主继续负责世界读取、真实占据观察、编辑事务、SDK 合并、客户端实体和销毁生命周期。不能把 MC 世界读入藏进纯规划器。

| 现有来源 | 目标归属／先后 | 本次迁移约束 |
| --- | --- | --- |
| `rail_render_profile.py` | renderer 的独立几何拥有规则 | 首批可迁移小模块；通过 states 提供的标准 name/state 查合法坡轨，不另维护一份状态真值表 |
| `render_layout.py`、两段 biome block shader 的解码／中心裁剪 | renderer | schema、中心偏移、连续坐标和裁剪上限必须一起版本化；保留越界几何回归 |
| `render_context.py` 的纯 palette／owned-body 规划 | renderer 的后续适配层 | 先隔离宿主 Document／存储访问，保留 snapshot/targets/visibility 的区别；禁止直接整文件搬家冒充独立库 |
| `rail_neighbor_data.py`、注册表、rail state 变换 | states／状态规则来源 | 此次无需复制进 renderer；原生放置读回证据不证明几何表面高度或 GPU 裁剪正确 |
| `WorldProjection`、`ProjectionOccupancy`、`OccupancyShader` | 宿主与 renderer 的明确适配边界 | 先留宿主，不能在第一批迁移同时重写发布／退役／缺失检测；独立主体继续跟随同一个目标集合 |
| 本次 28 状态夹具与三路诊断结果 | renderer 小型回归证据 | 记录游戏版本、方块表散列、规则/着色器 schema 和源文件散列，不复制整套游戏或巨型运行目录 |

这份建议仅界定铁路相关的首个可复用切片，不表示两个库已经接入生产。
