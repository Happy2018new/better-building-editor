# 新对话交接：现代化投影建筑编辑器

## 2026-10-16 00:00 最新范围与01:30旗帜截止

- 用户确认暂缓展示框内特殊物品的全面支持，保留普通物品基线与已有候选。新增明确范围是尽快接入能覆盖大多数普通方块的展示框显示；动态方块允许静态或简化的次级实现，不要求立即复刻世界动画。`item_r20`负责此项，先保存原候选并梳理已有方块模型复用途径。
- 物品候选已保存`096a1bda`，恢复与未关闭项见`docs/ITEM_RENDER_CANDIDATE_R20_PAUSED.md`；自有MC／MCDK均正常退出。新的glint方向与幅度、普通物品绝对亮度约1.0763倍及厚度质感尚未完成验收，生产门仍False。
- 旗帜与盾牌的编辑器接入继续研究，不随全面特殊物品扩展暂停。用户要求**2026-10-16 01:30（Asia/Shanghai）前给出旗帜编辑器接入的明确结论**；先旗帜后盾牌，必须区分原生UI／world绑定正例与真实可旋转编辑器结果。`shield_r20`优先验证既有骨骼模型绑定路径，不把单一路径不显示推广为全部原生接口不可能。
- 用户要求全量找出未附魔但自带附魔光效的物品并对应处理；下界之星、末地水晶、磁石指针是待查证例子，不是已确认清单。新增`intrinsic_glint_r21`负责目标3.10资源／规则遍历、独立规则模块与`item_sprite_plan.py`集成；不改真实附魔NBT，也不为动态指示物品读取定位／时间／目标NBT。
- 本轮共享index已依次保存root`fadfac30`、讲台离线控制`c41e2005`、物品候选`096a1bda`。MC仍总上限5（含用户），shield／snow各预留1槽；WGC在批次边界轮换，不暂停其他宿主或游戏。08:00休眠任务已再次读回启用、动作`shutdown.exe /h`、`StartWhenAvailable=False`。

## 2026-10-15 23:30 检查点，已无缝继续至08:00

- 正式书／台体提交`021a4bc3`已启用两份PRODUCT_QUALIFIED。root独立book provenance通过28源码／19资源，重放默认owner、原生book raster、讲台北正面、五面台体边界和453帧dense均通过。owner报告无native reference故artwork/raster=False是预期；另有原生参照报告两门True。讲台侧背轮廓仍开；离线新线索为原生顶板伸出单格，被packed-context中心格裁边，待空讲台未裁／已裁独立控制，不能因正面门通过关闭全方向。
- 水最终UI包提交`e6ec80b0`，root独立完整`--pixels`重放191图／3093来源通过，保留3张loading无效图及169／230／370／435ms elapsed失败。191图只关闭对应UI像素子集，生产仍False；CPU与wall新profiling只有聚合值，未解释长尾。world19与alpha后续继续。
- 物品旧附魔方向／速度／亮度失败基线提交`655ff72e`，冻结850文件并可从原图重拟合。新方向三路诊断误差<.3°、速度比约1.00–1.014，但新亮度幅度候选仍待完整dense；先前两次采样前握手超时均completed=False且恢复，不当成功。WGC独占以后在批次边界协调，不暂停其他采集宿主／游戏。
- 末地门原生属性提交`5559dcd1`：实际16层depth=0,2,...30，颜色UV逆序4×4；root已目检有效彩条及解码。这解释旧候选输入不一致，但不是星点外观资格。新隔离adapter按实测布局冷验中，正式portal资源／旧资格未变。
- 含雪工具检查点`6032b991`。native WorldToScreenPoint已是物理像素，旧雪QA再次乘逻辑缩放导致world ROI屏外，已加positive／double-scale negative修正。蓝花h0/h4/h7三路径形状／inside-cell等通过，但原生黑背景墙上部像素仍缺失，99%背景门继续失败；不降低阈值，不将其当植物失败。旧实例已恢复并正常退出，下一独立冷副本用几何预设降低测试高度。
- 旗帜物品初评已向用户报告：UI控件及world原生3D绑定保留真实typed底色／图案；raw Combine复制框不带内容；可旋转编辑器PaperDoll尚无可靠旗面。用户提出优先复用方块逻辑，后续共用模型／图案资源和状态解析，物品单独处理展示姿态，避免提前全面重写。动态指示物品“不读NBT、随意转／循环”约定保留。
- 展示架240本体仍候选，root已准备独立`.runtime/projects/shelf-r20-v1`：新增引擎四面向／AO控制与原骨骼旋转对照，未启动；待portal释放原三槽之一。三槽物品／附魔组合仍须完整验收。
- 已知DisabledSkin守护v2运行至08:00：PID16252、创建身份134365525898805833，日志`.runtime/disabled-skin-watch-r20-v2`。只允许本轮明确owner前缀、指定project子树、两进程身份和精确@47断言，每实例最多一次后台IDIGNORE；目前0恢复／0其他断言／0错误，无真实恢复成功证据。新冷副本四自动reload=False，根ignored `.mcdev.json`同样已关。全机总上限5、shield/snow各预留1槽继续有效。
- 08:00计划任务已读回NextRunTime=2026-10-16 08:00；仍不push或合main，截止前须保存／恢复并休眠。

## 2026-10-15 23:27 最新实例上限与旗帜检查顺序

- **用户把上限重新改为总共5个活跃MC（含用户），仍为shield／snow各预留1个，其他五项轮换使用其余3槽。** 此条覆盖下方短暂的7槽授权。root不占实例；book和item已恢复并正常停止，portal也已停止。shield为MC46764，snow为MC25100（早期未绑定时误观察到shield PID已纠正），water为MC53572；任何新启动都先协调。
- 用户要求先检查旗帜物品，再处理盾牌旗帜图案。`SetUiItem`显示真实typed旗帜数据的蓝底／三层有色图案已有实际截图正例，但仅属于UI物品控件；它不能证明可旋转建筑编辑器、PaperDoll或world投影能携带图案。原生工作台结果格确有带图案盾牌，无法读取输出格的接口障碍单列，不把手写候选数据称为真实合成readback。
- 用户再次报告`DisabledSkinScreenController::onEntered @47`断言，过去一直手点忽略，夜间无人会阻塞。MCDK源码本已默认Steve，重复配置皮肤不能称修复；旧资料有完整addon重载触发的实证。根`.mcdev.json`四种自动重载已关闭（ignored本地设置），新冷副本需同样关闭。新增专用watcher只对明确owner、`.runtime/projects`内、game/MCDK创建身份均匹配的实例执行已知文本的后台`IDIGNORE`，每实例最多一次并保留完整错误；不处理其他断言，不激活窗口。尚未在真实新弹窗验证恢复，不称根因已修复。

## 2026-10-15 23:15 最新授权与专项分工

- 用户明确动态指示物品（时钟、指南针、磁石指南针、追溯指针）只需自行转动／循环显示；不为此读取NBT或实际世界时间、位置、目标。这不取消盾牌底色／旗帜图案等实际可见内容的数据读取。
- 原五项优先继续：`book_r20`负责附魔台／讲台，`item_r20`负责展示框通用物品及厚度／附魔，`water_r20`负责水，`portal_r20`负责末地传送门／折跃门，root负责展示架本体及三槽整合。
- 用户随后明确新增`shield_r20`和`snow_r20`，分别优先盾牌上的旗帜图案及含雪方块，各额外获得1个专属MC槽位；全机活跃引擎上限从5改为**7（含用户实例）**。不挪走原五项的实例槽，不嵌套代理。盾牌先核对真实图案与原生渲染，原生不能携带内容才做独立候选；含雪接续现有固定居中设计与八雪高／双层编辑验收。
- 用户指出展示框附魔移动方向错误属实。新相位拟合原生两层角约80.154°／-20.168°、速度+.133389／-.363552 cycles/s；旧候选30°／-30°、+.2／-.1不通过方向／速度门。旧dense只验连续变化，未验方向及速度等价；亮度也缺上限，实测仍偏亮。代理正在冷验独立修正，不能沿用旧连续动画通过关闭这三项。
- root v5 MC46796／MCDK12636已正常退出、session metadata stopped。portal代理已启动独立冷副本；root将使用专属Shelf副本，不再修改旧portal工程。Shelf AO四方向16图完成恢复；AO改善南北但东西仍偏亮，尚未证明原因，不改共享照明掩盖。
- 水证据包`water-ui-state-r20-v1`已由root独立`--pixels`重放通过；追加provenance及world短诊断提交`7410c4de`。169／230ms owner-call elapsed失败保留；短批32／7ms不能替代既有100ms门结论，也不能称纯CPU耗时。
- 23:30保存阶段结果后继续至2026-10-16 08:00并休眠的安排不变；无push／合main。

## 2026-10-15 22:45 名称澄清与最新验收边界

- **讲台是lectern，展示架是Shelf，后续不混称。** 用户先说明讲台通电不改变外观，随后明确自己混淆了名称，展示架确实有本体／连接外观问题。讲台不增加powered外观门；展示架原有木质本体、连接状态及内容组合范围继续。
- 用户再次强调展示架可放普通／附魔物品。`visible_item_contents`已有三槽解析，`item_sprite_plan`已有槽位及附魔标记；这不是三槽实机资格。此前dense glint四路只测展示框，不含展示架；需本体＋三槽普通／附魔、厚度／侧面、架体遮挡、三路径及恢复组合，不能补出木壳就关闭Shelf。
- 展示架隔离实测`.runtime/shelf-role-matrix-r20-v3`完成28图、恢复且源码未变。语义state写入后客户端同步有效，原生powered_shelf_type 0/1/2/3分别匹配unconnected/right/center/left，root已查看完整对照；不能按数字顺序猜左右。候选本体仍明显偏亮，纹理／光照和12木种／四方向待验，尚未接入产品。v1在aux5同步不一致处中止并恢复，不授资格；v2语义写入单例通过后才扩展v3。
- 讲台正面书页新复验已通过：真实aux2/north，precision .998291、recall .990341、RGB差2，5图完成恢复且来源不变，`7340deb2`保存。旧west侧背视图误用了木台作为page mask，但封面突出／页边轮廓差异仍保留，不能据正面通过称全姿态相同。候选owner三路径与生命周期通过，默认冷启入口矩阵仍在运行。
- 附魔台静态台体独立生产门仍False；book provisional并不会开启`static_table.table_proxy`，代理正在补齐独立台体准入链后再测默认入口，不能由默认书可见推定台体接管正确。
- 物品法线冷候选的+75侧面相对亮度已由约31%／76%偏差降至接近原生，几何／负控有正例；尚有绝对亮度和边界／UV、-75与附魔组合，陈旧帧拒收，厚度门仍False。只改框layout0的专用光照，不改框体或Shelf／营火共享光照。
- 水v6同Doll先RenderEntity后能显示、恢复RenderSkeletonModel又消失的诊断保留，但不能推广成必然API根因。v7使用root精确配置的冷副本，在渲染真正就绪后无需world priming即可显示96,436变化像素，恢复RMSE0；south/east相关性 .96375/.982906。首批92%加载屏有新QPC却不是场景图，明确无效，不计水阴性。最新LiquidPreview.advance最大230ms，生产门仍False，不能因重新可见关闭性能／最终矩阵。
- root旧v4 MC22800／MCDK49788普通关闭后均确认退出、metadata stopped。新v5正在冷启，新增AO对照仅为隔离资源；portal8/10/12层与start1候选已准备，尚未取得这几种层数的实图结论。08:00休眠和23:30保存后继续的安排不变。

## 2026-10-15 21:55 用户纠正与有效增量

- **展示框亮度的最终范围：** 比较编辑器空框与放入物品后的框体；空框本来具有的朝向明暗可以保留，不要求各面同亮，也不要求与真实世界的框体同亮。六朝向、普通／附魔共12组固定框体角ROI，hidden-before／shown／hidden-after最大RGB变化均0，+12RGB负控均拒绝，因此不改框体亮度。物品姿态仍独立验收。
- **用户再次提醒书架投影：** Shelf木质本体在原生Combine中缺失仍是明确未解决项。240模型候选只在隔离副本生成，不能因展示架物品／书模型进展而关闭；12木种、方向、通电联组、UV、三槽与三路径占据继续待验。
- 物品共享front plane15→14.75已保存`9eae52b0`，450mesh仅Z外移0.25模型像素；书1/32页间隙、白点检测漏检和dense硬门已保存`46f051d1`；水同会话原生side oracle及证据已保存`5ae12293`。三者生产门仍False，后续完整矩阵和当前源码绑定以各专项报告为准。
- 折跃门白色候选已确认为错误绑定`environment/end_sky.png`，诊断别名改用安装包`entity/end_portal.png`并逐字节捆绑原生fragment。root已实际查看v5正面及v6斜视对照，恢复黑底彩色星点，但候选仍偏亮，未安装共享资源／刷新旧资格。v6临时玩家平台及位置均有journal、最终恢复、source_unchanged=True；10个适用表面有内容，两个末地门平视为边缘视角，不算可见正例。旧斜视草地帧、白面均明确拒收。
- 半砖`.runtime/slab-interactions-r20-v3`已完成14项Scene pointer回调检查并恢复，包括面合并／侧面上下、自动涉水、严格前后图层、异材质、锁定和mask。改变项撤回／重做按完整解码格数据断言；序列化未使用palette残留不是数据丢失。全／缺失gallery图已实际查看，但物理桌面输入与完整像素资格仍False。
- **22:15后增量：** 物品朝下八旋转全部通过，`135b8193`保存姿态修正与可重放证据。用户特别要求厚度质感；+75°近侧独立ROI确认full/missing侧边覆盖等于原生，但按正面增益归一化后，r0侧面仍偏亮约31%，r1依侧法线差异更大。厚度门保持False，需物品专用明暗／UV及更近负向侧视，不能改框体亮度代替。
- 水在root实例公开pool湿／干／恢复有效可见，96,436变化像素、恢复RMSE0；专项冷实例相同业务Python与所有water/liquid资源却无水。共享registry值一致，只有root多12个portal别名；复制这些注册项冷试仍无水，正在做world skeleton priming前后对照。不是已证明水shader坏，生产仍False。
- 书当前来源五向台体边界复验残留／支撑损伤／恢复差异全0，旧错误负控有效；最终附魔书原生raster／artwork已通过。讲台west朝向页面边界未过（precision .9614／recall .8171，最大色差34），保留失败图，不开启共同书gate。`aebc53a4`保存当前motion／owner证据。

## 2026-10-15 20:45 新会话恢复开发（覆盖下方暂停与旧截止安排）

用户明确要求继续上一轮开发：今日 **23:30** 保存阶段进度并无缝进入下一轮，至次日 **2026-10-16 08:00（Asia/Shanghai）** 截止并休眠。已将既有计划任务 `Codex-BetterBuildingEditor-R20-Hibernate-20261016` 的触发时间从07:00改为08:00并启用，动作仍为 `shutdown.exe /h`；读回下一次运行时间08:00，系统支持休眠。`StartWhenAvailable=False`，避免错过计划后在用户之后开机时补执行休眠。下方开发暂停、07:00及其他旧期限均为历史状态。

- 当前从 `dev` 的 `aeabba9f` 继续，不推送、不合入 `main`。两份原water tracked WIP、五个palette探针及其他旧资料继续保留，不整体stage。
- 已核对旧MC均退出，全机只见9个零线程／零句柄残留；不使用历史PID、旧session或已移除的 `D:/bbe-*` 路径。新副本统一放 `.runtime/projects/`，需恢复旧候选时按归档manifest定向取回，不覆盖现行共享实现。
- 最多3个活动子代理、禁止嵌套、全机最多5个活跃MC。`book_r20`负责书封面闪动和台体／书外观；`item_r20`负责框边遮挡、物品侧面／姿态及共享生成器；`water_r20`负责同会话原生投影oracle和水最终准入。root负责末地原生表面适配、半砖、统一文档和共同来源回归。每个代理预留1个独立实例槽，root预留1个，启动前后通报身份。
- 后台不干扰约定继续有效：不主动激活、resize或投递桌面输入，不提高窗口z序覆盖用户；用户自行切前台不暂停／关闭游戏。陈旧帧、白图和缺失参考都拒收并报告。
- 书、水、物品gate仍False；折跃门密度缺陷仍开，不能仅刷新旧资格hash。所有阶段性通过按实现、有效图像、产品准入分别记录，不恢复已撤回的总工期估算。

## 2026-10-15 工作区与磁盘清理完成（优先于下方旧路径／实例记录）

用户在暂停开发后另行要求清理旧工作树、分支、D 盘根目录副本及两盘垃圾。本次仅执行清理、保存与验证；产品开发仍暂停，不启动游戏或代理，不推送、不合入 `main`。原次日休眠任务仍为 `Disabled`。

- `dev` 已提交 `bf2b31e3 docs: preserve retired agent work before workspace cleanup`，保存 43 个临时分支的头、159 个补丁独有提交审计、28 个缺失的历史诊断／证据；当前产品实现优先，不重新合并旧分支或重复旧提交。另 77 个原始调用资料仅私有备份。详见 [归档及恢复说明](retired-development/20261015/README.md)。
- 已移除 **40 个旧工作树、43 个 `codex/*` 分支、12 个普通测试副本**。Git 仅登记当前主工作区；保留 `dev`、`main`、`realm`、`render-dragon`、`uncomplete`，后四者原提交未变。下方历史 `D:/bbe-*` 和旧 `.runtime/r*-*` 工作树路径现已失效，不能直接运行。
- 完整本地备份位于 `.runtime/cleanup-20261015/`：`retired-agent-branches.bundle`、`retired-workspace-deltas.zip`、`clone-baseline-files.zip` 和 `workspace-backup-manifest.json`。12,459 个去重对象及 4,505 个精确基线文件均逐字节校验。备份含未提交／ignored 原始资料，可能含会话凭据，不整体 stage／发布。两原分支头本已在 `dev` 历史中，其余 41 个 ref 在 bundle 中。
- **候选续接位置：** 书副本对应 manifest label `42-bbe-r15-native-production`，物品候选 `50-bbe-r18-item-glint`，水候选 `51-bbe-r18-water-production`，折跃门适配候选 `52-bbe-r19-integrated-product`。从备份按需恢复到 `.runtime/projects/<名称>`；新工作树放 `.runtime/worktrees/<名称>`，不再写 D 盘根目录。
- 暂停时保留的两个 MC／MCDK 现已退出，本次清理没有终止它们。审计未发现活跃 MC 引擎；9 个零线程／零句柄残留对象不作活跃实例，也未终止。下表旧 PID／session 不可复用。item 侧视 v6 的原恢复未完成仍需在恢复开发后检查对应世界／journal；归档副本不等于世界已清理。
- C 盘移除 1,175 个今天以前的 MC 文本日志及废弃 VS 安装解压目录，共约 5.25 GiB 逻辑文件；保留今天日志、方块 dump、世界存档。1,004 个退休实例文本证据无损 NTFS 压缩，内容 SHA256 不变，节省约 2.81 GiB 分配空间。当前原始证据路径不变。D 盘旧目录共约 16.25 GiB 逻辑文件，净释放量扣除本地备份后另计，最终数值见 [清理结果](retired-development/20261015/cleanup-result.json)。
- 自动审批拒绝删除约 74 MiB 的 `retired-workspace-deltas.interrupted.zip`，仅给出 `blocked by policy`，该冗余文件仍保留。正式 ZIP 的 SHA256 已复核；不要把未完成 ZIP 当恢复来源。
- 原有两份 tracked water WIP 和五份用户 palette probes 未改、未 stage；清理后核对原工作区 **23,923 条**状态记录全部保留。没有因清理关闭任何产品待办或更新生产 gate。
- 用户要求模型请求使用 HTTP 流式传输。已在 `C:/Users/Happy2018new/.codex/config.toml` 当前 `blackpixel` provider 下设 `supports_websockets = false`，保留 `wire_api = "responses"`；其他解析配置未变。应在配置重新加载后应用；本次未抓取已建立请求，不能声称当前缓存连接已验证改为 HTTP。应用内部远程控制 WebSocket 与模型 API 传输不是同一个通道。

## 2026-10-15 18:12 用户要求暂停：API 不稳定（最高优先级）

用户要求“保存所有上下文和 mc 进程，创建对应提交，然后终止开发，之后再继续”。**当前只完成保存和提交，不再开发、启动测试、启动游戏或恢复代理；等待用户明确继续。** 此安排覆盖下方所有继续至 23:30／次日 07:00 的历史安排。

- 分支仍为 `dev`，不推送、不合入 `main`，不切分支、不删除现有工作目录或测试副本。
- 三个代理 `book_owner_r18`、`item_glint_r18`、`liquid_product_r18` 已停止／中断；旧嵌套任务亦无活动代理，不恢复。
- 计划任务 `Codex-BetterBuildingEditor-R20-Hibernate-20261016` 已禁用并读回 `Disabled`。本次暂停不再自动休眠，避免用户回来前丢失实例。
- 仅停止了身份匹配的宿主编排 Python PID4912（`item_edge_r19_candidate_stage_v6.py`），阻止其自动关游戏；子采集 PID16940 已结束。没有关闭下表 MC／MCDK。
- 无凭据实例快照保存在 `.runtime/pause-r19-20261015-1805/instances.json`；采集后核对两个游戏和两个 MCDK 均存活。当前窗口枚举均为空，**存活不等于能可靠截图或已就绪**。不能绕过窗口／身份保护去运行恢复脚本。

| 保留所有者 | 项目副本 | MC PID／原生创建身份 | MCDK PID／原生创建身份 | session 文件（仅路径，不提交凭据） |
| --- | --- | --- | --- | --- |
| `book-motion-r19` | `D:/bbe-r15-native-production` | `31116`／`134365299406499400` | `45044`／`134365299404663953`，端口63200 | `C:/Users/Happy2018new/.pyreact-debug/instances/d0ec1d51ff0144bba9ede1ef973f86d4/session.json` |
| `item-plane-r19` | `D:/bbe-r18-item-glint` | `32324`／`134365320812982299` | `56236`／`134365320811292356`，端口19370 | `C:/Users/Happy2018new/.pyreact-debug/instances/cfdc3dc8aefb40f9ae8e823c496c9271/session.json` |

### 恢复工作时首先处理

1. 先核对 session、owner、进程原生创建身份和可用窗口，不凭旧 PID 或 `state=ready` 直接复用。零线程／零句柄残留对象不是活跃引擎，不终止未知／用户进程。最多三个活动代理、禁止嵌套、最多五个活跃 MC 的原限制保留，除非用户另行修改。
2. **item v6 侧视恢复未完成**：`.runtime/item-plane-r19-side-v6/report.json` 为 `completed=False`，仅1图；窗口先最小化、随后不可用，保护机制拒绝 stop projection／blueprint restore／profile restore。可能遗留测试投影、原生方块 journal、保存的蓝图／profile／相机 globals。下次先检查并恢复，不能直接叠加新测试。宿主编排为 `.runtime/item_edge_r19_candidate_stage_v6.py`，阶段目录 `.runtime/item-edge-r19-candidate-control-v6/`。
3. `.runtime/item-plane-r19-front-v6/report.json` 已完成，14图、`source_unchanged=True`、`cleanup_errors=[]`；**尚未像素分析和归档，不是冷候选验收成功**。侧视失败不能被正面完成掩盖。
4. 暂停期间不修改游戏状态。恢复时仍不主动激活、调整窗口尺寸或投递桌面输入；用户自行切前台不暂停、不关游戏。背景白图／陈旧图必须拒收并报告，不能把新QPC当新内容。

### 已保存的代码、诊断与未关闭事项

- 已提交 `1bbf7c2d feat: add slab placement merging and public regression fixtures`：62个单半砖家族、面／高度放置、半高命中、同材质合并、三图层／撤回、公开 `test.groups.slabs`。`.runtime/slab-world-r19-v1/report.json` 已完成恢复、三图，但人眼像素复核及编辑器实际命中矩阵仍待。pointer工具调用语义Scene回调，不能充当物理鼠标验收；未来隔离支撑避免侧面／底面被其他格遮挡。
- 已提交 `9998a120 test: verify final item glint animation across render paths`：只关闭最终shader四路连续附魔采样条件，不关闭边缘／姿态／厚度／特殊物品或生产默认。
- 书台体的 target-only overlay 及强制 `body_boundary_pixels` 门正在保存为检查点，**书与台体生产gate仍False**。五向边界v2的占据残留／支撑变化／恢复变化均0，旧错误负控7337／10008／10006／9957／9972px。原始本地诊断 `docs/evidence/book-body-owner-r19-v{1,2}` 不整体提交（各1712文件，含未经发布脱敏的调用资料）；保留本地原件和工具供恢复分析。
- 书旋转闪动已复现为封面内部白色细点／斜线，稳定owner／camera追踪不支持整个owner闪烁。active17s／330帧；有效frozen96帧局部变化0；当前冷baseline17s／541帧、最大间隔48.49ms并恢复。depth1冷试仅1张陈旧森林帧，拒收；不声称深度系数已定位／已修复。`docs/evidence/book-motion-owner-r19-*` 和 `.runtime/book-r19-checkpoint.json` 留本地，后者部分旧字段以本节为准。旧热ReloadAllShaders超时恢复失败的实例已停止，磁盘原字节已恢复。
- 物品框边因果对照已在 `docs/evidence/item-rim-r19-plane-v1` 脱敏归档并独立重放：原7370px，向外0.25模型像素为7804px、逐像素等于原生；移走框体恢复端点，恢复基线变化0。只有item副本的一张钻石剑mesh front15→14.75（SHA `7b444e21182cd5d666301b1e8a81c7d3e18a52752900a4fe896e94093aaddcec`），共享generator／catalog／资源未改；冷候选侧面／全矩阵仍待，gate=False。0.5及更大偏移局部门失败，不采用。
- 水最终冻结合同 `20ab6570d676d884753b89ca2d6f35508e17e7dfac47909c245e26e86a5cf272`（3060文件），owner合同 `8dc274619c113161d933e9f08d6ff0420cf2890ff4bbee15970a85dc84b13c25`。editor48图有限通过；world v4的south/east .830878/.644174原失败保留。原生API标定发现旧解析投影最多4.46px误差；以固定原生网格跨会话重放v4为.949223/.937050，只是oracle诊断，不资格化。v5六张水图均陈旧标定帧、v6首帧全白，全部拒收。所有水实例已停止；三个脱敏包 `water-final-r19-{editor,world,projection}-v1` 保存有效与失败证据，生产gate=False，未修改shader。`.runtime/water-native-projection-r19-v7.py`／`water-final-r19-world-v7/plan.json` **仅准备未运行**；其临时提高z序方案尚未解决不干扰后台约束，恢复后不能默认执行。
- 末地折跃门过密是用户指出、root此前漏检的现有缺陷，不能改称已自主发现。`.runtime/portal-native-reference-r19-v1/native-compare.png` 的有效正面对照显示原生大星点与旧细噪点不同；斜视空缺／相机读回滞后拒收。`generate_portal_native_adapter_r19.py` 只向 `D:/bbe-r19-integrated-product` 生成顶点接口适配＋`#include "end_portal.fragment"` 的诊断别名，未改原生fragment正文；ES100 fragment／ES300各链接通过不代表外观通过。冷试 `.runtime/portal-native-adapter-r19-cold-v1` 首张后台图空白，已恢复并停止自有进程。共享portal资源／旧资格未改，**不刷新hash掩盖密度缺陷**；最新editor31／world28图已看但资格更新暂停。刷怪笼共享来源复验仍待。

### 验证与保留边界

全量回归已完成 **2937项、456.083秒、OK、1 skipped**，日志 `.runtime/r19-alltests-v1.log`；之后暂停收尾的90项定点回归全部通过。源文件、运行时ready、像素通过和产品默认准入严格分开。

暂停归档已独立重放：item局部框边包、水editor包、水world包、水projection包均通过各自验证器；这是证据完整性／有限条件重算，**不改变生产gate=False**。item manifest116项、水editor129项／world58项／projection65项，均逐字节核对Git暂存内容与清单SHA／大小一致，并扫描文本及ZIP内部文本的凭据模式，未发现待发布凭据。相关 `.gitattributes` 保持原始证据字节，未用换行规范化改写归档。业务定点review实际解析4文件，唯一advisory为既有 `prepare_context_batches` 9参数签名；不在暂停收尾中重构接口。之前单文件路径导致0文件解析的报告不算有效review。

已保存提交：`1bbf7c2d`（半砖）、`9888e98e`（台体独立归属／边界像素门及书闪动诊断工具）、`bc62f0bb`（框边因果对照／局部物品门）、`d49b2c53`（水最终来源三包／oracle诊断）。末地原生适配工具及本节另以 `test:`／`docs:` 检查点提交；完整顺序以 `git log` 为准。全部仅在本地`dev`，无推送或合并。

最终无凭据实例／报告摘要同时保存为 [暂停实例快照](evidence/development-pause-r19-v1/instances.json)。`.runtime/pause-r19-20261015-1805` 另保留最终身份核对、剩余工作区完整清单、未提交tracked差异补丁和近期提交列表；这是本机续接备份，不替代已提交源码。原始book／item／portal诊断仍留原路径，未经发布脱敏的session／调用资料不整体加入Git。

保留而不混入本轮提交的原WIP：`tools/diagnose_water_world_r16.py`、`tools/run_water_batch_r16.py`、五个用户 `tools/p0_palette_*probe.py`、其他旧未跟踪证据／工具。暂停提交按书边界、物品局部门、水证据、portal诊断及交接分组，不整体stage仓库；未提交原始证据仍保留在原路径，不删除。恢复时先读本节及统一清单，再取已执行报告，避免因429重放世界写入／启动操作。

## 2026-10-15 17:55 增量（优先于以下进行中状态）

仍 `dev`、最多三个代理／五个活跃 MC、23:30 保存汇报后无缝继续至次日 07:00 休眠；不 push／合 main。最新提交 **9998a120**（物品最终 shader 四路连续动画证据）。root 全量测试已完成 **2937 项，456s，OK，1 skipped**，不是仍运行。

- **用户新增视觉纠正：折跃门过密。** root 此前看图却未识别，已向用户承认漏检，不得声称此前已发现。暂停本轮 portal 资格更新。`.runtime/portal-native-reference-r19-v1` 12 张已完成恢复；正面实图清楚证实原生大星点与自定义细噪点不同，但后续斜视出现空场景、相机读回滞后一帧，**不算完整原生矩阵**。原资格文件未刷新。新 `tools/probe_portal_reference_r19.py` 用公共 `test.dynamic.portals` 派生结构、同坐标真实世界替换及服务端 journal 恢复；新增相机等待及图像可见门。
- **原生 shader 路线：** API 明确 Combine 仍排除末地门／折跃门。安装包原生 vertex 依赖 chunk/COLOR/UV1 平面元数据，不能直接接受现有四格模型 payload；native material 是 `One/SourceAlpha` 叠层，并非现有三层 SourceAlpha 混合。新 `tools/generate_portal_native_adapter_r19.py` 只在 `D:/bbe-r19-integrated-product` 冷副本预注册 `r19_native_portal_*`，通过 wrapper **include 未修改的安装包 `end_portal.fragment`**，补 highp、可见性和透明度，vertex 适配格位／层深。ES100 fragment、ES300 plain/skinning/instance 编译及链接通过；ES100 skinning 仍是原生 mat3x4 基线限制。16 个星空层及颜色索引／ray 坐标是待验证假设，**无原生同等外观声明／不改共享产品资源或 gate**。
- root 冷 alias 启动 `.runtime/r19_root_native_stage.py`／exec76507，输出 `.runtime/r19-reference-control-v2`，探针目标 `.runtime/portal-native-adapter-r19-cold-v1`；先取现有进程／报告／finally，不重放启动。冷副本 3065 文件合同 `c4f48048ad6bda71f5c916d8a51f9d7f23b39d72723648e686ea0dd05ed07110`；旧 3061 合同不再用于此副本。
- **物品框边根因成立：** 原生 mask7804、旧7370，移开 owned 框体恢复7795；法线前移 **0.25 模型像素** 后7804且逐像素与原生相同，局部门全过、恢复0差。证据 `docs/evidence/item-rim-r19-plane-v1` 已脱敏可重算。只在 item clone 改一张剑 mesh front15→14.75，尚未同步共享生成器／catalog／mesh。多次冷候选遇 MCDK 退出、原生断言或全白后台图，**没有冷候选通过**，gate=False。代理继续定位，不将高 QPC 当新鲜像素。
- **水 oracle 原因已缩小，不能乱改 shader：** v4 world 原阈值 south .830878/east .644174 失败仍保留。v5 六张 PNG 完全相同且仍石块标定画面，**全部作废**；native uniforms256组正确。独立原生石块 API 投影内参与旧解析模型最多差4.46px；用 v5 固定原生网格在同 pose 的旧有效 v4 图上跨会话诊断，south/east corr .9492/.9371、固定 texel-center均1.0，强指向采样投影 oracle，不是 shader 单格错位。跨会话诊断不能资格化。v6第一张标定也全白，已恢复停止；代理继续先做背景 render-ready／wet-dry-section 硬门后同会话验收。
- 水自有三包：`water-final-r19-editor-v1`（48+6张）、`water-final-r19-world-v1`（12+6张）、`water-final-r19-projection-v1`（65项，明确拒绝v5）。代理均离线重放通过；root还需独立检查，不以验证器通过宣称水产品已关。源码冻结仍20ab6570，水gate=False。
- **背景捕获失效已向用户明确报告**：流体陈旧画面及物品空白均拒收，不能静默算通过。不激活窗口；用户自己切前台仍允许。当前 agents 反复 headerless429；用 followup 恢复，先读已执行报告，不重放命令。book 最新 `book-motion-r19`／session d0ec1d51…／PID31116，冷 baseline17s/541帧通过恢复，depth1 exec5522待取；旧热 ReloadAllShaders 超时恢复失败已保留，原磁盘 bytes 恢复后旧49372正常停止。
- 半砖 world host 探针 `.runtime/slab-world-r19-v1` completed/restored/source_unchanged=True、无清理错；仅 gallery/full/missing 三图，未做人眼最终验收，editor pointer 矩阵尚未跑。root旧MC15212已退出，managed stop先超10s后实际消失；不要重复用旧身份。

## 2026-10-15 16:55 增量（优先于以下进行中状态）

期限仍为今天 23:30 保存／汇报后无缝继续，次日 **2026-10-16 07:00 休眠**，原计划任务保留。最多三个活动子代理、禁止嵌套，最多五个活跃 MC 引擎含用户游戏。零线程、零句柄残留单列、不占活跃槽；以下历史五实例计数已被纠正。仍在 `dev`，不 push／合 main。

- **用户明确的两项失败仍开：** 编辑器附魔台书自转闪动；展示框右框边截断旋转剑尖／边缘（用户图 `codex-clipboard-45b38bfc-…png`）。前者由 book 做固定机位连续 WGC／冻结姿态／原生参照；后者由 item 做同朝向和角度的真实框对照，已在哨兵复现，停止扩大矩阵。全局 2px 轮廓容差会漏过局部剑尖遮挡，必须加入交叠区域硬门。另一 top/bottom 原生哨兵不可见，属于夹具无效，不能记通过。
- **三个活动代理：** `book_owner_r18`、`item_glint_r18`、`liquid_product_r18`。水多次被同类 429 中断，root 已 followup；先取既有采样／finally，不重放世界写入。无需恢复旧嵌套代理。
- **物品连续动画有限关闭：** 最终 shader `3c288ec…` 四路连续采样均达原有 ≥7s、间隔 ≤250ms、每个重叠 1s 窗口变化 >5% 门槛；root 已实看 editor/full/missing/native 四张对照图并独立核对 48 项 manifest、10 项执行源、仅两个认证字段脱敏。归档 `docs/evidence/item-glint-r19-dense-v1`，原 1277 文件留 ignored runtime。自定义比原生亮；此结果不关闭框边遮挡、全部姿态／特殊物品，也不启用生产 gate。
- **台体有限诊断：** target-only overlay 的五向 occupied residue、support changed、restore changed 均 0；旧 context 负控每向 7337–10008 像素。首次 down 共面导致负控无信号的失败保留，修正机位后通过。book clone 仍旧 scene/session 来源，两个生产 gate 仍 False；最终全量来源回归另做。
- **水 editor：** 全量同步 3060 源后冷启，新冻结合同 `20ab6570d676d884753b89ca2d6f35508e17e7dfac47909c245e26e86a5cf272`；48 图全部完成恢复。九核心水例适用像素通过（几何 IoU .9553–.9898，池水 south/east UV corr .96375/.98291，隐藏／恢复 RMSE=0）。动画本轮冻结未验，world／普通默认及生命周期仍开。旧编辑器无水失败缺少原生模型读回，未确认为产品已修复；不能用本次通过改写旧失败。
- **半砖：** 新 `slab_placement.py`、真实半高 raycast／hit point、同材质互补合并、三图层及 undo 已接线，12 项专项离线通过，遍历 dump 的 62 个单半砖家族；公开 `test.groups.slabs` 已接入。实机 UI／完整与缺失投影尚待。
- **实例：** book MC49372／session `64353c37…`，water MC50016／session `a2cb3356e3c24efba4eea98d512bfc5e`，item MC42228／identity `134365272447609747`。PID 只供此次核对，后续仍按 session／owner／创建身份路由。root 尚未启动自己的实例，计划最多第四个活跃引擎。
- 全量回归 exec55598 写 `.runtime/r19-alltests-v1.log`，尚需取最终结果。共享 `render_context.py`／scene/session 改动使 portal/spawner 的旧来源校验失败；先实机回归再更新资格，不只刷新 hash。不要整体 stage 用户 palette probes 或原 water WIP。

## 2026-10-15 16:00 新轮继续开发（优先于以下历史安排）

最新期限：今天 23:30 保存本轮进度并汇报，随后无缝继续到次日 **2026-10-16 07:00**，届时休眠。已登记并读回计划任务 `Codex-BetterBuildingEditor-R20-Hibernate-20261016`，状态 Ready，触发 `2026-10-16T07:00:00+08:00`，动作 `C:\\WINDOWS\\System32\\shutdown.exe /h`。不要沿用下面 13:30／08:00 的历史截止安排。最多三个活动子代理、禁止嵌套，全机最多五个 MC（残留和用户实例均计入）。仍在 `dev`，没有 push／合 main 授权。

- 三个代理已恢复：`liquid_product_r18` 做 editor pool 单一 wet/dry 正负控定位；`book_owner_r18` 离线解决台体／邻域的边界归属，保持两个 gate=False；`item_glint_r18` 准备最终 shader 连续动画验收。root 维护公共文档，并审计半砖的实际命中／放置／合并链。
- 新增要求已进入统一待办顶部：`F04-S04-SLAB` 半砖专项；`F02-CONNECTED` 在 NBT／动态外观之后核销连缀变换；`PROJECTION-ROTATE` 最后实施。不得把单块姿态合法等同这些交互已实现。
- 当前全机五个 MC：三个历史拒绝访问残留继续保留；PID10284 非 root／这三个代理启动，按未知或用户实例保留；PID24608 是 water 本次受管启动。item 等待 water 完成最小对照释放／交接槽位，不额外启动。PID 仅用于这次核对，后续必须重新验证 session／owner／创建身份。
- 工作区原有 `tools/diagnose_water_world_r16.py`、`tools/run_water_batch_r16.py` 和五个用户 palette probes 及其他旧证据均保留，不整体 stage。当前基线 `8c91e9e5`。上轮全量 2,911 项通过（1 跳过）是旧来源结果，新改动仍须按影响验证。

16:30 更新：用户纠正实例计数后，root 重新核对三个旧条目均为 **0 线程、0 句柄、无窗口、32 KiB 工作集**，单列为残留对象，不再当作三个活跃引擎占槽。实际活跃实例启动／停止仍由 session／owner／创建身份验证，不能据此清理未知进程。

Codex 429 调查：已安装 `0.162.0-alpha.17.2`，当前 provider 的全局配置为 request retries=40／stream retries=200，实际日志 stream 上限100。用无认证、仅本机的 stub 做同配置对照：带 `Retry-After: 1` 的429实际请求8次（7次重试），不带该响应头只请求1次即结束；真实失败 request id `4b65ad7a-cf8e-4401-9c21-cbcbabd1d50a` 的头亦无 `Retry-After`。故增大次数不能独立修复此错误；未改全局配置、未使用付费接口测试。证据留 ignored `.runtime/codex-retry-local-probe-*`。代理中断后先查已启动采集／finally状态，再继续同一任务，禁止重放启动或修改世界操作。

## 2026-10-15 13:10 收尾检查点（当前状态）

本节覆盖以下历史状态。今天13:30截止、不休眠；最多3个活动子代理、5个MC；继续在`dev`，不push／合main。本轮登记的自有MC／MCDK父进程已停止，但最终核对发现三条残留Minecraft子进程，详见下文；不能宣称系统里没有MC，也不能按五个空槽启动。五个用户palette probes及其他未纳入提交的WIP保留。子代理不再开游戏，只做最终归档／身份核对。

- **估时纠正：** 用户指出剩余工期反复18–30小时没有收敛。已撤回旧区间的可靠排期含义，统一清单顶部固定12个剩余工作包及关闭条件。约12:15有效开发墙钟粗估100小时（95–110），自然经过约135小时，不累加代理、不当精确工时。不得在下轮再机械复述旧区间或用测试数量冒充产品完成百分比。
- **水：** 独立`ProductLiquidProjection`／`ProductWorldLiquidRenderer`完成产品专用±4 bounds、1 create/frame；冷启±4可见／±2不可见／±4恢复，固定相机近移返回可见。冻结19例×3路径、162行／348原图全部恢复；full/missing适用几何、alpha、CPU和108次停止读回通过。**editor九个核心水例无独立水像素**，即便8组ready、opacity=1；下一步仅做PaperDoll model ID、visibility、depth/layout正负控，不先重跑全矩阵。world side UV south .8143／east .6827低于.85而RMSE过，不称已证实可见接缝。动画burst、群系／占用、反向邻域、公开蓝图及普通默认仍待，water gate=False。
- **书：** candidate/default各65帧完成恢复，但真实占据留下台身底面和四侧context纹理。五组各12帧边界控制未取得无缝修复；`no_crop_face_block`影响邻面保留，不是背面剔除。**默认静态台体proxy已独立关闭**：`static_table_data.PRODUCT_QUALIFIED=False`，诊断须显式`CANDIDATE_ENABLED=True`并恢复。native fallback仍偏低.125格，不算修复。书gate=False。不要重装inset或移除component实验到默认资源；具体失败及下一步见`docs/evidence/book-owner-r18-v2/REMAINING.md`。
- **物品附魔：** 最终shader `3c288ec16d18d66b908393c34dd84b6bb4a884ca52b8a2e1039a94a392a3da87`与根目录／采集同字节，资源契约`515be879b61fc352b3e00e66d063f8da6e05036a8cd7d83aa54db563fb86815e`。最终v2三路径几何、原生参照、附魔可见性、普通／空负控通过；root实看四路径及占据／切面恢复。连续动画仍False：旧945ms间隔失败保留，250ms门限不放宽，旧shader dense帧不得替新版本授予资格。生产gate仍False，完整姿态／特殊物品另验。
- **Shelf／阴影：** 384状态／52原生视图已调查，候选240模型仅隔离生成，根生产未安装。归档含20张选定原生图及全部32张四向本体／阴影控制图，不能声称保存全部52张原生图。橡木候选轮廓接近不等于UV／光照／通电联组／内容合格。probe漏关anchor影子是测试bug；`probe_native_palette_body_r16.py`和`probe_liquid_pose_channel.py`已关闭。同实体同机位on/off明确复现与去除暗斑；正式full/missing原已关闭阴影。
- **证据：** `docs/evidence/{book-owner-r18-v2,book-default-r18-v1,book-default-admission-r18-v1,book-body-*,liquid-owner-r18-bounds-v1,liquid-owner-r18-matrix-v1,item-glint-r18-v1,shelf-body-r18-v1}`。水矩阵原227MB ZIP已留ignored `.runtime/liquid-r18-large-captures-original.zip`，正式分为6包、最大51.68MiB，696成员逐字节一致。稀疏物品GIF不能充当dense帧通过。首次Shelf helper缺失和物品相机漂移失败均保留，不记成功。
- **发布脱敏：** item归档报告中的两个本地MCDK token字段已在暂存前替换为`REDACTED`，原始报告留ignored runtime；`sanitization.json`明确记录转换字段和前后SHA。对发布报告实际重跑分析，全部像素指标及四个GIF不变，manifest29项／30文件核对通过；不是改原采集报告或仅手改分析hash。水7份ZIP内2,636个文本成员及其他本轮归档的凭据模式检查未发现同类值，未提交session凭据。
- **验证：** gate最后改动后全量2,911项通过（1跳过，225.560秒），日志`.runtime/r18-final-after-body-gate-alltests.log`，exec22133已exit0；故障注入traceback不等于失败，结论见日志247／249行。四个已启用锅／旗帜／末地表面／刷怪笼工作区及staged来源验证通过，book仍disabled；默认台体gate没有通过更新hash掩盖视觉失败。水两份归档重验通过，matrix348 PNG／348 receipts及bounds44图的像素重算均保留。
- **残留MC条目：** PID40520（02:25:33.684379+08:00）→父33752／session `9f5a6c7618df46069ef40b84ba98fc02`；PID3264（11:39:03.455412）→父46700／session `6d2af456cfda4e6886f875a6f35a99ba`；PID39028（11:54:53.833073）→父44588／session `9111908a4fd8432eb90a85e5bc8e9f5e`。三个父进程的原生creation identity均与session逐字匹配，子条目创建均在原父存活期。子条目本身OpenProcess(QUERY_LIMITED_INFORMATION)全部拒绝（error5），CIM路径null，无法取得原生creation identity，不得把`process_identity=None`误记为退出。当前未清理，继续计入最多5实例上限；下轮先核对本机实际状态，不复用旧PID、不杀无明确身份的用户进程。

13:20收尾补充：root按CIM的名称、父PID和精确CreationDate重新匹配上述三个自有残留，受保护地各尝试一次CIM Terminate；三者均返回`2`（Access denied）且仍被列出，回收未成功。没有更改系统权限、终止其他游戏或重启电脑。已确认的台体边界入口是`render_layout.context_center/local_context_center`及`modern_projection_biome_blocks.fragment`的闭区间裁剪；同坐标的两侧面不能仅靠位置区分归属。对应native vertex输入没有显式NORMAL attribute，不能未经验证就套用法线偏移；任何后续共享shader修改须重新核对受影响的既有资格。

准入待补项：`qualify_book_product_r18.py`已有owner、书面raster、讲台页面、来源和default五类门，但当前占据读回通过并不能拦住上述台体邻面残留。`analyze_book_body_occupancy_r18.py`现是单独的残留计量诊断，尚未整合成底面／四侧像素残留的硬性准入。保持两个生产gate关闭；修复时须将有效正负控、支持面保留和残留失败一起纳入，不把人工review标记或owner=0当作自动兜底。

水editor定位入口已核对：`tools/probe_liquid_workspace.py`的STATE目前记录`renderer.visible/poses/uniforms`缓存和Doll位置／尺寸，没有逐bank实际`GetModelId()`；`SkeletonLiquidRenderer`已有`dolls`与`ids`可用于比较实际ID／缓存ID。下一次只跑pool wet/dry正负控，先加入实际ID、必要的原生状态／payload读回，再分离材质、深度及Panel布局。`LiquidControls._renderer`用两bank PaperDoll，`LiquidTile`的Doll zIndex=306；这些是定位入口，不是已确定根因。不以新增缓存日志代替原始截图像素，也不先重跑348图。

已保存提交：`0327d438`（Shelf／阴影控制）、`1fdebea8`（关闭未资格台体与书边界回归）、`a8780a0f`（独立水owner与矩阵）、`0387b4e8`（附魔变换与可见性／动画分离）、`9338a59f`（保存此前同主题dense／占据／侧视工具）、`c923e225`（脱敏物品实机归档）。全部留在`dev`，没有push或合main；另有本节／清单／盘点文档提交。此前水诊断两文件和其他未纳入的WIP保留，不将其混入这些已核对范围。

下轮先读统一清单固定工作包，再按以上最小失败定位继续；不重复整批已完成调查。三个代理均已完成，没有运行中的本轮采集／分析／全量测试exec。不要恢复旧代理的嵌套任务。

## 2026-10-15 09:35 继续至 13:30（当前安排）

本节覆盖下方所有旧截止与代理安排。用户要求今天 13:30 截止，允许最多三个子代理；此前 08:00 休眠任务已禁用，13:30 不安排休眠。继续在 `dev` 开发，不推送、不合并 `main`；保留五个用户 palette probes 和其他 WIP，只显式 stage 本次完成的文件。

- 当前代理：`book_owner_r18` 分析独立书本 owner 的实机矩阵，`item_glint_r18` 验证新附魔 shader，`liquid_product_r18` 复验产品水 owner 的远距剔除修复。不要再启动第四个。
- root 的 `root-book-r18`（`b4252d2330f9451184ea9409526d7aa3`）与后续 `root-regression-r18`（`eccd076eb8134caeb5c8ba11c95e1c0e`）均已退出，后者 status 的历史 state 虽为 ready，`process_alive` 两项已为 false，不得复用旧 PID。`D:/bbe-r15-native-production` 副本现由 book 代理独占，允许它同步最终书来源并冷启。水／物品代理使用各自副本；后台运行、最多五个 MC，不抢焦点、不 resize。
- 书独立 owner 已接入 Scene/Session/WorldProjection；`.runtime/book-owner-r18-v1/report.json` 的 61 张截图已完成并恢复，`source_unchanged=True`，像素矩阵仍待分析。书 gate 仍 False。
- 附魔台原生 Combine 台身偏低 0.125 格；内部静态 proxy 已候选接入，`.runtime/enchanting-body-prepared-r17-v1` 四方向红色纹样 IoU 0.9571–0.9725，支撑内部 recall 均 1.0。不要将此单项当书整体资格。
- 水远距丢失已定位为 FreeModel 默认 ±2 包围盒导致视锥剔除，产品水 renderer 候选改 ±4，共享 owner 默认仍 ±2；新实现实机复验待完成，water gate 仍 False。
- 新 glint shader 修正原生 UV 变换顺序、半格偏移与 TILE_LIGHT_COLOR；编译与离线测试通过，新 shader 实机动画仍待。旧 dense capture 的后台间隔失败保留，不能改写为通过。
- 来源回归已冻结：旗帜 26／16／3 图，末地表面 31／28 图；刷怪笼候选 96／默认 78 图，每组 36 标识与 36 支撑检查通过，含隐藏／切面后 0.5／1.5 秒延迟观察。四组已启用资格的 worktree／staged 检查通过。
- 最新提交 `9631c3b1`（独立书本接线、共享包围盒扩展点、portal/spawner 回归），前一项 `e1d79450` 保存已验附魔台台身。书旧 61 图并未放实际占用块，agent 正补后重新冷启；新 glint editor 两剑消失，agent 正回到已知可见 shader 冷启。水同步完整 projection 闭包后 `b.project()` 异常未再复现，但 ±4 最终矩阵仍待。三个生产 gate 仍 False。
- 此前全量回归为 2,864 项通过、1 跳过，是旧源码基线；本轮定点 book owner 9、共享 liquid renderer 35、product liquid renderer 6、spawner 28 项已通过，故障注入 traceback 不代表套件失败。最终稳定后再运行一次全量。不要恢复任何嵌套代理。

## 2026-10-15 07:05 独立继续开发

禁止代理、08:00休眠不变；计划任务再次读回 Ready、shutdown.exe /h。最新提交 `d9054a6a` 已保存书 v4 外侧面修复、讲台页面原生对照、附魔台本体偏低证据和相关专项工具。下文 06:17 的 back-culling 候选已被否决，最终需要 InvertCulling，并移除 DisableCulling、DisableDepthWrite。

- 当前唯一 owned 游戏：owner `root-table-final-r17`，启动记录 `.runtime/r17-table-final-start.json`，project `D:/bbe-r15-native-production`。此前 `root-table-body-r17`、`root-table-integrated-r17` 已确认进程退出并归档。副本仍是 R16 冻结实现加选择性 R17 overlay，不是全 checkout。
- `.runtime/item-depth-dense-motion-r17-v4` 已完成和恢复；基础分析 `evidence_valid=True/all_bodies_passed=True`。高空标定通过，四路连续动画和普通物品负控有效；候选 glint 比原生偏亮，亮区质心速度比约 0.408/0.456/0.490，**不是纹理相位速度，不能据此盲目调快或授予产品资格**。world/native 四帧图已目检。v3 标定失败仍保留为失败。
- 附魔台静态 body 资源和 `static_table{,_data}.py` 已生成，导入链已修复；生成器现在独立写 JSON，不依赖液体生成器的业务导入链。`entity_render` 已接入 static_proxy 和 prepare_static_entities；3 项数据／图层／未知状态／来源保护测试通过。副本已冷启加载最终接线。`.runtime/book-table-integrated-r17-v1` 编辑器/full/missing 实机检查在运行（exec50501），确认 finally 恢复后再运行别的探针。
- table body 尚未生产验收、尚未提交；entity_render 改动导致 banner 来源资格失效，必须实机回归后再更新，不能只改 hash。其他三组 enabled 资格通过。全量 tests exec92914 输出 `.runtime/r17-table-alltests.log` 仍在运行；日志内异常可能为故障注入，要等最终结论。
- 书／物品／水 production gate 仍 False。五个用户 palette probes、其他 water WIP 保留。07:45 开始恢复／证据／交接收尾；08:00 休眠。

## 2026-10-15 06:17 继续开发检查点

仍禁止子代理，08:00截止并休眠，任务`Codex-BetterBuildingEditor-R17-Hibernate-20261015`再次读回Ready。唯一owned实例已经更换为session`a94b61bce9f64ba0bbb382b6c99f9ec6`、owner`root-book-culling-final-r17`，启动记录`.runtime/r17-book-culling-final-start.json`，project仍为`D:/bbe-r15-native-production`（R16冻结副本加选择性R17 overlay）。MC38856／MCDK3868仅供身份核验。06:00和更早实例均已停止。

- v4书资源已经安装主仓库和副本，并冷启动；修正底面绕序、候选back culling。修正后的raster alias不再额外添加`states: []`。`.runtime/book-v4-moving-double-r17-v1`19帧完成恢复，16个动态candidate帧覆盖68.8秒；真正的double负控再次复现密集斑点（已目检，自动检测拒绝）。默认v4同机位对照`.runtime/book-v4-moving-back-r17-v1`正在运行，exec68685；先确认恢复再修改游戏。10项book专项测试通过，但不能仅据静态测试宣布视觉修复。
- 附魔台本体偏移已经量化：`.runtime/enchanting-body-offset-r17-v1/report.json`36帧完成恢复，四方向原生台身／固定support对照显示，单独本体向上补偿0.125格恢复原生位置；红色纹样无图像平移IoU为1.0／0.9980／1.0／0.9774。`analyze_enchanting_body_r17.py`保存测量；尚无产品补偿接线。不要移动书pivot去掩盖台身偏低。
- 物品dense v2已结束，editor连续8秒229帧／最大72ms成功；world最大间隔169.7ms超过150ms门限而失败，finally已恢复，用户已明确获知。诊断工具随后将允许的间隔设为250ms，保留真实QPC时间、不插帧、不授予产品资格；尚未重跑。下次使用当前新session执行`.runtime/item-depth-dense-motion-r17-v3`，不能把v2失败改写为通过。
- 最新提交仍`0fcb3bc9`。v4书、动态诊断和物品工具WIP未提交；书／物品／水生产gate仍False。保留其余WIP及五个用户palette probes，不做全量stage。

## 2026-10-15 06:00 连续开发中的诊断状态

禁止子代理、08:00休眠不变。当前唯一owned实例：session`dc0a789e04944a328290dc55fa7e216b`，owner`root-book-animation-r17`，MC29124／MCDK7716仅供身份核验，启动记录`.runtime/r17-book-animation-start.json`；仍使用R16冻结副本`D:/bbe-r15-native-production`加R17资源。上一实例已stopped。

- 原始v3材质在`.runtime/book-original-near-r17-v1`固定三格观察平台重新出现斑点（65／54／17／11个孤立异常像素），19帧完成恢复；`analyze_book_surface_r17.py`会正确拒绝，专门的3项检测回归通过。此前无斑点的raster alias额外添加`states: []`，与原材质不构成单变量对照。`prepare_book_raster_controls_r17.py`现已修正为仅清理本来存在的state字段，新增2项约束测试，但**修正后的alias尚未安装冷启**。不能宣称背面剔除已经实测解决。
- `book-moving-back-r17-v1`被前景树叶遮住，不能验收；v2选址检查完整书体周围空气后干净。double对照也干净，故发现上述状态重置干扰。`book-moving-double-near-r17-v1`因host探针错误端侧调用在世界变更前失败并恢复；v2已修正。当前`--controlled-arena`可建空中固定三格观察平台并恢复原玩家foot和临时方块，避免新世界树木干扰。
- `book_model_geometry.py`改到v4，修正所有盒底面的反向绕序；generator候选采用back culling。10项book定点测试通过。`.runtime/book-hinged-cull-r17-v4`已生成，**主仓库和副本实际资源仍v3，尚未安装v4**。下一次冷启先安装v4，再生成不重置states的moving double/back/front诊断alias，验证动态对照和editor/full/missing。四个enabled资格暂不受这些未启用book改动影响。
- 连续物品动画新增`item_sprite_motion_capture.py`／`analyze_item_dense_motion_r17.py`与可选`--burst-exe --burst-sha256`。首次v1缺副本`_session`，未捕获burst，pipeline已恢复；依赖现补齐，独立1秒预检31有效帧／最大36ms间隔通过。**`.runtime/item-depth-dense-motion-r17-v2`正在运行，exec74022；先确认结束和恢复再动游戏。** helper是`.runtime/native_wgc/burst-build-r14/Release/native_wgc_burst_capture.exe`，SHA`82361ce558efc40dbde5bb272cb309f6cd68fa7c79e9087a6d3089f49443c0f6`。完成后先跑`analyze_visible_items_r16.py <report.json> <review-folder>`，再跑dense analyzer（参数report、review/analysis.json、新输出目录）。连续捕获失败需明确报告，不能当动画通过。
- `probe_native_palette_body_r16.py`新增`--body-offsets 0 .0625 .125 .1875`：分别生成table和固定support，核查原生台身偏低的具体偏移；此扩展尚未跑。原v2三种palette路径偏低证据仍有效。

上述诊断和v4生成器改动尚未提交，最新提交仍`0fcb3bc9`；水和其他物品WIP继续保留。此段是开发中检查点，不是停止工作指令。

## 2026-10-15 05:40 独立开发检查点

仍按用户最新要求：禁止子代理，独立工作至08:00并休眠；计划任务已读回Ready。`4876e3c0`已提交实际选框遮挡修复、书v3候选和末地表面新资格，`0fcb3bc9`单独修复原生actor校验的共享材质所有权边界。完整回归`.runtime/r17-depth-alltests-v2.log`为2,851项、297.156秒、OK（1跳过）；工作区和staged的四组enabled资格仍通过。

- `b91a7d2deed94ee695fae307fdf83e79`／owner`root-book-raster-r17`已正常退出，进程创建身份查询为空后重试stop归档。当前正启动`root-book-animation-r17`，启动报告`.runtime/r17-book-animation-start.json`；先读报告与真实session再复用，不能沿用旧PID。project仍为`D:/bbe-r15-native-production`，R16冻结副本加选择性R17overlay。
- 书v3产品23帧及原生同机位18帧均完成恢复，精简证据已提交。`.runtime/enchanting-body-palette-r17-v2`的20帧有效且已目检：原生直接palette、序列化roundtrip、prepare三路均出现附魔台台身偏低／与支撑相交。v1截图被未关闭workspace遮住，**无效**，不得引用。精确偏移仍待测，不用任意移动书pivot掩盖本体问题。
- 薄封面细点与后方方块选框是两项问题。固定time10的double／back／front近景及16方向double／back扫描未复现，不能证明culling修复有效；恢复真实旋转的`.runtime/book-moving-depth-r17-v1`33帧已完成恢复并目检，在多帧重新出现细密斑点。已准备moving三种剔除alias等待冷启，随后必须用真实动画对照。工具现增加实际BookProjection模型名回执，防止只登记未使用变体。
- 物品`.runtime/item-depth-final-r17-v2`广泛front矩阵因相机标定一处污染，evidence_valid=False，不能当全面通过。新放大`.runtime/item-depth-closeup-readback-r17-v1`有效且恢复，服务端／客户端回读stone→air后，full／missing实际物品恢复，四张动画拼图已目检；此前v1的画面石块残留未再复现，不确认为稳定产品缺陷。未改变runtime/F11写入。原生对照plain／enchanted形状在2px容差内precision／recall均1。
- 新放大glint颜色变化和覆盖充足，但稀疏帧亮区质心速度比例0.18–0.25仍未过门；它不等于真实动画速度。新增可选WGC连续采样工具准备核查采样混叠和真实运动，不放宽阈值或直接调快shader来迎合分数。`item_sprite_motion_capture.py`及相关host脚本WIP尚未实机运行。

当前水、物品、书生产gate仍False。保持显式stage；不碰五个用户palette probe和其他water WIP。截止前恢复夹具并更新本节，勿把诊断alias或反编译Java源码提交为产品资源。

## 2026-10-15 04:45 遮挡修复、末地表面重新资格化

继续独立开发至08:00并休眠，禁止代理。当前唯一owned实例是session `e47e110d34b54f729120afbf2b02a7a2`，owner `root-depth-final-r17`，project `D:/bbe-r15-native-production`，MC18088仅供身份核验；下方旧session均已正常回收。副本为R16冻结实现加R17选择性资源overlay，不是最新全仓库。计划任务仍Ready。

用户黑线根因已实测确认：后方真实方块选框覆盖未写深度的自定义表面，树叶／石头／玻璃都能触发。新发现无遮蔽展示架剑也受影响（半砖平台有效负控17／29→0／0）；证据 `docs/evidence/render-depth-r17-v1/shelf-item`。12条书／末地表面／图标／旧剑材质现在显式移除DisableDepthWrite，水与锅未改。旧native矩阵已完成恢复，采样旗帜正面可见且未复现；早期侧向／空actor截图不算验收。

末地最终资源名冷启检查 `.runtime/portal-depth-editor-r17-v1`31帧和`.runtime/portal-depth-world-r17-v1`28帧均completed/restored/source_unchanged，全部11张sheet已目检。新资格已写 `docs/evidence/portal-product-r16`，SHA `8679dbf644334aa12132531cd812dc00209f6d8968ccd561a173598c264dac0e`，四组enabled校验通过；旧证据备份`.runtime/portal-product-r16-before-depth-r17`。gateway是三个格构成L形，不能把预期轮廓误判缺面。

新书geometry v3、depth和icon资源已安装root及冷启副本，但仍未提交。`.runtime/book-hinged-final-reference-r17-v1`18帧完成恢复，同camera实图已看：讲台方向修正有效；附魔书封面有新发现的细密深度冲突点（极薄双面关闭剔除），原生/投影附魔台顶面相对支持块也不同，需继续独立核对，不混作黑线原因。书产品23帧探针exec65280运行中，先确认恢复。候选gate均False，不得直接开启。下一步先完成当前book检查，再跑新depth的visible item回归，然后仅在冷重启前安装书culling/薄面候选；不在活跃capture时改资源。

上个提交701cb043仅保存诊断和原对照，不含实际材质修复。保持显式stage，不碰五个用户palette probe及无关water WIP。

## 2026-10-15 03:55 选框穿透已复现，继续独立开发

仍禁止代理，08:00截止并休眠，计划任务Ready。最新唯一owned MC session=`7935726409c84528b9505d137947dc2e`，owner=`root-books-depth-r17b`，project=`D:/bbe-r15-native-production`，MC4364仅供核验；复用前读session状态。下面02:20及更早实例已回收，不再使用。

用户书本黑线已确认是后方真实方块选框穿透：树叶／石头／玻璃均复现，原生alpha父材质关闭深度写入；显式开启后消失。旧书20帧、新铰链书／讲台／折跃门／锅／营火100帧、锅与末地门顶面半砖对照48帧均完成恢复。自动分析旧书和新书、折跃门的air重复稳定、off负控敏感、on内部零变化，精简证据`docs/evidence/render-depth-r17-v1`。锅表面本次未复现，不能全局修改水／图标材质。native族矩阵`.runtime/depth-native-families-r17-v1`仍运行（exec9574），先确认完成／恢复再修改同实例。

书参考`.runtime/book-hinged-reference-r17-v1`14帧完成恢复；讲台默认候选方向错90°，额外`.runtime/book-lectern-turn64-r17-v1`5帧证明uniform+64方向对齐，但夜间光照不能用于最终亮度接受。新geometry v3在模型中固定该90°坐标转换；主仓库生成资源仍v7。generator源与新`book_model_geometry.py`未提交，`.runtime/book-hinged-r17-v2`待安装冷启。portal generator也新增显式depth write，`.runtime/portal-depth-r17-v1`待安装冷启，尚未更新生产资源／资格。参考probe已加clear-noon保存恢复及诊断方向参数。

新增深度准备／探针／分析和材质继承审计工具，7项针对性测试通过；book atlas test通过。main文件已有其他R17未完WIP，严格显式stage；五个用户palette probe不碰。后续先完成无遮蔽物品和native族调查，再冷启最终book/portal候选做完整普通路径与透明度／占用恢复，随后更新资格和提交；不要把资源hash更新等同实机通过。

## 2026-10-15 02:20 用户黑线纠正与遮挡调查（优先）

用户指出的横线来自后方树叶，**不是**此前修复的 atlas 黑色 padding。01:46“修复用户黑线”的表述不成立：v7 只修复另一项 UV 黑边。当前截图显示类似原生准星方块选框穿过投影书封面；`entity_for_skeleton_alpha` 原生继承 `DisableDepthWrite`，书／图标／末地表面共用该继承路径，具体受影响范围仍需实测。必须区分真实树叶表面与选框，不能全局修改流体透明材质。

`.runtime/book-depth-{off,on}-r17-capture-v1` 完成恢复，但动画冻结没有生效（两帧姿态不同），所以 **addon reload 后的材质／shader 对照无效**。随后 `ReloadAllMaterials()` 导致 owned MC36448 失去响应，已通过 session/owner 受管回收（所有夹具此前已恢复）；旧 session `8b5bb11bf3cd4881acb9eec560e6d955` 已 stopped。正在冷启动 owner `root-depth-r17`，启动结果 `.runtime/r17-depth-start.json`，不得复用旧PID。

新增未提交诊断参数：book generator 的 `--depth-write-control`、`--animation-time-control`；reference probe 的 `--case`、`--samples`、installed source hashes 和 `PickFacing` 回执。只修改隔离副本，不代表生产启用。书几何／折叠／UV／讲台暗色和底座穿插仍未修复。Java独立参考模型位于 ignored `.runtime/java-water-study-20261013/books-r17/decompiled/fus.java`（真实双封面／书脊／双页体／翻页片），勿提交反编译源码。

## 2026-10-15 00:42 独立恢复第十七轮

01:46进展优先：完整回归2,841项／288.869秒／OK（1跳过）；图标源提交`e13ae3cf`。书本已找到有效原生参考：`.runtime/book-reference-r17-matched-player-v8`、`book-reference-r17-geometry-v9`，近眼高、实际玩家视角，native书可见；原脱离相机无书证据不能作外观依据。实际朝向与候选保持一致，玩家rot会恢复。v9 NBT rott导出约0.40 rad/s。生成器候选采用竖立idle书、讲台1.04高，转速0.4整周期回绕，最新v7修复用户书页／封面黑线（UV包含原图不透明黑padding；现在每面取有效texel中心）。`.runtime/book-product-r17-v7/report.json`23截图、completed/restored/source_unchanged均true，编辑器和full/missing投影可见，4项book tests通过，四enabled bundle校验仍通过；精简图`docs/evidence/books-r17-v7`。生产book仍False；本体底部条纹、附魔台body高度差和完整姿态校准／接线未完成。当前独占游戏reload_addons仍same session，副本只更新书v7资源，未同步icon等主分支最新源。无正在运行的书探针。保持独立开发直到08:00，禁止代理。

01:18补充：icon候选现在拥有独立`item_icons/skeleton.json`，900条注册不再共享legacy骨架；骨架字节进入资源指纹，17项icon tests和生成器check通过，四组enabled render qualifications仍通过。同期保留450个side-UV候选mesh，不表示侧面／附魔最终实机资格通过。完整R17回归日志`.runtime/r17-solo-alltests.log`运行中，不能引用为已通过。

书本原生参考v5（真实物品放置）16帧恢复成功，但目检真实附魔台／讲台均无书，不能用于校准；讲台实际aux2而候选原aux0的对照缺陷已修正。v6 attached玩家视角被正上方支撑块遮挡，不能证明原生书缺失；v7正在用附近眼高空位验证。工具`tools/probe_book_reference_r17.py`记录真实方向、NBT、恢复世界／库存／玩家朝向。当前唯一MC为session`8b5bb11bf3cd4881acb9eec560e6d955`、owner`root-solo-r17-protected`，project`D:/bbe-r15-native-production`；MC36448／MCDK37840仅供身份核对，不按PID直接操作。该副本是冻结R16书本候选，非主仓库最新资源。

用户要求继续开发至今天08:00并休眠，明确禁止使用任何子代理。主会话独立执行，旧代理不恢复。Windows任务`Codex-BetterBuildingEditor-R17-Hibernate-20261015`已从07:00改为08:00，实际读回Ready、2026-10-15T08:00:00+08:00、shutdown.exe /h。保持dev、不push／合main，后台实机测试和最多5游戏限制继续生效；启动新实例时必须取得新session身份。先修复已复现的EditJob跨批次成组编辑，再按有效证据推进渲染缺口。暂停检查点提交为ab05e6a5，R17未完源码保留工作区。

## 2026-10-14 23:45 用户要求暂停以切换模型

本节优先于以下连续开发计划。用户最新要求先保存上下文，然后终止本会话、所有子代理和全部打开的Minecraft实例。已停止新开发，实机代理执行恢复与身份绑定回收，主会话仅保存检查点／已验证提交／核对停止状态。切换后等待用户明确继续，不自动恢复代理或游戏。

分支仍`dev`，不push／合main；五个用户`tools/p0_palette*_probe.py`未编辑、未stage。07:00休眠任务仍保留（用户未取消），原计划为第十七轮截止；如下一次恢复改变截止或休眠指令，以新指令为准。下方23:30处的运行中实例均为历史身份，不可直接复用。

### 第十七轮暂停时的真实增量

- `render_contract_review_r17`完成工具级漏洞修复：`tools/verify_render_qualifications.py`现核对冻结资源契约、资源字节和shared registry的owned entries；无关新条目不使已有资格失效。9项focused负控测试通过，当前四个enabled bundle全部通过（锅31／旗帜4／门16／刷怪笼9个资源检查），没有改runtime或资格hash。新icon复用的`item_sprite/skeleton.json`仍漏入契约，必须补依赖后再资格化。
- `data_layer_regression_r17`复现新缺陷：512格选区EditJob计算批次错误限制成组伙伴，门替换结果0；`jobs.py`提前恢复完整selection的两行WIP使replace正确，但checker跨批仍上半AIR／下半stone，而小文档两半stone。未提交、未写新tests，不可当完成修复；恢复时需有界伙伴请求处理，先读`.runtime/r17-data-layer-checkpoint.md`。
- `water_qualification_r16`独立新增`liquid_product_render.py`／`liquid_product_projection.py`与profile factory，10focused tests通过。共享`liquid_projection.py`已恢复原字节，`world_projection.py`未接线；owner数据未regen，生产False。v19同高度horizontal近x3水可见、远x63水缺失而stone可见，但远terrain也未加载，尚不能区分距离／chunk context。测试已恢复，自有v18／v19及MCDK均退出。交接`docs/evidence/water-product-r16-v1/HANDOFF_MODEL_SWITCH_2339.md`。
- `visible_items_r16`新icon side-UV候选／独立侧面分析器仍需实机资格和完整姿态矩阵；与R16已提交旧生成器修复分开。16focused tests通过，实机原生对照仍失败；front plane14.75替代15及side normal lighting仅为未应用假设。最终源码、附魔与icon skeleton闭包尚待核对，生产False。检查点`.runtime/r17-visible-items-checkpoint.md`；MC16920／MCDK34588确认退出，session`797034991a5740ff82d420038f193ec5`为stopped。
- `banner_special_r16`真实world book同camera参照完成16capture、completed／restored均true、cleanup_errors空；真实方块回读恢复air，库存／UI／camera／临时classes已归还。原件`.runtime/book-reference-r17-v1`和工具`tools/probe_book_reference_r17.py`保存，但尚未目检，不算资格。亮度／高度／旋转方向及editor讲台书缺失仍开。
- `shelf_body_r17`仅有atlas源核对与两个独立host工具，未生成Shelf runtime／mesh。新instance启动120秒未ready，尚未执行夹具或相机／world写入；应正常关闭session`4c41d4cf0634408589edd389667c8b03`（MC54368／MCDK50728），不把启动算实测。
- `native_dynamic_audit_r17`独立工具`tools/audit_dynamic_routes_r17.py`通过语法和3项既有blueprint tests，但未实机跑，prismarine别名的flipbook_indexes映射须修正，约300ticks／15s每帧。七种头颅有效源、伸出活塞本体＋辅助臂、原生岩浆和普通动态三路径仍待；旧SkullType255不能用于原生不支持结论。
- `block_item_models_r17`／`item_tint_families_r17`／`special_items_plan_r17`主要保存研究，无产品完成新增。1,338个block物品不能直接以Damage映射block aux或当cube；应先诊断3.10原生BindItemToSkeletonModel。命名spawn egg用物种PNG、药水真实aux纹理映射可复用；leather/firework TGA颜色尚未测。ID级unsupported混入无效aux，不代表整个ID不支持；map raster／shield atlas等依赖仍未解决。

### 独立检查点

恢复时先读本文件、统一待办和外观附件，再按实际要接手的专项读取：`.runtime/r17-render-contract-checkpoint.md`、`.runtime/r17-data-layer-checkpoint.md`、`.runtime/r17-native-dynamic-checkpoint.md`、`.runtime/r17-block-items-checkpoint.md`、`.runtime/r17-item-tints-checkpoint.md`、`.runtime/r17-special-items-checkpoint.md`、`.runtime/r17-visible-items-checkpoint.md`、`docs/SHELF_BODY_R17_CHECKPOINT.md`以及水的tracked交接。`.runtime`检查点本地保留但ignored；关键结论已在此收敛。WIP源码保留工作区，不用reset/revert用户或代理变更；恢复前先检查git diff和门控，最后一次2,817项全量结果是R16冻结源，不能自动算R17未完源码全绿。

23:47实际进程检查没有任何具有活动句柄或有效路径的Minecraft；历史零句柄／无路径进程记录不能当作活动游戏。用户3.9 PID40452此次依照“全部打开MC”新授权核对path／创建时间后关闭（无窗口）。此前“不操作用户40452”适用于开发测试，不阻止本次明确的关闭要求。

## 2026-10-14 23:30 第十六轮检查点与第十七轮接续

本节优先于下方历史安排。第十六轮23:30结束后无缝进入第十七轮，持续至2026-10-15 07:00（Asia/Shanghai），届时休眠而非关机。用户最新授权最多10个活动子代理；活动MC仍最多5个，含用户3.9 PID40452，该用户实例不操作。继续在`dev`，不push、不合main、不清工作树。模型继承用户选择的`gpt-6.1-sol (ultra)`。后台测试不focus／resize／桌面输入；用户自行前台观察不暂停，捕获不可靠必须报告。

一次性Windows任务`Codex-BetterBuildingEditor-R17-Hibernate-20261015`已登记并验证：下次运行2026-10-15T07:00:00+08:00，`C:\\WINDOWS\\System32\\shutdown.exe /h`，Ready、WakeToRun。07:00前先恢复夹具和保存进度；不要重新启用旧R15任务。

- 提交`06831f59 test: diagnose missing native shelf bodies and verify render provenance`、`27362111 fix: extend versioned block appearance adapters and item geometry`已保存。后者包含生产刷怪笼标识、旗帜editor静态深度、末地门／折跃门表面、物品与书候选及精简证据；不表示水／物品／书默认资格通过。此检查点后出现的R17 icon side-UV改动尚属候选，须独立提交。
- 最终完整回归`.runtime/r16-alltests-geometry-final.log`：2,817项、431.123秒、OK；此前2,815项也通过。运行时223文件白名单无违规。工作区与staged的锅／旗帜／门／刷怪笼来源校验均通过；Git保存实际测试字节，不能用改写hash掩盖换行差异。
- 物品生成器west／east暴露邻居确实反向，已修复并重生成48旧模型和450新icon。修复后侧视可见，但同物品／同相机／足够尺度的plain剑仍有分段侧边：product52×161、native55×161，独立side mask recall0.93255、precision0.94401。不是已证实厚度不足；新icon采用opaque-texel-center side-UV候选正在R17对照。48＋12姿态与最终源附魔复验仍缺，生产False。
- 附魔双层原生纹理v3的157／158px近景三路径证据已通过有限可见性，旧正弦方案失败保留；后续侧面几何变化要求最终源复验，用户亮度／原生外观问题不由有限光效通过关闭。
- 青色`cyan_concrete`在同坐标、同camera、无书／物品／水的actual-world与normal full projection对照中，投影顶面／侧面边界有背景色细线，真实块无此线。有效v2读回和恢复完成，证据`docs/evidence/cyan-seam-r16`。这是普通投影缺陷；mesh、UV、MSAA、深度或变换原因未定位，用户截图的竖边尚未完全隔离。不盲目膨胀所有方块。
- 书候选v4已见附魔台常驻浮动／旋转和world讲台书，但editor讲台书缺失；用户指出亮度、浮空高度、旋转方向不对。下一步真实世界原生书同camera连续帧参照，而非空palette基准。book生产False，原始19帧原生观察／23帧候选均保留。
- 水R16覆盖57／57 case-route、12／12 alpha、54／54独立切面、108／108生命周期；35源闭包未变。world侧UV、冷构建103／157ms、远距／context、三路径动画／群系、精确占用、反角度、gallery、普通默认冷启九类仍开，生产False。同v18、固定玩家foot的远Y3／近Y-61对照已复现远水缺失而native stone可见；具体剔除原因尚未确认。R17 texture-center独立诊断editor两面／world south吻合，world east仍明显不符，不拟合图片放宽门槛。
- Windows句柄增长原因未定位，不能当已证实模组／GPU泄漏。水v18 PID37732已因超预算回收；启动新实例必须核对当前owner、session、创建时间，不能按历史PID批量操作。

### 第十七轮分工与接续顺序

10个子代理：`water_qualification_r16`（水）、`visible_items_r16`（侧面／附魔）、`banner_special_r16`（真实书参照）、`shelf_body_r17`（架本体）、`block_item_models_r17`（3D方块物品）、`item_tint_families_r17`（颜色家族）、`native_dynamic_audit_r17`（动态／头颅／活塞资格）、`data_layer_regression_r17`（数据／成组回归）、`render_contract_review_r17`（来源及架构审查）、`special_items_plan_r17`（特殊内容家族）。后六个先离线，不自行启动游戏；主会话负责青色接缝、实例分配和整合。

23:35附近在用：user40452、items16920、books45248、水v19 PID48680（session`9966378c03354934b8e607e3b6245e94`，owner`water-product-r16`）。Shelf获第5槽15分钟短测授权，完成后回收供root使用；进程状态随时变化，以上不是可直接操作的身份凭据。

水冷构建拟用water-only renderer，避免改变已资格化共用文件；`liquid_projection.py`属于锅／门来源闭包，修改会使旧资格失效，不能仅保留旧hash。代理需优先考虑独立product projection子类／工厂，在冻结入口整合后再验。五个用户`tools/p0_palette*_probe.py`继续不编辑、不stage；不可`git add .`。本轮增量任务仅在`IMPLEMENTATION_GAPS.md`维护，技术依据在外观附件。

剩余工期尚在按10代理的实际任务重估；不得把旧3代理10–18小时估计直接除以代理数量，也不得根据通过测试数换算百分比。完整NBT可见物品特殊家族与最终集成是主要不确定性，先核对现有范围和source证据。

## 2026-10-14 第十六轮历史进行记录

本轮截止为今天23:30（Asia/Shanghai），没有休眠任务。继续在`dev`开发，不push、不合main；用户指定`gpt-6.1-sol (ultra)`，最多3个活动子代理、5个活动MC。第十五轮最终结果仍以下方17:20检查点为准，本节仅登记本轮进行中的工作，不代表新增资格已通过。

- `water_qualification_r16`：水默认冷启、side UV／切面／邻域／透明排序及预算，先补实机证据，再决定精确3.10生产资格。独立副本`D:/bbe-r16-water-production`，owner`water-product-r16`。
- `visible_items_r16`：通用可见物品／附魔和框槽位，资源来源及家族参数分开；特殊物品不静默降级。owner`visible-items310-r16`。
- `banner_special_r16`：旗帜v6b家族契约及editor变换／图层／缩放／切面、world回归；完成后继续特殊表面。使用隔离副本`D:/bbe-r15-native-production`，owner`banner-special-r16`。
- 主会话：刷怪笼配置有／无／未知标识、原生动态族产品验收、共享入口接线和最终证据／文档／提交整合。共享Session／Scene／bridge等源变动要同步给水资格负责人，防止冻结旧源。cauldron及native已冻结字节契约不得无解释失效。

18:17实时核对只有用户3.9 PID40452有活动句柄；其他历史MC记录均零句柄，不按旧PID批量杀进程。该用户实例不操作；三个代理各最多1个实例，主会话最多1个，总量含用户实例不超过5。继续后台测试，不主动focus／resize／桌面输入；用户自行前台观察不暂停。截图或夹具不可靠必须显式报告。五个用户`tools/p0_palette*_probe.py`不编辑、不stage；不能`git add .`。

### 22:40接续增量

- Root检查点`06831f59`已保存Shelf缺本体四向对照、负控分析器和实际／staged资格来源校验。root实例PID14632及MCDK22336已正常退出；不复用历史身份。共享功能与精简证据正在显式stage，不push／main merge。
- 刷怪笼、editor旗帜深度及末地门／折跃门表面有限范围已默认启用，锅既有资格保持。`verify_render_qualifications.py`工作区四包通过。首次staged检查抓到3个未改动共享文件的Git换行差异，现用精确字节属性和定点renormalize保存实测CRLF，不改写实机hash；后续仍须重验staged。
- 水world全空并非已证实shader错误：相机在测试平台附近但真实玩家约65格外。移近玩家后几何／透明／切面通过；同代码不同干净实例的远近对照尚不足确定剔除阈值，保留实际远距可见性限制。侧UV两面0.814／0.683和一次约157ms冷构建未达门槛，生产False。来源35闭包未变。
- 附魔v3有效原生157／158像素放大对照已通过三路径可见性；完整姿态未完成，生产物品False。用户新增贴框／无侧面：已确认共享silhouette_cubes左右暴露邻居检测反向，正在取before并做最小修复；影响旧3.9禁用候选及450新icon资源，生成器／资源须一起更新，最终回归需覆盖冻结后的源。离框位置／侧面照明仍待实测，不能靠有厚度字段关闭。
- 用户两张讲台青色支撑截图疑似竖边接缝，banner专项补真实方块／纯Combine／无书对照。截图雪山背景与该专项森林实例不同，不假定它是同实例。book候选仍False，讲台初版实际未见书，附魔书初版偏平；最终候选在测。
- 第一遍2,815项全库失败的book空actor、水mock类型和actor材料适配hash已focused修正，第二遍日志`.runtime/r16-alltests-final.log`正在运行；没有完成前不得写全绿。若随后修改共享物品生成器，必须以最终冻结源补相应回归／第三遍，而非引用修复前结果。
- 句柄持续增长是未定位的V06环境／资源问题，不等于已证实模组或GPU泄漏。短批重启只是风险控制。完整raw仍保留ignored `.runtime`，提交只选精简review及来源回执，用户五探针不stage。

## 2026-10-14 17:20 第十五轮最终接续点

本节优先于下方所有暂停／恢复记录。分支`dev`，不push、不合main；本轮17:30停止，无休眠任务。用户选择`gpt-6.1-sol (ultra)`，最多3个活动子代理、5个活动MC。三个专项已完成本轮操作、正常停止全部自有游戏，没有残留exec；未受管用户3.9 PID40452不得按旧PID回收，恢复时先核对实时身份。

17:29最终进程检查纠正了上午旧clean实例已停止的说法：13804仍有687句柄，命令行／创建时间确认属于session`e150444343dd46f0a0f791b165872648`及owner`clean-nemc310-runtime-audit-r15`。此前夹具已恢复；正常stop未退出，随后仅对此受管身份执行`stop --force`成功，游戏13804及MCDK44480已回收。没有操作用户40452，也未按零句柄历史记录批量杀进程。

### 已交付与验证

- `f46e5e66 fix: preserve native banner patterns and transformed world poses`：旗帜render-only方向适配、图案无损及world静态有限准入；保存NBT不变，editor和飘动不由此放行。
- `fcb7952e fix: render biome-aware cauldron contents and isolate custom water`：shared水ownership、native-less纯水发布／空状态修复；锅专用计划／preview／projection、版本化实测数据和资源、精确3.10默认资格；公开7个动态和7个NBT分页及33例锅。锅纯水调用`biomes.water_appearance(document.biome)`，药水／CustomColor独立。默认三路径平原→沼泽→平原已看图。
- `d349f804 fix: preserve qualified cauldron source bytes across checkouts`：确实发现Git旧过滤把部分实测CRLF转LF，已用`-text`及定点renormalize保存原始source／data／receipt字节。14个源／数据与95个资源／证据blob逐项核对；不是改写实机hash。生成vertex三个空白行保留，属性只针对这两个冻结文件处理blank-at-eol检查。
- `655c0834 test: preserve water transparency and biome acceptance evidence`：提交约1MB review包、源闭包审计、host多owner选择／群系重发布、像素负控与证据生成工具。完整raw仍本地，不因这些证据修改水生产资格。
- `eed00305 test: archive measured banner editor depth candidate`：保存v6b源／原生差分／编译报告、10组已看截图／捕获／状态回执及数值测量；已归档native receipts的原始换行也固定。不是生产shader改动。旗帜剩余家族集成与静态矩阵约1.5–3小时，飘动另计。
- 全仓库`python -X utf8 -m unittest discover -s tests`为**2,719项／474.663秒／OK**，日志`.runtime/r15-alltests-latest.log`。其后锅全14预设×6纯水位及药水／RGB不变性补测，锅专项27项；水host／biome负控及analysis专项25项；debug蓝图28项。203运行时文件白名单无违规。专项通过没有冒充第二次完整回归。
- 锅产品资格`docs/evidence/cauldron-product-r15/qualification.json`绑定12源、资源与证据；保留56文件约44MB，原始165MB在ignored `.runtime/cauldron-product-r15-raw/`。10个独立near-view case×3路径，不冒称33例逐格三路径全测。
- 水最终review约1MB：`docs/evidence/water-production-final310-r15-v1/review/README.md`。最终36alpha／本体图、4world east/falling burst、9纯水几何、editor纯水内容和missing pool占用／恢复、三路径biome均有正例。root已看alpha/body/biome/锅及native候选截图。保留旧动画伪透明度失败和初版80%biome阈值失败，不改原始捕获。完整zip／burst原图留本地，精简包不是独立raw重放包。
- `tools/audit_water_source_closure_r15.py`和`source-closure-audit.json`核验两份完整ZIP的每个member。最新biome snapshot `fb2dccac...`与当前35owner、专属资源／注册完全一致；final `a01f2884...`只差`liquid_deployment`、`liquid_product_deployment`、`session`中的引擎门控和锅默认接线，没有水shader／mesh／texture变化。owner contract为`f783b06b...`。

### 恢复顺序与明确缺口

1. 水`liquid_product_qualification_data.PRODUCT_QUALIFIED`仍False。现有实机均显式注入candidate。下一步补普通Session默认资格的精确3.10三路径冷启、相邻side UV连续性、切面／部分实块邻域／隐藏恢复及透明排序／模型／tick预算，再冻结资格。不要再次把candidate通过直接写成默认已验。
2. banner editor深度v6b是成功隔离候选，代码仍在`D:/bbe-r15-native-production`，未复制生产shader。测得banner/pole家族原点450、native-to-block比例约0.64，不适用于其他actor或新引擎。源快照、差分、测量、编译限制与正常停止在`docs/evidence/native-render-profile-r15/BANNER_EDITOR_DEPTH_DIAGNOSTIC.md`及`depth-candidate-v6b-sources/`。原生GLSL100 skinned `mat3x4`基线失败仍保留，不声称所有variant编译通过。下一步版本化家族契约、生产变换／图层／zoom像素及同shader世界full/missing／占用复验，再准入；飘动另验。
3. 通用可见物品和附魔、展示架／营火／讲台等内容、常驻附魔书、末地门／折跃门、头颅／活塞静态臂、普通动态族、刷怪笼有／无配置生物标识，以及最终含雪／连缀集成仍待。默认空NBT样本不能替代非默认外观样本。
   17:25已复核默认表：MobSpawner有type8空`EntityIdentifier`；TrialSpawner的两份config没有配置生物字段，`current_mobs`不是配置存在性，默认试炼样本只能记未知。先补真实正／负／未知公开case，不能猜Java字段。离线NBT审计生成器还保留归档scope分类名，后续规划元数据更新须同步当前排除项和I类标识，raw证据保持不变。
4. 继续保持用户范围：粒子、教育、moving_block、信标／导管激活、宝库内部物品特效排除；固定居中植物是设计。原生世界岩浆允许，锅内容自定义；本次不更新3.9 registry／transform表。
5. 估计从本轮最终状态继续还需**10–18小时有效墙钟，风险18–28小时**，主会话加3代理。锅关闭与水诊断节省不全部作用在最长专项上；详细并行流见技术附件。不要用测试数量或经过时间换算产品完成率。

最终文档提交ID见`git log`和本轮最终回复。五个用户`tools/p0_palette*_probe.py`保持untracked，不改不stage；大量完整raw证据和未完成探针仍只留本地，不能`git add .`。恢复时先读统一待办和技术附件，再按实时身份决定是否启动新游戏。测试不主动focus／resize／桌面输入；用户手动观察前台时照常继续，捕获／夹具失败须显式报告。

## 2026-10-14 16:35 增量（优先于下方恢复／暂停记录）

- `debug_compatibility_blueprints`新增7个动态、7个NBT分页，已登记普通玩家的测试蓝图页。资源候选48名称和默认NBT155名称来源覆盖测试通过。独立case提取会rebase已知空间字段，内容／类型／未知字段保留。完整MD映射已写入外观附件。还需要逐族实机资格，不把生成蓝图等同于支持。
- 炼药锅10个near-view case × editor/full/missing，六岩浆液位、RGB／药水／纯水／雪、动画、占用／恢复和切面／33例gallery均已看图。`cauldron_deployment.production_profile(engine_version)`已由Session调用，仅精确3.10启用；完整来源／资源／实现／证据哈希门控，精简证据32文件约24MB。原始165MB存ignored `.runtime/cauldron-product-r15-raw/`。最新冷启动默认入口及plain→swampland实机继续由`r15_cauldron_live`执行；其首次测试空域被天然草块preflight拦截，未写世界且恢复，改抬高测试空域。
- 最新水source archive `a01f2884...`的36透明度、4world东向／向下burst、纯水editor空状态、missing pool实际占用恢复均完成；root已看两份contact。实例已正常停止。`r15_water_live`补最后三路径群系切换；产品仍False，不能静默启用。root新增exact3.10调用参数与qualification engine字段，owners contract扩到35个源，未知版本返回None。
- native editor旗帜depth仍未通过，候选仅在隔离副本；world-only banner静态准入已完成，root尚未提交。源shader没有因试验更改。v4斜视仍被石块错遮挡；代理继续一次数值诊断。
- 全仓库第一遍回归发现测试GBK默认读UTF-8 shader及actor材料manifest旧hash。只新增8个cauldron材质，旧定义逐项结构比对零更改；已更新适配hash而保留原生源／dump hash，并修正test显式UTF-8。版本bundle14项随后通过。最终全仓库重跑输出在`.runtime/r15-alltests-latest.log`，尚未完成时不能引用为全绿。

17:30截止，不休眠；仍在dev，不push/main merge。最多3活动代理、5游戏。五个用户`tools/p0_palette*_probe.py`继续不改不stage。最终commit和停止状态在收尾后追加。

## 2026-10-14 15:30 恢复开发（优先于14:05暂停与上午记录）

**15:40用户缩减范围：** 激活导管／持续特效、moving_block、信标光束、宝库内部物品特效、教育版排除；附魔台仅常驻书动作。刷怪笼生物模型仍排除，但新增统一“有／无配置生物”的替代标识F03-SP01。火／灵魂火原生能力与三路径资格分开记录。当前剩余估计**11–20小时有效墙钟、风险20–30小时**，替代下方15:30暂估，不继续追查已排除的外观。

用户切换至`gpt-6.1-sol (ultra)`后恢复第十五轮，最多3个活动子代理、5个活动MC；17:30截止、不休眠。分支`dev`，不推送、不合入main。三个活动专项是`r15_water_live`、`r15_cauldron_live`、`r15_native_live`；旧沙箱代理保持终止，不再次唤醒。当前改动未全部提交；五个用户`tools/p0_palette*_probe.py`不修改不stage。

- **水根因已确认并修复接线。** `docs/evidence/water-native-duplicate-r15-v2/report.json`六图固定相位、独立Combine名称：原路alpha0仍有原生蓝水，移除原生水后alpha0正常透见栅栏和后金块，默认.45半透明、alpha1不透明。主会话已看图。新`liquid_render_ownership`根据profile声明排除两层原生水，仅处理detached draw；完整文档、NBT、target与逻辑邻域保留，原生岩浆保留。geometry_palette、bridge、context、cache、world、occupancy均接线；删除自定义前景水后再提升剩余原生背景本体。ContextBatchBuilder纯自定义格保持分帧。纯水无原生网格允许投影发布／占用隐藏恢复，真实Combine失败仍报错。方向15项旧通过保留；修复后新三路径透明度仍在实机采集。
- **炼药锅已接共享链。** Session candidate默认None；独立CauldronPreview／controls、WorldProjection companions、原生空壳适配、profile cache identity、诊断／可见错误／retry，以及独立公开蓝图已接。专用模块复用原LiquidPreview／LiquidProjection生命周期。生成数据核验21份测量来源，六档高度和雪高度、RGB／药水形态均有依据。普通水采用document biome预设的产品样式与独立灰水纹理，精确原生锅水颜色未接受；药水和CustomColor保持实际独立颜色。三路径实机进行中，不默认放行。
- **实入口错误已捕获修正。** 首次product water测试遇到`SurfacePalette`没有biome，已保留失败并恢复；bridge从完整document读取biome，裁剪palette从当前session document获取。离线新测试直接覆盖真实ClientBridge.geometry而非仅供假bridge。scene恢复viewport会invalidate cauldron controls。
- **旗帜有限世界资格整理中。** ordinary／3pattern／6pattern的identity、rotate90/180/270、mirrorX/Z world图和missing隐藏恢复已由专项查看。render-only native actor以当前状态刷新bannerDirection，保存NBT与图案不变；拟只启用world model_local静态子集。源世界旗帜缺失的对照不能证明原生视觉等价，editor深度和飘动仍待。
- **最新相关测试：** 首批114项通过；新增ownership、SurfacePalette、cache、纯水full/missing／occupancy／关闭cleanup／真正native failure回归均通过。更广集成与MOD结构review待本轮最终记录。不能把单测数或未读截图计为像素验收。

当前有效实例须按owner/session再查：水第二次product owner `water-alpha310-r15-product` / `bcb751aa241144dda77ed25768f523d9` / PID19216；炼药锅 `cauldron-product310-r15-live` / session由专项记录 / PID49848；native旧13540完成旗帜fixture恢复后准备回收。clean13804夹具已恢复并释放；旧cauldron32868、water43268/32396与native47968已按所属身份停止。未受管用户3.9 PID40452保留。所有测试不主动focus/resize/桌面输入，用户自行前台观察照常继续，失败捕获显式记录。

剩余时间已重估为16–28小时有效墙钟，风险28–42小时，按主会话加3代理。水／锅约3–6小时、通用物品约8–14小时、特殊NBT与动态12–19小时并行，加最终集成4–7小时；具体状态与估计只在统一待办和技术附件维护。不能保证17:30完成全部范围。

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
