# NEMC 3.10 方块外观兼容盘点

**23:45模型切换暂停：** 用户要求保存上下文并停止全部会话／MC，恢复以[交接顶部](CONVERSATION_HANDOFF.md)为准。R17资源资格验证补齐owned注册条目／资源契约；水独立分帧候选尚未接入口，书／物品仍未资格化。1,338个block物品不是1,338个需自定义模型的证明，item aux不能直接当block aux；catalog ID级unsupported包含失败aux，与同ID有效aux可能同时存在，后续范围必须按有效变体评估。

**2026-10-14 23:30最新修订：** 第十六轮检查点已经保存，第十七轮连续开发至2026-10-15 07:00后休眠；最新10代理／最多5游戏。刷怪笼标识、旗帜editor有限静态家族和末地门／折跃门表面默认资格已启用，锅保持既有资格。最终2,817项离线回归和四包工作区／staged字节验证通过；生产水／物品／书仍False。物品左右暴露邻居反向已修复，放大侧边仍分段；书的editor讲台缺失、亮度／高度／方向仍待原生世界参照。普通cyan_concrete同camera实块／投影已复现投影细线，原因未明。水同实例远近对照证实可见性差异，side-UV／冷构建预算及最终门仍开。下方22:40与第十五轮记录仅作历史依据；当前待办以[统一清单](IMPLEMENTATION_GAPS.md)顶部为准，实例／source约束见[交接](CONVERSATION_HANDOFF.md)。

**17:15收尾修订：** 最新状态见[统一待办](IMPLEMENTATION_GAPS.md)。自定义owner排除重复原生水后，最终36张固定相位三路径透明度、4项world流向复验、9项纯水几何、纯水editor空状态／missing pool恢复及三路径群系像素已通过；水仍为candidate，默认冷启、side UV／切面邻域及预算待验。炼药锅的六档岩浆、水／药水／RGB／细雪、动画、占用、切面、公开蓝图和默认三路径群系冷启已通过，仅精确3.10默认启用；纯水随文档水色，药水／RGB独立。世界旗帜静态图案／变换／占用有限范围已启用，editor深度v6b在隔离副本有正例，未合入；飘动仍待。公开蓝图已覆盖盘点来源48个动画名称及155个默认NBT名称，逐族资格独立记录。下方历史观察不自动代表当前状态。

更新：2026-10-14，第十五轮17:20收尾修订。待办状态只在 [IMPLEMENTATION_GAPS.md](IMPLEMENTATION_GAPS.md) 维护；本文件是该清单 F01-W05/W06、F03、F04、F05 的范围、技术分类、实机审计和估时附件。名称与状态盘点已完成，像素资格和生产接入分别记录；候选数量不等于需要自行重写的数量。

## 第十六轮实测增量（22:40，进行中）

本轮截止2026-10-14 23:30，最多3个活动子代理、5个MC（含用户实例），不休眠。下表优先于本文第十五轮状态；资格仅覆盖声明的实测版本和路径，不把本体、内容与动画混为同一结论。

| 家族 | 已取得的结果 | 当前边界／下一步 |
| --- | --- | --- |
| 普通／试炼刷怪笼 | 已默认启用配置有／无／未知三类标识，保留原生外壳。6例×editor/full/missing及图层、切面、实际占用恢复；候选72图、默认冷启54图均完成恢复 | 不画生物模型。未知字段不当空，允许自定义实体ID；早期一张隐藏图连支撑都空，失败保留，不声称获得GPU完成栅栏 |
| 旗帜 | 已默认启用实测3.10家族的编辑器深度适配，保留原生颜色／图案；变换、图层、切面、缩放、投影及占用恢复有证据 | 有限静态姿态资格，不由此声明旗面飘动完成 |
| 末地门／折跃门 | 专用有限星空表面已默认启用；editor/full/missing、变换、透明度、图层、切面、动画及占用恢复有证据 | 不模拟传送／粒子；折跃门瞬时光束仍未完成，不将表面资格扩大到光束 |
| 物品框／发光框 | 原生框体可见；上向180°及非零旋转反向已修复。新双层原生附魔纹理／平方混色通过三路径原生放大可见性，保留旧0.66倍幅度／0.24倍速度的失败对照 | 生产物品资格仍关闭，完整48＋12姿态矩阵未通过。已有0.5／16格厚度的轮廓挤出，但左右暴露邻居判断错误，正修复并补斜视；3.9沿用的15／16正面位置未取得3.10独立侧视资格，不据此宣称贴框已解决 |
| 展示架 Shelf | 真实橡木展示架四向本体可见；live client palette、原样往返和product prepare三路四向均缺本体，支撑保持可见；roundtrip完全一致、actor为空 | 应补共享静态本体而非增加猜测actor字段。只对橡木aux0取得负向实证，12木种、连组角色和通电状态待验；内容overlay仍单独资格 |
| 常驻附魔书／讲台书 | 本轮19帧近景：附魔台原生仅台体；有效hasBook=1／writable_book讲台与空讲台画面相同 | 自定义共享书模型家族候选开发中，未接生产；附魔台仅常驻动作，用户不要求靠近打开 |
| 水 | 编辑器新冷启core与neighbors完成恢复，切面／部分实块邻域／透明本体／后方正例通过。修正玩家未移近平台的夹具后，world core及邻接几何／alpha／切面通过 | world侧UV仍低于原门槛，一次冷构建约157ms超100ms。远近两干净实例约65.31／6.44格的水可见性不同，尚未测同实例阈值与实际远距边界；近景修复不关闭产品远距差异。生产资格仍False |

刷怪笼、旗帜、门表面的资格分别保存在`docs/evidence/spawner-product-r16`、`banner-product-r16`、`portal-product-r16`；Shelf原生对照见[`shelf-native-r16/README.md`](evidence/shelf-native-r16/README.md)。`tools/verify_render_qualifications.py`可分别核对工作区或`--staged`的实测实现字节，不能代替图像验收。统一待办仍只在`IMPLEMENTATION_GAPS.md`维护。本轮最终估时在收尾后更新；进行中的候选和失败尚不计作已完成。

## 范围与依据

- 开发引擎：NEMC `3.10.0.420447`，MCBE `1.21.130.0`。本次不更新方块表，不更新旋转／镜像转换表；仍遍历仓库 `3.9.0.401155` dump 的全部 **1340 名称、15,858 状态**，其中 19 名称／19 状态属于项目预览方块，原版为 1321 名称／15,839 状态。
- NBT 默认来源：`tools/data/native_block_entity_defaults_nemc_3.9.0.401155.json`，实际捕获 **57 个 NBT 根 ID、155 个方块名称**。用户提供的 59 个 ID 参考另外包含没有原版注册样本的 `NeteaseContainer`、`ModBlock`。这个来源说明旧版本的数据，不是 3.10 所有非默认外观已支持的证明。
- 普通动态外观：遍历 dump 的全部状态，关联 3.10 安装的 vanilla、chemistry、三个 chemistry 版本资源补丁与 vanilla_netease 的方块／地形纹理／flipbook 数据。报告：`tools/data/render_compatibility_nemc_3.10.0.420447.json`，保留全部名称的状态键、aux、NBT 分类、动画候选与未映射项。
- vanilla 中 **48 名称／516 状态**关联动画资源；教育资源新增 `chemical_heat`，合计 **49 名称／517 状态**，分为 **37 个普通方块名称／415 状态**与 **12 个 NBT 方块名称／102 状态**。候选的某些状态可不播放动画，例如熄灭营火或未激活的状态，不将每个状态都算作动态阳性。
- vanilla 的三份原始 JSON 与归档的 3.9 版本逐字节相同，SHA 分别为 `cb3aad2d0d012bfb63a462ec9a5d8af54128c8afc26d74ac6f4ae074c9d50faa`、`9ce3e389999a7aff19968a60fd21dad1811cf63ec3edd6afac0af0df649e212c`、`54fef45e43eabb065a703f829d70320430c746744289775e57af582cb240fd7a`。资源相同不能代替 3.10 渲染行为／时钟观测。
- 3.10 已有干净投影与实际 actor 证据见 [官方支持审计](NEMC310_PROJECTION_SUPPORT_AUDIT.md)。目前只有部分类型有结构性观察；原生演员字段存在、NBT 读回成功、模型生成成功都不等于编辑器和投影像素通过。

**15:40用户范围修订，优先于历史记录：** 粒子、`moving_block`外观、教育版方块、潮涌核心激活核心／框架／旋转／持续特效、信标激活光束、宝库及类似方块内部物品特效均不适配。附魔台只需常驻书本动作，不随玩家靠近翻开。普通／试炼刷怪笼不绘制内部生物，但必须以替代外观区分“有配置生物／没有生物”，不能把这一要求当成完全排除。被排除的外观仍无损保存原NBT。水自定义、世界岩浆可原生、锅内容自定义；固定居中植物是设计要求。预览保持快照，不模拟传播、红石、燃烧、刷怪、植物生长或交互。

## 3.10 原生能力标记

本文件后续表格中的“原生”只表示 3.10 的官方 Combine／原生 actor 路径能够提供相应的方块本体、状态或 typed NBT 字段；它不自动表示编辑器、完整投影或缺失投影的像素验收已经通过。每个条目必须同时看下面的能力级别和验收路径。

资格需要分四层记录：①资源／官方文档声明；②目标版本真实状态、typed NBT 和 palette 字段；③干净 Combine 投影中已人工观察的本体／内容／连续帧；④项目 editor、full projection、missing projection 的集成资格。`NATIVE` 是前两层的能力标签，不替代后两层。负坐标或相机夹具中连投影石块阳性都不可见时，该轮属于夹具无效，不能给目标方块判“不支持”。

| 标记 | 含义 | 后续动作 |
| --- | --- | --- |
| `NATIVE` | 官方文档覆盖，且 3.10 干净样本已经观察到与该外观相关的字段或本体 | 保留原生 owner，补 editor／full projection／missing projection 像素和动态验收；不重复实现已经存在的本体 |
| `NATIVE-PARTIAL` | 原生只覆盖本体、状态或 typed NBT 的一部分，可见内容、动画或姿态仍缺 | 原生本体与自定义 overlay 分离；只为缺失部分建立适配 |
| `CUSTOM` | 官方明确不支持，或产品约束要求绕过官方路径（当前世界水、炼药锅液体） | 使用版本化项目适配器；保留原始状态和 NBT，禁止与原生几何重复绘制 |
| `UNVERIFIED` | 有资源或默认蓝图，但没有足够的 3.10 结构／像素证据 | 不能宣称支持；先用公开蓝图取得可追溯实机证据 |
| `EXCLUDED` | 用户明确不要求的外观或方块 | 从开发和验收工期中移除，保留盘点来源与原数据，不把它写成已支持 |

### 原生支持矩阵

这是按方块家族归并的显式判定。具体颜色、方向、配对、非默认 NBT 和动态帧仍按 NBT 表及普通动态表逐项验收。

| 方块／家族 | 3.10 原生能力 | 当前边界 |
| --- | --- | --- |
| 告示牌 `standing_sign`、`wall_sign`、悬挂告示牌 `*_hanging_sign` | `NATIVE` | 两面文字、颜色、发光和姿态字段已观察；字体排版、切面和三条产品路径仍待像素验收 |
| 旗帜 `standing_banner`、`wall_banner` | `NATIVE` | world静态model_local有限子集已启用，0／3／6图案、旋转／镜像及占用／恢复通过；editor v6b深度／切面正例仍为隔离候选，未授予飘动或全族scene资格 |
| 潮涌核心 `conduit` | `NATIVE`（静态本体） | 新干净投影已见未激活本体；激活核心、框架、旋转、持续动画／特效由用户排除，产品三路径本体仍须回归 |
| 花盆 `flower_pot` | `NATIVE` | `flowerPotPlant` 字段已观察；所有植物种类、切面和三条产品路径仍待像素验收 |
| 铜箱各氧化／涂蜡变体 | `NATIVE` | 铜类型、配对、方向和开度字段已观察；箱盖时序和内容不外绘仍待验收 |
| 铜傀儡雕像各氧化／涂蜡变体 | `NATIVE` | 铜类型、涂蜡、姿态和方向字段已观察；所有姿态像素仍待验收 |
| 普通箱子与陷阱箱 | `NATIVE-PARTIAL` | 配对、方向和开度字段已观察；双箱局部消隐、箱盖和三条产品路径仍待验收 |
| 钟 `bell` | `NATIVE` | 挂接／方向字段已观察；摆动时序仍待验收 |
| 火 `fire`、灵魂火 `soul_fire` | `NATIVE` | `fire-v2`包含两种火，干净同屏已见本体及明显帧差、石块静止。没有已证实必须自定义的缺项；产品各状态、三路径／切面待验单独记录，粒子排除 |
| 世界岩浆 `lava`、`flowing_lava` | `NATIVE-PARTIAL` | 用户允许使用官方路径；液位、流向、比水慢的动画及透明／占用仍需验收，炼药锅岩浆不适用 |
| 世界水 `water`、`flowing_water`、`bubble_column` 及含水本体 | `CUSTOM` | 即使 3.10 文档列出水，项目仍使用自定义半透明／流向／含水路径；不得同时保留官方水几何 |
| 炼药锅 `cauldron` 的水、岩浆、细雪、药水和染色液体 | `CUSTOM` | 版本化有限液面overlay已完成并在精确3.10默认启用；纯水取文档群系预设，药水／CustomColor不受群系影响。六档高度与颜色来自测量，三路径有限case／切面／占用／动画／默认群系冷启已验 |
| 下界传送门 `portal` | `NATIVE-PARTIAL` | 新干净投影已见紫色门面；轴向、深度、动画和三条产品路径仍待验收 |
| 末地传送门 `end_portal` | `CUSTOM` | Combine 文档明确不支持，必须使用专用动态表面；不实现传送行为或周边粒子 |
| 末地折跃门 `end_gateway` | `CUSTOM` | Combine 文档明确不支持，必须使用专用表面／光束几何；不模拟传送、冷却或周边粒子 |
| 物品框／发光物品框、展示架 | `NATIVE-PARTIAL` | 框体本体可由原生提供，但当前 actor 不含展示物品；物品模型、附魔光效、槽位和深度必须用共享 overlay |
| 箱子、潜影盒、末影箱 | `NATIVE-PARTIAL` | 壳体／方向／配对字段优先原生；库存只无损保存，不外绘，开盖和切面仍待验收 |
| 末地门框 `end_portal_frame` | `NATIVE-PARTIAL` | 这是静态框架方块，不是第四种传送门；末影之眼状态按原生状态验收 |
| 信标 `beacon` | `NATIVE`（静态本体） | 新干净投影本体可见，无需新增激活光束；保留三路径静态本体回归 |
| 附魔台、讲台、活塞／黏性活塞 | `NATIVE-PARTIAL` | 台体可见；附魔书常驻动作、讲台有书和伸出臂姿态未资格化，不要求近玩家翻开书或移动块内嵌外观 |
| 普通／试炼刷怪笼 | `NATIVE-PARTIAL` | 保留原生笼体／状态；补配置生物有／无的统一静态标识，不绘制生物模型 |
| 未覆盖的头颅／特殊活动姿态 | `UNVERIFIED` | 有默认NBT或资源不等于有效姿态支持；先修复样本，不用夹具缺失判不支持 |
| 移动块、教育版方块 | `EXCLUDED` | 用户明确排除外观适配，NBT仍无损保存 |

`NATIVE`表示原生能力已有依据，三路径资格另列。尚未完成产品回归本身不会把它降级；只有有效画面证实所需本体、内容或动态确实缺失，才记`NATIVE-PARTIAL`并补缺项。排除的动画不再作为降级或阻止完成的依据。

## 技术分类

| 分类 | 适用问题 | 共用方案与职责 | 难度 |
| --- | --- | --- | --- |
| A 原生外观直通 | 3.10 能正确提供本体、纹理和 actor 字段 | 版本化能力选择器决定唯一渲染者；保留原生 actor 和完整 typed NBT；通过实际画面后才停用对应 3.9 代理 | 低至中 |
| B 可见物品补充 | 框、架、营火、讲台等有原生本体但缺内容 | 共用物品解析／模型或 sprite／附魔层；槽位、朝向、缩放为家族参数。内容 owner 与本体 owner 分离，显隐／深度／切面同步 | 高 |
| C 姿态与表面参数 | 头颅、床、箱盖、潜影盒、图案与文字 | 原生优先，缺项由已有静态代理／参数映射补足。纹理来源与状态来源分别版本化；不用库存内容推测外观 | 中至高 |
| D 通用动画纹理 | 灯笼、海晶石、幽匿、植物、命令块、火等 | 共用 atlas/flipbook 帧序、速度、资源来源与动画时钟；只有原生投影缺动画时补材质。常驻动画与状态激活条件分开 | 中 |
| E 自定义世界水 | 液位、流向、含水、半透明、邻域 | 复用现有纯液面几何、面纹理、运输和 owner；版本独立时钟；编辑器／完整／缺失投影共用完整快照上下文 | 最高 |
| F 炼药锅液体 | 锅内液位、岩浆、药水ID颜色、自定义RGB | 锅体原生，独立有限尺寸液面 overlay；共用 D 的纹理动画，不使用整格水几何或群系颜色覆盖药水／染色RGB | 高 |
| G 特殊材质与可见模型动画 | 末地门、常驻书、旗面、头颅等 | 按材质／模型家族复用，先验原生；信标／导管激活和宝库内部特效不计此组；姿态与时钟分别验证 | 高 |
| H 活塞静态快照 | 活塞本体、辅助臂、伸出状态 | 共用现有方块状态／位置适配，不启动真实运动；moving_block内嵌显示已排除 | 中 |
| I 刷怪笼生物占位标识 | 普通／试炼刷怪笼 | 版本化NBT解码配置的生物，使用统一有／无标识；状态外壳原生，标识与本体同步显隐、切面和占用恢复 | 低至中 |
| S 状态决定的静态外观 | 瓶位、书架占位、炉子开关、门开合等 | 保留实际状态，直接取原生对应网格／纹理；无需为每个状态切换单独写循环动画 | 低至中 |
| X 排除项 | 粒子、内部生物模型、moving_block、教育版、信标／导管激活、宝库内部物品特效、未注册类型 | 不做这些外观补充，NBT仍保存；刷怪笼有／无标识另归I，本体回归不免除 | 无新增实现 |

分类不是模块白名单。运行时不能仅凭 ID 在表里就宣称支持；能力记录需要包含引擎版本、内容类别、显示路径、观察依据和未解决边界。未知字段无损保存，未知外观明确登记，不能静默丢弃。

**刷怪笼样本边界（17:25复核）：** 默认NBT表中的`MobSpawner.EntityIdentifier`是type8空字符串，可作为该旧版本的空配置来源，但非空样本仍需3.10真实配置验证。`TrialSpawner`默认根只有`current_mobs`、时间、玩家与`normal_config`／`ominous_config`等字段；两份config包含数量、范围、时序和掉落表，没有配置生物字段。不得用`current_mobs`数量或这份默认缺字段样本推导无生物，也不得猜Java的`SpawnData`字段。下一步公开测试蓝图应增加真实有配置、已确认无配置、未知／畸形三类数据，替代标识保留未知状态，三路径另验。

`audit_native_nbt_inventory.py`的部分分类名仍描述归档时的技术范围，例如`excluded_mob_spawner_internal_creature`和`visible_beam_geometry`；它们不是当前产品待办或准入条件。下次更新生成的规划元数据时须同步本轮用户排除项和新增I类标识，保留既有原始NBT／像素来源及其hash，不重写历史证据。

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
| Cauldron | 1，`cauldron` | 空锅／fill_level 1..6；水、岩浆、药水、染色液体与细雪；液面高度、遮挡、纹理与颜色 | F+D，高 | 3.10已读回三类液体0..6档、药水aux5..46及两组CustomColor；aux0是清水瓶，aux1..4保持空锅。字段已知，液面overlay与像素仍未完成。`lava_cauldron`是资源定义，不在旧dump，不能凭资源创建方块ID |
| ItemFrame | 1，`frame` | 物品、旋转、地图或其他有特殊内容的物品、附魔光效 | B，高 | 普通／附魔真实物品 NBT 存在，3.10 palette 内容 actor 仍 `{}`；sprite资源仅有diamond_sword，连续帧诊断阳性不等于通用物品支持或生产资格 |
| GlowItemFrame | 1，`glow_frame` | 上述内容及发光本体／内容光照 | B，高 | 同普通框；不能以框体可见代替物品可见 |
| Shelf | 12，`acacia_shelf`、`bamboo_shelf`、`birch_shelf`、`cherry_shelf`、`crimson_shelf`、`dark_oak_shelf`、`jungle_shelf`、`mangrove_shelf`、`oak_shelf`、`pale_oak_shelf`、`spruce_shelf`、`warped_shelf` | 三槽真实物品、附魔、联组角色、通电状态 | B+S，高 | 旧默认样本为空，3.10 内容未验证；应复用框物品方案并参数化槽位 |
| EnchantTable | 1，`enchanting_table` | 书本模型和常驻动作 | G，中高 | 台体原生可见；常驻书模型／动画仍待有效样本。用户不要求靠近打开、交互朝向或文字粒子 |
| Lectern | 1，`lectern` | 无书／有书的模型与页面姿态 | B/C，中高 | 新干净投影本体可见，有书非默认样本仍待有效采集；无需渲染GUI全文，也不模拟翻页交互 |
| Beacon | 1，`beacon` | 静态本体 | A，低 | `NATIVE`本体已见，三路径回归即可；激活光束／染色分段不要求实现 |
| EndPortal | 1，`end_portal` | 特殊动态材质与透明／深度关系 | G，高 | 3.10 Combine文档仍明确不支持，须专用表面；实际跳过／画面另验。没有flipbook不代表静止，安装中有`end_portal.vertex/fragment` |
| EndGateway | 1，`end_gateway` | 门内特殊材质与捕获状态；光束是否有可用快照依据 | G，高 | 3.10 Combine文档明确不支持；不能用传送坐标当可见状态，不模拟传送和冷却计时 |
| MovingBlock | 1，`moving_block` | `EXCLUDED` | X，无 | 用户明确不要求外观适配，内嵌NBT仍保留 |
| PistonArm | 2，`piston`、`sticky_piston` | 本体、臂及完整伸出静态状态 | H+S，中 | 不适配moving_block内部运动快照；实际根ID仍按实测来源保留 |
| Skull | 7，`creeper_head`、`dragon_head`、`piglin_head`、`player_head`、`skeleton_skull`、`wither_skeleton_skull`、`zombie_head` | 方向、玩家外观来源、龙嘴／猪灵耳的可见模型姿态 | C/G，中高 | 3.9 四种头颅局部姿态通过；玩家、龙、猪灵及3.10仍待，不能加载普通生物代替头颅 |
| ShulkerBox | 17，`black_shulker_box`、`blue_shulker_box`、`brown_shulker_box`、`cyan_shulker_box`、`gray_shulker_box`、`green_shulker_box`、`light_blue_shulker_box`、`light_gray_shulker_box`、`lime_shulker_box`、`magenta_shulker_box`、`orange_shulker_box`、`pink_shulker_box`、`purple_shulker_box`、`red_shulker_box`、`undyed_shulker_box`、`white_shulker_box`、`yellow_shulker_box` | 六向、颜色、闭合或可捕获的开盖姿态 | C，中高 | 3.10紫色actor `{}`；旧静态六向代理可复用但未完成新版本资格。箱内库存不外绘 |
| Chest | 10，`chest`、`trapped_chest`、`copper_chest`、`exposed_copper_chest`、`weathered_copper_chest`、`oxidized_copper_chest`及四种铜箱的`waxed_`版本 | 单／双箱、朝向、主副半、箱盖捕获姿态、氧化／涂蜡 | A/C，中 | 3.10已有配对、方向、开度与铜类型字段；原生像素及局部消隐待验。内部库存不外绘 |
| EnderChest | 1，`ender_chest` | 本体、方向、箱盖姿态 | A/C，中 | 新干净投影本体可见，方向／箱盖／三路径仍待；紫色周边粒子排除，私有库存不影响外观 |
| Banner | 2，`standing_banner`、`wall_banner` | 底色、类型、完整图案顺序、旗面常驻动作 | A/C/G，中高 | 新r15两种投影图案已见，真实物品交互后palette与NBT一致；3帧未见飘动，不宣称动态通过，优先原生图案 |
| Sign | 24，`standing_sign`、`wall_sign`及`acacia`、`bamboo`、`birch`、`cherry`、`crimson`、`darkoak`、`jungle`、`mangrove`、`pale_oak`、`spruce`、`warped`各自的`_standing_sign`与`_wall_sign` | 两面文字、染色、发光、排版、支撑／朝向 | A/C，中 | 3.10真实文字／颜色／发光字段已见；优先原生。旧橡木ID不带oak前缀，darkoak与悬挂款dark_oak不同 |
| HangingSign | 12，`acacia_hanging_sign`、`bamboo_hanging_sign`、`birch_hanging_sign`、`cherry_hanging_sign`、`crimson_hanging_sign`、`dark_oak_hanging_sign`、`jungle_hanging_sign`、`mangrove_hanging_sign`、`oak_hanging_sign`、`pale_oak_hanging_sign`、`spruce_hanging_sign`、`warped_hanging_sign` | 两面文字、悬挂姿态、材质与发光 | A/C，中 | 3.10字段已见，实际editor/full/missing未全部验收 |
| FlowerPot | 1，`flower_pot` | 空盆与实际盆栽植物 | A/C，低中 | 3.10 已见 `flowerPotPlant`，旧默认空盆不覆盖全部植物 |
| DecoratedPot | 1，`decorated_pot` | 四面陶片图案、朝向和当前外观姿态 | A/C，中 | 旧陶片／四向局部验收可复用；3.10 非默认样本待验。不显示盆内隐藏库存 |
| Campfire | 2，普通／灵魂营火 | 火焰／余烬动画、熄灭与点燃、四个烹饪物品的可见模型 | A+D+B，中高 | 动画纹理已关联；烹饪内容非默认 NBT 尚未验。烟雾／火星排除，不运行烹饪计时 |
| Bell | 1，`bell` | 挂接方向、本体与可捕获的摆动姿态 | A/C/G，中 | 3.10 附着／方向字段已见；原生默认静态姿态和动态动作分别观察，不模拟敲钟事件 |
| Conduit | 1，`conduit` | 非激活静态本体 | A，低 | `NATIVE`本体已见；激活核心、框架、眼睛、旋转、持续动作／特效均不要求适配 |
| Bed | 1，`bed` | 两格完整模型、16颜色、头尾、方向和局部消隐 | A/C/S，中 | 3.9 部分公开用例通过；3.10 原生色／配对待核查；NBT库存不适用 |
| BrewingStand | 1，`brewing_stand` | 三个瓶位的占位外观 | S，低中 | 状态 `brewing_stand_slot_a/b/c_bit` 可表示八种组合；不必按每瓶药水画完整物品，不模拟酿造 |
| ChiseledBookshelf | 1，`chiseled_bookshelf` | 六槽占位纹理与方向 | S，低 | `books_stored` 0..63 ×4方向，共256状态；不是 Shelf 的通用物品模型问题 |
| BrushableBlock | 2，可疑沙／沙砾 | 刷除进度的表面和真实可见的内藏物品姿态 | S/B，中高 | 含物品非默认快照和进度来源待核查；不启动刷除、掉落或粒子 |
| Vault | 1，`vault` | 状态材质、开口静态姿态 | A/S，低中 | 内部物品／物品特效明确排除；状态外壳仍须原生回归，不模拟开奖 |
| TrialSpawner | 1，`trial_spawner` | 普通／不祥／活动外壳及配置生物有／无标识 | A/S/I，中 | 不画内部生物；需版本化有效配置样本，不能把current_mobs当笼内配置生物；替代标识三路径待实现 |
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
| ChemistryTable | 4，`compound_creator`、`element_constructor`、`lab_table`、`material_reducer` | `EXCLUDED` | X，无 | 用户不要求教育版方块；raw资源／NBT盘点保留以供版本diff，不计实现或验收 |
| CraftingTable | 1，`crafting_table` | 原生静态本体 | A，低 | 原生确有该根ID；无需专门NBT外观overlay |
| NetherReactor | 1，`netherreactor` | 历史方块合法状态纹理 | A/S，低 | 不复活历史反应功能；注册存在与可放置性分别登记 |
| MobSpawner | 1，`mob_spawner` | 笼体与配置生物有／无标识 | A/I，低中 | 实测typed EntityIdentifier为空可区分无配置；非空样本须核验，未知／缺字段不能静默当空。内部模型、粒子与刷怪排除 |

参考中的 `NeteaseContainer`、`ModBlock` 不在实际原版捕获清单；无真实注册定义时不新增虚构原版样本。普通实体如盔甲架、画、生物不属于本次方块NBT范围。

## 普通动态方块

下表保留完整原始关联37个普通名称，合法aux在离线报告保留；教育`chemical_heat`明确排除，当前普通候选目标为36名。来源盘点不删行，产品目标按范围标记筛选。原生正确的条目只做接入／回归，不逐个重写shader。

| 分类 | 方块名称（省略 minecraft:） | 数量 | 外观与技术方案 | 当前实机边界 |
| --- | --- | --- | --- | --- |
| E | `water`、`flowing_water` | 2 | 自定义半透明、源水／流水高度、四向与下落纹理、含水本体、群系近似色 | 3.10独立无纹理时钟已测得+1；水本身帧序／四向／顶侧面及完整三路径仍待，不采用官方水替代 |
| A+D | `lava`、`flowing_lava` | 2 | 官方原生优先，检查顶／侧面、液位和比水慢的动画 | 3.10 静态／流动动画、切面／占用待验。锅内岩浆不归此方案 |
| E+D | `bubble_column` | 1 | 水面归E；可见泡柱纹理若原生缺失则复用D | 纹理动画与 standalone 气泡粒子分开；粒子不实现 |
| A+D | `fire`、`soul_fire` | 2 | 官方原生火模型＋flipbook；保留支持面／点燃状态 | 干净同屏火组有明显帧差且石块静止；editor/full/missing与局部隐藏仍待 |
| A+D | `lantern`、`soul_lantern` | 2 | 8 ticks火光纹理、摆放姿态 | `lantern-v3`同屏世界与Combine本体可见；发光不自动代表动画通过，不新增火星粒子 |
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
| X | `chemical_heat` | 1 | `EXCLUDED`教育版热块 | raw来源保留，用户明确不要求适配或实机验收 |

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

### 公开调试蓝图与盘点范围的对应

所有场景都从编辑器的“测试蓝图”页打开。新增的小画廊与自动测试共用同一份蓝图、case ID、坐标、独立提取入口和相机描述，验收样本必须能从公开蓝图复现。`debug_compatibility_blueprints.py` 的 schema 为1；名称与状态仍使用保留的3.9方块表，不能据此宣称新版本全部状态已经验证。

| 测试分页／蓝图ID | 可直接观察的范围 | 自动测试关联 |
| --- | --- | --- |
| 方块实体：`test.entities.catalogue.01`至`.07` | 实测默认NBT表的155个名称，每页最多24个；包括各木种告示牌、悬挂牌、展示架、各色潜影盒、铜箱与雕像；保留完整默认typed NBT | `test_debug_compatibility_blueprints.py`逐名比较原始捕获表并校验真实蓝图actor根ID／坐标 |
| 方块表：`test.dynamic.fluids` | 水／流水、岩浆／流动岩浆、气泡柱、锅、三种传送门、末地门框 | 动态资源源表的名称覆盖；公开default和另一合法状态，不宣称穷举像素 |
| 方块表：`test.dynamic.fire` | 火、灵魂火、两种营火、点燃高炉与烟熏炉 | 同一公开case支持editor／full／missing独立提取 |
| 方块表：`test.dynamic.lanterns` | 普通、灵魂和八种铜灯笼 | 默认及另一合法状态，底座阳性对照 |
| 方块表：`test.dynamic.sculk` | 六种幽匿／感测器家族 | 默认及另一合法状态；不模拟振动或红石 |
| 方块表：`test.dynamic.aquatic` | 海带、海草、萤火虫灌木、海晶石五种形状、海晶灯 | 植物成组默认／状态快照和相邻支撑 |
| 方块表：`test.dynamic.nether` | 绯红／诡异菌柄与菌核、岩浆块、重生锚 | 纹理动画与充能状态快照 |
| 方块表：`test.dynamic.special` | 三类命令块、切石机、附魔台、讲台、静态导管／信标、两类刷怪笼、宝库、大垂滴叶 | 本体／书本／配置标识待验范围；不包含已排除的激活和内部物品特效 |
| 方块实体：`test.entities.cauldrons` | 水／岩浆／细雪各六档、三种RGB、四种药水ID各三种形态，共33例 | 已有三路径产品工具；纯水取文档群系水色，药水／CustomColor独立颜色 |
| 原有实体外观、物品、文字、陶片、双层、邻接／连缀分页 | 非默认NBT图案／文字／物品、含水、含雪和部分占用邻居 | 各自`VISUAL_CASES`及专项三路径工具继续保留 |

新增七个动态小画廊覆盖资源关联的全部48个有效名称，并额外列出特殊模型与传送门；七个NBT全览完整覆盖155名称。全览保留原始教育版／MovingBlock样本仅供观察，不扩大用户已经排除的支持范围。离线覆盖通过只能关闭“蓝图遗漏”，没有逐项看图的外观仍按原表保持未验。投影验收必须另外启动world full／missing，不能由编辑器蓝图截图替代。

### 炼药锅的共享实现边界

旧registry有21个合法状态：water的aux0..6、lava的aux8..14、powder_snow的aux16..22，各自`fill_level=0..6`。第十四轮干净样本只有空锅／满水；第十五轮独立专项已经读回全部21个状态及60行真实交互，证据见[炼药锅审计](evidence/cauldron-runtime-r15/README.md)。药水物品aux0是清水瓶，逐次填充至2／4／6且`PotionId`/`PotionType=-1`；aux1..4保持空锅；aux5..46才返回对应`PotionId`。喷溅／滞留aux43..46和`PotionType=0/1/2`均有读回。状态可以直接设置成功，不等于每个液体档位都能通过原生玩家交互到达。

[PocketMine锅NBT](https://github.com/pmmp/PocketMine-MP/blob/stable/src/block/tile/Cauldron.php)与[Nukkit锅NBT](https://github.com/CloudburstMC/Nukkit/blob/master/src/main/java/cn/nukkit/blockentity/BlockEntityCauldron.java)是辅助资料；目标3.10已接受Int `CustomColor=-65536`和`16711680`并精确读回。该结果只证明存储，RGB/ARGB解释、alpha语义、药水颜色表仍需实际液面图像或目标版本资源佐证。保留原始有符号值和类型；药水43..46的新效应颜色不能照搬过时第三方色表。

建议独立纯解码`cauldron_appearance`与版本化内缘／液位／颜色profile，使用锅内有限水平面；复用液体owner／透明度／切面／占用显隐和纹理帧采样。现有世界水网格占满整格、依赖邻域，不能把锅液面伪装为普通水cell。原生锅壳在渲染副本中使用空锅状态，避免自带液体和overlay重叠；文档state/NBT保持。水纹`cauldron_water`为2 ticks，锅岩浆用`still_lava`为16 ticks，细雪独立静态材质；精确内缘及六档高度均未取得可信数值，不猜测。

本轮 MD 完成后继续开发，并实际观察未验证项。先核查原生能力，再决定哪些需要自定义，避免为已被3.10支持的外观重复实现。

### 实机范围核查后的修订

本轮按证据来源修订范围，以下成果分别解决盘点、字段与像素问题：

- [NBT运行时索引](evidence/nemc-nbt-r15/runtime-family-results.json)是第十四轮3.10归档的重新分析；现有28个工作组完整索引57根ID，但大量组没有来源样本，不能称为“57族新实测”。后续repair已纳入：旗帜真实NBT含`bs/Color 1`、`ts/Color 14`，对应更新palette保留图案字段；早期未读到Patterns不能覆盖后续成功读回。归档overview被菜单遮挡，不能新增像素通过。
- 告示牌、旗帜、花盆、铜箱、铜傀儡雕像和钟已有原生结构字段，可继续原生本体路线；潮涌核心仅有默认字段／本体依据。新增`native_render_profile`候选已接入palette、actor坐标上下文、editor/full/missing及缓存身份，168项相关离线测试通过；当前只允许显式选择普通／铜／末影单箱、床、花盆，并校验实际payload。Session默认仍为None，尚未启用生产原生分流，其他名称／无效字段保留已有路径；`model_local`或`context`须实机决定，版本号本身不自动放行。
- 展示框专项已取得editor、full projection、missing projection连续帧；普通剑稳定、附魔剑变化、空框阴性及真实原版展示框时间变化都有诊断证据。现有sprite资源只覆盖`diamond_sword`，框体轮廓／尺度、远景、资源生命周期、展示架、营火、讲台、刷除和宝库内容仍待，`NATIVE-PARTIAL`及`production_qualification=false`保持。
- 旧动态大画廊实际只含37个普通候选中的33个，缺`water`、`flowing_water`、`lava`、`flowing_lava`；额外加入的`big_dripleaf`、`conduit`、`end_portal`、`end_gateway`不能补足这四项，12个NBT动画名称也没有进入该gallery。editor／projection图字节相同且比例过小，`pixel_acceptance=false`；公开蓝图能构造样本不等于这些样本已经逐项观察。
- 三种传送门的最终产品资格均未完成。`portal`有原生flipbook候选；`end_portal`／`end_gateway`仍被Combine文档明确排除，专用表面任务保留。新干净投影必须先让同屏石块阳性可见，再判断目标缺失；失败启动、无石块的负坐标夹具和菜单遮挡均不作为不支持的像素证据。
- 炼药锅已取得60行3.10交互／读回、21个液体状态及两组`CustomColor`；不再列为“没有专用字段夹具”。剩余是准确药水／自定义颜色、六档高度、有限液面、深度／透明度和三个产品路径，现有证据`pixel_acceptance=false`。
- 水四向疑似反向已有3.9密集采帧局部证据；3.10独立无纹理时钟新测得递增`+1`，与3.9归档的`-1`不同。该测量只解除了独立时钟方向未知，水纹帧序、UV四向与下落仍需新版本密集采帧，不能直接移植旧方向修正。

这些结果减少重复实现原生本体的必要性，也明确了候选路由的实机启用、通用物品和特殊材质仍是剩余工作。重新估时使用下方的实际剩余工作与最多3个活动子代理，不再沿用十代理假设或用已经过去的墙钟扣减。

展示框本轮原始结果保存在 [`item-product-r15-310-summary.json`](evidence/item-product-r15-310-summary.json)，字段中明确保留 `production_qualification=false`；它是实机证据，不是把诊断结果直接升级为产品能力。

### 11:25新增近景观察与夹具限制

主会话已打开`r15-solo-runtime`的新PNG复核。独立的[`fire-v2`](evidence/r15-solo-runtime/fire-v2/report.json)与[`lantern-v3`](evidence/r15-solo-runtime/lantern-v3/report.json)中，真实世界与官方Combine模型同屏可见；火组有明显帧差，静态石块对照保持静止，灯笼组至少确认本体可见。它们证明干净官方路径的有限范围，不是项目三路径资格。

随后[`batch-v2`](evidence/r15-solo-runtime/batch-v2/)采用origin `(0,-58,0)`，每组带投影石块阳性。下表只登记主会话已经查看的图像，不把其余已生成报告算作观察完成。报告中的`pixel_acceptance=false`保持。

| 已查看样本组 | 此次投影中实际可见 | 仍未解决或不能据此判定的内容 |
| --- | --- | --- |
| `signs` | 立式／墙面告示牌红色正面文字、橡木悬挂牌绿色背面文字可见 | 全部木种、双面排版／发光、姿态与产品路径仍待 |
| `containers`、`shulker_bed` | 普通箱、铜箱、末影箱、紫色潜影盒及床本体可见 | 配对局部消隐、箱盖、颜色／方向全覆盖未验；同组龙头未见，不据此判不支持 |
| `pottery` | 盆栽虞美人和饰纹陶罐外壳可见 | 其他植物、陶片四面顺序与姿态未验 |
| `special_nbt` | 附魔台本体、信标本体、未激活导管本体可见 | 本轮未见书或光束；激活样本及客户端同步尚未建立，不能据此排除原生能力 |
| `portals` | 下界门紫色表面可见 | 本轮未见末地门／折跃门，仍按官方不支持保留自定义方案；此次缺失图本身不新增可信负向结论 |
| `frames`、`contents` | 普通／发光框框体、讲台和雕纹书架本体可见 | 未见剑与展示架；真实内容和客户端同步须先确认，不扩大为“所有原生内容不支持” |
| `special_states`、`pistons` | 钟、铜傀儡雕像、活塞／黏性活塞本体可见 | 动态姿态、伸缩／移动快照未验；本轮未见moving_block，不据此判不支持 |
| `heads` | 石块投影阳性可见 | 猪灵头、玩家头、骷髅头与前述龙头未见；需有效客户端样本重验 |
| `batch-v2/banners` | 该次旗面呈黑色 | 原始typed NBT为Base4／两图案，而palette为Base0／零图案，来源不一致；保留失败原件，后续`banners-v4`已补有效图案投影 |
| `copper_a/b/c` | 加上此前基础款，八种铜灯笼本体已查看且可见 | 连续时间裁剪尚未人工复核，只有差分统计时不授予动画通过 |
| `prismarine_a/b/c`、`sculk`、`sculk_nbt`、`sensor` | 已查看的海晶石形状、幽匿及感测器本体可见 | 慢动画、各激活阶段与时间裁剪仍待复核，不把本体可见外推为动画接受 |

该批从`signs`开始，真实世界前排在图像中也未显示，虽然服务端／状态读回有效；因此客户端同步或显示夹具仍有问题。投影石块阳性允许保留“实际看到的投影本体”这一正向事实，不能使预期内容缺失自动成为引擎不支持结论。`plants`组又出现投影石块不可见，批次因此停止；该组及未查看的动态组均未完成资格。需要修复客户端可见参考、等待并核对客户端状态／actor内容，再重跑缺失与非默认样本。该夹具问题保留在本次风险估计内。

后续定位在相同缺失石块ROI执行原版`/setblock dirt`后立即看见泥土，说明捕获区域本身可以显示世界方块。当前怀疑夹具的`SetBlockNew(updateNeighbors=False)`未使世界显示及时刷新，正使用更新邻居的版本重跑旗帜；这仍是待验证原因，不将它写为确定引擎缺陷。新负向结论必须绑定已固定的夹具源码快照，并同时核对真实世界、客户端palette与原始NBT。

本轮重新检索的`SetBlockNew`官方资料只把`updateNeighbors`定义为相邻方块更新／事件开关，没有承诺它控制客户端mesh刷新。资料另外提示，放置后立即调用影响相关客户端表现的服务端接口可能异常，建议下一帧再操作。这两项需分别控制，不能把参数名称当作根因证据。

**11:50旗帜复验：** 主会话已查看[`banners-v4/rois.png`](evidence/r15-solo-runtime/banners-v4/rois.png)。经真实`PlayerUseItemToPos`使用带`userData`的旗帜物品后，palette的Base4／两图案（bs颜色1、ts颜色14）与原始NBT一致，立式／墙挂投影均清楚显示彩色图案；直接`SetBlockEntityData`只写原始字段的前一方案没有刷新此palette内容。该有效正向样本解决的是两种旗帜的这组图案显示。三帧`changed_gt12=0`，当前未见飘动，不能宣称永久静止或动画通过。`updateNeighbors=True`后真实世界石块可见，但真实世界旗帜仍未显示；因此世界参考与最终产品资格继续待验。新的`batch-v3`还在补采其他类型，未查看结果不提前计入。

### 3.10独立时钟证据

独立无纹理`TOTAL_REAL_WORLD_TIME`诊断[`clock310-v2.json`](evidence/water-clock-nemc310-r15-v1/clock310-v2.json)已完成：13个有效帧、11个变化间隔，`clock_direction=+1`；红通道约31.596／秒，诊断公式预期31.875／秒；支持区域13帧均为12,584像素。`completed`、`restored`、`source_unchanged`和`capture_temporal_complete`均为true，`product_acceptance_claimed=false`。原件已归档，[相对路径索引](evidence/water-clock-nemc310-r15-v1/artifact-index.json)记录SHA256与字节数，保存13帧及当次诊断工具／shader，避免依赖原报告中的会话绝对路径。

这个结果约束的是该3.10诊断shader所用时钟的方向及速度，不能单独证明水纹流向正确。3.9的递减时钟证据只保留历史来源；水的产品shader、帧序和UV需按3.10实测分别验证。独立测量已取得，不重复列为待建立；水的三路径资格保持未通过。

午间新增[3.10流向诊断汇总](evidence/water-flow-nemc310-r15-v1/summary.json)：复用当前world shader／mesh／图集、使用不透明洋红控制uniform的独立freeModel，四向顶面各26帧／25个有效间隔，正确方向比例均0.84，反向时间序列均被拒绝；生产shader没有修改。下降侧面v2为0.667、加密sky背景v3为0.45，虽然非零位移向下，质量门未通过，整项`completed=false`。恢复及源码不变通过，归档保存两份报告与原图。该结果不是Scene／WorldProjection owner、透明度或editor/full/missing资格，不能据顶面统计宣布水已完成或流向已修复。

### 原生profile候选实机进度

候选已经在单独的3.10产品实例运行，图像写入[`native-render-profile-r15`](evidence/native-render-profile-r15/)。专项已查看`06-full-local`／`12-missing-restored`中的三种单箱、床和虞美人花盆，model_local路线对齐；`10-missing-occupied`中占用位置的主体消隐，床头半格保留还须单独核对。`16-full-context`对照出现单箱错位／重复、床错位，花盆仍对齐。`14-editor-oblique`则暴露原生主体被支座错误遮挡，正在定位编辑器共享深度。以上是候选的正例、反例与待修问题，不能宣称已经上线；默认profile继续None，编辑器／占用边界和最终三路径资格仍未完成。

| 批次 | 同屏样本与控制 | 必须留下的结果 |
| --- | --- | --- |
| R1 高难度原生边界 | 附魔台常驻书／讲台、末地门／折跃门、活塞静态伸出臂、龙／猪灵头、刷怪笼有／无标识 | 本体、内容、姿态和所需动态分别观察；moving、教育、信标／导管激活及宝库内部特效不再计待验 |
| R2 可见内容 | 框／发光框／展示架普通、附魔、空槽；营火食物；讲台书；刷除进度物品 | 空内容阴性、正常内容阳性、附魔连续帧；真实NBT与实际物品尺寸／位置／遮挡对应 |
| R3 官方覆盖的NBT | 文字两面、旗帜图案、花盆植物、陶片、箱子／潜影盒／床／铜雕像、书架／瓶位 | 原生显示、项目显示分别记录；非默认样本不能用默认空样本代替 |
| R4 普通动画全族 | 上表36个在范围名称，按家族分页；NBT的12个动画名称一起核查 | 连续时相与固定视角，灭／亮等状态控制；慢速海晶石须覆盖有效帧变化，教育chemical_heat排除 |
| R5 最终产品三路径 | 合入后的同一公开蓝图：editor、full、missing | 切面、透明度、邻域、真实方块局部占用、隐藏后恢复、内容替换与资源释放 |

首次范围核查可以用 editor 或投影之一，但最终交付须覆盖三个产品路径。内置蓝图只验编辑器，投影另行运行。所有画面检查关联公开测试蓝图或来源明确的同内容夹具；源码／资源／NBT／PNG／时间／相机与版本绑定。截图空白、被菜单遮挡、来源错配、采样不足均不算通过，须显式报告。

普通材质族按资源关联扩展测试覆盖；个体不需要重复写实现。共用修复须包含静态阴性、动画阳性、独立未知输入与移除恢复，防止错误外推。水时钟／纹理方向须使用3.10的新观测，旧3.9递减时钟证据只保留为历史。

当前授权最多3个活动子代理、最多5个活动MC；测试器不主动前台化、不使用桌面输入。用户手动切到前台时继续。按身份回收所属实例，捕获失败不能静默吞掉。本轮要求12:00前修订技术MD与估时，继续开发至2026-10-14 17:30（Asia/Shanghai），不自动休眠。

## 按难度的开发顺序

下面是风险优先的并行安排；每个适配器开发前先有同族原生观测。基础能力选择器／测试入口是这些任务的必要前置，不需要为此重构整个仓库。

| 顺序 | 工作组 | 高风险原因／复用收益 |
| --- | --- | --- |
| 1 | E世界水；G末地材质／常驻书／旗面；C头颅 | 透明深度、动画时钟和私有材质影响最大；先决定原生可复用范围，用户排除项不继续追查 |
| 2 | B展示框／展示架／附魔及营火／讲台内容；F炼药锅 | 通用物品与小液面overlay建成后复用多个NBT族，避免逐个试接口 |
| 3 | C头颅／箱盖／潜影盒／旗帜／文字／陶片缺项 | 3.10原生已覆盖的部分直接接受并回归，剩余状态参数化处理 |
| 4 | D所有动态纹理；A/S原生本体与状态 | 通用时钟／帧序／材质检测覆盖整族；官方岩浆、火等只补实际缺项 |
| 5 | 三路径集成、含雪、连缀／占用、性能与冷启动 | 专项可并行补测，最终同一提交验收；不以局部或旧版本记录关闭总体资格 |

## 本轮修订的剩余工期评估

估计更新点为2026-10-14本轮收尾：炼药锅有限产品范围已完成，水透明度／颜色／纯水发布与占用恢复有三路径实机依据，世界旗帜静态子集已启用，editor旗帜深度得到可复用的隔离正例。单位为继续开发所需有效墙钟，包含实现、自动实机验收和集成。上限为主会话加3个活动子代理、5个活动MC；共享代码、冷启动和人工读图仍有串行阶段。此处替代15:40的11–20／20–30小时，不按过去时间机械扣减。

| 阶段／并行流 | 尚需完成的具体工作 | 预计墙钟 | 依赖与完成口径 |
| --- | --- | --- | --- |
| 共同前置 | 整合已测native家族契约，扩充其余有效样本；editor旗帜候选源审查与有界接入 | 0–1小时 | 不把banner/pole的450原点／0.64比例应用到其他actor；世界单箱／花盆／静态旗帜已有限启用 |
| 并行A：水与原生岩浆 | 默认水资格冷启、相邻side UV／切面与部分实块邻域／透明排序／预算；官方岩浆实际动态 | 2–4小时 | 锅本轮已完成，不再计入实现；水现有alpha／biome／纯水／motion证据保留，不重复诊断已解决的重复原生水 |
| 并行B：可见物品与静态NBT | 通用框／架物品、附魔、营火／讲台／刷除内容；静态NBT回归；刷怪笼有／无标识 | 8–12小时 | 不含宝库内部物品特效；特殊物品仍须模型来源，解析NBT不等于通用显示 |
| 并行C：特殊外观与动态候选 | 末地门／折跃门表面、常驻书、旗面／头颅、活塞静态臂；在范围动画候选分页核查 | 6–10小时 | 移动块、信标／导管激活、教育排除；世界旗帜静态及深度诊断已计入，未把候选当交付 |
| 最终串行集成 | 同一生产版本的editor／full／missing、切面／占用／透明度、保存变换、含雪及连缀、资源释放和冷启动 | 2–5小时 | 公开分页和2,719项回归可复用；后续改动仍须适当回归，不机械重跑相同绿灯 |

**本轮收尾重估：还需10–18小时有效墙钟，风险18–28小时。** 主会话加3代理稳定并行时，共同前置0–1小时＋最长专项8–12小时＋最终集成2–5小时；三个专项不相加。相较15:40的11–20／20–30，关闭了锅默认三路径及水主要诊断，新增公开源覆盖使后续回归更直接；最长专项仍由通用物品与特殊NBT决定，因此整体工期不会按水专项节省的时间等量缩短。物品模型来源、末地表面或其他actor深度需要改方案时进入风险区间。

最新水biome冻结归档与35个owner及专属资源／注册逐项一致；较早alpha/direction归档只差版本门控和锅接入，没有水shader／mesh／texture差异。闭包审计不能代替默认资格冷启或side UV验收。旗帜editor深度已找到有实测依据的候选，不再重复盲试，但须先做精确版本的家族适配及世界回归。以上工作不把测试数或默认蓝图数量换算成全部外观完成率。

范围包含已授权P0、多格／连缀、NBT／动态外观及自动验收；不包含全部P1/P2、RenderDragon、完整安卓认证或已明确推迟的方块表／旋转镜像版本迁移。17:30是本轮停止时间，今日剩余窗口足以推进原生范围核查、能力选择和专项增量，不能承诺在该窗口内关闭上表全部工作。遇到未取得有效样本的类型时保留未知与待办，不以缩减可见内容来满足截止。

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
