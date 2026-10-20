# OB-02／OB-03：普通透明方块调查与可见性修复（R23）

## 正式主源的三植物短验（2026-10-19 22:47）

金合欢树苗、脑纹珊瑚、气泡珊瑚已接入正式 `ordinary_` 固定居中交叉代理，并在独立冷启动的 `ordinary-final-r23-v1`、未增加 alpha 诊断补丁的主源材质下完成真实编辑器、北向缺失投影及完整投影四向短验。树苗 aux 0／1 都在编辑器和缺失投影实图可见，完整投影四向检查的是 aux 0；另两种珊瑚四向均可见。三个路径共 32 行显示／隐藏采样，含空气和石头控制，三张实际目标裁图联系图均已查看。14 份正式源资源在完整投影采集前后哈希一致，四份报告均恢复并独立读回，无诊断标记、临时实体或残留投影，实例 22:47 释放后交由其他专项继续使用。

新入口 `test.blocks.ordinary_plant_visibility` 已通过实际测试页及确认流程载入，当前编辑器几何就绪，八格精确为四支撑和树苗 aux 0／1、脑纹珊瑚、气泡珊瑚。入口原图已查看，未展开小构图的精细外观验收。小证据包为 [formal-runtime-v1.json](evidence/plant-proxy-r23/formal-runtime-v1.json)，正式资源与已测候选仅标识／atlas key 变化的独立比较为 [formal-resource-review-v1.json](evidence/plant-proxy-r23/formal-resource-review-v1.json)，具体报告和联系图见 [植物专项文档](PLANT_PROXY_EDITOR_MISSING_R23.md)。

这只是三种固定居中植物的可见性修复；原生尺寸、随机偏移、含雪／含水、其他姿态和占用消隐仍待验，`NATIVE_MESH_AUTHORITY=False`、`SNOW_QUALIFIED=False` 保持不变。海带与芍药的北向缺面尚未修复，梯子及其他代表不因本次三植物通过而扩大资格，**OB-02／OB-03 整项仍开放，本阶段关闭 0 项问题**。下文保留各历史阶段的原始失败、隔离实验和当时结论。

23:22追加的含水短查误用了已被用户否决的原生水路径：两个珊瑚只露出顶部枝片，大部分本体被水立方遮挡。23:27用户重申水须单独实现、原生岩浆已接受；此次结果仅归档为旧路线诊断，不用来评价自制水方案，也不再次安排原生水验收。详见[含水边界补查](PLANT_PROXY_EDITOR_MISSING_R23.md)。两层CPU数据保留与代理默认湿格映射事实仍有效；下一轮先确认自制水renderer接入，再做组合外观与占据恢复。

## 初期离线调查（历史）

本轮已完成原生贴图、运行调色板和材质继承的检查，尚未得到这些代表方块的实机像素结论。**源图不是全透明，现有项目覆盖按官方合并规则也没有移除原生透明材质的 `DisableCulling`。因此不能直接把“完全不可见”归因于背面剔除，更不能据此批量关闭问题。**

调查对象为金合欢树苗、脑纹珊瑚、气泡珊瑚、仙人掌花、海带、红树根、梯子。继续保留当前雪目录和已有资格；没有修改共享注册、普通植物代理或雪目录。随后在专用受管实例执行了空气／石头校准，但两路石头正控均无目标像素，未继续植物采集；见下文实机界限。

## 贴图与状态证据

资源读取自安装的 `3.10.0.420447/data/resource_packs/vanilla`。七个名称对应十三张颜色图，全部有非空可见 alpha，且只有 0／255 两种 alpha 值。`vanilla_netease/textures/terrain_texture.json` 中没有这些十三个贴图键的覆盖项。原生 `blocks.json` 给出其纹理和声音，但没有给出这些对象的具体渲染网格。

| 代表 | 原生纹理键／状态注意事项 |
| --- | --- |
| 金合欢树苗 | `acacia_sapling` → `textures/blocks/sapling_acacia`；aux 0／1 仅 `age_bit` 不同，需都保留 |
| 脑纹珊瑚 | `brain_coral` → `textures/blocks/coral_plant_pink`，不应误用珊瑚块／扇纹理 |
| 气泡珊瑚 | `bubble_coral` → `textures/blocks/coral_plant_purple`，不应误用珊瑚块／扇纹理 |
| 仙人掌花 | `cactus_flower` → 同名纹理；源图顶行有透明留白，不能把碰撞高度直接当成可见网格高度 |
| 红树根 | 顶／底 `mangrove_roots_top`，四个侧面 `mangrove_roots_side`；不属于交叉植物网格 |
| 梯子 | `ladder` → 同名纹理；当前表列出 aux 0—5，但代表性可放置水平朝向应测 2—5，默认 aux 0 不能证明四个合法水平面的行为 |
| 海带 | 原生声明使用 `kelp_a/b/c/d`、`kelp_top`、`kelp_top_bulb` 六个纹理键，不能无依据简化为单张普通花草纹理 |

实际贴图尺寸、alpha 像素数／边界、源图哈希、完整原生定义、逐状态 `prepare_palette` 输出和原有 Combine 回执摘要保存在 [native-alpha.json](evidence/ordinary-alpha-r23/native-alpha.json)。准备调色板时上述名称保持原生身份，未套用当前雪植物的 centered 代理。

`.runtime/round-20261019/ordinary-support-v1.json` 证明七个**默认状态**的原始和准备后调色板均得到成功 Combine 返回；该报告明确没有像素检查。成功返回不能证明有非空网格、朝向正确、片元未被丢弃或实际出现在相机内。梯子的四个水平朝向不包含在该默认状态结论内。

## 材质继承与项目差异

需读网易组合网格所在的 `vanilla_netease/materials/terrain.material`。只读 `vanilla/materials/terrain.material` 不能回答 Combine 实体网格的继承关系。

资料库查询 `netease 覆盖材质` 返回《材质合并规则》：不同目录中的同名材质字段合并；普通字段以后加载的值覆盖；`states`／`defines`／`samplerStates` 支持 `+` 添加与 `-` 删除；合并顺序是先全部覆盖，再全部添加，最后全部删除。查询 `netease 材质` 的《材质定义》确认冒号后的名称是父材质。新工具按这些规则保留同名声明中各份 `+states`，避免普通 `dict.update` 丢掉先前的添加列表。

下表省略共同前缀 `netease_block_as_`；结果针对默认状态，非实际引擎抓取。

| 材质 | 原生父项 | 原生 `DisableCulling` | 合并项目后 | 项目新增默认状态 |
| --- | --- | --- | --- | --- |
| `entity_mesh` | 无 | 无 | 无 | `Blending` |
| `mesh_doubleside` | `entity_mesh` | 无 | 无 | 继承 `Blending` |
| `mesh_alpha_single_side` | `entity_mesh` | 无 | 无 | 继承 `Blending` |
| `mesh_alpha` | `mesh_alpha_single_side` | 有 | 有 | 继承 `Blending` |
| `mesh_alpha_seasons` | `entity_mesh` | 有 | 有 | 继承 `Blending` |
| `mesh_blend` | `entity_mesh` | 无 | 无 | 无（原生已有） |
| `mesh_blend_alphatest` | `mesh_alpha` | 有 | 有 | 无（原生已有） |
| `mesh_blend_alphatest_seasons` | `mesh_alpha_seasons` | 有 | 有 | 无（原生已有） |
| `mesh_blend_alphatest_singleside` | `mesh_alpha_single_side` | 无 | 无 | 无（原生已有） |
| `mesh_blend_no_culling` | `mesh_blend` | 有 | 有 | 无（原生已有） |

`mesh_doubleside` 的名字本身不等于显式关闭剔除；其原始声明为空，继承的根项也没有该状态。另一方面，`mesh_alpha`、`alpha_seasons` 及相应 blend 后代的双面状态有明确原始定义，项目没有声明删除它。十个材料的完整链、宏、shader 路径、变体原片段、项目显式 shader 字段及来源哈希保存在 [materials.json](evidence/ordinary-alpha-r23/materials.json)。

检查命令：

```powershell
python tools/audit_ordinary_materials_r23.py --native-data D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data --output docs/evidence/ordinary-alpha-r23/materials.json
```

报告中的递归 shader 绑定是按照定义推导的名义结果。它没有读取引擎编译后的每个后代 shader，也没有证明每类原生方块实际被分派到哪个材质。既有水系诊断已提示：只覆盖父项不足以替代后代的实际绑定检查。

## 最小可验证的修复顺序

先在当前实例以产品 `product` 路线校准石头，再对照原始 `raw` 路线；产品石头失败时暂停其余路线，先核对目标屏幕投影、实际 actor 位置、渲染距离与实体可见范围。石头正控成立后，才对同一相机、同一份原始方块数据建立当前资源快照 A 与显式 shader 绑定快照 B。B 仅将原生普通 alpha／doubleside 后代的**完整原生声明**复制到隔离测试资源，保留父项、宏、状态、采样与变体，显式绑定项目当前的顶点及片元着色器。候选包括 `mesh_alpha_single_side`、`mesh_alpha`、`mesh_doubleside`、`mesh_blend_alphatest`、`mesh_blend_alphatest_singleside`；季节后代现已显式绑定也应保留原生完整字段。不要同时增加双面状态，避免两个变量一起改变。

若 B 恢复可见，再分别确认编辑器、完整投影和缺失投影，从四个水平朝向与斜角观察，并检查透明孔洞、透明度 0／中间值／1、占据消隐与恢复。梯子用 2—5 四个朝向及实际支撑面；树苗两种年龄；珊瑚的原生正控应避免离水死亡改变状态；红树根检查顶和侧；海带检查顶部及中段。普通石头、玻璃、已适配植物和水作为邻近回归对照。

若显式绑定不恢复，则再做独立剔除 A/B，范围只限隔离测试快照，用于识别原生分派到 single-side 的可能。`alpha` 族本来已有双面状态，给其重复添加 `DisableCulling` 没有解释力。若从所有相反方向都不可见，应继续核对原始网格／着色器丢弃与相机变换，而非直接认定缺背面。

只有在上述路径明确失败后才准备代表性代理：树苗／珊瑚等使用成对正反面的透明交叉片；梯子按 2—5 四面分别构造贴墙面片；红树根使用顶底和四侧的透明方壳。原生纹理可复用，但高度、偏移、UV 和朝向仍需真实对照。安装目录的 `experimental_vanilla_block_geometry/models/blocks/cross.geo.json` 为正反面片提供了原生格式参考，**不能当作这些指定方块的实际网格契约**。

这一方案不需要先扩大雪目录，也不改变文档和世界中的原生方块身份。目前只完成离线调查与测试计划，没有批量生成或接入这些代理，没有关闭 OB-02／OB-03。

## 本轮采集工具和隔离补丁

`tools/capture_ordinary_alpha_r23.py` 已准备，不在准备阶段连接游戏。默认十个样本（空气、石头、金合欢树苗、脑纹珊瑚、海带、芍药、四个水平梯子方向）和四个固定水平斜视角；可用重复的 `--sample`／`--view` 缩小首批。空气和石头控制自动保留。所有样本共用局部目标 `(1,1,1)`、同一底部石头台及固定相机目标；芍药构造上下两半。梯子仅提供合法方向状态，没有原生世界摆放或侧面支撑正控，不能据此声称世界放置外观一致。

路由分为 `product`、`raw`、`raw_loaded`、`raw_opaque`、`prepared` 和 `prepared_opaque`。当前默认依次执行 `product` 与 `raw`，先证明同一实例的产品路径可见；若产品石头失败，记录原因并推迟 raw，不再连续重复透明度路线。显式指定 `raw_loaded` 会自动先跑 `product`，产品正控通过后才继续；它仅把 actor 放在玩家 `GetFootPos()+(0,1,0)`，沿用产品偏移补偿公式保持世界几何位置及机位不变，既不加透明度调用，也不加产品 uniform。显式指定 `raw_opaque` 时，在单独的新实体及唯一模型上调用 `EnableActorBlockGeometryTransparent(name, True)`、`SetActorBlockGeometryTransparency(name, 1.0)`；`raw` 保留未调用透明度 API 的诊断基线。`prepared` 与 `prepared_opaque` 在对应对照上增加准备调色板；五条诊断路线均不注入产品布局 uniform。`product` 走现有完整投影。它们均不写真实方块。脚本复用 `SignCheck`、所属实例的 WGC 截图、蓝图状态备份和恢复流程，不启动游戏、不激活或缩放窗口。实机运行必须显式提供所属 `--session`／`--owner`／`--project`，由 root 分配时段。

这一分离来自本轮离线复查：当前 `modern_projection_biome_blocks.fragment` 的末尾对未带产品上下文的实体无条件将 alpha 乘 `COMMON_BLOCK_GEO_FLOAT1_1`。未设置该参数可能使原始诊断实体透明，不能据此判断植物原生网格为空。官方两个 API 文档确认先启用透明度再赋值才生效，二者均返回 bool。`raw_opaque` 只记录成功调用和请求值，不声称读取到了 GPU uniform。五条 raw／prepared 诊断路线创建实体后，还沿用 `world_projection.py` 已有路径调用 `CreateModel(entity).SetEntityShadowShow(False)`；该 API 返回无值，报告单独记录调用完成、返回值和无读回能力，避免实体阴影混入可见／隐藏差分。

每张原图及 WGC 回执保留，裁切是原图的直接裁切，默认矩形为客户区 `[0.25W,0.15H,0.75W,0.85H]`。每对可见／隐藏帧记录前后 actor、模型、相机、玩家身份；另外读取实际 actor 的 `GetFootPos`、本地玩家的实体渲染距离、目标格中心与八角的公开 `WorldToScreenPoint` 结果及屏幕尺寸。屏幕投影只作机位／裁切诊断，须对照实际 PNG，不能凭 `isInScreen` 认定模型已渲染。与同路线、同视角的空气对照计算差分信号，另外重复空气可见帧估计背景噪声。差分图明确标为分析输出，不代替原图。每条路线的石头必须在所有请求视角上高于空气噪声阈值，才继续该路线的植物。路线正控失败会保留原始失败帧和回执并跳过该路线植物；产品正控失败会暂停其余路线；所有路线都失败则采集报错。普通目标首个请求视角没有足够信号时默认推迟其余角度，并记录原因。所有报告保持 `pixels_accepted: false`，`completed` 仅表示采集流程完成。

离线生成首批计划（不会访问 MC）：

```powershell
python tools/capture_ordinary_alpha_r23.py --plan-only --calibrate-only --view north --output <新计划.json>
```

所属实例就绪后，由 root 执行类似首批命令：

```powershell
python tools/capture_ordinary_alpha_r23.py --session <所属会话.json> --owner <owner> --project <测试副本> --output <新证据.json> --calibrate-only --view north
```

首批仅校准空气与石头。确认正控有真实像素后，移除 `--calibrate-only`，用重复 `--sample` 指定植物。若此前相机已为离体相机，使用已有诊断约定的 `--restore-detached` 恢复原离体相机位置。`--all-views` 仅取消普通样本弱信号后的提前停止，不越过石头正控，也不表示授予像素资格。

`tools/prepare_ordinary_alpha_r23.py` 为独立测试副本应用单文件补丁。仅向原生五个普通 alpha／doubleside 后代声明添加显式 vertex／fragment 路径，保留其原生完整字段；其他项目材料不变。它拒绝主仓路径及解析后指向主仓的目标，要求副本的原始材质和 shader 与当前审阅源码一致，并在写入前保存原始与候选字节。主仓 `resource_pack/materials/terrain.material` 不由此脚本修改。

```powershell
python tools/prepare_ordinary_alpha_r23.py --snapshot <测试副本> --native-data D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data --output <新补丁备份目录>
```

本轮已在 `.runtime/ordinary-alpha-r23-patch-preview-v1/` 生成补丁预览：`patch/terrain.before.material`、`terrain.candidate.material`、`patch.json`。其中 `resource-staging` 仅承载三个资源文件，不是可启动的完整游戏副本。检查确认原有项目声明逐项不变，只增加五个保留完整原生字段的显式声明；没有进行冷启动或像素采集。

离线工具回归 4 项通过：共同位置／空气负控／完整芍药／四向梯子、原生字段保留及输入不变、主仓与未知策略拒绝、精确裁切及差分信号和资格分离。七段格式化游戏注入代码在实际 Python 2.7.13 下编译通过，尚未执行。

随后透明度校准修订增加两项离线回归：分别执行未设置／固定 opacity 1 的实际附着注入，核对 API 调用顺序；模拟未设置路线石头失败后保留证据、跳过该路线植物，并仅在固定 opacity 路线石头成功后继续植物。该修订共 6 项通过，9 段格式化注入代码通过实际 Python 2.7.13 编译，证据为 [tools-opacity-offline.json](evidence/ordinary-alpha-r23/tools-opacity-offline.json)。它属于实机采集前的离线工具验证。

## 实机校准界限和下一步

专用 `alpha-r23-v5` 实例的原始报告为 `.runtime/round-20261019/ordinary-alpha-calibration-v5a.json`。`raw` 与 `raw_opaque` 的严格 Combine 和透明度 API 回执成功，但空气和石头的 actor 差分均为零，石头相对空气目标差分也为零；原始全帧、裁切和差分已查看，非中心差分来自调试 HUD 和世界生物。工具在正控门槛停止，没有采集植物，报告 `completed=false`、`restored=true`、`cleanup_errors=[]`。不能将这个结果算作植物网格失败、空网格证明或 OB-02／OB-03 的新关闭结论。

该实例于北京时间 18:26:45 以 `0xC0000005` 退出，MCDK 同时正常退出；末次采集帧约为 18:24:59。精确进程证据在 `.runtime/round-20261019/exact-exit-alpha-v5.json`。随后只读查询在本地进程身份校验阶段被阻止，没有向失效实例发送调用，没有盲目重启。原始校准报告中的“恢复完成”仅表示诊断恢复调用当时成功，不能据此否认稍后进程崩溃；现有证据也不能确认崩溃与几何释放有关。

离线源码核对表明，两路线使用同一 anchor 资源及 `(-0.5,0,-0.5)`、Y 旋转 180° 的既有坐标约定；产品路径另有 0.2 秒实体就绪等待、布局及双缓冲 uniform、当前可见性发布和临时实体渲染距离设置。更具体的差异在 `bridge.follow_projection()`：产品已记录“空的高层子区块可能在相机裁剪前漏掉客户端实体”，因此每帧把 mesh actor 移至玩家脚边已加载区，再补偿几何偏移。v5 的 raw actor 在 Y=-40、玩家脚部在 Y=-60，二者处于不同子区块，raw 且没有进入产品 follow。此差异有直接源码依据，但尚未用新对照证明它就是这次正控零像素的原因。raw 清理直接调用官方支持的 `DestroyClientEntity`，产品清理会先隐藏 uniform 和所属几何再销毁；官方接口没有规定销毁前必须手动 detach，也不能据此推断稍后的崩溃原因。

为此，工具下一版默认以产品石头正控开始，增加屏幕八角、实际实体位置与渲染距离读回，并增加独立 `raw_loaded` 路线只改变 actor 所在子区块。回执保留 entity anchor、geometry origin 和实际 offset；离线重建世界原点验证补偿不移动几何。新增产品正控失败不运行 raw、精确八角读取及 loaded 补偿不变性回归；共 9 项工具回归、11 段实际 Python 2.7.13 编译均通过，详见 [tools-product-control-offline.json](evidence/ordinary-alpha-r23/tools-product-control-offline.json)。离线最小计划为 `.runtime/ordinary-alpha-r23-calibration-plan-v7-loaded.json`，请求 `--route raw_loaded --calibrate-only --view north`，报告会明确先执行产品石头校准。这些修改未再连接或启动 MC，等待 root 提供可用受管实例。

## 已建立有效正控的四向基线

root 随后分配 `barrier-r23-v3` 受管实例，并先验证 product／raw_loaded 石头可见。代表采集先执行北向，再执行北／东／南／西四向；两次均 `completed=true`、`restored=true`、`cleanup_errors=[]`。四向报告为 `.runtime/round-20261019/ordinary-alpha-representatives-four-v5.json`，共 56 组可见／隐藏对照；没有修改运行副本资源、世界方块或玩家位置。最后独立只读检查确认三个诊断标记均移除，投影和任务关闭、导航静止、临时实体为空、玩家仍在 `(0.5,-60,0.5)`，然后将实例交还 root。

已实际查看两条路线的带边界拼图，观察结果一致：

| 代表 | 北 | 东 | 南 | 西 | 当前含义 |
| --- | --- | --- | --- | --- | --- |
| 金合欢树苗 | 无 | 无 | 无 | 无 | 本例四向均没有植物；不等于原生网格为空 |
| 脑纹珊瑚 | 无 | 无 | 无 | 无 | 本例四向均没有珊瑚；尚未覆盖其他珊瑚种类 |
| 海带 | 无 | 可见 | 可见 | 可见 | 已复现方向性缺面，仍须修复 |
| 芍药 | 无 | 可见 | 可见 | 可见 | 已复现方向性缺面，上下两半在其余方向可见 |
| 梯子 aux 2 | 可见 | 可见 | 可见 | 可见 | 单一合法状态的四向基线成立；其他 aux、原生侧墙支撑和编辑器仍待验 |

石头在两路线、四方向的目标格内部均有约三万个差分像素，说明本次机位与已加载区内的 actor 控制有效。`WorldToScreenPoint` 八角均入屏，实际 actor 位于 `(0.5,-59,0.5)`；产品临时实体渲染距离为 256，raw_loaded 为恢复后的 72，均能看到石头。此时仍不可见的植物，才有资格继续研究源路径与材质。

不能直接把整张 crop 的差分量当植物存在证据：北向首次产品四植物各出现 6,545 个差分像素，但全来自画面边缘移动的史莱姆；目标格内部均为零。四向南侧也有动物从空目标后方经过，导致树苗／珊瑚目标 ROI 出现少量非零像素。`tools/analyze_ordinary_alpha_r23.py` 使用公开八角投影的凸包、向内收 4 像素，保存每目标数据与拼图；它校验输入图哈希，保留原图及直接裁切，明确不把非零像素自动提升为通过。芍药 ROI 仅统计下半格，外观判断同时查看完整裁切。

复算命令为：

```powershell
python -B tools/analyze_ordinary_alpha_r23.py .runtime/round-20261019/ordinary-alpha-representatives-four-v5.json --output <新分析.json>
```

当前分析为 `.runtime/round-20261019/ordinary-alpha-representatives-four-v5-analysis.json`，两条路线分别有同前缀的 `-product-contact.png`／`-raw_loaded-contact.png`。来源报告、恢复状态、资源与工具源码 SHA-256、各方向计数、观察结论保存于 [visual-baseline-20261019.json](evidence/ordinary-alpha-r23/visual-baseline-20261019.json)。这里建立的是完整投影 actor 基线，未检查编辑器 UI、缺失投影或原生世界放置参照，**本阶段关闭 0 项问题**。下一步由 root 正常关闭当前实例后冷启动显式材质绑定 B，保持样本和机位不变，再决定是否需要独立的双面状态实验。

## 其余代表的可选诊断（离线准备）

工具额外允许 `--sample bubble_coral`、`cactus_flower`、`mangrove_roots`、`firefly_bush`、`redstone_wire`、`big_dripleaf`、`big_dripleaf_head`。这些样本全部显式选择，默认 `SAMPLES` 仍为原十项；没有自动扩大冷测矩阵。空气／石头控制及 `--route raw_loaded` 先走产品正控的门槛不变。

六个原生名称均按当前 registry 的合法默认 aux 0 构建；气泡珊瑚、仙人掌花、红树根、萤火虫灌木无状态，红石线仅 `redstone_signal=0`。大型垂滴叶默认是 `head=false`、`tilt=none`、`south`，只显示茎；额外的 `big_dripleaf_head` 从同一默认状态设置 `head=true` 后通过 `from_states` 求得合法 aux 4。它仍是未倾斜、朝南的单个叶盘状态，没有构造虚假的双格配对，也不涵盖其他倾斜、通电或邻接状态。芍药继续构建合法上下两半；如果后续 registry 的默认配对会覆盖底部支撑或越出样本，工具会拒绝生成。

萤火虫灌木 fixture 的原始 Document／raw palette 保留 `minecraft:firefly_bush`，`prepared` 与产品路径则仍会选择现有 `modern_projection:centered_firefly_bush` 静态代理；新离线回归确认准备过程不修改原始文档和 palette。这使 `raw_loaded` 可用于原生网格动画的隔离试验，不需要为试验修改产品 `PLANT_PROXIES`。动态候选与独立飞虫边界另见 [FIREFLY_BUSH_R23.md](FIREFLY_BUSH_R23.md)。

此修订共 **12 项** 工具回归通过；**24 段**包含新 fixture 的注入代码在实际 `D:/Program/Python27/python.exe`（2.7.13）编译通过，并由该解释器独立核对 9 个控制／新样本的原生名称、aux、状态。只生成 `.runtime/ordinary-alpha-r23-samples-v2/optional-samples-plan.json`，未连接或启动 MC。验证摘要见 [tools-optional-samples-offline.json](evidence/ordinary-alpha-r23/tools-optional-samples-offline.json)。

原四向基线工具 SHA-256 保留为 `c4f5e19ca8a6534f9c93124fc52d6c97e917e3bc6153b5537c0753bd252b35e4`，与原始 v5 报告相符；对应原源码逐字节备份为 `.runtime/ordinary-alpha-r23-samples-v2/capture_ordinary_alpha_r23.baseline-four-v5.py`。新工具 SHA-256 为 `f11a984b6ccbb9c661c46b08c592b9326f5bdd9fd6cebb9e38b97daf204046f7`。旧报告及旧像素证据没有改写，这次扩展仍关闭 **0 项** 渲染问题。

## 材质 B 冷启动实测与无效四向批次

root 冷启动 `alpha-r23-b-v1`，材质 SHA-256 为候选 `33d899b29e9cccdcd3bbd6fbe6195df0bb92a3c97d31a5bf0655e212328b6105`，两份 shader 与 A 的哈希相同。先跑原五个代表的北向 `product`／`raw_loaded`，14 组可见／隐藏对照完成，恢复正常且 `cleanup_errors=[]`。原报告为 `.runtime/round-20261019/ordinary-alpha-b-five-north-v1.json`，同前缀 `-analysis.json` 与两个 `-analysis-*-contact.png` 保留哈希及可视分析。

两条路线的北向石头目标内部差分分别为 30,889／29,997 像素，梯子 aux 2 为 9,712／9,721；树苗、脑纹珊瑚、海带、芍药的目标 ROI 均为 0。两张拼图已目视检查：前四个目标缺失，梯子可见。因此，显式绑定五个材质后代没有恢复这些目标的北向可见性。**A 与 B 并非相同世界或绝对机位**：A 玩家在 `(0.5,-60,0.5)` 的平坦世界，B 玩家在 `(-749.5,69,-699.5)` 的自然地形。局部 fixture／相机角度相同，仍不能将结果写成严格配对的像素 A/B，也没有关闭渲染问题。

随后四向批次 `.runtime/round-20261019/ordinary-alpha-b-five-four-v2.json` 在产品东向石头正控停止。空气重复帧噪声为 76,423 像素，门槛为 229,269，石头差分 109,888 未达门槛；仅采集 6 对控制，尚未运行植物或 raw_loaded。原始画面中石头实际可见，空气首次／重复的远景树木和雾有变化，背景加载／渐变是候选原因，未证明唯一原因。没有降低门槛、覆盖原报告或把此批次算作方块失败。该批次 `completed=false`、`restored=true`、`cleanup_errors=[]`；原始帧与东向控制拼图均保留。

最后只读状态确认三个诊断标记均清除、projection／busy／transition 为 false、临时实体为空、玩家位置未变，随后将实例交回 root。本 lane 不再访问实例。上述来源、状态、有效北向测量及无效四向控制见 [material-b-cold-20261019.json](evidence/ordinary-alpha-r23/material-b-cold-20261019.json)。下一次 alpha 冷启动由 root 明确采用 `--preset ui` 的平坦世界，重新建立原五代表的正确场景对照。

## C：仅增加 DisableCulling 的冷启动结果

root 已在独立 `alpha-r23-cull-v1` 副本中只改变 `terrain.material`，向 `netease_block_as_mesh_doubleside`、`netease_block_as_mesh_alpha_single_side`、`netease_block_as_mesh_blend_alphatest_singleside` 增加 `+states: ["DisableCulling"]`；没有增加显式 shader 绑定。材质 SHA-256 为 `de2291bd7e9a8db1acf11a9e1fbe76edd21c608830ca5fa6f5c4112c858eaa8f`，vertex／fragment 与 A 相同。生成时的 patch 清单仍如实保留 `runtime_started=false`；随后受管 session 及采集报告另行证明本次确已冷启动和运行，未改写旧记录。

本次使用正确 `ui` 场景，玩家仍在 `(0.5,-60,0.5)`。五代表加空气／石头，在 `product` 与 `raw_loaded` 两路线各跑北／东／南／西，共 **56 组可见／隐藏对照**。两路线四向石头均超过原有空气噪声门槛；没有降低门槛。与 A 对应的全部相机读回逐项相同，但背景生物随时间变化，不能把全图非零差分当植物恢复。

实际查看两份完整四向 ROI 拼图，以及金合欢树苗和梯子原始裁切后，结果如下：

| 代表 | C 两路线四向 | 相对 A 的结果 |
| --- | --- | --- |
| 金合欢树苗、脑纹珊瑚 | 全部不可见 | 仍未修复 |
| 海带、芍药 | 全部不可见 | A 的东／南／西可见性退化 |
| 梯子 aux 2 | 全部不可见 | A 的四向可见性退化 |

局部 ROI 中少量非零像素来自空目标后方的牛羊或史莱姆，原图中没有目标几何；产品石头目标内部仍有 `30,881 / 32,108 / 31,016 / 32,004` 像素。**该精确候选不能启用，新增关闭数为 0。** 结果不证明 `DisableCulling` 这一状态本身无效，也不证明 Combine 生成空网格；实际材质合并／variant 选择尚未直接读取。

精简来源、控制、哈希、计数与恢复证据见 [material-c-culling-20261019.json](evidence/ordinary-alpha-r23/material-c-culling-20261019.json)，配套 [产品四向拼图](evidence/ordinary-alpha-r23/material-c-culling-product-20261019.png) 与 [raw_loaded 四向拼图](evidence/ordinary-alpha-r23/material-c-culling-raw_loaded-20261019.png)。这两张图是校验原图哈希后的局部裁切缩放，只覆盖目标格及支撑；芍药上半格仍以私有原始全图为准。未修改的全帧、完整拼图、WGC 回执和报告保存在 `.runtime/round-20261019/ordinary-alpha-culling-four-v1*`。

采集 `completed=true`、`restored=true`、`cleanup_errors=[]`，世界方块及玩家位置未改。随后独立只读检查确认三个诊断标记已清除、投影／busy／transition 均为 false、临时实体和 preparing_entity 均为空、factory 恢复 `EngineCompFactoryClient`；完成后将 C 交回 root 调度。没有把 C 资源切回主仓。

## 干植物代理备用候选的边界

为避免材质实验阻塞不可见植物，已在 ignored 运行目录准备独立 `ordinary-plant-cross/candidate-v2` overlay。它沿用现有 centered 双向交叉面生成器，限定金合欢树苗两种 age 状态、脑纹珊瑚及气泡珊瑚；共九文件，仅在候选中增加三种内部代理及映射。三者未进入原有代理的原因是当前生成范围取自 `debug_snow_blueprints.NAMES`，这些名称不在该范围，尚未发现贴图映射错误。

代理使用安装包原始贴图并保留正反 signed UV 的 alpha 形状；单位高交叉面是复用模板的几何假设，未声称恢复原生随机偏移或权威尺寸。主业务、雪目录和雪资格均未改变。root 后续已在新的 `alpha-r23-proxy-v1` 冷测副本按 manifest 的 base／candidate SHA-256 精确应用九文件；此处只登记准备事实，尚未取得该副本的 MC 像素结果，不能记为修复通过。
