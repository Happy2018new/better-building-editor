# 新对话交接：现代化投影建筑编辑器

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
