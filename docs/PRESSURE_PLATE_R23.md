# R23 压力板状态厚度诊断（OB-09）

状态：当前产品路径未复现原报告，16 材质实图补测完成，待周末人工确认；未关闭。本文只记录压力板；两独立库快照、铁路及植物适配不在本任务的改动范围。

## 验收目标与证据边界

编辑器与投影应区分未按下和已按下压力板的静态快照。轻质、重质测重压力板需包括代表性信号强度。不增加红石模拟或按压过渡动画。原生 `CombineBlockPaletteToGeometry` 如果能正确表达该外观，应保留原生路径。

SDK 返回模型名只证明调用成功；调色板状态保留不证明几何体厚度正确；碰撞或选取箱只能辅助判断原生形状，不能代替实图。候选模型尺寸在未取得原生参考前不作为事实写入实现。

## 已完成的离线追踪

2026-10-19，使用当前 BBE 工作区：16 种压力板，每种 16 档状态，共 256 条。状态均为 `redstone_signal: 0..15`。逐条执行 `Document.palette_data()` 与产品 `prepare_palette()`，原材质、aux 及语义状态全部保留；未发现这段路径将按压状态压回默认值。

真实 Python 2.7.13 与 3.13.13 各自重复通过上述 256 条，并执行从 `bridge.py` 精确提取的 `_native_palette` 三个边界函数，确认 SDK 字符串转换后信号仍为整数。另将同一种压力板的 0、1、7、15 档同时放在 x=0、15、16、31，逐类验证完整调色板邻域、增量文档邻域、产品 packed batches：每个解释器 224 个材质／状态保留断言通过，包含跨 16 格分区及邻格重复，未发现状态缓存碰撞。报告保存在 `docs/verification/PRESSURE_PLATE_R23_OFFLINE.json`，包含执行脚本、解释器路径、源码 SHA-256 和实际运行结果；临时脚本位于 `.runtime/pressure_r23_offline.py`。它没有调用游戏 SDK，不能推断 Combine 的实际网格厚度。

方块表来源仍为 NEMC 3.9.0.401155，SHA-256 `6b2d9e961e934a745f5ab30d697cf22fb463fd3792d371a6dd42cb4342062f01`。该结论不能改写成 3.10 实机通过；本轮实机使用配置中的 3.10.0.420447 引擎，运行时版本会另外记录。

## 有界实机诊断

入口：`tools/diagnose_pressure_plate_r23.py`。必须明确传入 `--session`、`--owner`、`--project`，并校验进程身份和实际项目路径；不使用默认 MCP 端口。原生截图调用现有受保护 WGC 工具，不激活窗口。诊断不改真实世界、玩家位置、物品栏或持久建筑库。

覆盖石、橡木、轻质、重质四类压力板的 0、1、15 档：原始调色板与产品预处理各一次，共最多 24 个独立 Combine 名。记录原生反序列化/序列化的 common 与 states，保留完整冻结快照。产品编辑器和投影对三个信号分别生成同位截图，进行 0/15 图像差分，最后恢复草稿、投影参数和相机。

可选 `--raw-actors` 增加四类压力板 0／15 档的 6 倍原生 actor 图像，在已有的 24 个 Combine 名中选取，不额外生成模型。该 actor 不写入产品布局 uniform，便于区分原生 Combine 几何与产品邻域解码。`--raw-actors-only` 则只采集调色板和这组原生 actor，省略产品编辑器／投影。临时客户端实体在结束或异常清理中销毁；放大只用于诊断，不是产品行为或原生世界基准。

独立项目位于 `.runtime/projects/pressure-r23-v1`，仅 behavior/resource 两包及配置，排除 Python 缓存。包文件共 118,870,903 字节、3,665 文件，快照 manifest 逐文件记录大小与 SHA-256。该目录为诊断运行副本，不进入独立库快照或发布包。

压力板独立实例没有启动。为减少 MC 空转，本轮复用 root 的 `ordinary-r23-v2` 集中短时窗口，session `982665a1e5044e1e9bcd84a4dec75d69`，owner `ordinary-r23-v2`。截至此处尚未新增压力板模型，也未更改产品默认渲染路径。

## 首次实图检查（2026-10-19 16:57–16:59）

原始报告冻结在 `.runtime/round-20261019/pressure-native-v1.json`，24 次严格 Combine 全部返回模型名，prepared 调色板反序列化／序列化保留四类的 0／1／15 信号。产品投影三次相机位置、目标和视角相同，支撑石英轮廓稳定。实际打开局部图后，石、橡木、轻质、重质四类均能看到 0 档较厚、1／15 档较薄，产品路径并非总是同厚。编辑器橡木与金板也能看到区别；400% 视图裁掉两端，不将其算成完整四材质编辑器覆盖。

局部对照：`.runtime/round-20261019/pressure-product-world-matrix.png`、`pressure-editor-0-crop.png`、`pressure-editor-15-crop.png`。整图差分包括 HUD、动物和背景变化，仅用于找局部，不作为厚度数值或通过门槛。

原生放大 actor 的四组图片中板体未可见，该对照失效，不能证明原生几何同厚或不同厚，也不能取其差分数值作为产品改善。后续暂不重跑该无效视图，也不因它生成手工代理。

工具已补充可重复的 `--material` 与 `--zoom`（默认 2.5），每批最多四种，文档尺寸／焦点随数量变化。下一窗口计划补足四类完整编辑器，并对剩余十二类作同样 0／1／15 静态快照检查。OB-09 仍保留，等待实际覆盖后再缩小／关闭；尚无原生世界尺寸基准。

首轮恢复核查 `.runtime/round-20261019/pressure-cleanup-v1.json`：临时 actor、蓝图 probe、visual save 标记均已清除；投影 inactive，主实体／preparing 为空，额外投影实体数 0；玩家脚位仍为 `(0.5, -60, 0.5)`，工作台恢复关闭。时段已交回 root，未启动或关闭游戏。

## 四批补充检查的窗口停止记录（2026-10-19，后续 v3 已补齐）

补充检查统一使用产品编辑器与投影路径、缩放 2.5，每批四种材质，分别采集信号 0／1／15。不再启用未能显示板体的原生 actor 对照。每批须先实际打开六张编辑器／投影图，确认四种板体都在画面中、0 与 1／15 的厚度可区分，再进入下一批。最后核查草稿、投影、相机及临时标记恢复。

| 批次 | 原生材质名（省略 `minecraft:`） | 当前状态 |
| --- | --- | --- |
| 1 | `stone_pressure_plate`、`wooden_pressure_plate`、`light_weighted_pressure_plate`、`heavy_weighted_pressure_plate` | 首次补测在窗口预检被阻止，未派发；仍需补齐四材质完整编辑器视图 |
| 2 | `acacia_pressure_plate`、`bamboo_pressure_plate`、`birch_pressure_plate`、`cherry_pressure_plate` | 尚未尝试 |
| 3 | `crimson_pressure_plate`、`dark_oak_pressure_plate`、`jungle_pressure_plate`、`mangrove_pressure_plate` | 尚未尝试 |
| 4 | `pale_oak_pressure_plate`、`polished_blackstone_pressure_plate`、`spruce_pressure_plate`、`warped_pressure_plate` | 尚未尝试 |

首批补测冻结报告为 `.runtime/round-20261019/pressure-product-default-v2.json`。入口返回 `ProtectedWindowError`，原因 `owned_game_has_no_usable_visible_window`；`execute_code_dispatched=false`，`cases=[]`，`completed=false`，没有执行调色板、安装 probe、修改相机或开始截图。它没有产生新的实图或恢复义务，不能计入通过。已将该报告 SHA-256、预检字段和四批待测清单另存至 `docs/verification/PRESSURE_PLATE_R23_PENDING.json`。

root 随后离线检查确认绑定游戏的窗口仍存在，但处于最小化状态且坐标在屏幕外。遵守本轮不恢复、不激活窗口的约定，停止此批及后续三批；压力板任务不再访问 MC，游戏生命周期交回 root。该结果表示运行前置条件未满足，不能解释为产品厚度渲染失败。

该停止时点压力板业务代码和资源改动数为 0，OB-09 关闭数为 0。当时已确认的范围限于首轮四类投影及其中两类编辑器的可见厚度差、256 状态的离线路径保留；四批补测仍全部待测。上述 `PENDING` 文件是这个时点的冻结记录，不作为下面 v3 补测后的当前覆盖状态。

## v3 四批产品实图补测（2026-10-19 18:22–18:46）

用户重新授权继续实测后，root 冷启专属 `pressure-r23-v3` 并授予独占使用；本任务没有自行启动或关闭游戏。绑定 session `d297ef2e76df4b44b36a3c5151a9e72b`，game PID 43604、identity `134368787366111232`，项目 `.runtime/projects/pressure-r23-v3`。保持不激活窗口，四批均使用同一产品诊断工具、缩放 2.5、石英支撑、信号 0／1／15，不使用原生放大 actor。

| 批次／报告名（位于 `.runtime/round-20261019/`） | 材质 | 编辑器实际检查 | 投影实际检查 |
| --- | --- | --- | --- |
| `pressure-product-default-v3.json` | 石、橡木、轻质测重、重质测重 | 四板体完整可见，0 较厚，1／15 较薄 | 四板体完整可见，0 较厚，1／15 较薄 |
| `pressure-product-wood-a-v3.json` | 金合欢、竹、白桦、樱花 | 四板体完整可见，0 较厚，1／15 较薄 | 四板体完整可见，0 较厚，1／15 较薄 |
| `pressure-product-wood-b-v3.json` | 绯红、深色橡木、丛林、红树 | 四板体完整可见，0 较厚，1／15 较薄 | 四板体完整可见，0 较厚，1／15 较薄 |
| `pressure-product-remaining-v3.json` | 苍白橡木、磨制黑石、云杉、诡异 | 四板体完整可见，0 较厚，1／15 较薄 | 四板体完整可见，0 较厚，1／15 较薄 |

全部 24 张原始截图已逐张打开，检查板体顶面及侧缘相对于固定石英支撑的高度差。16 种材质的 1 档与 15 档外形一致，均低于 0 档；没有将整图差分、API 返回成功或侧栏标题作为形状判断。编辑器右侧最后一个支撑块底部会被视口裁切，但压力板本体完整可见。截图侧栏名称和计数可能滞后一份草稿，产品提交记录中的当前文档身份、原生材质 aux 和实际场景作为来源依据。

四份报告均为 `completed=true`、`restored=true`，96 次严格 Combine 调用成功；这些调用状态与实图观察分开记录。四批结束后各做一次独立恢复读回，临时 actor／blueprint／visual 标记均不存在，投影 inactive、主实体与 preparing 为空、额外投影实体数 0，工作台关闭，玩家脚位仍为 `(0.5, -60, 0.5)`。恢复记录为 `pressure-cleanup-{default,wood-a,wood-b,remaining}-v3.json`。第四批恢复后立即释放实例给 root，之后不再访问 MC。

版本化汇总位于 `docs/verification/PRESSURE_PLATE_R23_RUNTIME.json`，含四批完整配方、来源版本、报告／截图／恢复读回 SHA-256、每次产品材质提交记录和实图观察边界。四张 `pressure-product-*-v3-contact.png` 仅用于找到对应原图，原始分辨率图片保留用于复核。四批日志均保留同一条内置 `petSysClient.py` 的 `_ShowPetToast`／`NoneType.show_toast` 异常，不宣称全局错误日志干净。

结论：在本次 3.10.0.420447 引擎、运行时 `1.21.130.0`、当前产品路径与四批固定静态快照中，未复现“压力板始终同厚”。保留现有原生渲染，不新增手工厚度模型。OB-09 调整为“原报告未复现，待周末人工确认”，关闭数仍为 0。尚无真实世界压力板的尺寸参照，不能据本轮声称产品绝对厚度与原生世界逐像素一致；也没有验收红石模拟、按压过渡或所有状态组合。

## 周末集中入口与小型对照

本轮另注册 `test.blocks.pressure_signals`，实际入口现为“测试蓝图 → 方块表 → 压力板 · 信号 0／1／15”。它在同一份16×5×20文档中放置四行石／橡木／轻质／重质压力板，每行三列分别为信号0／1／15，下面各有石英支撑，总计24格。10-20确认原manual分类因UI只接收`test.ordinary.*`前缀导致缺卡，已仅把metadata改为registry；ID／构建器／Document不变，改前后1,228字节canonical数据SHA均为`e5f037eee634a6828e579f6ad31decfe2bcedb33c4958670a7ab9fdcc4878df8`。真实页面函数的全471卡可达性回归、蓝图18项及普通目录4项通过，真实Python2.7.13编译和构造通过。这个一行修复未热拷贝进当前珊瑚冷副本，周五最终候选须补实际冷启入口检查。

新模块结构 review 命中 1 文件、0 发现；与注册器一起检查为 2 文件，注册器保留既有 `build` 分发函数较长和 `Fixture.put` 参数较多两项提示。本轮仅新增一个分发分支，没有扩大重构。这个集中布局尚需冷启实图核对，不能用之前四批不同布局的图冒充它已通过。

四批 24 张原始图的直接像素裁切已整理为 [小型对照包](evidence/pressure-plate-r23/README.md)，4 张 PNG 合计约 3.09 MiB，每个拼入矩形逐像素核对来源，包含固定坐标、来源报告和图像 SHA。这不新增实测记录或问题关闭数。周末操作见[本轮普通方块复核页](acceptance/2026-10-24-r23-candidates.md)。
