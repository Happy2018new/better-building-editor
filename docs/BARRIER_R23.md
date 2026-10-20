# OB-05：屏障可视标记（R23，实机复核完成，人工待验）

本轮为编辑器及投影加入屏障的专用可视标记：使用原版红色屏障图案，放在格子中央三个互相垂直、正反面都有图案的透明面片上。每面宽高为 0.75 格，不创建实心红墙。**这是用于建筑观察的标记样式；真实文档、存储、导出及世界放置仍是 `minecraft:barrier`。**

当前已完成下述代表视角的实机截图复核，以及受控占据观察器下的缺失投影消隐／恢复检查；标记设计观感仍待周末人工验收，不在本记录中整体关闭 OB-05。原生世界中屏障自身的显示、碰撞、粒子和持有物品行为均不由该标记修改。

## 接入方式

`barrier_render.py` 只定义原生名称到内部标记名称的映射。与现有树叶／植物代理相同，`geometry_palette.prepare_palette` 在临时渲染调色板中替换名称；界面视图和投影共用该入口。不会往 `Document.blocks` 写代理，不往世界写标记方块，也不把代理加入用户材质选择器。

标记 ID 为 `modern_projection:preview_barrier_marker`，不注册到创造栏，并加入 `INTERNAL_RENDER_BLOCKS`。模型为三个零厚度面片，每个面片显式写两个相反面，覆盖 north／south／east／west／up／down 六面；不依赖关闭背面剔除来掩盖缺失的反面。模型在各轴都限制于格内 0.125—0.875，没有越格覆盖。不会注册实体、原生模型包或新材质。

共享注册修改已由 root 整合，准确片段保存在 [barrier_registration_r23.json](../tools/data/barrier_registration_r23.json)：

- `resource_pack/blocks.json` 增加对应 `netease_model` 项。
- `resource_pack/textures/terrain_texture.json` 增加命名空间纹理项。
- `geometry_palette.py` 的代理选择和内部方块过滤接入 `BARRIER_PROXIES`。

新增模型／行为文件和纹理均在独立路径：

- `resource_pack/models/netease_block/preview_barrier_marker.json`
- `behavior_pack/netease_blocks/preview_barrier_marker.json`
- `resource_pack/textures/blocks/modern_projection/barrier_marker.png`

## 原生资源与格式来源

资料库中的 `CombineBlockPaletteToGeometry` 明确列出屏障不支持合并，故本轮直接沿用已知的自定义模型代理路线。网易《自定义方块模型》确认 `models/netease_block`、`blocks.json` 的 `netease_model` 和 `terrain_texture.json` 的贴图绑定，并说明透明模型配合 `netease:render_layer`、模型配合 `minecraft:block_light_absorption`。实现沿用项目已有版本格式及 `netease:no_crop_face_block` 约定。

本轮读取的安装资源根为：

`D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data/resource_packs/vanilla`

原版 `blocks.json` 将 `barrier` 绑定到地形贴图键 `barrier`；`terrain_texture.json` 将该键解析到 `textures/blocks/barrier.png`。该图不是 `textures/items` 下的物品图标。源图原字节复制到项目命名空间，不改色、不改 alpha、不采样放大。

| 项目 | 值 |
| --- | --- |
| 原生贴图 | `textures/blocks/barrier.png` |
| 尺寸／格式 | 16×16 RGBA PNG |
| 文件大小 | 186 字节 |
| SHA-256 | `144dc5d61706124c91e19c4b7e2b410da58b240e6eeb01ca421330b90dbb18a4` |
| 透明／不透明像素 | 138／118，没有中间 alpha |
| 造型来源 | 原版纹理＋本轮明确设计的三轴标记，未声称恢复原版屏障网格 |

小型来源清单为 [barrier_source_r23.json](../tools/data/barrier_source_r23.json)，记录实际引擎版本、方块表指纹、原生 blocks／terrain／贴图哈希，以及生成的四个文件哈希与大小。没有复制安装资源全集。

日常一致性检查使用：

```powershell
python tools/generate_barrier_marker_r23.py --check --registered --native-resource-root D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data/resource_packs/vanilla
```

只有经审阅的来源更新才执行 `--capture-native <资源根> --engine-version <版本>`；检查命令不会自动重新采集哈希，也不会自动接受改变的资源。

## 专用人工检查入口

内置蓝图 `test.blocks.barrier_visibility`，标题“屏障 · 三轴可视标记”，位于“测试蓝图 → 方块表”。原始数据包含 13 个真正的屏障格：孤立屏障、相邻两格、3×3 屏障板、悬空屏障，另有石头对照和少量台座；不需要构造 NBT。

| 对象 | 本地坐标 |
| --- | --- |
| 孤立屏障 | (3,3,3) |
| 相邻两格 | (7,3,3)、(8,3,3) |
| 3×3 板 | X=3—5、Y=2—4、Z=9 |
| 悬空屏障 | (11,5,9) |
| 普通石头对照 | (11,3,3) |

先在编辑器从东／西／南／北／上／下和斜向转动观察，确认图案可辨认、背面存在、透明区域不被填红，普通石头外观不变。再在完整和缺失投影重复代表视角，观察相邻标记是否错误消失。缺失模式用准备好的三个占据点：孤立格、相邻组第一格和板的中央格，验证占据／移除后标记独立消隐及恢复。加载前保存草稿，重新载入本蓝图可恢复候选，不操作用户建筑。

## 验证与边界

专用回归 `tests/test_barrier_render.py` 覆盖原生 ID／存储保真、完整及部分缺失输入的代理位置、临近石头不受影响、世界写入仍使用真实屏障、内部 ID 过滤、格内零厚度几何、六个显式面、26 种观察方向的投影面积下界、原版 alpha 和来源／生成文件一致性。离线几何和调色板检查不能代替实际引擎输出。

| 验证层 | 结果 |
| --- | --- |
| 原生贴图及生成资源检查 | `--check --registered --native-resource-root` 通过，四个生成文件、源图及共享注册一致 |
| 专用离线回归 | 8 项通过 |
| 接入回归 | 屏障、调色板、全部测试蓝图、普通方块清单共 50 项通过，27.723 秒 |
| 实际 Python 2 | Python 2.7.13 编译／导入三个新增运行模块、构建屏障及四个变换蓝图通过 |
| 结构与依赖审查 | 两个屏障运行模块 review：2 个文件、0 项发现；imports 未引入 SDK、跨端侧初始化或新事件 |
| 编辑器实机像素 | v3b 的斜向、东／西／南／北／上／下 7 张原图已逐张查看；这些视角均可见标记，正反面及透明区域有效 |
| 完整投影 | 正面、背面、仰视 3 张原图及各自隐藏投影实体的对照图已逐张查看，当前来源匹配，标记、石头及台座可辨认 |
| 缺失投影及占据恢复 | 同一仰视相机的空占据、动态隐藏、初始隐藏、恢复 4 阶段及各自隐藏实体的对照图已逐张查看；三个目标分别消隐并恢复，石头、五个台座及相邻保留格没有误消 |
| 原生世界真实占据 | 未测试；本轮仅临时替换占据观察器，没有往世界放置屏障或代理 |
| 周末人工验收 | 未检查 |

离线检查记录和检查后源码指纹保存在 [offline.json](evidence/barrier-r23/offline.json)。普通组合场景使用八个显式来源白名单，屏障专用入口不自动派生新的普通组合场景，也没有改变原有八项的范围。

候选只覆盖屏障可识别性，不把其他不可见内部方块统一转成标记；不改变那些方块在普通验收清单中的范围。实图确认三轴图案在斜角会重叠，正交视角也会出现前后格沿视线重合。这些画面没有被当作所有格都独立可读的证明；标记密度、清晰度和样式仍交由周末人工判断，不用离线面积检查或截图差值代替观感验收。

## R23 实机证据复核

有效采集为 `.runtime/round-20261019/barrier-runtime-v3b.json`，截图时间为 2026-10-19 18:47—18:48（北京时间）。其 `completed=true`、`restored=true`、`cleanup_errors=[]`。独立离线复核实际查看了 14 张主图（7 编辑器＋3 完整投影＋4 缺失阶段）和 7 张隐藏实体对照；另对初始基线截图做散列与截图元数据核对，共验证 22 张原图。原始采集的 `pixels_accepted=false` 保持原样，本节记录的是后续复核结论，不伪装成采集器自动验收或用户人工通过。

保留的证据总览均从原图固定矩形裁出，标签位于图像外：

- [编辑器七视角](evidence/barrier-r23/editor-contact.png)：统一原图矩形 `(600,350,1510,850)`，缩至每格 455×250；正交视角的前后重合可在这里直接看到。
- [完整投影三视角](evidence/barrier-r23/full-contact.png)：统一矩形 `(420,330,1530,900)`，缩至每格 555×285；隐藏对照保留原图指针，不重复打包大图。
- [缺失投影四阶段](evidence/barrier-r23/missing-contact.png)：统一矩形 `(420,340,1090,750)`，保留 670×410 原生裁图，无缩放。
- [三个目标及石头逐项对照](evidence/barrier-r23/missing-targets.png)：每个对象在四阶段使用同一矩形，保留 160×180 原生裁图，无缩放。相邻组右侧标记为占据目标，左侧为保留格。

四张 PNG 合计 584,696 字节；没有把全部原始大图复制进 Git。[runtime-summary.json](evidence/barrier-r23/runtime-summary.json) 记录每张原图相对路径、SHA-256、字节数、尺寸、截图时间、WGC 信息、快照来源、固定裁图矩形、逐项测量及总览图散列，可用以下纯离线命令重建：

```powershell
python tools/pack_barrier_evidence_r23.py
```

### 三个目标与对照

三个占据目标一同输入临时观察器，随后分别按画面位置复核；这证明的是本用例三个格的独立渲染结果，不是逐个放置真实世界方块的测试。四阶段中，观察状态依次是 `[1,1,1]`、`[2,2,2]`、`[2,2,2]`、`[1,1,1]`；动态隐藏与恢复各产生一次提交，初始隐藏使用重新建立的投影。各阶段的文档和投影快照均与采集前一致，所有格的真实材料身份继续保留。

| 对象 | 原图固定测量矩形 | 空占据 → 动态隐藏 → 初始隐藏 → 恢复 | 实图结论 |
| --- | --- | --- | --- |
| 孤立屏障 `(3,3,3)` | `(765,350,825,415)` | 红色像素 1790 → 0 → 0 → 1790 | 目标完整消隐并原位恢复 |
| 相邻组目标 `(7,3,3)` | `(620,450,653,481)` | 红色像素 618 → 0 → 0 → 618 | 目标消隐，另一格保留，随后恢复 |
| 板中央 `(4,3,9)` | `(976,529,1017,571)` | 红色像素 636 → 3 → 3 → 636 | 中央标记消隐，周围八格保留，随后恢复；隐藏时 3 个红色像素位于矩形左边缘，来自相邻标记裁边 |
| 相邻保留格 `(8,3,3)` | `(575,478,601,508)` | 红色像素 600 → 600 → 600 → 600 | 四阶段测量矩形像素完全相同 |
| 普通石头 `(11,3,3)` | `(453,493,559,583)` | 四阶段像素完全相同 | 没有随三个目标误消 |
| 五个灰色台座（相邻两格共用一组裁图） | 4 组固定矩形，见 summary | 四阶段各矩形像素完全相同 | 五格均保留，没有随目标误消 |

红色计数使用 `R≥150、G<100、B<100`；差值测量使用通道差大于 12。计数用于定位和复核，不作为自动通过阈值。石头与各台座除四阶段相同外，在隐藏整个投影实体的对照中也确实消失，排除了把世界背景误认成对照方块的情况。缺失阶段的仰视画面中，部分非目标标记会被普通台座自然遮挡，本节没有据此声称 13 个标记在每张截图中都完全无遮挡。

### 运行版本与截图安全

运行项目快照为 `.runtime/projects/barrier-r23-v3`，绑定 owner `barrier-r23-v3`、游戏 PID `31012`、进程 identity `134368794181151398`。离线复核按运行 JSON 中的 8 个 SHA-256 逐字节检查该快照里的屏障映射、蓝图、调色板入口、行为／模型／贴图及两处共享注册；8 项均相符，并且打包时主仓同名文件的字节也全部一致。采集工具版本 SHA-256 为 `746c78cedc0e0b4840b663dd5e6f2595061bef00abf80063600fb26839216c97`，打包时的工具文件相同。不能用后续主仓路径相同来替代这个运行快照证明。

基线 SDK 提交记录为 13 个内部标记、1 个石头、5 个浅灰混凝土，原生 volume 为 `(16,16,8)`；编辑器聚焦格仍直接返回 `minecraft:barrier`。缺失四阶段均记录 `document_preserved=true`、`snapshot_preserved=true`，且 owner／cache／origin／snapshot 全部匹配当前投影。结合工具代码，本轮只临时替换占据读取并恢复观察器、相机、文档、视图和投影状态，没有写入世界；不扩充为原生屏障实际放置、碰撞、粒子或存储导出全流程的新实机证明。

22 张原图均验证 `Windows.Graphics.Capture`、1994×1105 原生分辨率、文件字节／散列匹配、可靠且在本次请求后取得的新帧。截图采用 `allow_user_foreground`：允许用户自己把窗口放到前台，代理激活被禁止，未用激活回退；所有记录的前后台 guard 均为 no-activate、非最小化、前台窗口未改变。内部 `capture.background_only=false` 不表示代理抢焦点，实际约束由这些 no-activation 字段与 guard 记录证明。截图 helper 的实际文件 SHA-256 也与全部记录一致：`cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8`。

### 保留首轮失败

首轮 `.runtime/round-20261019/barrier-runtime-v3.json` 未完成，只有斜向／东／西 3 张编辑器图，完整／缺失投影均未执行；它仍记录 `restored=true`、`cleanup_errors=[]`。失败为检查器等待 `north` 时直接比较目标 yaw `180` 和 SDK 归一化结果 `-180`，报 `TimeoutError: editor view north: {'pose': [-180.0, 15.0, 1.5]}`。这是测试工具的角度等价判断错误，不能写成渲染缺图，也不能把该轮改为通过。v3b 将 yaw 按 modulo 比较后完成全部阶段。

| 原始记录 | SHA-256 | 工具 SHA-256 |
| --- | --- | --- |
| `barrier-runtime-v3.json`（未完成，清理成功） | `ac19d634fdbf666ea1d31eabfc4f2499f173b3695935061d011b6a6aa8b782d5` | `b7d3f5931e1f91530bfc0db551724e17d2b64c995b150e429832abb41d94befc` |
| `barrier-runtime-v3b.json`（完成，清理成功） | `d51152ec07e8c7f9c05ad8a76ebc403100f8a0bfdeeb92e8ea150444be875957` | `746c78cedc0e0b4840b663dd5e6f2595061bef00abf80063600fb26839216c97` |

两份原始记录及原图保留在 `.runtime/round-20261019`，历史 [offline.json](evidence/barrier-r23/offline.json) 仍保留当时尚未实机检查的状态。当前结论仅补齐本节所列视角、来源与受控消隐恢复证据，OB-05 的整体关闭和标记样式人工验收仍然保留。
