# 新对话交接：现代化投影建筑编辑器

## 2026-10-14 14:05 模型切换暂停点（优先于下方历史记录）

用户要求立即保存上下文、终止主会话及所有子代理，切换模型后再继续。MC允许保留。本轮仍为第十五轮，原定17:30截止、不休眠；本次暂停不视为全部完成。分支`dev`，不推送、不合入`main`。最新授权最多3个活动子代理、5个活动MC，恢复前核查时间和实例身份。

- **水的方向已通过，透明度未通过。** `docs/evidence/water-production-nemc310-r15-v1/review/`包含editor/full/missing × 四向及下落共15项生产资源方向证据，时间倒放全部拒绝。3.10原生时钟为正向，不迁入3.9负时钟修补。主会话复核近景发现含水栅栏与后方金块几乎不可见；专项确认原透明度测试被不同动画相位误导，水下本体与无本体控制的RGB几乎相同。旧报告`transparency=true`只保留为历史工具输出，**不得宣称透明度完成**。下一步固定时钟或同帧对照，检查混合、深度、绘制顺序和重复表面；不要通过降低像素差门槛放行。
- **首批原生路由已完成有限生产接入。** exact 3.10版本＋真实完整payload门控；普通／铜／末影单箱仅world走model_local，editor保留静态代理以避开已证实的共享深度异常；花盆走context。床保持代理。主会话已看最终69/71/74/76画面，96项相关测试通过；专项207项测试记录见qualification。版本、payload、scene限制和缓存身份均独立记录。
- **旗帜仍为候选。** raised world full/occupied/restored已见正确；context出现重复漂移，editor布面被支撑误遮挡，不能生产放行。后续在render-only native_actor适配中由当前material states刷新bannerDirection，不能把变换后的合法旗帜静默排除。头颅新真实物品放置样本已捕获，95组截图尚未人工查看。
- **炼药锅未接入共享生产链。** cauldron_profile/render_plan/preview/projection与专用资源、测试均在工作区；稳定接口由专项交接记录。root尚未修改Session/Scene/bridge/world来接入它。六档高度实测接近5/16、7/16、9/16、11/16、13/16、15/16，内缩1/8；CustomColor及药水主采样有效。普通锅水与药水纹理/透明度不同，不能拿白色药水对照推导出错误水色。`candidate_profile`数据生成与三路径验收未完成，不能启用默认。
- **原生广泛采样不是全通过。** r15-solo-runtime已查看batch-v2/v3、fire-v2、lantern-v3及banners-v4；有56个NBT根ID数据样本，缺MovingBlock真实运动源。教育chemical_heat/compound_creator出现泥土样回退；plants/heads旧夹具存在额外层水污染，负向结论无效。新版heads见专项交接。
- 最近root相关验证：96项单测通过，native_render_profile结构审查files=1/findings=0。不要重跑整个库只为制造验证数量。五个用户p0_palette探针不得修改或提交。

专项恢复入口：`docs/evidence/native-render-profile-r15/HANDOFF-native-resume.md`、水`review/`的纠正说明与handoff、`docs/evidence/cauldron-surface-r15/`的handoff。原始水证据约538MB留本地，提交仅约16MB的review包；干净检出没有所有原始帧，文档需明确可复核范围。

最近有效实例为clean owner `clean-nemc310-runtime-audit-r15` / session `e150444343dd46f0a0f791b165872648` / PID13804，以及native owner `native-render310-r15` / session `60695c6595894ffcbe4c9fca5e36be0e` / PID47968。未受管3.9 PID40452保留。water PID35392已按身份正常关闭；新water/cauldron是否启动须以专项最后交接和instances status为准。native实例仍有head临时区域与raw geometry，恢复journal已保存。不得跨agent操作clean相机；所有测试继续遵守不主动前台化、不resize、不桌面输入，用户自行前台观察允许继续。

上午18–31小时（风险31–46小时）的估计仍是最近一次正式估计，不因流向通过直接减去墙钟；透明度新增确认缺陷、普通锅水待定、通用物品及特殊表面仍需工作。模型切换后根据实际关闭项更新。

暂停最终回报：三个活动子代理均已保存交接并终止，无待执行exec。水未启动新实例；炼药锅产品实例已启动一次，owner `cauldron-product310-r15`、session `bf6a4f16278246a3b549448e42e68d21`、project `D:/bbe-r15-cauldron-production`、game PID32868／MCDK34124；就绪等待超时但日志显示14:00:20后已入世界，恢复先检查身份/IPC，禁止盲目重启增加实例。clean保留锁定相机及恢复journal。炼药锅`cauldron_native_data.py`尚未生成，`candidate_profile()`当前不可调用；`water_colors={}`，十个补采药水形态因约0.000007度roll浮点差被分析器拒绝，需量化合理相机容差后复析，不能接受此前看向天空的无效图。

已创建本地原生路由检查点`39cb31f6 fix: scope native block actor rendering to verified routes`。其他检查点见本轮最终回复和git log。炼药锅及后续原生/时钟诊断的未完成源码、资源和大体积原始证据保留在工作区；不要reset/clean，也不要将五个用户探针一起stage。水透明度最终纠正文件为`review/review-assessment.json`（overall=false）和`review/HANDOFF_TRANSPARENCY.md`，优先于未改写的原始summary。

2026-10-14第十五轮上午最新入口：先看[统一待办顶部](IMPLEMENTATION_GAPS.md)和[外观兼容技术表](NEMC310_RENDER_COMPATIBILITY_INVENTORY.md)。用户已恢复最多3个活动子代理、最多5个活动MC；12:00前修订技术MD与估时，继续开发至17:30，不自动休眠。此前“独立开发、禁止子代理”、最多10代理和07:00／08:00休眠均为被后续指令替代的历史安排。一次性任务 `Codex-BetterBuildingEditor-R15-Hibernate-20261014` 已Disabled；02:00–08:00没有产生工作增量。

开发在 `dev`，目标NEMC `3.10.0.420447`／MCBE `1.21.130.0`。`main`、`render-dragon`和五个用户探针保持原状；本轮不更新3.9方块表或旋转／镜像转换表。粒子与刷怪笼内部生物排除；植物固定居中是设计要求。世界水继续自定义，世界岩浆可走官方，锅内水／岩浆／药水／染色液体／细雪仍要独立overlay。三种传送门均在范围内，末地门／折跃门仍被官方Combine排除。

离线范围为1340名／15,858状态、57个NBT根ID／155名；动画资源候选49名（普通37、NBT12）。`NATIVE`只表示官方本体或实测字段路线，必须另记干净投影像素和editor／full／missing资格。技术MD已按A–H、S、X共用方案分类，不为每个ID分别写渲染器。最新剩余估计为18–31小时有效墙钟，风险31–46小时，按最多3代理重算：共同前置2–4小时＋最长并行专项12–20小时＋最终集成4–7小时；不是从旧估计减去已过去时间。假设与分项只在[技术附件](NEMC310_RENDER_COMPATIBILITY_INVENTORY.md#本轮修订的剩余工期评估)维护，状态只在统一待办维护；17:30前不保证全部关闭。

上午已纠正的证据口径：

- `nemc-nbt-r15/runtime-family-results.json`是第十四轮归档复析，28个工作组已完整索引57根ID；不是全族新实测。已合入repair的真实旗帜`bs/Color 1`、`ts/Color 14`，菜单遮挡的旧overview不新增像素通过。
- 旧动态gallery只覆盖33/37普通候选，漏水／流水／岩浆／流动岩浆；额外big_dripleaf／conduit／end_portal／end_gateway不是补齐项，12个NBT动画名称也未在gallery中。字节相同且比例过小的旧图保持`pixel_acceptance=false`。
- 炼药锅60行真实交互与21个状态已采集：aux0清水瓶产生fill2／4／6且PotionId=-1，aux1..4保持空锅，aux5..46返回药水ID；CustomColor两值精确读回只证明存储。专用液面六档、颜色、透明度与三路径仍待。
- 物品r15有普通／附魔／空框与真实原版展示框的连续帧诊断，summary已补实际capture路径映射；sprite资源只有diamond_sword，框体尺度／轮廓、通用物品、其他内容家族、生命周期和生产资格仍未关闭。
- `native_render_profile`候选已接入palette、静态代理选择、actor坐标、三条显示路径与缓存身份，168项相关离线测试通过；仅显式允许有效payload的普通／铜／末影单箱、床、花盆。Session默认None，model_local/context选择须实机决定，生产原生路线尚未启用；不靠版本字符串放行。
- 3.10独立无纹理`clock310-v2`已测得时钟+1：13帧／11变化间隔、红通道31.596每秒（预期31.875）、区域12,584像素稳定，完整捕获／恢复／源码不变通过。3.9旧-1时钟和局部反向水纹证据不能转用；3.10水产品帧序／UV方向与三路径仍待。持久原件在[water-clock-nemc310-r15-v1](evidence/water-clock-nemc310-r15-v1/clock310-v2.json)，相对路径artifact-index绑定13帧、源码与SHA256。

11:25主会话已查看新干净3.10近景：独立fire-v2／lantern-v3真实世界与Combine同屏可见，火有明显帧差、静态石块稳定；随后 `docs/evidence/r15-solo-runtime/batch-v2/`已见实际告示牌文字、多个NBT本体和下界门紫色表面。该批真实世界参考前排却为空，旗帜NBT为Base4／两图案而palette为Base0／零图案，需修复客户端同步夹具；本轮未见书／光束／剑／架／头／moving_block不能判官方不支持。`plants`因投影石块不可见停止。旧负坐标试验同样归夹具无效。已查看结果并入[逐组近景表](NEMC310_RENDER_COMPATIBILITY_INVENTORY.md#1125新增近景观察与夹具限制)，所有未查看PNG、API成功和actor字段均不新增像素通过；生产三路径及`pixel_acceptance=false`保持。

11:40追加观察：八种铜灯笼、海晶石形状和幽匿／感测器本体已查看可见，但时间裁剪未查看，不计动画通过。同一世界缺失ROI用原版`/setblock dirt`立即可见，主会话正验证`SetBlockNew(updateNeighbors=False)`导致同步未刷新的可能性；旗帜重跑与源码快照核对完成前不作新的不支持判定。

11:50旗帜v4复验已查看：真实`PlayerUseItemToPos`带item userData放置后，palette与NBT一致（Base4、bs1／ts14两层），立式／墙挂投影彩色图案清楚可见；此前直接写NBT的palette未刷新。三帧未见飘动，不授予动画资格。真实世界石块已可见但旗帜仍缺，保持有限投影正例；batch-v3补采中，未查看内容不预先关闭。原生profile专项已看model_local full／恢复图，五名称对齐；context对照箱／床错位，editor原生主体被支座错误遮挡，missing床半格仍待核。候选在修复，默认None保持，不宣称已上线。

最近可复用受管实例为session `C:/Users/Happy2018new/.pyreact-debug/instances/e150444343dd46f0a0f791b165872648/session.json`，owner `clean-nemc310-runtime-audit-r15`，project `D:/bbe-r15-dynamic-runtime/.runtime/nemc-clean-310`，最近PID13804、MCDK44480、port53471；恢复时先核验身份和IPC，不按旧PID直接操作。PID40452是未受管3.9实例，保留。没有窗口／线程／句柄的历史进程记录不能按条数当作活动游戏。测试器不主动前台化、resize或桌面输入；用户手动前台观察时继续，按 `MCDEV_ALLOW_USER_FOREGROUND=1`记录实际授权与捕获元数据。

上午模型切换曾中断10个Astra子代理，不直接唤醒旧代理；之后按用户当前模型与3代理上限重新分工。已有离线六模块25项、render/NBT盘点与100来源provenance通过不代表新像素通过。下方保留9月项目背景和历史验收，只能作为来源，不能当作本轮运行身份或本轮最终资格。

更新于 2026-09-25，工作区 `D:/Happy2018newの个人文件/GitHub/better-building-editor`，本轮以 `1af6a65` 的交接及 `998218a` 的功能为基线。此文档用于把当前项目和近期对话带入新任务；具体行为以当前源码为准。`docs/` 中的阶段报告保留当时的实现与测试记录，部分旧措辞已过期。

## 待办事项统一入口（2026-10-09）

全部待办、优先级、验收标准及状态统一维护在 [功能完整性审计与待实现清单](IMPLEMENTATION_GAPS.md)。该文件同时收录源码审计、开发记录逐项复核、历史关闭证据和未合并实验的结论；后续任务直接更新其中的 F／V／X 编号，本交接文档不再另列待办摘要。

下文保留各阶段交接记录。判断某项问题是否仍待处理时，以统一清单及其后续证据为准，避免将历史失败、已撤回实验或局部测试结果误当成当前状态。

## 最新增量：移除逐格遮罩、批量更新与高处可见性（2026-09-28）

用户否决九格遮罩，要求性能优先、单实体、实机 debug，以及 64×128×64 大建筑。当前已删除逐格 shader 索引、片元所属格计算与 discard，Python 差量集合没有九格上限；shader 只负责同一实体上两份完整模型的缓冲选择和透明度。详见 [实现、数据及限制](PROJECTION_OCCUPANCY.md)。

自动更新缓存每个 16³ 块的可见材质索引，只改脏格后拼接完整调色板；大范围使用客户端批量调色板巡检，初始化增加均匀行快路径。保留交互提示、远处巡检和构建期间反向变更，不新增服务端占位消息。原生查询对未加载区块也可能返回空气，现使用客户端区块加载/卸载事件判断可信性，未知保持最后状态。快速提示队列 256 项不是变化容量。

一个实体常驻两个完整资源，后台准备新缓冲时保留旧画面。实机发现满体积网格在原生 Combine 返回后仍延迟生成，旧 150 ms 等待在 249 帧中出现 37 帧消失；现采用体积/调用时间决定的等待，524,288 格至少 1.25 秒。最终 224 张大建筑采样、5 次重建均保持检测区域显示，小模型 119+120 张也通过。等待不是 GPU 栅栏，截图也未覆盖每个 GPU 帧。

玩家地面、高处离体相机不可见的问题已通过将模型实体锚定玩家加载区域、几何 offset 保持世界位置修复。高度 0/+20/+127，过滤开/关六组均通过，玩家不移动。满尺寸实心 524,288 格初始准备由优化前 115.8 秒降至 11.20 秒；66,852 格墙/楼板由 41.2 秒降至 12.17 秒。64 格批量变化各合并为 2 次更新，约 3.49/3.56 秒收敛；无提示远端变化约 4.26/4.15 秒。均是本机墙钟观测，包含分帧调度与宿主查询，不能解读为 GPU 或整帧耗时。

最终单元测试 408 项中 407 通过、1 跳过；85 个运行时文件白名单无违规；7 模块 review 解析通过，保留长函数及既有相机防御 advisory。冷启动 24 项实机功能、六组高度、两种满尺寸性能和三组连续画面通过。证据在 .runtime/projection_batch_checks.json、projection_height_checks.json、projection_full_volume_performance.json、projection_shader_checks.json、projection_large_visual_checks.json 及配套图像。修改随 Git 提交保存，未生成发布包；手机、真实双客户端/命令方块和长时多人压力未测试。宿主 Pillow/NumPy 不进入游戏运行时。

本轮专用实例 06dd2cac6a5745359910432b5bfc8f15（owner: occupancy-batch）已恢复夹具并停止，后续验证请创建新实例。

## 既有增量：法杖与手机适配

完整实现和证据见 `ASTRAL_STAFFS_AND_MOBILE.md`，手机连接资料见 `MOBILE_DEBUGGING.md`。本轮修正机审报告的缓存初始化/tuple 推断、安全区排版及全屏底色、JSON UI/安卓返回路由、触控移出误释放；新增非吞噬多触点入口。两种物品升级为带视差星空宝石和悬浮晶簇的三维法杖，手持时有六类 GPU 魔法效果。点击动画已经再次修改：**每颗黄色晶体从自己的中心生长，完成后进入常驻运动**，下文旧的“碎片聚拢”描述仅代表 `b8e0922` 历史版本。

该阶段本地验证为 **323 项单元测试通过，84 运行时文件白名单无违规，并在游戏 Python 2 中编译通过**。真实 Esc 和 F11 单指拖动通过；注入双触点缩放/释放及返回去重通过，安全矩形 `(48,13,408,235)` 和全屏背景通过原生尺寸/截图核验。该阶段尚未完成安卓硬件验证，**后续 9 月 26 日已补安全区和双指专项**，见 `MOBILE_DEBUGGING.md`；系统返回、其他机型及最新手机 shader 等仍待覆盖。尚未重新提交网易机审。

最后冷启动实例 owner 为 `astral-review`，session 为 `C:/Users/Happy2018new/.pyreact-debug/instances/68d93463687e49ad8d3f89866916ac24/session.json`，使用前先查 status。`fragments-final` 和中间 `astral-staff-final` 已停止。不要在需要仅重载新 shader 时再次调用整套资源热重载；本机开发客户端完整重载会触发原版 PBR shader 错误及执行通道失效，单独的公开 `ReloadOneShader` 已成功。

## 项目与约束

- 项目是网易 Minecraft 基岩版 ModSDK 建筑编辑器，行为包在 `behavior_pack/`，资源包在 `resource_pack/`。游戏内 Python 为 2.7；宿主测试和工具为 Python 3。
- 工作台通过可合成的投影终端打开（右键或手持 HUD 按钮），已移除 P 键入口；另一件可合成物品是投影测绘器。工作台提供三维编辑、建筑库、世界投影、材料目录和字符串分享/导入。
- 文档最大尺寸为 **64×128×64**，编辑视图始终显示整栋建筑，底层以 **16³** 分块维护原生模型；不要重新做成玩家必须切换分块的界面，也不要为相机旋转重建方块模型。
- 触屏模式跟随游戏原生输入状态；Windows 开发客户端用 **F11** 模拟切换，**不是 F12**。PC 与触屏的点击/拖动语义不同，应分别验证。Windows F11 模拟不能等同安卓真机。
- **只有 `behavior_pack/` 下的 Python 受网易模块白名单约束**；`tools/` 不受该要求限制。运行 `python tools/audit_runtime_imports.py` 检查。只用本地客户端实体绘制选区、投影与特效，不让其他玩家看见；世界写入和测绘导入由服务端按实际玩家身份鉴权。
- 本机建筑库经客户端配置保存，不是服务端多人共享库。世界测绘导入新建库条目并处理重名/满库，不覆盖当前草稿或已有配置。分享码使用压缩、Base64 和校验；它不是可信权限凭证。
- 项目 UI 使用内置的 Pyreact-MC 和原生 JsonUI，已同步过 Pyreact upstream 并保留本地兼容补丁。先看 `.agents/skills/pyreact-ui-building/SKILL.md`；实机调试先看 `.agents/skills/pyreact-debugging/SKILL.md`。

## 当前视觉与交互约定

- 建筑世界投影外框默认 **炫彩**，玩家也可选 **金色** 或 **星空**；每种风格各自保存流速、亮度、线宽等参数，金色/星空还支持环绕速度和晶体密度。三种主框默认实体棱线宽一致，正常世界前景仍应遮挡后方棱线。
- 测绘器的两点世界选区**固定金色**，不随投影外框设置改变。框线带 GPU 驱动的晶体、星芒与拖尾；两个选点有入场动画和常驻效果。点击原生方块面经过服务端验证后传回，不应随相机移动而改变。
- 测绘器选区已移除白色逐格覆盖和白色面，只保留金色框线与特效。主框线有细亮芯和流动高光；环绕光点、星芒、拖尾使用独立叠加发光材质，不写深度但保留深度测试，晶体沿用原来的透明深度材质。环绕粒子的实际尺寸已放大。点击端点使用 **1.8 秒**发光碎片形成动画：逐片出现、旋转聚拢、在选点融合，然后保留常驻环绕效果。复用 strike 模型原有空闲四边形，不新增实体。
- 投影终端和测绘器手持 HUD 使用原版灰色按钮图集，按钮均为 50×20 UI 单位；无论 PC/F11 触屏状态，相关按钮均显示。测绘器始终显示“导入选区”“清除”，未选满两点点导入会给提示。框选提示是按钮上方独立的 Actionbar 风格短时消息，PC 同时保留右键选点、左键导入、潜行＋右键清除的操作说明，切换触屏时隐藏鼠标说明。已删除读取选区和导入成功的两条左上角通知。提示用原版 `hud_tip_text_background` 贴图；此前直接调用客户端 `SetTipMessage` 返回成功但实机截图未显示，因此没有依赖它。
- 世界测绘 PC 用右键选两点、左键导入；触屏轻触实际方块选两点，拖动只转视角。投影终端可右键打开工作台。现有代码仍拦截手持工具破坏方块。
- `docs/survey_golden_wireframe_preview.html` 是先前用户认可的金色线框 HTML 参考；游戏实现此后又调整了晶体亮度、线宽、点击面、环绕星光和碎片动画。旧版星空特效源码保留在 `extras/astral_survey_v1/`，供其他模组迁移。按用户 2026-09-26 的要求，`dist/astral_survey_v1.zip` 仅在用户明确要求打包时生成或更新；日常修改、调试和回归测试不要顺带重建，也不要自动恢复已删除的归档。归档测试继续使用系统临时目录并自动清理。

## 关键代码位置

| 职责 | 路径 |
| --- | --- |
| 游戏输入、PC/触屏工具事件、UI 入口 | `behavior_pack/modern_projection/client_system.py` |
| 服务端测绘选点与导入权限 | `behavior_pack/modern_projection/server_system.py` |
| 测绘请求、客户端选区、捕获与投影桥接 | `behavior_pack/modern_projection/projection/bridge.py` |
| 工具 HUD 按钮与 Actionbar 风格提示 | `behavior_pack/modern_projection/projection/tool_hud.py`、`resource_pack/ui/ModernProjectionTools.json` |
| 金色测绘/金色和星空投影效果 | `behavior_pack/modern_projection/projection/survey_effects.py`、`resource_pack/shaders/glsl/modern_projection_survey_stars.*` |
| 投影外框与独立风格参数 | `behavior_pack/modern_projection/projection/projection_outline.py`、`outline_settings.py`、`resource_pack/shaders/glsl/modern_projection_*outline.*` |
| 草稿、建筑库和编辑状态 | `behavior_pack/modern_projection/projection/model.py`、`session.py`、`ui.py` |
| 聚焦测试与真实输入回归 | `tests/test_survey_effects.py`、`tests/test_bridge.py`、`tests/test_server_stream.py`、`tools/verify_world_tools.py` |

## 最近提交和验证

| 提交 | 内容 |
| --- | --- |
| `998218a` | 白色逐格测绘覆盖、原版风格工具按钮、客户端 Actionbar 风格提示、加快点击特效。 |
| `5e39214` | 三种可配置的投影外框、金色测绘效果、点击面识别、线宽/透明背景修正及旧特效迁移包。 |
| `cac5397` | 金色线框 HTML 预览。 |

`998218a` 的历史验证（非本轮最终状态）：`python -m unittest tests.test_survey_effects tests.test_bridge tests.test_server_stream -q` 为 **59 项通过**；`python tools/audit_runtime_imports.py` 为 **83 个运行时 Python 文件、违规 0**；JSON 和 `git diff --check` 通过。独立开发游戏截图确认白色逐格覆盖、金色框、按钮和 Actionbar 风格提示可见；最新 MCDK 错误日志为空。游戏资源更新需要重新加载；仅 Python 热更新或旧着色器缓存不足以证明最终观感。

本轮验证（2026-09-25）：`python -m unittest tests.test_client_entry tests.test_tool_hud tests.test_survey_effects tests.test_bridge tests.test_server_stream tests.test_tool_assets tests.test_tool_import tests.test_session tests.test_selection_outline -q` **111 项通过**；运行时模块审计 **83 文件、违规 0**，改动的 Python/JSON/材质语法及 `git diff --check` 通过。独立实例冷启动后，实机录屏确认较大的发光碎片出现、翻转、聚拢，并以同一端点实体重播；金色和星光外框均拍摄静态及动态证据，星芒的大小、明暗随时间变化。星光配色现在也保留共用亮芯和流动高光。最新版 MCDK 错误日志为空。旧实例曾有 `xupdate` 递归异常与旧资源残留，不能拿旧实例的录屏证明新着色器已加载。

原生 HUD 读回：两个按钮均为 **50×20**，顶边 Y=220；双行提示为 **159×26**，底边 Y=210，间隔 **10 UI 单位**，截图确认无重叠且 PC 操作说明可见。入口单元测试验证没有世界按键订阅、终端右键仍打开且不会重复入栈；运行时确认旧 `key` 方法已不存在。

**仍需复测：**真实 P 键与最新 PC/F11 HUD 点击未完成整轮端到端验证。`verify_entry.py` 本轮尝试真实按键时，Windows 以 `FOCUS_DENIED` 拒绝切回游戏，不能记为真实输入通过。`TerminalHudScreen.Create` 已包含 HUD 重建时清除旧显隐缓存的修正；需在有前台焦点时运行 `verify_entry.py` 和 `verify_world_tools.py`。不要把阶段 71/72 的旧 F11 通过记录当成最新版本的验证。旧回归工具的界面准备已改为显式工作台入口，只有 `verify_entry.py` 保留 P 键的负向检查。

## 调试与工作区状态

- 受管 MCDK 独立测试实例最近为 owner `fragments-final`，session 文件：`C:/Users/Happy2018new/.pyreact-debug/instances/2f32f8143bb84397801614103e842f9a/session.json`；旧 `golden-targeted92` 实例已正常停止。跨对话**先查 `instances.py status`**，不要假设它仍在运行；不要直接用默认 19133 端口或无绑定 MCP 调用。真实鼠标/键盘输入要确认当前窗口焦点，工具返回“已发送”也必须检查业务状态或截图。
- 最近证据在忽略 Git 的 `.runtime/`：`survey_fragment_formation.mp4`、`survey_fragment_preview.webp`、`survey_orbit_large_golden.png`、`survey_orbit_large_starry.png`、两种颜色同名前缀的 `.mp4`、`hud_final_verified.jpg`。可用 `tools/verify_survey_fragments.py` 重新录制；脚本只创建客户端临时特效并恢复相机和选点，不写世界方块或建筑库。
- 本轮将粒子、金色/星光框、HUD、文案与 P 键移除一并提交。用户自己的未跟踪文件 `GPT提示词-网易MC星穹线框方盒特效.md` 未纳入提交。**保留该文件，不要顺手提交、删除或覆盖。**
- 若继续修改效果，先读 `docs/OUTLINE_EFFECTS_ACCEPTANCE.md` 的历史验收矩阵，但以当前源码和本文件的最新状态为准；窄改动优先聚焦测试，扩展到渲染共享行为时再扩大实机范围。相关历史背景另见 `docs/MODERN_PROJECTION.md`、`docs/WORLD_TOOLS_71.md`、`docs/SURVEY_STARDUST_72.md`、`docs/VIEWPORT_PERFORMANCE.md`。
