# 开发记录与待办清单复核

复核日期：2026-10-09。复核前主线为 `5827d86`，生产代码仍为 `7bd5495`。本记录解释 [待实现清单](IMPLEMENTATION_GAPS.md) 第二轮更新的来源，保留历史结论与后续修复之间的关系；不替代各报告的原始验证说明。

## 范围与判定方式

- 检索本地所有 Git 引用可达的 **152 个提交**，其中主线到 `5827d86` 共 **121 个**；核对 `main`、`dev`、`realm`、`uncomplete` 及已有远端跟踪引用。数量为本次文档提交前的快照，没有把同一修复在其他分支上的不同哈希算成不同功能。
- 核对当前 `docs/` 中除待办清单外的 **33 份文档**，以及根说明、框架修改说明、旧调试工具和冻结特效的补充文档。历史 Markdown 路径还发现 **4 份主线没有的实验记录**，以及迁移前的 `behavior_pack/HelloScript/pyreact/UPSTREAM.md`；后者属于同一框架记录的旧路径。
- 按“记录提出问题→后续提交／报告→当前代码”确认状态。旧测试通过只能证明原记录的版本和场景；回调注入、PC F11、离线 GPU 测试、真实安卓和普通游戏实机分别保留证据边界。
- 本轮核对仓库记录及其中引用的验证结论，没有重新打开游戏、重放 `.runtime/` 全部视频／截图或运行历史世界写入工具。仓库之外未提供的聊天、审核后台和未拉取提交不在本次证据范围；没有将“未找到记录”写成“从未做过”。

## 对待办的实际调整

| 调整 | 复核结论 |
| --- | --- |
| 新增 F13 | 主线仍有透明建筑投影挡住后期星点的问题。`uncomplete` 的保护层方案在普通世界失败，不能关闭此项。 |
| 新增 F14 | `dev` 的 RenderDragon 工作只完成离线转换覆盖和安装资源实验，普通附加包接入及画面一致性未交付。单列分支目标，不算主线既有支持。 |
| 新增 F15 | 分享／分页存档中断或索引失败后的未引用页没有完整回收；更小的后续保存也可能留下尾页，内存替身已复现。 |
| 新增 V09 | 官方 `GetChosen` 只保证第一人称准确，第三人称触屏测绘需专门验收并确定支持边界。 |
| 更正 V01 | 9 月 26 日已有 Android 真机安全区及双指修复与验证，不能继续写“移动端只有 PC／模拟证据”；剩余的是更多设备、平台和完整流程。 |
| 补充 F02 | 记录 16 项白名单的初始提交、分帧复制、冰的遗漏及状态表接入后未更新的事实；区分明确动机与名单来源推断。 |
| 补充 F08、F11 | 旧名称／aux 存在无法自动辨别的版本歧义；世界事务日志只在内存，未提供崩溃后恢复。 |
| 澄清 F12 | 透明排序曾按用户要求为性能让步；保留兼容边界与验收，不预设必须上通用逐三角形排序。 |
| 补充 V06、V07 | 覆盖首次 UI／参数创建、同步调用停顿，以及正式面板滚动到底后连续选材的完整路径；后续滚动条修复已认可。 |

更新后为 **15 项 F、9 项 V、7 项 X**。原有 F01–F11 的数据和编辑缺口没有找到完成记录；X01–X07 仍属于需单独确定范围的扩展能力。

## 当前开发文档逐项核对

“已实现”指有对应实现和记录，不表示所有平台已验收；表中的编号指向待办清单。

| 文档 | 当前结论／待办归属 |
| --- | --- |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 核对初始实现、阶段 1–53、后续投影／状态表／滚动条记录。旧大尺寸、局部视图和世界撤销已被后续产品决定替代；方向变换仍受限（F02），版本歧义见 F08，透明取舍见 F12，历史输入和性能尾项见 V04–V07。阶段 54 以后还须结合专项报告。 |
| [CONVERSATION_HANDOFF.md](CONVERSATION_HANDOFF.md) | 交接中的最新 HUD／P 键负向测试仍有前台焦点中断（V07）；旧手机待测段落应结合 9 月 26 日真机记录阅读。 |
| [MODERN_PROJECTION.md](MODERN_PROJECTION.md) | 当前使用边界与 F01–F12、V03–V04、X01–X07 对照；同步本次新增限制的入口。 |
| [CONTROLS_PERFORMANCE.md](CONTROLS_PERFORMANCE.md) | 页面复用、滑条和控件反馈已有实现；初次资源加载和提交耗时不等于全部操作稳定，归 V06。 |
| [VIEWPORT_PERFORMANCE.md](VIEWPORT_PERFORMANCE.md) | 调试回执解析热点和连续点击已有修复；阶段 27／30 的单模型／局部视图是历史方案，不能重新列成待实现；当前上传及长期资源验收归 V06。 |
| [EDITOR_PERFORMANCE_32.md](EDITOR_PERFORMANCE_32.md) | 大范围编辑优化已实现；最大模型 60–80 ms 原生短按失败没有原用例闭环，保留 V05。其 `SetLayer` 主路径已被阶段 69 替代，须当前复测。 |
| [INPUT_FONT_BATCHING.md](INPUT_FONT_BATCHING.md) | 整数字号、原生占位结构和常规焦点对比度已有后续修复；480 字符末尾文字／光标裁剪仍留失败记录，归 V04。 |
| [LARGE_REGIONS.md](LARGE_REGIONS.md) | 分块数据、历史、分页和流式传输已实现；原 256×384×256 不是当前容量承诺。日志无持久化补入 F11，删除空配置文件的 SDK 边界与 F15 区分；性能和世界压力归 V03、V06。 |
| [PYREACT_UPSTREAM.md](PYREACT_UPSTREAM.md) | 上游合入、原生名称 `str` 修复和滚动条根包装修复已实现；禁止恢复内部 `gui` 拦截／错误滚动路径。长文本和短按问题没有因框架合入自动关闭。 |
| [ORBIT_PERFORMANCE_54.md](ORBIT_PERFORMANCE_54.md) | 相机成本优化已有证据；该轮完整交互套件未完成，后续阶段 55／69 提供更多覆盖。保留具体 V05／V07，不将整个旋转功能列为未完成。 |
| [FONT_ATLASES.md](FONT_ATLASES.md) | 完整字形图集、纹理合并和缺字回退已实现；其待前台验收已由阶段 55 补齐。 |
| [FOREGROUND_ACCEPTANCE_55.md](FOREGROUND_ACCEPTANCE_55.md) | 原地“取消→重试”及点击穿透已有修复和 PC／F11 验证。该轮分享使用内存剪贴板，不能扩大为手机系统剪贴板证据（V01）。 |
| [MATERIAL_AUX_AND_OUTLINES_56.md](MATERIAL_AUX_AND_OUTLINES_56.md) | aux 编辑、选区不随视线裁切和局部材质通知已实现；常用栏的真实点击在独立卡片完成，正式面板完整路径归 V07。 |
| [MATERIAL_BADGES_57.md](MATERIAL_BADGES_57.md) | 已缩小常用栏角标、移除目录角标；早期石英 aux 示例不能覆盖后来权威表的解释规则（F02、F08）。 |
| [SHARING_ASSESSMENT.md](SHARING_ASSESSMENT.md) | 前半段 MP1 为评估，后续 MP2／MPS2 与 256／512／1024 分段已交付；分页残留归 F15，同步调用与手机传输边界归 V06、V01。 |
| [PROJECTION_VISIBILITY_63.md](PROJECTION_VISIBILITY_63.md) | 转向消失、线宽和阴影已有修复；后来占用报告进一步处理玩家与离体相机加载区域，不重复列为缺失。 |
| [MATERIAL_NAMES_64.md](MATERIAL_NAMES_64.md) | 中文名称查询与旧别名名称解析已实现，不意味着材料已换算为备料物品数量（F09）。 |
| [BIOME_TINT_65.md](BIOME_TINT_65.md) | 群系预设、当前位置匹配、草侧面／树叶／草蕨代理已有后续修复；逐位置群系仍是 X02，双层和 NBT 仍是 F01、F03。 |
| [SCENE_SETTINGS_66.md](SCENE_SETTINGS_66.md) | 场景设置分组、图标和选择状态已有实现，没有单独未关闭事项。 |
| [PERFORMANCE_67.md](PERFORMANCE_67.md) | 布局／掩码快路径保留；内部输入路由合并已在阶段 68 撤回，不能沿用包含它的性能数字。首次参数和提交峰值归 V06。 |
| [WHITELIST_68.md](WHITELIST_68.md) | 此处是 **Python 模块白名单**，与 F02 的方块变换白名单不同。违规模块替换已完成；分帧层级队列被阶段 69 删除，不应恢复。来源及发布审核归 V08。 |
| [ORBIT_REGRESSION_69.md](ORBIT_REGRESSION_69.md) | 固定层级和共享深度已修复旋转棋盘错位及触屏跟随问题；不能据此认定通用透明排序完成（F12）或旧短按压力已通过（V05）。 |
| [VIEWPORT_CLIPPING_70.md](VIEWPORT_CLIPPING_70.md) | 预览裁剪原点补偿、双缓冲对齐和线宽裁剪已实现；后续 `631f59f` 继续修复网格深度及描边，不重复列为未实现。 |
| [WORLD_TOOLS_71.md](WORLD_TOOLS_71.md) | 测绘器／终端、导入存库、满库重试及服务端身份限制已实现；读取只保留当前单层数据（F01、F03），真实多人／手机完整流程仍见 V01–V02、V07。 |
| [SURVEY_STARDUST_72.md](SURVEY_STARDUST_72.md) | 点击确认和客户端测绘效果已实现；早期星点载体已被后续方案替代。`GetChosen` 第一人称限制仍适用，补 V09。 |
| [SURVEY_REFERENCE_EFFECTS.md](SURVEY_REFERENCE_EFFECTS.md) | 星穹效果重构已有实现；无真实场景颜色采样的折射近似是既定视觉边界，不擅自增加真实折射需求。手机／多人画面归 V01–V02。 |
| [OUTLINE_EFFECTS_ACCEPTANCE.md](OUTLINE_EFFECTS_ACCEPTANCE.md) | 外框、晶体、星点、近裁剪及定向背景回归已有记录；后续天空／半透明背景修复见 `5376a30`，投影与后期星点的剩余合成问题归 F13。 |
| [ASTRAL_STAFFS_AND_MOBILE.md](ASTRAL_STAFFS_AND_MOBILE.md) | 法杖、移动入口、安全区及返回代码已实现；其“未测手机”是当时边界，后续安卓安全区和双指已验证。机审未重提归 V08。 |
| [MOBILE_DEBUGGING.md](MOBILE_DEBUGGING.md) | **首轮遗漏的完成证据：** 9 月 26 日 Android 真机安全区对齐、双指张合、释放状态与用户确认；修改 V01，保留其未测机型／横竖屏／iOS 边界。 |
| [MOBILE_SHADER_PRECISION.md](MOBILE_SHADER_PRECISION.md) | `TIME` 及随机链精度修复已提交；数值模拟不能代替手机 GPU 验证，最新特效仍归 V01。早期手机 UI 实测不覆盖这些 shader。 |
| [PROJECTION_OCCUPANCY.md](PROJECTION_OCCUPANCY.md) | 占用消隐、未知区块保护、批读、单实体双缓冲和高处可见性已实现；不能恢复九格限制或把 256 提示队列误写成容量。完整格进度归 F10，多人和就绪／资源验收归 V02、V06。 |
| [PARTICLE_TRANSPORT.md](PARTICLE_TRANSPORT.md) | 编码插值、移动拖尾和选点形成修复已交付；末节明确未解决透明投影挡星点，补 F13。`SetFootPos`／业务入口驱动录像不是物理键鼠端到端验证。 |
| [MCDK_ASSISTANT_UPSTREAM.md](MCDK_ASSISTANT_UPSTREAM.md) | 工具及资料库更新已经完成；资料版本为 3.10 Beta，而多数实机是 3.9，接口存在不能自动视为目标客户端支持。工具能力演示不算产品待办。 |

## 补充文档与历史分支

| 来源 | 核对结果 |
| --- | --- |
| [README](../README.md)、[第三方说明](../THIRD_PARTY_NOTICES.md) | README 的功能范围和限制与清单交叉核对；许可归属文件不据此产生新功能需求。 |
| [框架修改说明](../behavior_pack/modern_projection/pyreact/UPSTREAM.md) | 印证安卓真机修复、公开 SDK 边界及共享深度替换。旧 `HelloScript/pyreact/UPSTREAM.md` 随 `d784a63` 迁移，不是另一个未完成框架。 |
| [旧调试工具](../tools/pyreact_legacy/README.md) | 保留回归兼容工具，当前默认通道已迁移到 MCDK；不把旧工具仍存在当作迁移未完成。 |
| [冻结特效 README](../extras/astral_survey_v1/README.md)、[参考效果](../extras/astral_survey_v1/REFERENCE_EFFECTS.md) | 是可迁移的旧版效果归档，已补高精度 shader；打包工具已存在。不包含编辑器业务属于该归档范围，移植后验证要求不算主编辑器新缺口。 |
| `dev`：[RENDERDRAGON_MIGRATION.md](https://github.com/Happy2018new/better-building-editor/blob/bc376f15c2b8b52a0191b3efb9900e6055d073e6/docs/RENDERDRAGON_MIGRATION.md) | 离线矩阵完成，普通附加包运行时接入和视觉验收未完成，归 F14。 |
| `dev`：[RENDERDRAGON_PILOT.md](https://github.com/Happy2018new/better-building-editor/blob/bc376f15c2b8b52a0191b3efb9900e6055d073e6/docs/RENDERDRAGON_PILOT.md) | 替换游戏安装资源出现测试颜色／星空，不证明普通附加包可加载；早期伪 UV／法线等试点不算视觉等价。 |
| `dev`：[tools/renderdragon/README.md](https://github.com/Happy2018new/better-building-editor/blob/bc376f15c2b8b52a0191b3efb9900e6055d073e6/tools/renderdragon/README.md) | 离线工具生成编译产物；运行时与视觉标志仍为 false。和上两条属于同一未交付目标，不重复计三项。 |
| `uncomplete`：[PROJECTION_COMPOSITING.md](https://github.com/Happy2018new/better-building-editor/blob/ecd9da1a4dad99a24eb825d40e080a1b8da92c7a/docs/PROJECTION_COMPOSITING.md) | 文首明确“未通过最终实机验收，不应合并为修复”；保留失败原因和未来验收组合，归 F13，不移入主线代码。 |
| `realm` 与重复修复提交 | 当前与主线的行为包／资源包／文档比较只有两份 manifest 的 UUID 差异；没有独立的新增功能缺口。其他分支上的重复修复按实际内容核对。 |

## 关键关闭证据与仍需复测的区别

- **常规光标**：阶段 17–21 的失败不能单独作为现状；阶段 25 的中性灰焦点底色已经通过。保留的是超长文本末尾裁剪（V04）。
- **触屏拖动**：阶段 36 的模式模拟、阶段 37 的中断记录由阶段 38 的真实 F11 持续拖动验证补充；双指／安全区又有 9 月 26 日安卓真机修复（`1b78abb`）。它们没有覆盖所有手机或 iOS。
- **滚动条**：阶段 56／57 的临时材质卡片不能证明正式面板路径；`212985e` 已修复 SDK 包装路径并实测 PC／F11 拖动。剩余 V07 要补正式面板的连贯操作，不能重新写“滚动条未实现”。
- **旋转时显示错位**：阶段 68 的分帧层级队列在 `0f61d3e` 删除；阶段 69 的连续画面验证关闭对应问题。方块内容本身的旋转状态变换（F02）是另一条链路。
- **草木及雪原外观**：`da8d37a`、`0ff09ab`、`6cffdc7` 已补群系代理、模型对齐和雪原回归；不能因此认为含雪复合格的背景层（F01）或整栋群系分布（X02）已经保存。
- **粒子**：`5376a30` 修复天空／半透明地形背景下的发光，`7bd5495` 修复动态参数插值。透明建筑投影挡住后期星点仍由主线报告明确保留；`ecd9da1` 的 52 项离线 GPU 断言被最终游戏场景否决。
- **性能**：已经撤回的内部 `gui` 优化、旧 256×384×256 上限、局部视图以及单次平均 FPS 不能当作当前承诺。最新架构需按 V05–V06 的具体压力用例复测。

## 本轮新增核验

官方资料检索 `api GetChosen` 返回“目前只有在第一人称视角才能准确获取”；当前触屏测绘仍使用它。这里确认接口边界，不宣称本轮已在游戏复现第三人称误选。

F15 使用 `tests/test_sharing.py` 的内存 Bridge 与正式 `Sharing`／`archive.save_steps`：索引写入失败留下 1 个未引用页；保存生成器在写完 2 页后关闭，随后同编号保存 1 页内容，仍残留第 2 页。检查旧库为空、失败状态和 I/O 释放均符合当前实现；没有操作真实建筑库。此复现证明清理缺口，不意味着旧草稿或有效索引已经损坏。

本轮修改均为文档，完成 Markdown 链接、编号／数量、报告覆盖及差异空白检查。首轮 `5827d86` 的 456 项离线测试（455 通过、1 个外部方块表来源检查跳过）仍是最近一次完整套件结果，本轮未重跑或新增实机结果。
