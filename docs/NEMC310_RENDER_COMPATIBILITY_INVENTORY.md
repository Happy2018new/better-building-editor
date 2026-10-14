# NEMC 3.10 方块外观兼容盘点

更新：2026-10-14。待办状态只在 [IMPLEMENTATION_GAPS.md](IMPLEMENTATION_GAPS.md) 维护；本文件是该清单 F01-W05/W06、F03、F04、F05 的范围、技术分类和实机审计附件。本文先给出离线盘点，实机阶段须按实际结果修订“待核查”，不能把候选数量当成需要自行重写的数量。

## 范围与依据

- 开发引擎：NEMC `3.10.0.420447`，MCBE `1.21.130.0`。本次不更新方块表，不更新旋转／镜像转换表；仍遍历仓库 `3.9.0.401155` dump 的全部 **1340 名称、15,858 状态**，其中 19 名称／19 状态属于项目预览方块，原版为 1321 名称／15,839 状态。
- NBT 默认来源：`tools/data/native_block_entity_defaults_nemc_3.9.0.401155.json`，实际捕获 **57 个 NBT 根 ID、155 个方块名称**。用户提供的 59 个 ID 参考另外包含没有原版注册样本的 `NeteaseContainer`、`ModBlock`。这个来源说明旧版本的数据，不是 3.10 所有非默认外观已支持的证明。
- 普通动态外观：遍历 dump 的全部状态，关联 3.10 安装的 vanilla、chemistry、三个 chemistry 版本资源补丁与 vanilla_netease 的方块／地形纹理／flipbook 数据。报告：`tools/data/render_compatibility_nemc_3.10.0.420447.json`，保留全部名称的状态键、aux、NBT 分类、动画候选与未映射项。
- vanilla 中 **48 名称／516 状态**关联动画资源；教育资源新增 `chemical_heat`，合计 **49 名称／517 状态**，分为 **37 个普通方块名称／415 状态**与 **12 个 NBT 方块名称／102 状态**。候选的某些状态可不播放动画，例如熄灭营火或未激活的状态，不将每个状态都算作动态阳性。
- vanilla 的三份原始 JSON 与归档的 3.9 版本逐字节相同，SHA 分别为 `cb3aad2d0d012bfb63a462ec9a5d8af54128c8afc26d74ac6f4ae074c9d50faa`、`9ce3e389999a7aff19968a60fd21dad1811cf63ec3edd6afac0af0df649e212c`、`54fef45e43eabb065a703f829d70320430c746744289775e57af582cb240fd7a`。资源相同不能代替 3.10 渲染行为／时钟观测。
- 3.10 已有干净投影与实际 actor 证据见 [官方支持审计](NEMC310_PROJECTION_SUPPORT_AUDIT.md)。目前只有部分类型有结构性观察；原生演员字段存在、NBT 读回成功、模型生成成功都不等于编辑器和投影像素通过。

用户最新范围：**粒子无需实现**；刷怪笼等内部生物不显示。水保持自定义，世界岩浆可以使用 3.10 官方支持，炼药锅内水／岩浆／药水／染色液体仍需自定义。原生已兼容的其他 NBT 和火等外观优先使用。固定居中植物是设计要求。预览保存快照，不模拟流体传播、红石 tick、燃烧、刷怪、植物生长或玩家交互。

## 3.10 原生能力标记

本文件后续表格中的“原生”只表示 3.10 的官方 Combine／原生 actor 路径能够提供相应的方块本体、状态或 typed NBT 字段；它不自动表示编辑器、完整投影或缺失投影的像素验收已经通过。每个条目必须同时看下面的能力级别和验收路径。

| 标记 | 含义 | 后续动作 |
| --- | --- | --- |
| `NATIVE` | 官方文档覆盖，且 3.10 干净样本已经观察到与该外观相关的字段或本体 | 保留原生 owner，补 editor／full projection／missing projection 像素和动态验收；不重复实现已经存在的本体 |
| `NATIVE-PARTIAL` | 原生只覆盖本体、状态或 typed NBT 的一部分，可见内容、动画或姿态仍缺 | 原生本体与自定义 overlay 分离；只为缺失部分建立适配 |
| `CUSTOM` | 官方明确不支持，或产品约束要求绕过官方路径（当前世界水、炼药锅液体） | 使用版本化项目适配器；保留原始状态和 NBT，禁止与原生几何重复绘制 |
| `UNVERIFIED` | 有资源或默认蓝图，但没有足够的 3.10 结构／像素证据 | 不能宣称支持；先用公开蓝图取得可追溯实机证据 |

### 原生支持矩阵

这是按方块家族归并的显式判定。具体颜色、方向、配对、非默认 NBT 和动态帧仍按 NBT 表及普通动态表逐项验收。

| 方块／家族 | 3.10 原生能力 | 当前边界 |
| --- | --- | --- |
| 告示牌 `standing_sign`、`wall_sign`、悬挂告示牌 `*_hanging_sign` | `NATIVE` | 两面文字、颜色、发光和姿态字段已观察；字体排版、切面和三条产品路径仍待像素验收 |
| 旗帜 `standing_banner`、`wall_banner` | `NATIVE` | 底色、类型、图案顺序字段已观察；旗面飘动和所有图案组合仍待像素验收，不能回退成无图案 actor |
| 潮涌核心 `conduit` | `NATIVE-PARTIAL` | 官方 Combine 明确列入支持，原生字段路径可用；激活核心、框架、旋转、持续动画和粒子之外的可见效果尚未资格化 |
| 花盆 `flower_pot` | `NATIVE` | `flowerPotPlant` 字段已观察；所有植物种类、切面和三条产品路径仍待像素验收 |
| 铜箱各氧化／涂蜡变体 | `NATIVE` | 铜类型、配对、方向和开度字段已观察；箱盖时序和内容不外绘仍待验收 |
| 铜傀儡雕像各氧化／涂蜡变体 | `NATIVE` | 铜类型、涂蜡、姿态和方向字段已观察；所有姿态像素仍待验收 |
| 普通箱子与陷阱箱 | `NATIVE-PARTIAL` | 配对、方向和开度字段已观察；双箱局部消隐、箱盖和三条产品路径仍待验收 |
| 钟 `bell` | `NATIVE` | 挂接／方向字段已观察；摆动时序仍待验收 |
| 火 `fire`、灵魂火 `soul_fire` | `NATIVE-PARTIAL` | 官方支持本体；火焰 flipbook、状态切换和切面需实机验证，烟雾等粒子排除 |
| 世界岩浆 `lava`、`flowing_lava` | `NATIVE-PARTIAL` | 用户允许使用官方路径；液位、流向、比水慢的动画及透明／占用仍需验收，炼药锅岩浆不适用 |
| 世界水 `water`、`flowing_water`、`bubble_column` 及含水本体 | `CUSTOM` | 即使 3.10 文档列出水，项目仍使用自定义半透明／流向／含水路径；不得同时保留官方水几何 |
| 炼药锅 `cauldron` 的水、岩浆、细雪、药水和染色液体 | `CUSTOM` | 原生锅壳和 fill 状态可复用，锅内有限液面、药水颜色和 `CustomColor` 必须由项目 overlay 提供 |
| 下界传送门 `portal` | `NATIVE-PARTIAL` | 普通透明方块和 flipbook 可走原生路径；轴向、深度、动画和三条产品路径仍待验收 |
| 末地传送门 `end_portal` | `CUSTOM` | Combine 文档明确不支持，必须使用专用动态表面；不实现传送行为或周边粒子 |
| 末地折跃门 `end_gateway` | `CUSTOM` | Combine 文档明确不支持，必须使用专用表面／光束几何；不模拟传送、冷却或周边粒子 |
| 物品框／发光物品框、展示架 | `NATIVE-PARTIAL` | 框体本体可由原生提供，但当前 actor 不含展示物品；物品模型、附魔光效、槽位和深度必须用共享 overlay |
| 箱子、潜影盒、末影箱 | `NATIVE-PARTIAL` | 壳体／方向／配对字段优先原生；库存只无损保存，不外绘，开盖和切面仍待验收 |
| 末地门框 `end_portal_frame` | `NATIVE-PARTIAL` | 这是静态框架方块，不是第四种传送门；末影之眼状态按原生状态验收 |
| 末地门／折跃门之外的特殊 NBT（附魔台、信标、活塞／移动块等） | `UNVERIFIED` | 有默认 NBT 或资源不等于原生像素支持；按下方技术分类和实机批次确认 |

矩阵中的 `NATIVE` 不是“无需测试”，而是“不要重复造一个已经存在的原生本体路径”。任何原生路径在 editor、full projection、missing projection 中出现空白、静止、错位、内容丢失或切面错误，都降级为 `NATIVE-PARTIAL` 并进入对应自定义适配待办。

## 技术分类

| 分类 | 适用问题 | 共用方案与职责 | 难度 |
| --- | --- | --- | --- |
| A 原生外观直通 | 3.10 能正确提供本体、纹理和 actor 字段 | 版本化能力选择器决定唯一渲染者；保留原生 actor 和完整 typed NBT；通过实际画面后才停用对应 3.9 代理 | 低至中 |
| B 可见物品补充 | 框、架、营火、讲台等有原生本体但缺内容 | 共用物品解析／模型或 sprite／附魔层；槽位、朝向、缩放为家族参数。内容 owner 与本体 owner 分离，显隐／深度／切面同步 | 高 |
| C 姿态与表面参数 | 头颅、床、箱盖、潜影盒、图案与文字 | 原生优先，缺项由已有静态代理／参数映射补足。纹理来源与状态来源分别版本化；不用库存内容推测外观 | 中至高 |
| D 通用动画纹理 | 灯笼、海晶石、幽匿、植物、命令块、火等 | 共用 atlas/flipbook 帧序、速度、资源来源与动画时钟；只有原生投影缺动画时补材质。常驻动画与状态激活条件分开 | 中 |
| E 自定义世界水 | 液位、流向、含水、半透明、邻域 | 复用现有纯液面几何、面纹理、运输和 owner；版本独立时钟；编辑器／完整／缺失投影共用完整快照上下文 | 最高 |
| F 炼药锅液体 | 锅内液位、岩浆、药水ID颜色、自定义RGB | 锅体原生，独立有限尺寸液面 overlay；共用 D 的纹理动画，不使用整格水几何或群系颜色覆盖药水／染色RGB | 高 |
| G 特殊材质与可见模型动画 | 末地门、光束、书、旗面、导管等 | 按材质／模型家族复用，先验原生；光束是几何而非粒子。需要动画的模型用独立姿态／时钟合同；不给整种 NBT 套同一立方体代理 | 高，部分最高 |
| H 被移动方块快照 | 活塞本体、臂、moving_block 内嵌方块 | 共用嵌套方块／actor 解析与位置偏移，展示捕获状态；不启动真实活塞运动或红石计算 | 高 |
| S 状态决定的静态外观 | 瓶位、书架占位、炉子开关、门开合等 | 保留实际状态，直接取原生对应网格／纹理；无需为每个状态切换单独写循环动画 | 低至中 |
| X 排除项 | 粒子、刷怪笼内生物、未注册自定义类型 | 不做外观补充；NBT 仍无损保存。排除内容不妨碍检查方块本体、材质、可见静态状态 | 无新增实现 |

分类不是模块白名单。运行时不能仅凭 ID 在表里就宣称支持；能力记录需要包含引擎版本、内容类别、显示路径、观察依据和未解决边界。未知字段无损保存，未知外观明确登记，不能静默丢弃。

### 三种传送门

| 方块 | 是否NBT | 技术分类与范围 |
| --- | --- | --- |
| `minecraft:portal`（下界传送门） | 否 | D/G，原生透明flipbook优先，检查两种轴向、动画、深度、切面及占用后恢复 |
| `minecraft:end_portal`（末地传送门） | `EndPortal` | G，官方Combine明确不支持，需要专用动态表面；检查顶面／底面可见性和透明合成 |
| `minecraft:end_gateway`（末地折跃门） | `EndGateway` | G，官方Combine明确不支持，需要专用动态表面；检查多面、深度与快照可决定的光束 |

三种均纳入外观范围，不包含传送行为、传送目的地的世界模拟或周边粒子。`end_portal_frame`是另一个静态框架方块，其末影之眼状态归S，不是第四种传送门表面。

## NBT 逐类评估

下表完整列出 57 个实际捕获根 ID。数量是具体方块名称，不能把床的颜色／方向、箱子的配对或旗帜图案数量重复计作名称。所有“原生待核查”都需要本轮编辑器或投影观察；已有 3.9 局部验收只供复用，不自动升级为 3.10 接受。

| NBT ID | 名称数／方块 | 需要检查或补充的外观 | 分类／难度 | 3.10 与项目当前依据 |
| --- | --- | --- | --- | --- |
| Cauldron | 1，`cauldron` | 空锅／fill_level 1..6；水、岩浆、药水、染色液体与细雪；液面高度、遮挡、纹理与颜色 | F+D，高 | 原生基础 fill 已见；内容未完整支持，必须自定义。旧dump含water/lava/powder_snow，3.10 GameTest也有对应状态；药水与CustomColor还须目标实机确认。`lava_cauldron`是资源定义，不在旧dump，不能凭资源创建方块ID |
| ItemFrame | 1，`frame` | 物品、旋转、地图或其他有特殊内容的物品、附魔光效 | B，高 | 普通／附魔真实物品 NBT 存在，3.10 palette 内容 actor 仍 `{}`；现有 sprite 与绑定候选未完整验收 |
| GlowItemFrame | 1，`glow_frame` | 上述内容及发光本体／内容光照 | B，高 | 同普通框；不能以框体可见代替物品可见 |
| Shelf | 12，`acacia_shelf`、`bamboo_shelf`、`birch_shelf`、`cherry_shelf`、`crimson_shelf`、`dark_oak_shelf`、`jungle_shelf`、`mangrove_shelf`、`oak_shelf`、`pale_oak_shelf`、`spruce_shelf`、`warped_shelf` | 三槽真实物品、附魔、联组角色、通电状态 | B+S，高 | 旧默认样本为空，3.10 内容未验证；应复用框物品方案并参数化槽位 |
| EnchantTable | 1，`enchanting_table` | 书本模型、翻页／常驻动作、打开姿态和朝向 | G，高 | 台体不代表书已显示；模型/动画原生支持待核查。文字粒子排除 |
| Lectern | 1，`lectern` | 无书／有书的模型与页面姿态 | B/C，中高 | 有书非默认样本待采；无需渲染 GUI 全文，也不模拟翻页交互 |
| Beacon | 1，`beacon` | 本体、实际激活状态的光束与染色分段 | G，高 | 光束是可见几何，不属于粒子排除；快照是否提供结构上下文与原生光束待核查 |
| EndPortal | 1，`end_portal` | 特殊动态材质与透明／深度关系 | G，高 | 3.10 Combine文档仍明确不支持，须专用表面；实际跳过／画面另验。没有flipbook不代表静止，安装中有`end_portal.vertex/fragment` |
| EndGateway | 1，`end_gateway` | 门内特殊材质与捕获状态；光束是否有可用快照依据 | G，高 | 3.10 Combine文档明确不支持；不能用传送坐标当可见状态，不模拟传送和冷却计时 |
| MovingBlock | 1，`moving_block` | 内嵌被移动方块／实体外观、偏移与可显示的瞬态快照 | H，高 | 默认或外壳代理不代表嵌套内容已显示；边界须真实样本确定 |
| PistonArm | 2，`piston`、`sticky_piston` | 本体、臂及完整伸出状态；内部移动数据 | H+S，中高 | 实际根 ID 位于活塞本体；不是按辅助臂方块名称推断 |
| Skull | 7，`creeper_head`、`dragon_head`、`piglin_head`、`player_head`、`skeleton_skull`、`wither_skeleton_skull`、`zombie_head` | 方向、玩家外观来源、龙嘴／猪灵耳的可见模型姿态 | C/G，中高 | 3.9 四种头颅局部姿态通过；玩家、龙、猪灵及3.10仍待，不能加载普通生物代替头颅 |
| ShulkerBox | 17，`black_shulker_box`、`blue_shulker_box`、`brown_shulker_box`、`cyan_shulker_box`、`gray_shulker_box`、`green_shulker_box`、`light_blue_shulker_box`、`light_gray_shulker_box`、`lime_shulker_box`、`magenta_shulker_box`、`orange_shulker_box`、`pink_shulker_box`、`purple_shulker_box`、`red_shulker_box`、`undyed_shulker_box`、`white_shulker_box`、`yellow_shulker_box` | 六向、颜色、闭合或可捕获的开盖姿态 | C，中高 | 3.10紫色actor `{}`；旧静态六向代理可复用但未完成新版本资格。箱内库存不外绘 |
| Chest | 10，`chest`、`trapped_chest`、`copper_chest`、`exposed_copper_chest`、`weathered_copper_chest`、`oxidized_copper_chest`及四种铜箱的`waxed_`版本 | 单／双箱、朝向、主副半、箱盖捕获姿态、氧化／涂蜡 | A/C，中 | 3.10已有配对、方向、开度与铜类型字段；原生像素及局部消隐待验。内部库存不外绘 |
| EnderChest | 1，`ender_chest` | 本体、方向、箱盖姿态 | A/C，中 | 原生待核查；紫色周边粒子排除，私有库存不影响外观 |
| Banner | 2，`standing_banner`、`wall_banner` | 底色、类型、完整图案顺序、旗面常驻动作 | A/C/G，中高 | 3.10已见底色／图案字段，旧“actor为空”结论不适用于此版本；飘动尚未验收，先原生后补缺项 |
| Sign | 24，`standing_sign`、`wall_sign`及`acacia`、`bamboo`、`birch`、`cherry`、`crimson`、`darkoak`、`jungle`、`mangrove`、`pale_oak`、`spruce`、`warped`各自的`_standing_sign`与`_wall_sign` | 两面文字、染色、发光、排版、支撑／朝向 | A/C，中 | 3.10真实文字／颜色／发光字段已见；优先原生。旧橡木ID不带oak前缀，darkoak与悬挂款dark_oak不同 |
| HangingSign | 12，`acacia_hanging_sign`、`bamboo_hanging_sign`、`birch_hanging_sign`、`cherry_hanging_sign`、`crimson_hanging_sign`、`dark_oak_hanging_sign`、`jungle_hanging_sign`、`mangrove_hanging_sign`、`oak_hanging_sign`、`pale_oak_hanging_sign`、`spruce_hanging_sign`、`warped_hanging_sign` | 两面文字、悬挂姿态、材质与发光 | A/C，中 | 3.10字段已见，实际editor/full/missing未全部验收 |
| FlowerPot | 1，`flower_pot` | 空盆与实际盆栽植物 | A/C，低中 | 3.10 已见 `flowerPotPlant`，旧默认空盆不覆盖全部植物 |
| DecoratedPot | 1，`decorated_pot` | 四面陶片图案、朝向和当前外观姿态 | A/C，中 | 旧陶片／四向局部验收可复用；3.10 非默认样本待验。不显示盆内隐藏库存 |
| Campfire | 2，普通／灵魂营火 | 火焰／余烬动画、熄灭与点燃、四个烹饪物品的可见模型 | A+D+B，中高 | 动画纹理已关联；烹饪内容非默认 NBT 尚未验。烟雾／火星排除，不运行烹饪计时 |
| Bell | 1，`bell` | 挂接方向、本体与可捕获的摆动姿态 | A/C/G，中 | 3.10 附着／方向字段已见；原生默认静态姿态和动态动作分别观察，不模拟敲钟事件 |
| Conduit | 1，`conduit` | 非激活／激活核心、框架状态、旋转／眼睛等可见外观 | A/G，中高 | 官方宣称支持，但空 actor 不说明激活模型是否完整；粒子与攻击实体排除 |
| Bed | 1，`bed` | 两格完整模型、16颜色、头尾、方向和局部消隐 | A/C/S，中 | 3.9 部分公开用例通过；3.10 原生色／配对待核查；NBT库存不适用 |
| BrewingStand | 1，`brewing_stand` | 三个瓶位的占位外观 | S，低中 | 状态 `brewing_stand_slot_a/b/c_bit` 可表示八种组合；不必按每瓶药水画完整物品，不模拟酿造 |
| ChiseledBookshelf | 1，`chiseled_bookshelf` | 六槽占位纹理与方向 | S，低 | `books_stored` 0..63 ×4方向，共256状态；不是 Shelf 的通用物品模型问题 |
| BrushableBlock | 2，可疑沙／沙砾 | 刷除进度的表面和真实可见的内藏物品姿态 | S/B，中高 | 含物品非默认快照和进度来源待核查；不启动刷除、掉落或粒子 |
| Vault | 1，`vault` | 状态材质、开口姿态、若实际可见则展示物品 | A/S/B/G，中高 | 默认 NBT 不证明活动／不祥／显示物品受支持；先实机分离状态和内容，不模拟开奖 |
| TrialSpawner | 1，`trial_spawner` | 外壳及普通／不祥／活动状态材质 | A/S，中 | 内部生物与粒子排除；不能因此跳过外壳状态核查 |
| CopperGolemStatue | 8，`copper_golem_statue`、`exposed_copper_golem_statue`、`weathered_copper_golem_statue`、`oxidized_copper_golem_statue`及这四种的`waxed_`版本 | 姿态、朝向、铜阶段、涂蜡 | A/C，低中 | 3.10已有姿态／类型字段；不是普通铜傀儡实体捕获功能 |
| SculkSensor | 1，`sculk_sensor` | 感应阶段、触须动画和材质 | A+D/S，中 | 动画纹理候选；不模拟振动传输／红石信号，粒子排除 |
| CalibratedSculkSensor | 1，校频幽匿 | 同上及校频本体／方向 | A+D/S，中 | 动画候选，3.10 动画/状态待核查 |
| SculkCatalyst | 1，`sculk_catalyst` | 普通／bloom 纹理状态 | A+D/S，中 | 状态激活动画来源已见；灵魂粒子排除 |
| SculkShrieker | 1，`sculk_shrieker` | 内部纹理、可召唤／激活状态外观 | A+D/S，中 | 原版有两种内层速度资源；声波粒子、音效及召唤排除 |
| Furnace | 2，未点燃／点燃熔炉 | 对应静态面纹理与方向 | A/S，低 | `lit_furnace` 未关联 flipbook，不能凭“炉子”家族把它算动态纹理；烟／火粒子排除 |
| BlastFurnace | 2，高炉及点燃高炉 | 点燃时正面动画、方向 | A+D/S，低中 | `lit_blast_furnace` 关联10 ticks动画；库存不外绘 |
| Smoker | 2，烟熏炉及点燃款 | 点燃时正面动画、方向 | A+D/S，低中 | `lit_smoker` 关联10 ticks动画；烟粒子排除 |
| CommandBlock | 3，普通／连锁／循环 | 四面动画纹理、方向、conditional状态 | A+D/S，低中 | flipbook 明确存在；命令字符串保存但不执行 |
| Barrel | 1，`barrel` | 方向、开闭快照纹理 | A/S，低 | 不显示隐藏库存、不运行开箱交互 |
| Beehive | 2，蜂箱／蜂巢 | 朝向和 honey_level 对应外观 | A/S，低 | 保存内部蜂与物品NBT但不渲染蜂实体／蜜滴粒子 |
| Crafter | 1，`crafter` | 当前合成／通电静态纹理及方向 | A/S，低 | disabled slots等NBT保存；不模拟合成或物品投出 |
| CreakingHeart | 1，`creaking_heart` | 朝向及实际激活状态纹理 | A/S，低中 | 不能把追踪粒子当纹理动画；不生成嘎枝实体 |
| DaylightDetector | 2，普通／反相 | 两种顶部纹理 | A/S，低 | 输出值不是独立可见NBT内容 |
| Comparator | 2，通电／未通电 | 朝向、模式、火把亮灭 | A/S，低 | 信号/粒子模拟排除，当前状态外观保留 |
| Dispenser | 1，`dispenser` | 面向与本体 | A/S，低 | 库存无损保存，投射/发射不属于预览 |
| Dropper | 1，`dropper` | 面向与本体 | A/S，低 | 隐藏库存不外绘 |
| Hopper | 1，`hopper` | 面向与本体 | A/S，低 | 内部库存不外绘，不模拟传输 |
| Jukebox | 1，`jukebox` | 有／无唱片的实际本体差异 | A/S，低中 | 若NBT不改变可见表面则无内容overlay；不外绘藏在机内的唱片，音乐/音符粒子排除 |
| Music | 1，`noteblock` | 本体、当前对应静态状态 | A/S，低 | 音高不是可见模型；声音与音符粒子排除 |
| SporeBlossom | 1，`spore_blossom` | 固定居中的花模型 | A/S，低 | 孢子全部排除；仅因有NBT不需新增动画实现 |
| Lodestone | 1，`lodestone` | 原生静态本体 | A，低 | 罗盘绑定等数据不是本体可见内容 |
| StructureBlock | 1，`structure_block` | 模式对应本体纹理 | A/S，低 | 游戏操作的结构边界框不自动变成建筑预览内容，不执行结构载入 |
| JigsawBlock | 1，`jigsaw` | 本体与朝向 | A/S，低 | 名称／连接池等NBT不外绘，不执行结构生成 |
| ChemistryTable | 4，`compound_creator`、`element_constructor`、`lab_table`、`material_reducer` | 四种本体和合法状态外观 | A/S，低中 | 实验反应、烟／爆炸等粒子排除；教育资源存在不证明世界已启用相关功能 |
| CraftingTable | 1，`crafting_table` | 原生静态本体 | A，低 | 原生确有该根ID；无需专门NBT外观overlay |
| NetherReactor | 1，`netherreactor` | 历史方块合法状态纹理 | A/S，低 | 不复活历史反应功能；注册存在与可放置性分别登记 |
| MobSpawner | 1，`mob_spawner` | 笼体及状态材质 | A/X，低 | 内部旋转生物、粒子与刷怪排除；保留完整NBT |

参考中的 `NeteaseContainer`、`ModBlock` 不在实际原版捕获清单；无真实注册定义时不新增虚构原版样本。普通实体如盔甲架、画、生物不属于本次方块NBT范围。

## 普通动态方块

下表覆盖已关联动画资源的全部 **37 个普通方块名称**，每个名称全部合法 aux 已在离线报告保留。它们是必须实机核查的候选集合；3.10 已正确显示的条目只需原生路径接入／回归，不应逐个重写 shader。

| 分类 | 方块名称（省略 minecraft:） | 数量 | 外观与技术方案 | 当前实机边界 |
| --- | --- | --- | --- | --- |
| E | `water`、`flowing_water` | 2 | 自定义半透明、源水／流水高度、四向与下落纹理、含水本体、群系近似色 | 3.9 既有部分通过；3.10 时钟／顶侧面／完整三路径仍待，不采用官方水替代 |
| A+D | `lava`、`flowing_lava` | 2 | 官方原生优先，检查顶／侧面、液位和比水慢的动画 | 3.10 静态／流动动画、切面／占用待验。锅内岩浆不归此方案 |
| E+D | `bubble_column` | 1 | 水面归E；可见泡柱纹理若原生缺失则复用D | 纹理动画与 standalone 气泡粒子分开；粒子不实现 |
| A+D | `fire`、`soul_fire` | 2 | 官方原生火模型＋flipbook；保留支持面／点燃状态 | 用户接受官方外观；editor/full/missing 的动画与局部隐藏待观察 |
| A+D | `lantern`、`soul_lantern` | 2 | 8 ticks火光纹理、摆放姿态 | 发光不自动代表动画通过；不新增火星粒子 |
| A+D | `copper_lantern`、`exposed_copper_lantern`、`weathered_copper_lantern`、`oxidized_copper_lantern`及这四种的`waxed_`版本 | 8 | 同灯笼动画器，材质／铜阶段作为参数 | 检查共享图片导致的关联与各变体实际材质，不逐个实现 |
| A+D | `sculk`、`sculk_vein` | 2 | 20 ticks纹理、薄附着面／邻接 | NBT幽匿四种另见上表；脉络多面和含水仍需上下文 |
| A+D | `kelp`、`seagrass` | 2 | 原版纹理帧序与层数，固定居中植物形状 | 海带上下／海草高低状态与水深遮挡待验，不模拟摇摆物理或生长 |
| A+D | `firefly_bush` | 1 | 已有 firefly_bush 纹理flipbook，检查植物平面材质 | 此纹理动画不是独立 firefly 粒子；后者不实现 |
| A+D | `prismarine`、`prismarine_slab`、`prismarine_double_slab`、`prismarine_stairs`、`prismarine_wall` | 5 | 同一海晶石缓慢变色序列，形状／邻接留给原生 | 300 ticks每帧，短双帧截屏可能误判静止；复用原生或统一时间采样，不分别写五种模型 |
| A+D | `sea_lantern` | 1 | 5 ticks光纹；原生优先 | 静态发光与动画分开核查 |
| A+D | `crimson_stem`、`crimson_hyphae`、`warped_stem`、`warped_hyphae` | 4 | 15 ticks侧面动画，轴向正确 | 去皮款未关联该动画，不凭木种名字扩大名单 |
| A+D | `magma` | 1 | 10 ticks动画 | 不模拟伤害、滴岩浆或泡柱生成 |
| A+D/G | `portal` | 1 | 下界门flipbook、透明深度和轴向 | 不传送、不生成周边粒子；末地门是NBT特殊材质，另行处理 |
| A+D/S | `respawn_anchor` | 1 | 顶面动画与充能状态，未充能资源可能固定帧 | 不模拟充能或爆炸；有无动画须按状态判断 |
| A+D | `stonecutter_block` | 1 | 锯片三帧，1 tick步进 | 它是纹理动画，不必重写锯片骨骼 |
| A+D | `chemical_heat` | 1 | 教育资源10 ticks热块动画 | 旧vanilla48表漏项；教育功能加载条件及实际投影待核查 |

### 其他外观变化的边界

| 方块／家族 | 筛选结论 | 对应工作 |
| --- | --- | --- |
| `big_dripleaf` | `big_dripleaf_tilt` 是倾斜姿态状态，未关联flipbook | 验捕获状态下叶头／茎的原生形状，归C/S；不运行玩家站立造成的自动倾倒过程 |
| 门、活板门、栅栏门、拉杆；按钮／压力板 | 开合／按压是状态驱动几何，不能把状态变化全部当常驻动画 | 归S和既有F04，当前快照应正确；不额外承诺交互过渡动画 |
| `piston_arm_collision`、`sticky_piston_arm_collision` | 辅助臂本体不是已捕获NBT根ID，但需与本体和移动格一起显示 | 归H；相关NBT `PistonArm`/`MovingBlock` 已列，避免重复计工时 |
| 红石、铜灯泡、红石灯、蜡烛／蜡烛蛋糕、火把、珊瑚、作物等 | 亮灭、数量、年龄、枯死等是快照状态；其中只有粒子的动态效果排除 | 本体和状态保持归S；不因发光而伪造动画纹理或启动红石／生长逻辑 |
| 火把、蜡烛、熔炉烟雾、营火烟雾、树叶、孢子花、菌丝、滴水石滴液、哭泣黑曜石泪滴、末地烛、音符、幽匿声波等 | 粒子不实现 | 不列为新增渲染阻塞；营火火纹、高炉／烟熏炉面纹等非粒子部分仍验收 |
| 沙、沙砾、粉末、雪、龙蛋等 | 下落是实体／世界模拟，粉尘是粒子 | 不新增物理模拟；保留当前静态方块形状和状态 |

### 未映射名称与完整性限制

只查 vanilla 会留下188个无同名定义名称。加入教育资源及补丁后收敛为24个：19个项目预览方块，以及 `grass_block`、`iron_chain`、`client_request_placeholder_block`、`micro_block`、`unknown`。草／链的旧资源别名需单独确认；后三者需核查引擎占位或网易专属语义。它们没有被自动判为“无动画”或“已支持”。详尽名单和每条状态保留在报告中。

另外，`lava_cauldron`资源定义不在旧dump；不得把它当已经注册的旧方块名称。独立审查还实际解码了1253张原版方块PNG/TGA颜色贴图，83张纵向条带中未关联flipbook的只有导管风层两张和废弃水两张：`conduit_wind_horizontal`、`conduit_wind_vertical`各11帧，属于NBT导管的硬编码风层，已归G；旧`water_flow`/`water_still`是教育flipbook明确标注的deprecated兼容贴图，当前grey贴图另有引用。未发现新增普通方块条带漏项，但引擎私有模型／shader行为仍须实机观察。

安装资源中的粒子、普通实体动画、实验渲染包不自动加入普通方块候选。离线遍历已覆盖整个保留的方块表；未映射项不是被默认为“无动画”或“支持”。

## 实机审计与复用规则

### 炼药锅的共享实现边界

旧registry有21个合法状态：water的aux0..6、lava的aux8..14、powder_snow的aux16..22，各自`fill_level=0..6`。空锅默认NBT只证实`PotionId`/`PotionType`为Short且值为-1；3.10干净样本仅有空锅／满水，不能代替其他内容。

[PocketMine锅NBT](https://github.com/pmmp/PocketMine-MP/blob/stable/src/block/tile/Cauldron.php)与[Nukkit锅NBT](https://github.com/CloudburstMC/Nukkit/blob/master/src/main/java/cn/nukkit/blockentity/BlockEntityCauldron.java)可佐证`CustomColor` Int及药水字段，但仍须目标3.10读回。保留原始有符号值／alpha，不先验截掉类型。药水43..46的新效应颜色不能照搬过时第三方色表；先批量取得目标版本来源。

建议独立纯解码`cauldron_appearance`与版本化内缘／液位／颜色profile，使用锅内有限水平面；复用液体owner／透明度／切面／占用显隐和纹理帧采样。现有世界水网格占满整格、依赖邻域，不能把锅液面伪装为普通水cell。原生锅壳在渲染副本中使用空锅状态，避免自带液体和overlay重叠；文档state/NBT保持。水纹`cauldron_water`为2 ticks，锅岩浆用`still_lava`为16 ticks，细雪独立静态材质；精确内缘及六档高度均未取得可信数值，不猜测。

本轮 MD 完成后继续开发，并实际观察未验证项。先核查原生能力，再决定哪些需要自定义，避免为已被3.10支持的外观重复实现。

### 实机范围核查后的修订

本轮已完成的核查改变了“需要写多少适配器”的判断，但没有把结构证据误报成产品通过：

- 3.10 干净 actor／默认蓝图实际结构字段已覆盖 14 个代表族；告示牌、旗帜、花盆、铜箱、铜傀儡雕像和钟可保留原生本体路径，潮涌核心为原生部分支持。
- 展示框专项已取得 editor、full projection、missing projection 的连续帧；普通物品静止、附魔光效变化和空框阴性均有 ROI 证据，真实原版展示框也读回了附魔 NBT 并观察到时间变化。但编辑器近景中框体本体未稳定出现，框体尺度、资源生命周期、展示架和其他可见物品内容仍未关闭，不能把 `NATIVE-PARTIAL` 升级成生产通过。
- 动态方块专项确认 3.10 后台 WGC 捕获链路可取得可靠图像，但当前大画廊夹具的 editor／projection 两张图字节相同且比例过小，后台没有可靠重绘差异；`pixel_acceptance=false`，不能把 37 个普通候选或 12 个 NBT flipbook 候选当作逐族通过。
- 三种传送门仍未取得可靠像素证据。`portal` 有原生 flipbook 候选；`end_portal`／`end_gateway` 被 Combine 明确排除，必须保留自定义材质／几何任务。失败启动实例已回收，不计作画面阴性。
- 公开测试蓝图已经能构建 57 个 NBT 族和 37+12 个动态候选，但除水／岩浆等少数夹具外，许多条目只有静态 registry gallery；gallery 存在不等于动态或投影验收覆盖。
- 炼药锅仍只有默认 actor／空锅和普通水结构证据，没有六档水／岩浆／细雪、药水 `PotionId`／`PotionType` 或 `CustomColor` 的专用可视夹具。

这一条在本轮被细化：炼药锅代理已经取得 60 行 3.10 原生交互／读回，覆盖水、岩浆、细雪桶，PotionId 0–46、喷溅／滞留药水 43–46 和两组 `CustomColor`，并采集三类液体的 `fill_level=0..6` palette/NBT。它仍没有取得可信锅内像素验收，因此“原生字段／状态已覆盖”不等于“锅内 overlay 已完成”。

因此将初始估时修订为：**还需20–34小时有效墙钟时间**。其中水与炼药锅约7–13小时，框／架／附魔及其他可见内容约5–10小时，末地门／折跃门／信标／导管／移动块等特殊材质与嵌套快照约5–9小时，动态族批量验收和三路径集成约3–6小时。若特殊材质必须建立新渲染 owner、3.10 方块表延迟迁移或后台捕获再次失效，风险上限为 **34–50小时**；本轮剩余时间不能保证全部交付。该估时已经扣除了原生告示牌、旗帜等本体适配，不扣除仍必须完成的像素验收。

展示框本轮原始结果保存在 [`item-product-r15-310-summary.json`](evidence/item-product-r15-310-summary.json)，字段中明确保留 `production_qualification=false`；它是实机证据，不是把诊断结果直接升级为产品能力。

| 批次 | 同屏样本与控制 | 必须留下的结果 |
| --- | --- | --- |
| R1 高难度原生边界 | 附魔台／讲台、末地门／折跃门／信标／导管、活动宝库、活塞／移动块、龙／猪灵头 | 编辑器或投影的本体、内容、材质、姿态和动态分别观察；缺失／静止／错误必须逐项登记 |
| R2 可见内容 | 框／发光框／展示架普通、附魔、空槽；营火食物；讲台书；刷除进度物品 | 空内容阴性、正常内容阳性、附魔连续帧；真实NBT与实际物品尺寸／位置／遮挡对应 |
| R3 官方覆盖的NBT | 文字两面、旗帜图案、花盆植物、陶片、箱子／潜影盒／床／铜雕像、书架／瓶位 | 原生显示、项目显示分别记录；非默认样本不能用默认空样本代替 |
| R4 普通动画全族 | 上表37名称，按家族分页；NBT的12个动画名称一起核查 | 连续时相与固定视角，灭／亮等状态控制；慢速海晶石须覆盖有效帧变化，不能只录一两秒 |
| R5 最终产品三路径 | 合入后的同一公开蓝图：editor、full、missing | 切面、透明度、邻域、真实方块局部占用、隐藏后恢复、内容替换与资源释放 |

首次范围核查可以用 editor 或投影之一，但最终交付须覆盖三个产品路径。内置蓝图只验编辑器，投影另行运行。所有画面检查关联公开测试蓝图或来源明确的同内容夹具；源码／资源／NBT／PNG／时间／相机与版本绑定。截图空白、被菜单遮挡、来源错配、采样不足均不算通过，须显式报告。

普通材质族按资源关联扩展测试覆盖；个体不需要重复写实现。共用修复须包含静态阴性、动画阳性、独立未知输入与移除恢复，防止错误外推。水时钟／纹理方向须使用3.10的新观测，旧3.9递减时钟证据只保留为历史。

最多10个活动子代理、最多5个活动MC；测试器不主动前台化、不使用桌面输入。用户手动切到前台时继续。按身份回收所属实例，捕获失败不能静默吞掉。本轮截止已延长为2026-10-14 08:00（Asia/Shanghai），先保存并回收，再休眠。

## 按难度的开发顺序

下面是风险优先的并行安排；每个适配器开发前先有同族原生观测。基础能力选择器／测试入口是这些任务的必要前置，不需要为此重构整个仓库。

| 顺序 | 工作组 | 高风险原因／复用收益 |
| --- | --- | --- |
| 1 | E世界水；G末地材质／光束／书／导管；H移动块快照 | 透明深度、动画时钟、私有材质或嵌套内容影响最大；尽早实机决定可复用的原生范围 |
| 2 | B展示框／展示架／附魔及营火／讲台内容；F炼药锅 | 通用物品与小液面overlay建成后复用多个NBT族，避免逐个试接口 |
| 3 | C头颅／箱盖／潜影盒／旗帜／文字／陶片缺项 | 3.10原生已覆盖的部分直接接受并回归，剩余状态参数化处理 |
| 4 | D所有动态纹理；A/S原生本体与状态 | 通用时钟／帧序／材质检测覆盖整族；官方岩浆、火等只补实际缺项 |
| 5 | 三路径集成、含雪、连缀／占用、性能与冷启动 | 专项可并行补测，最终同一提交验收；不以局部或旧版本记录关闭总体资格 |

## 初次剩余工期评估

此评估在完成离线MD之后、补充3.10实机范围核查之前作出；最终需要按本轮实机结果再次更新。单位是实际开发墙钟小时，包含代码、自动验收与集成，按最多10代理／5游戏实例估计，不是十份代理工时简单相加或除十。

| 工作 | 专项预计耗时 | 主要条件 |
| --- | --- | --- |
| 本轮原生能力批量观察、修订表格和运行目标分流 | 3–5小时 | 多族同屏；不逐个重启。先区分原生缺失与旧3.9代理干扰 |
| 世界水完成3.10资格；炼药锅液体 | 6–12小时 | 可并行一部分；水的方向／透明度／时钟及锅颜色数据是关键不确定项 |
| 框／架／附魔及其他可见物品内容 | 6–12小时 | 复用已有候选；展示架真实槽位与特殊物品模型需先观察 |
| 非原生覆盖的特殊NBT模型／材质 | 4–8小时 | 若书、门材质、导管、光束等原生不支持，则会上升；不会为全部57类各写适配器 |
| 动画纹理族、官方岩浆／火和静态NBT | 2–5小时 | 批量观测后只补缺项；海晶石慢动画需要可靠取样 |
| 既有含雪／多格连缀收尾与统一集成验收 | 4–7小时 | 与上述并行，但最终产品资格及冷启动有串行阶段 |

综合初估：**还需18–30小时有效墙钟时间**。若3.10原生覆盖多数特殊模型且共用物品路径顺利，接近下限；若展示架／特殊物品、末地材质或移动块须建立新渲染路径，风险范围约 **30–45小时**。相比之前的估计，新增了全面外观核查与此前未覆盖的可见内容，同时扣除了粒子和自定义世界岩浆实现；两者不能只凭名称数互相抵消。

范围包含已授权P0、多格／连缀、NBT／动态外观及其自动验收，不包含全部P1/P2、RenderDragon、完整安卓认证、方块表／旋转镜像版本迁移。今晚08:00前应争取完成原生范围核查和高风险专项增量，不能仅凭剩余时间保证全部交付。

## 重跑盘点

```powershell
python tools/audit_render_compatibility.py --check
python tools/audit_native_nbt_inventory.py --check
```

升级资源时先归档与核对新来源，不把新资源覆盖旧证据目录。当前离线盘点捕获方式：

```powershell
python tools/audit_render_compatibility.py --capture --vanilla-pack D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data/resource_packs/vanilla
```

`json5`只在宿主审计工具解析原版含注释JSON时使用，不引入游戏Python2运行时。完整名称与字段来源附录由NBT离线审计报告保留；本表的分类和未知边界不能被生成器自动改成成功。
