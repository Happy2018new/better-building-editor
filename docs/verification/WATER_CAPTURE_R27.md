# R27：水采集尺寸与编辑器单例诊断

本页记录2026-10-21 23:30开始的水专项。沿用私有41源项目 `water-r25-final41-v2`，source合同 `a564563ecf20f74b786565aaf0516575ab34c448b370a2bb2199319dc6b5c194`、owner合同 `d0f37c33f8e054a0e906f44361edc43f49957b26b4af7853da9f2c0ca49bf20f`，4479源／1391辅助文件，原bootstrap core `088ae57b8ea713b7881a01b94b4289cb7b04f7e17f791d17fc2bf2be2b49fa26`。不是当前主仓全部来源的最终合流资格，41源也不是完整传递依赖闭包。

原旧S0的636.6348ms起始缺口仍保留。原逐poll／FrameArrived记录说明worker持续有界等待而callback断供，不能区分game、DWM、WGC或driver；lifetime诊断没有复现，不解释旧失败。本轮选择实际客户区从1994×1105降至1280×720，以减少画面像素／拷贝负荷；准备1500ms、测量3200ms、最大间隔150ms、512MiB计账上限不变。诊断helper不授正式动画A、最终owner或默认冷启D资格。

## 两次前置失败保留

| 独立尝试 | 实际观察 | 限制及收尾 |
| --- | --- | --- |
| size720-v1，owner `water-r27-final41-size720-v1` | 冷启114.7s、单次bootstrap12.7s成功。新尺寸host遗漏DPI初始化，尺寸断言读到1287×738，未进入camera／A | 属host准备错误，不能算水A失败。独立marker／actor恢复通过、源不变、普通stop0；精确game `26232 / 134370708677114537` 退出 `0xC0000409`，MCDK0。原host／stdout／stderr／回执不改 |
| size720-v2，owner `water-r27-final41-size720-v2` | 复用现有border helper和DPI设置；物理Per-Monitor V2实际1280×720、logical读回853×480、DPI144，前后台身份相同。额外world-camera门中front／right通过、tilted失败，尚未进入A | 原camera completed／restored为true、passed为false；独立恢复通过、源不变、普通stop0。精确game `65608 / 134370713961404219` 退出 `0xC0000409`，MCDK0。不能称正常引擎退出或新相机资格 |

v2资源接近6GiB门时，子代理对本任务Python group宿主执行一次17.47s挂起，父代理要求后立即核对PID31408及create_time1792597781.016246恢复。game／MCDK、bootstrap子进程和guard未挂起，bootstrap实际已通过当时7.70GiB前置门并派发。此干预及pause／resume回执完整保留，v2不能当作纯尺寸单变量时序实验；没有采集动画，也没有据它发放资格。后续不用OS级挂起规避资源守门。

v1／v2各自独立assert watcher在game／MCDK精确身份已消失后，通过保留句柄及创建身份回收；没有按进程名强杀game。上述raw均位于 `.runtime/round-20261022/water-size720-v1` 与 `water-size720-v2`。

两次失败后的独立恢复只覆盖回执列明的标准测试marker、客户端／世界actor及busy状态，不涵盖私有bootstrap receipt marker的删除。原bootstrap回执确认原函数identity已恢复，但两个失败组均未走到显式retire-bootstrap-marker步骤；私有receipt随该游戏解释器退出消失，不能写成实机显式删除已验证。

## 720p相机失败的只读定位

原tilted shown／hidden实际读图可见完整石块顶面和正面。原signal的bounds为 `[595,340,686,417]`，完整预测为 `[594,307,686,417]`；RMS16.5076px、IoU0.7013，原门未放宽。`stone_signal`先用中性色阈值筛选，再取最大连通块：y339整行混色约RGB(132,156,178)，未通过原RGB spread<13门，切断顶面与正面。顶面内部1320／1320像素本来同时满足中性色和shown-hidden差异门；最大连通块随后丢掉完整顶面。这是signal提取的具体失败，不证明FOV或水供帧有误。

只读候选在原neutral seed上作3×3闭运算，补入像素仍须通过原shown-hidden差异>20，再取最大连通块，不使用解析预测hull补图。重放原720p三图和旧1994×1105三图，原算法5／6通过、候选6／6通过原RMS／IoU／2px阈值；shown=hidden负控仍拒绝。此候选只在runtime，未改共享工具、未重写原结果、未授world-camera资格。后续world测试仍须审阅修改并同session重新采集校准。

00:40前后的独立审核补充了v1原21控未涵盖的反例：灰方块中央1／2px低贡献缝，只有缝两端存在shown-hidden贡献。closing虽只在有贡献处桥接，后续继承的填洞仍间接新增88／176个无贡献像素。因此v1仅通过六实图及初始负控不够，原候选、原结果及反例全部保留，不允许拿它发放world-camera资格。

私有v2改为 `old_outline OR (new_outline AND contribution_gt_20)`：旧算法输出作为完整基线保留，最终新增差量也必须通过原>20贡献门；没有解析hull补图或放宽拟合门。六张原图仍按原FOV及原RMS／IoU／2px阈值6／6，41项离线控制通过，各图最终新增unsupported=0且旧轮廓移除0。直接读取独立审核的原PNG时，v1的88／176伪填充可复现；v2伪填充0，中央88／176个无贡献信息仍保留为缺失。v2首次离线准备因CRLF搜索模式不匹配原LF而在写candidate／binding前断言停止；原脚本和失败记录保留，随后按原换行精确生成。v2补丁及完整回执在 `.runtime/round-20261022/water-camera-signal-v2`，仍是私有待独审候选，未改共享工具、未启动新的world校准。

## 编辑器诊断的必要前置

冻结 `probe_product_water.py` 的304—316行只在routes包含非editor时要求same-session world-camera校准。408—442行对editor burst比较scene_capture_state前后稳定，对world route才检查camera及校准viewport。独立一基原行／原SHA保存在 `water-size720-v3/editor-contract-readonly-v1.json`。

因此editor-only `flow_east`的最小前置是：正确source及单次bootstrap、精确PID／创建身份／window identity、实际物理1280×720读回、editor scene前后不变、burst原协议及内存／时序／前后台守门、统一quiet安排。它不需要world tilted camera资格，也不能据此授world A。

## 00:17—00:21：v3完成一次编辑器lifetime诊断

在父代理明确安排quiet后，新owner `water-r27-final41-size720-v3` 完成单次冷启、单次原core bootstrap、物理客户区1280×720读回和editor-only `flow_east`。该组没有OS挂起。实际session `fc991536a3734f729f9e1e4382268206`，game `67844 / 134370730145871057`、MCDK `52924 / 134370730143704713`；实际执行前绑定为 `prelaunch-host-binding-r27-direct.json`（SHA `8810d3a80162f9530e897750e28daacbb9f0085efe50efef0466576f613d182e`），此前两份准备binding保留。冷启99.357s、bootstrap11.300s、resize0.471s，单例A诊断host阶段30.393s。

| 本次实际采样 | 结果与边界 |
| --- | --- |
| 完整测量 | 42个有效帧／43次尝试；准备1500ms、完整测量3200ms；capture_valid、temporal_complete均true |
| 原150ms时序门 | 首段0.7277ms、最大内部84.8451ms、尾段41.7495ms；181次FrameArrived，最大arrival间隔60.0374ms |
| frame生命周期 | 结构完整，取得frame均成功Close并释放，异常0，最大Close0.3462ms；只说明本次可观测调用，未读取WGC池内部状态 |
| 内存与资源 | 峰值计账221937664B，小于536870912B原门。连续guard248样本；game最大879句柄／相邻增长138，MCDK最大235／增长10；guard与modal breach均空 |
| 恢复及来源 | 原report completed、restored、source_unchanged均true，cleanup_errors为空；独立标准恢复通过；4479源／1391辅助、core不变 |
| 显式bootstrap清理 | `bootstrap-marker-retired-v1.json`读到原函数identity为true，并实测marker_retired=true；这是v3的显式清理证据，不反向补齐v1／v2 |
| 关闭 | 普通stop完成；same-handle observer实测game为`0xC0000409`，MCDK为0，精确身份已消失；随后按精确创建身份回收watcher。不能称正常引擎退出 |

子代理实际打开wet、wet_later原still和burst第1／22／42帧，水面可见，纹理相位存在变化。此读图只作spot check，不等于流向、速度、UV、alpha或产品外观验收；未使用旧像素ROI。单次尺寸变化且冻结产品来源不同，不能据此断言1280×720修复了旧S0的636.6348ms缺口。原旧失败、v1／v2前置失败及v2挂起回执均保留。

## 正式A的最小后续

保持本41源、实际1280×720、1500ms准备／3200ms完整测量／150ms最大间隔及512MiB计账门不变。先把私有lifetime trace替换为已审非trace `water-startup-protocol-v2` 固定准备helper（exe SHA `1bf5d8db04b339042751e4bbd954786292efd21115cd4c07e6d8d84fa530a155`），新冷启后先做editor `flow_east`一例；该例即便通过也只是正式矩阵的一个单元。完整A仍需`flow_east`、`flow_south`、`flow_west`、`flow_north`、`falling`乘editor／full／missing的15个burst，以及原可见动画和物理流向分析，不以纹理相位变化替代方向门。

full／missing的10个world单元必须取得新same-session、实际1280×720的三机位stone校准与原相机／viewport守门。上面的signal修复尚是runtime离线候选，需先审阅修改，再实机重采；不能直接把6／6重放结果当相机资格。editor route只要求scene前后稳定，不依赖world校准。即使本41源完整A通过，也不自动覆盖本轮主仓其他共享渲染修改后的最终来源；最终合流仍须正确owner绑定及相应F／B／R／G／默认D。

## 00:52—00:57：非trace正式采样器单例未通过时序门

父代理释放实例并明确授予quiet后，执行新的独立owner `water-r27-final41-formal-editor720-v1`，保留相同41源、core、1280×720及原准备／测量／gap／内存门，只把私有lifetime trace替换为已审非trace fixed-startup-v2 helper。该组不临时加入world或相机校准。实际session `bf6d66304e104404a3ffd0f28741e43c`，game `62456 / 134370751714099759`、MCDK `52648 / 134370751711717925`。冷启83.902s、单次bootstrap8.725s、resize0.444s，唯一editor `flow_east`采样host阶段24.276s后按原门失败，未重试。

原burst保留36有效／37尝试，首gap17.7829ms、最大内部gap593.9861ms、尾gap30.7163ms；helper退出2，capture_valid及temporal_complete均false。这说明720p单例lifetime诊断通过不能证明正式采样已修复，更不能关闭A。非trace没有FrameArrived／lifetime事件，不据这次数据推断game／DWM／WGC／driver根因。

原report restored及source_unchanged为true，独立标准marker／actor恢复passed；普通stop0，game实际退出`0xC0000409`、MCDK0，精确身份消失后按创建身份回收watcher。失败组没有走到显式bootstrap marker retire；bootstrap本身已确认原函数identity恢复，但不能把解释器退出称为私有marker的显式删除。原失败在 `.runtime/round-20261022/water-formal-editor720-v1`，不覆盖v3诊断或旧S0。

## 720p物理流向采样的只读边界

冻结41源原分析器对v3执行`--partial-diagnostics`，evidence_valid=true、capture_failures为空；42帧的editor `flow_east`物理流向row仍false，41个相邻帧对中可测对0，signal标准差3.1719。这是独立失败记录，不因时序完整或纹理相位变化而通过。

原96×96物理采样点映到1280×720的bbox为x458.35—581.95、y271.21—324.79；SDK screen为641×360，原分析器已做native／engine比例换算，不能简单归因漏乘DPI。子代理实际打开采样格叠图、全水面预测叠图及三帧展开的采样信号图，预测几何与实图存在纵向错位，采样混入静态边界和空白。解析水面遮挡检查中9216点没有更近水面，两个轴正反四种仅诊断分析都未通过；该计算不是原生depth或像素证明。下一项应独立核对UI PaperDoll的投影／位移合同，不能移动ROI追逐纹理或放宽方向门制造通过。完整15条A留到最终正确合流来源及采样合同核清后再排程。

完整raw保留在 `.runtime/round-20261022/water-size720-v1`、`water-size720-v2`、`water-size720-v3`。仓库[精简证据索引](../evidence/water-size720-r27-v1/index.json)分别记录原raw与脱敏／压缩派生SHA；完整burst及119MB源archive不入仓。

新增用户人工关闭为0，正式A、最终owner与默认路径继续开放。

## 非trace缺口的逐帧只读复核

最新有效复核为 `water-formal-editor720-v1/gap-readonly-r27-v3.json`，SHA `1f2f67f6b77e4802d6a9689800ef800a6335f6003b9d6e73dc2a04c6f6837191`。早先v1把无readback的0当成时间，得到无意义大值；v2已改数值但文字误称两组都在末帧没有readback。原错误报告不覆盖。正确缺失位置是trace第43次末次尝试与nontrace第1次首次尝试，最新报告将其记为null并排除undefined duration。

nontrace有效样本的最大poll前守门至readback为15.3026ms，trace为4.1512ms。nontrace第27→28次的worker成功观察间隔为538.3221ms；最大593.9861ms的**source帧时间**缺口则在第28→29次，其worker间隔79.7914ms。第28次取到的source已有532.802ms age，尚在原单帧1000ms上限内，最终仍被完整timeline的150ms缺口门拒绝。不能把两个不同序列对的数值合并为一次readback延迟，也不能用有效帧数或平均间隔盖掉内部缺口。

三份Python采集wrapper在formal／trace两组逐bytes相同；C++差异为固定数组记录的poll、arrival、Close／release等数字事件以及QPC调用，其调度开销不能假定为0。PNG编码均在采集阶段结束后执行。nontrace没有callback、empty-poll和COM lifetime的实际事件时间，不能补造，也没有证据把缺口归因于game、DWM、WGC或driver。

`rpc-boundary-static-r27-v1.json`（SHA `048e06fedab78e566386d091cfe249b7cc7f542ffea46571aaa6b038ca936385`）冻结相关函数原文与SHA。产品host在同步`native_burst`之前读scene，成功返回后再读scene；`tracked_burst`前后metrics调用Win32进程内存／句柄接口；helper由`Popen.communicate`同步等待。这些函数没有在burst中定时派发MC scene／telemetry RPC。该结果只是静态调用边界，未审计运行时全部RPC，不能排除任意MCDK背景任务或据此证明game render线程没有被阻塞。

## 01:20后：UI锚点与GUI缩放的独立产品缺陷线索

对原实图、原控件geometry及原解析顶点作只读对照，旧1994×1105／SDK499×277约整数GUI4样本与原预测基本对齐；新1280×720／SDK641×360约整数GUI2样本的水面明显浮在预测与支持石块上方。四格组的位移随各自PaperDoll短边变化，不能用一个固定像素平移解释。两组的`liquid_deployment.py`、产品UI vertex及`analyze_product_water.py`逐bytes相同。

现有产品`ui_offset`与分析器都写`min(size)/4`。预先声明的诊断假设为：原生physical中心至anchor的偏移等于`min(logical PaperDoll size)`，因此需要的logical补偿是`min(size)/integer_GUI_scale`。GUI2的两个组分别预测额外上移82.3532px和133.6548px，叠图与实际浮水边缘一致；GUI4的假设与原公式重合。该叠图只对固定几何公式作对照，没有搜纹理、phase fit、移动flow ROI或修改资格。颜色signal受邻面／透明／裁切污染，不能作为正式几何拟合门。

只读记录为 `water-size720-v3/anchor-layout-hypothesis-r27-v1.json`（SHA `f61294f59a47dd5345daa9acd572f998f902de78fca377af6a5b29be6126e9b9`）；旧GUI4／新GUI2两张叠图均实际打开检查。这里仍是**待中性原生几何验证的锚点假设**，不是已完成的修复。产品代码与原flow ROI未改，720p的0个可测相邻帧对仍按失败保留。该线索针对编辑器UI位置，不据它推断world projection也有相同GUI缺陷。

官方`GetScreenViewInfo`合同给出physical画布并按整数GUI倍数向上对齐；项目`Theme.configure`已用`round(GetScreenViewInfo()[0]/GetScreenSize()[0])`取得整数GUI，避免将向上对齐／logical截断的比率误当小数缩放。若需要SDK补偿，可复用该来源；产品不能依赖Win32或WGC查询屏幕比例。优先研究由原生矩阵消除anchor的方法，不能在未校准前直接将`/4`换成另一个分辨率常数。

## 独立neutral／matrix校准源与host准备

父代理批准准备独立诊断源，启动仍由统一实例排程决定。新私有项目 `water-r27-anchor-diagnostic-v1` 逐SHA复制原4479源／1391辅助，只在独立namespace追加neutral anchor1.5／0及原生matrix诊断资源：4484源／1391辅助，source合同 `334717aae34a1980dcb8c30a0fe50e596bbd4d027889a8315d5d9a67cb01c402`。原model／material条目语义逐项未变，原41源未改。这是新诊断来源，不是最终产品合流或完整传递依赖闭包。

新独立archive为119615969B，SHA `7bb7bd6de2d09f91672a586952699e5ea83c6f9f3d18859fd4535b9e0f1a30de`，5875个zip条目逐bytes SHA核过；只留runtime。不能借原119MB archive声称覆盖本次新增资源。neutral fragment固定opaque RGB约64，无纹理／动画；anchor0版仅去掉原vertex的`+1.5`；matrix版读取WORLDVIEWPROJ／WORLDVIEW／PROJ／WORLD／BONE的signed24控制格，量化最大误差1/4096。

预声明矩阵为GUI4／3／2、wide／tall控件、front／tilted姿态；每项对照empty、原生stone、anchor1.5下offset0／1⁄4／1⁄GUI、anchor0下offset0及五份native matrices，另有六项轴位移对照，共138张静态计划。GUI值必须由实际SDK读回核对，不能凭窗口尺寸假定。UI使用raw `Style`，避免`widgets.S`二次乘`Theme.scale`；每次resize后重新mount，前后读取实际native control geometry，至少三个ready帧。wrong GUI、轴符号／排列、错误offset符号、固定±20px平移及shown=hidden负控预先列明。这里不运行正式动画A，1500／3200／150ms／512MiB原门全部保留。

初始host自审发现私有source没有原生C++截图目录，因此不能直接使用私有`capture_native_window.ROOT`。未启动的v1全部保留；修正host独立放在 `water-anchor-calibration-v2`，将截图工具ROOT绑定共享已审host目录并钉住原static capture exe SHA。v2计划SHA `05a8c641aadc73f9ebf3e935e9e2f524b188795f5afd721c4c2fd42327edca6d`，host binding SHA `e3fff81b5223c34a811cbc59475c3091852e2ebeeec71dd209814a6b6cd05710`。22个host脚本Py3 AST及游戏payload true Python2编译通过；尚待父代理独审与实机窗口，不能把准备完成写成native校准通过。

相机signal v2后来另获books独立审核：20项扩展控、9反例、7假fit拒绝及六实图均符合原要求，回执 `books-editor-v1/camera-signal-review-v1/actual-v2-review.json` SHA `764db0e3d7ea67740bb34be2354d7f14c9b11302e77a87c7bf8e756eb6259a75`。父代理允许以后私有新owner同session world stone校准使用；尚未据此重采或授world资格。前文v1反例及原失败继续保留。

截至上述准备，本专项新增用户人工关闭仍为0；正式A、最终owner、默认冷启路径继续开放。原212-entry精简包未覆盖随后新增的formal失败／gap复核／anchor材料，后续另建补充包，不覆盖旧索引。

01:50前后完成独立补充包 `docs/evidence/water-size720-r27-v2/index.json`，SHA `5e589aa1fc32c5049a074abdea5763eb1f71111b5a347507503a6fc332270db8`，281条／四份索引页，单件最大240000B，总5950703B。其scope覆盖formal失败、旧错误gap报告与最新v3、camera v1拒绝及actual v2独审、原失败ROI和anchor v1／v2准备；不含未来实机或随后v3 host修正。原raw及212条旧包未改，脱敏输出secret值0，待父代理独审。

父代理独审前要求补强失败收尾；冻结v1／v2均保留，最终host单独位于 `water-anchor-calibration-v3`，owner仍是尚未启动的 `water-r27-anchor-calibration-v1`。v3 plan SHA `7ed261548726f4b8e00dbeff77a75e14da2e0842b459b15630a069814b003dcd`，host binding SHA `7b1ca0f232ad058611a126c29209196829f6675ca21c59548482e02edd05386e`。最后只读恢复RPC或source audit失败会记入`cleanup_errors`／`restore_unknown`，仍保存最终report，不覆盖原始采集异常；group普通stop超时也保存异常、观察精确进程身份与已有same-handle退出回执。直接执行实际AST finally的五个host故障控与一个group stop超时控通过；六个实际AST资源边界控也通过，均是明确的synthetic IO，没有MC／RPC／子进程。第一次离线fixture遗漏wrapper局部`launch`初始化而失败，原脚本／输出保留；随后仅修fixture，实际host未因该测试错误改写。

v3的截图前后句柄门由两个实际执行层承担，`resource-coverage-v1.json`（SHA `cc5bba287499600e271e2ec6a808eac28b90b3773946154c6a0a2dea288f9e71`）包含冻结SHA及一基函数原文：`run_anchor_calibration.py`的`resource_sample`在同一保留句柄上核对game／MCDK创建身份并读取count，配置前、紧邻截图前、截图成功后或失败路径的尝试性后检都执行，数值先记账再要求句柄<250000、相邻正增长<10000、可用commit≥6GiB；独立`watch_handles.py`仍在取得精确game／MCDK身份后启动，每秒检查相同固定句柄门、unknown modal及deadline，触门普通owner stop。两条样本流分别保留，不合并冒称全时连续观察；间隔内极短峰值未被证明。static WGC wrapper负责所属身份、新鲜帧、PNG及窗口守门，本身不执行game／MCDK的句柄增长门。短命WGC child受所属子进程回收约束，不冒称共享game／MCDK的增长检查。此处仍只是准备的执行合同；实际覆盖要由随后运行回执确认。

## 主代理归档复核

root 已独立核验[初包](../evidence/water-size720-r27-v1/index.json)212项与[补充包](../evidence/water-size720-r27-v2/index.json)281项：原raw SHA、所有压缩分片／解压SHA、4个原始session凭据的实际脱敏、PNG原样与JPEG有损标记、索引页及单件尺寸均通过，最大单件240,000B；两个包分别5,753,556B及5,950,703B。JPEG只作预览，不用于像素门。独立回执位于`.runtime/round-20261022/root-water-package-review/report.json`。root实际打开旧GUI4、新GUI2锚点叠图和原flow ROI图，确认图中存在明显的产品水面错位，仍需中性几何校准来检验公式，不能直接修改ROI追逐纹理。

这两个包冻结的是上述历史尝试与anchor v1／v2准备；后续host修订和实机运行必须另包，不回写这些索引。正式采集失败和所有原门保持，新增人工关闭0。

## 02:05—02:06：neutral／matrix首次冷启被watcher健康门停止

root 独审v3 host后授予一次40分钟独占窗口。实际group于02:05:07启动，owner仍为`water-r27-anchor-calibration-v1`。启动前全局历史Minecraft条目均不可`OpenProcess`，正式launch也确认有效实例0；可用commit约15.9GB，高于原6GiB门。实际session为`fc4f754726034c1590beb686e6683532`，game`34508 / 134370795193948571`、MCDK`46292 / 134370795191797446`。

此次没有到ready：r20 assertion watcher在读取所属starting `session.json`时记录`PermissionError(errno=13)`，并永久保存在`status.errors`。continuous guard第4个样本于02:05:41.995读到`assertion_watcher_not_healthy`，按原fail-closed门发出普通owner stop。该次stop等待结束时游戏尚未退出，返回1；随后same-handle observer在02:06:16.98记录game`0xC0000409`、MCDK0，starter因原game创建身份结束而拒绝绑定。group最终普通stop0、精确身份消失true、watcher按创建身份回收true。不能将此写成自然崩溃或正常引擎退出，也不能归因于中性材质／matrix shader。

原v3 host、grant、stdout／stderr及失败回执全部保留，没有原条件重试。只读复核`water-anchor-calibration-v3/startup-failure-review-v1.json` SHA`820bcfc00f82a2e84cb1912498e8c45f6599afcb468958fef5831314c6803650`确认5875项源与辅助逐SHA未变；bootstrap、诊断UI、所有138张计划样本都未执行。因此UI恢复与bootstrap marker显式retire在该次不适用，不能借没有marker称已实测恢复路径。launch采样game最大669句柄／相邻正增长42、MCDK230／150；独立continuous 4样本最大game670／44、MCDK230／16，句柄门本身未breach。两条采样流分别记账，不据此保证间隔内全部瞬时峰值。

静态代码可见r20直接读manifest，再由`load_session`二次读取；任一次`OSError`都会永久进入watcher错误列表。writer的原`_session.write_json`已有对Win32 5／32／33替换锁的有限重试，reader没有。但原watcher只记录errno13，没有WinError；“Windows文件共享／替换瞬态竞争”仍是机制假设，不冒称原事故已测得32或某个锁的持有者。

## 私有manifest reader候选与真实Windows锁控制

root要求先保留失败，再准备私人host修复。v4草稿仅对`PermissionError.winerror`的5／32／33有限重读整次双读。在真实`CreateFileW(share=0)`临时锁控制中，本机Python的`pathlib.read_bytes`／`io.open`只抛errno13、丢失`.winerror`，因此草稿没有把此错误当已知Win32共享错误，首次控制失败。原v4文件、fixture及`first-control-failure-v1.json`保留；没有把全部errno13都纳入重试。

经root允许，私有v5改用保留句柄的`CreateFileW`／`ReadFile`读取，实际失败立即保留`GetLastError`，读句柄允许共享read／write／delete以支持原writer原子替换。通用`bounded_manifest_read(callback, events, label)`只对实测Win32 5／32／33重做完整callback，等待0.05／0.1／0.2／0.4s，共0.75s；耗尽记录后仍raise，由原健康门停止。恢复事件单独记账，成功后不用旧snapshot，原schema、resolved path、owner、可选ready、process creation identity及eligible root／state检查完整保留。私有`native_load_session`只规范化函数名和read IO后的AST与原`load_session`一致；没有全局修改`Path`，共享生产源与旧r20 host未改。

候选位于`water-anchor-watcher-v5`：watcher SHA`804aab25fa70ab91c63cffc3eb5db170dbd5800e3c4450da5b52c5a897e49565`，共用reader SHA`2ae4d46fc4fc63249b1b10d8cc6e7028009f4fa1941ea64f88452871a89eb28d`。15项离线控制通过，报告`windows-lock-controls-v1.json` SHA`132503ab70cceb7b7491cb9f3492bc966bcec4986140bcf4096b6865e583c6a9`：包括真实Windows首读与次读临时锁恢复、持续锁五次耗尽，main临时恢复不永久记录错误／持续锁仍fail closed，8组输入与原`load_session`同值，畸形JSON／schema、owner变化、实际Win32创建身份不符、missing WinError2与非retry1314拒绝，以及未知dialog仍报告且不Ignore。main控制明确替换registry根和dialog枚举，身份控使用本测试Python实际创建身份，未模拟或声称PID复用；没有启动MC。候选仍待root独审和以后新owner实机，不授native校准、动画A或产品资格。

离线中性像素分析器也在观察新像素前冻结了固定RGB64±5、贡献>20、双向2px度量及shown=hidden／固定±20px／错误GUI／轴符号排列／错误offset符号对照；对称单元可能重合，只保留指标而不捏造拒绝。该轮没有像素输入可分析，原flow ROI不动、原失败不改。本专项新增用户人工关闭仍0，正式A、最终owner与默认路径继续开放。

root随后在独立输出目录重放原冻结15控，并独核loader AST同值，批准共用上述精确v5 watcher与reader，回执位于`root-watcher-v5-review/root-review.json`。该批准只覆盖host修复，不覆盖MC启动或产品渲染。变换专项也绑定同一reader原件，未复制另一套实现。

新的中性诊断lifecycle独立位于`water-anchor-calibration-v4`，新owner`water-r27-anchor-calibration-v2`；plan SHA`1afd1e9989097c8df157cd508ebaa5bf60d176b29240fb4b15e7c0ec105d7a0c`，host binding SHA`5672c7573e0171204ed4487dfbf91e5338913bbe84fd692489e6622815678183`。23个host／35个external绑定，六份游戏payload真实Python2编译通过；4484源／1391辅助逐SHA核对，复用同一个已审archive，并逐bytes复核5875条，无重新zip。新host只改变生命周期owner／私有marker、共用watcher与所属manifest读取；原138张像素计划、原资源门、普通关闭和失败收尾保留。launch所属manifest若耗尽有限读取，保存事件后raise；watch_handles初始snapshot也复用同一reader。原v3失败及v4草稿控制失败不改，尚未启动该新owner，待root独审和统一窗口。

## 02:33—02:35：v4冷启通过，首个配置因诊断参数类型失败

上述v4随后获root逐项独审及独占窗口。启动前实际有效MC为0、可用commit`16,086,441,984B`，23host／35external及5875源辅助SHA再核通过。session`40d79e4c1dff462c8dbc53eaca499b4d`，game`54452 / 134370811979662105`、MCDK`68864 / 134370811977621740`；冷启98.170s到ready，单次原bootstrap10.492s通过。v5 watcher实机健康，errors、unknown assertions与manifest重读事件均为空；本次没有实际遇锁恢复，不据此声称锁恢复已在MC内触发。

物理客户区读回1994×1105，实际SDK logical499×277、ScreenView1994×1106，整数GUI4读回通过。第一项`gui4_wide_front_empty`在CONFIGURE构造`pack_group`时立即失败：本子代理把RGB字节写成浮点`(0.,0.,0.)`，原`appearance_uniform`严格要求整数0—255，抛`Invalid liquid tint channel`。此前Python2编译只证明语法，不会调用这项值合同；这是诊断payload准备错误，不能归因水产品、native矩阵或neutral材质，也没有生成任何捕获。

完整失败原件保留，未原条件重试。原report restored／source_unchanged为true、restore_unknown为false、cleanup_errors为空，独立UI／actor恢复true；显式bootstrap `marker_retired=true`。普通stop0，same-handle实测game`0xC0000409`、MCDK0、精确身份消失true，assert watcher按创建身份回收。continuous guard105样本，game最大878句柄／相邻正增长100、MCDK235／20，句柄与modal breach均null。只读复核`water-anchor-calibration-v4/payload-failure-review-v1.json` SHA`9f32a978746ec6c851917d2b6c10220dd1780c10a368337f597b70c6cb513874`逐项核过源与收尾，成功捕获数0。

## v5最小payload纠错与真实Python2值合同控制

新的独立lifecycle放在`water-anchor-calibration-v5`，新owner`water-r27-anchor-calibration-v3`；游戏payload唯一变化为`(0.,0.,0.)→(0,0,0)`，不放宽原严格整数门、不改产品源。plan SHA`bf3db61e85549631603e7d6d7a61eed37d35f6331859d56abfbd3b65a2057d9c`，host binding SHA`dbb6ba82ea1938a055a71533e97f300e6479f511357693f565832bf5d0614576`；24host／35external，原诊断archive复用并再次5875条逐bytes复核。

`verify_configure_payload_py2.py`在实际Python2.7中执行全部138项**原CONFIGURE文本**，加载原冻结`Document`、`pack_group`、`validate_uniforms`模块，仅将SDK.GetSystem、bridge.geometry和UI setter作为明确fake边界。138项uniform及group值合同通过；还执行原v4首项CONFIGURE，精确复现原`ValueError: Invalid liquid tint channel`。报告`configure-py2-execution-controls-v1.json` SHA`1ff049d25452b41ad141bc9eca51bf46d2b2c21ab74bc5a647b250f37cfd7fdd`。这不是MC原生渲染或UI运行验收，候选待root独审及新窗口，原两次失败不覆盖。

在新像素到来前另完成10项投影算术控制，`projection-math-controls-v1.json` SHA`2cdc486f24fb1a0834f4229037cc131763eaf873ceb40968af73a049548b82d2`：独立手算正交bbox、透视clip/w八角、固定错误GUI／offset符号／轴符号、zero-w拒绝及实际分析main对synthetic PNG与axis引用。完整立方体的y／z置换在对称base重合被如实保留，轴位移单元才区分。另预声明`analyze_matrix_factors_v1.py`最终SHA`ad0f0e2d398b59f83efa0f46a928208eb362de3ef1553b476cc4ffa24db2edef`，直接检查`WVP≈PROJ·WORLDVIEW`，误差界从各元素独立signed24量化±1／4096推导；4项数学控通过，固定错误乘法顺序／位移拒绝。该工具还报告`+1.5` entity-y投影位移以拆分旋转pivot，跨五矩阵只比较position／global_position／size，model ID单列；没有拟合或新像素结论。

截至该准备，本专项新增人工关闭仍0；正式A、最终owner及默认路径继续开放。新的v3精简证据包将另存失败链、reader修复及以后真正执行的中性结果，原两个索引不回写。

## v5预启动字节拒绝与v6完整静态前置

root独立重放138项Python2值合同及原错误复现后批准新窗口，最终回执在`root-anchor-v5-review-v5/root-review.json`。v5 group启动后1.267s即在创建MC进程前被原core字节校验拒绝：clone默认文本写入将`candidate_bootstrap.py`原LF转成CRLF，实SHA为`4c3a888e843cee19be6e12dbdb08ab835fa67e744b039a0a9766b088a3b21c61`，与原core`088ae57b8ea713b7881a01b94b4289cb7b04f7e17f791d17fc2bf2be2b49fa26`不符。不能因语义相同改写原字节门。

没有MC、MCDK或session，只有先启动的assert watcher；已按精确PID8772／创建身份134370838176214514回收，身份消失true，保留`prelaunch-helper-retirement-v1.json`及`prelaunch-failure-review-v1.json`。group原finally不覆盖“尚无launch/session但watcher已启动”的分支，这次回收是单独执行，不能称group自动完成。原v5失败不改，root撤回窗口，未原条件重试。

v6只恢复原core精确LF字节，分配新owner`water-r27-anchor-calibration-v4`／marker；其余不变文件bytes复制，诊断源／archive复用。plan SHA`627bb6a9cf39988c8e720e0469f0f328e74b0ce4ff7bc69031c055a379e65b47`、binding SHA`16e6f59dfe5c7d055fa90bebd4de6a94ec6e07375dbe9e7031073d445e4cb11e`，23host／35external。

`verify_static_launch_v6.py --output-root <独立目录>`执行实际launcher的70个AST节点，停在Popen前，仅mock鲜活watcher status字典并重定向launch报告目录，不创建watcher／session／MC、不发RPC。实际source／aux、archive、core、qualification、config、exe、guard、registry owner、0活MC／6GiB门全通过，实际bootstrap checked_sources和dispatch bytes通过，group／calibration／guard／cleanup依赖实际import成功。子代理报告`water-anchor-calibration-v6-static-review-v1/static-launch-review-v1.json` SHA`b48777d5b4530bcf0442fff98f372a672098490d3f591529d46969fb6f69d325`；root又在独立目录无覆盖复跑通过。静态控制不声称真实watcher或游戏client／server ready，原instances.py readiness及依赖只由external SHA绑定。

root新授40分钟窗口后，v6于03:23前后开始唯一新owner组；启动前实际活MC0、可用commit15,736,979,456B，23／35host、5875source／aux和core SHA再核true。原138项静态计划／原资源门不变，后续实机结果另记，原动画A与用户人工关闭0不变。


## 03:23—03:26：v6隐藏原生控件尺寸为0，原宿主错误尺寸门拒绝

v6 session为`5aeb9ffda83a49128f23b3f4e18f3f23`，game `67056 / 134370842343959985`、MCDK `70320 / 134370842342055547`；冷启103.403s及原bootstrap 13.658s通过。首项`gui4_wide_front_empty`的逻辑ready为true、stable_frames129，renderer两槽都隐藏、native model ID均为−1。三个hidden PaperDoll的实际`GetSize`全部为`[0,0]`，位置为约`[59.88,52.63]`；宿主却要求空场景内所有hidden控件都等于声明rect `[379.24,171.74]`，因此在第一张捕获前断言失败，成功图片0。这里是宿主把hidden语义当可见尺寸合同的准备错误；没有原生中性模型像素或矩阵结果，不能推出water shader的成败。

原始失败、原138计划及原尺寸断言均保留。原report restored/source_unchanged true、restore_unknown false、cleanup_errors空；独立恢复true、显式bootstrap marker_retired true，普通owner stop0，watcher按精确身份回收。group保存same-handle退出snapshot时MCDK尚live，该早snapshot不回写；独立observer稍后于03:26:07.835完成，game退出码`0xC0000409`、MCDK0，二者创建身份最终均消失。continuous guard114样本，无句柄或modal breach。最终只读复核`water-anchor-calibration-v6/hidden-geometry-failure-review-v1.json` SHA `3adc5f810b36698672f7c04099ddde26153be69afc53ef262d60e0a45636d6e5`逐项核过5875源辅助SHA及真实晚到observer。

## 最小真实UI几何观测准备，不再盲跑138项

root要求先确认原生hidden/visible尺寸、active bank、parent geometry及ready语义。新的`water-ui-geometry-observer-v1`明确增加持续可见Panel wrapper，作为独立诊断结构变化，不据它的parent合同成功给原生产控件授通过。原生`GetVisible`分别记录parent与三个Doll，hidden尺寸如实保留0；active控件单独对照声明rect、父位置加显式offset、native model ID及renderer bank ID。逻辑ready、原生几何观测完成与产品资格分别记录。

新owner `water-r27-ui-geometry-v1`，plan SHA `fce561cb6070a499acbd89bdf76b99a71775b1399eb52c7258deb0f9ed6f847f`、host binding SHA `2dd59591831606d995fb72953d14c4f28d3e84dcbe1397b18c81a48564b784d5`。计划GUI4/3/2各在同一次挂载中执行`empty_before → stone → neutral15 → empty_after`，从首次post-config RPC保存raw，逻辑ready后继续6次样本，保留两bank及空→可见→隐藏时序；阶段间显式CLEAN/CLEAN_READY、独立marker/navigator/actor恢复后才resize/remount。这个初始host只观察SDK几何，不截图、不decode矩阵，不触动原138像素计划。资源门、精确身份及ordinary stop保留；增加尚未创建session但已启动helper的精确回收分支，仍须实际回执证明执行。

12项synthetic几何控制通过，报告`geometry-synthetic-controls-v1.json` SHA `26cfeaac69949ddc37552ca6f3904fcb2466a066df922651e2e15e9aa2be6267`；5份游戏payload真实Python2语法通过。`verify_static_observer_v1.py`在Popen前执行实际70个launcher AST节点、源辅助/archive/core与实际bootstrap派发bytes，lifecycle实际imports及绑定SHA通过，仅mock freshwatcher字典和输出目录；报告`water-ui-geometry-observer-static-v1/static-launch-review-v1.json` SHA `ffde280719e1eb4cedf675b137b52385a51c9c86d0c60ed8f0dfec27cefe342b`。原bootstrap core继续精确LF SHA `088ae57b8ea713b7881a01b94b4289cb7b04f7e17f791d17fc2bf2be2b49fa26`，复用同一诊断源及119MB archive，没有重新打包。此处尚未启动新MC，等待root独审与统一实例窗口。

截至上述准备，本专项本轮新增人工关闭仍0；正式动画A、最终owner/默认路径及GUI锚点修复均未关闭。


## 03:50—03:59：v2真实UI几何、38张独立原生对照及精确释放

root独审实际70个launcher AST节点、共用reader及固定单次followup hold策略后，v2以新owner `water-r27-ui-geometry-v2` 启动唯一session。原bootstrap core精确LF字节不变，源仍为独立diagnostic的4484项与1391辅助。plan SHA `1045326cad31196f4bed32d453dd3e0f0e55456291871036387e5c6c0ba2e0c9`，host binding SHA `4aff1e8f737720ccc630ed6675e502c624e0baff25e4cce4753d7e8cee0bf698`。固定hold只允许root原子授权的精确SHA脚本 `root-followup.py` 执行一次，最长600秒；没有通用job queue或任意路径执行。

实际game `68020 / 134370858444454299`，MCDK `36612 / 134370858442452820`。冷启103.6927秒、bootstrap11.8236秒，初始12状态49.2356秒。GUI4/3/2分别一次挂载执行 `empty_before → stone → neutral15 → empty_after`；逻辑ready后各保留6样本、0.2秒间隔，阶段间独立恢复再resize/remount。可见Panel wrapper持续存在且SDK尺寸/全局位置符合声明；该结构变化仍只属于诊断UI，不授原生产控件资格。所有hidden Doll实测size0；可见stone确有正常像素但 `GetModelId=-1`，原helper三组矛盾原样保留，不能把skeleton的model-ID语义移植为block_geometry门。neutral可见bank的native与renderer ID一致。

SDK logical/ScreenView实测GUI4为 `[499,277]/[1995,1107,0,0]`、GUI3为 `[533,300]/[1600,900,0,0]`、GUI2为 `[641,360]/[1281,720,0,0]`。ScreenView是公开SDK取整后的视角，不冒称原始物理客户区。几何观测原report SHA `3de2320403074ba5de6b65f55715a39dcfa8ba024949838c02078395ef301a2e`。

同session内root授权固定followup（SHA `bde1df192369df5152a8f4f0808f1478bb622f456190f9ea518782f608c792af`），实际完成38/38张：GUI4 wide/front；GUI2 wide/front、tilted及原六轴单变量控制；empty、独立stone、anchor15 zero/quarter/inverseGUI、anchor0 zero及五类native矩阵。GUI3仅有上述SDK几何，尚无像素。原138项plan和宿主断言不改，新host只在独立诊断子集中单列已知stone -1语义；不得回授原门通过。capture report SHA `a0d848756f52e152bf7a6e0afe70b57b684533c3a3f9fb44046b9971380adbf4`，原PNG全部留存。

固定全图分析器未修改，原RGB64±5、相对empty贡献>20、双向2px度量及97负控照旧。GUI2 front quarter IoU0，inverseGUI IoU0.972449；tilted quarter0.004002、inverseGUI0.973958；对应三轴inverseGUI约0.954707—0.974222。原全图neutral mask明确混入屏幕顶部debug灰文字，bounds因此过大；原分数和负控仍保留，不借新scope覆盖或改阈值。原分析report SHA `c95d800d9bae63b49a01ba107447690dcfb731504a7c35d816547d49b0d1f7b1`。

root另外在采集前已声明、且SDK实际确认的 `viewport_parent` 全矩形内做派生测量，矩形按SDK几何换算，未按图片搜索ROI、未平移/缩放拟合；沿用同一RGB64±5、贡献>20及2px。该新scope中GUI4 quarter IoU0.98387、GUI2 front inverseGUI0.97531、tilted inverseGUI0.97963，三轴约0.97963，双向2px recall全部1；主体y约差1px。GUI2 quarter front仍相差约111px/IoU0，tilted仍约111px/IoU0.004。它支持GUI偏移候选，不能代替原全图结果、GUI3像素、产品Scene或正式A。派生report SHA `47a14f5c39375ef89a675ea201cebc9eacead45f8abf1863d99fa718e87ce449`。

独立矩阵因子分析继续按原signed24各项±1/4096的误差界检查 `WVP≈PROJ·WV`：GUI4 front最大ratio0.406805、GUI2 tilted0.792074；**GUI2 front为1.190508，原样失败**，不放宽量化界、不声称已证实机制。native geometry跨五矩阵一致。`+1.5 entityY` 在front屏幕位移为0、tilted约 `(+68.90625,-41.66016)px`，因此保留旋转pivot，不能当成GUI偏移删掉。因子report SHA `3b4048dc6eb16f6d9593f4a15e32c9da75f3763758d1596a7ace82dfa1ad6494`。

group共524.8296秒，root核图与独立after-followup恢复后原子release。最终restored/source_unchanged为true、cleanup_errors空、bootstrap marker显式retired；continuous guard484样本，无句柄/modal breach。普通owner stop返回0；same-handle observer随后实测game于03:59:17.861退出 `0xC0000409`，MCDK于03:59:17.865退出0，精确创建身份均消失；不把game退出码写成引擎正常退出。watcher `66748 / 134370858335265484` 已精确回收，水MC窗口完整释放给变换专项。

## 自定义水GUI偏移窄候选准备

仅在 `.runtime/round-20261022/water-gui-offset-candidate-v1/candidate/` 准备三份私有文件：`widgets.py`把原configure已经计算的整数gui存为 `Theme.native_gui_scale`，赋值在字体/主题early-return之前；`liquid_product_deployment.py`只给显式Product水profile添加 `ui_offset_for_gui(size,gui)=(0,min(size)/gui)`，unknown/非正整数/非有限值拒绝；`scene.py`仅水分支使用可选接口，legacy profile仍用原callback。其他item/cauldron/portal/book分支AST不变；不新增tick/group内SDK读取，不改shader、pivot、生成owner或qualification数据。共享生产源和原冻结snapshot未改。

真实Python2执行29控通过，覆盖GUI4/3/2同字体5.0时仍刷新cache、取整SDK比例、invalid GUI、Product dynamic/frozen实例绑定、300组真实Scene水闭包访问无额外FFI、legacy fallback、四个其他profile AST同值，以及原resize闭包 `.05/.25` 调度下物理尺寸单独变化和最终逻辑变化均调用configure。SDK/构造器/UI render是显式fake边界，不冒称真实窗口resize或水原生像素验收。第一次fixture因文件系统路径混用unicode失败，第二次因Python2的list.append不可hash失败；仅纠正fixture，三份候选bytes未改，原fixture留存。最终controls report SHA `e723c64db56edb5c22c5e4804817fbad12c8644232b5659fc7c16aa915a72926`。

候选随后仍需root独审、独立新source合同及三GUI正常workspace/Scene实机；原生产构造因资格与owner不符继续拒绝，显式bootstrap不能授默认入口资格。正式A、最终owner、默认路径、GUI3像素和产品GUI修复均未关闭；本水专项新增用户人工关闭0。


## 04:12—04:29：独立GUI候选源与正常Scene三GUI入口冻结

root已独审三文件接口方向，仅批准私有候选。新的枚举源位于 `.runtime/projects/water-r27-gui-offset-v1`，source仍4484项、aux1391项，只改已声明的widgets、Product deployment与Scene三个文件；source合同 `45985a50b720b72cd9dd55a68cdeb7064fffa7201c79084b1ec8953ca11d5424`，manifest SHA `f187a7f6f5dd17b2d870af27c86f72c433cffeb1f2d98cbd4fc80e07a36103ae`。新archive119616132B，逐5875项bytes验证；旧源、诊断资源、原owner/qualification与共享生产文件均未回写。这个枚举源仍不是完整传递闭包，不授最终合流资格。

初始未启动host v1离线复核发现，native readback的单次RPC需要显式import Theme，不能依赖上一RPC全局；另加固定scene child900秒预算。v2随后执行实际launcher前置，在Popen前被原PROJECT身份断言拒绝：泛文本owner替换误碰了同名源目录basename。原v1/v2文件与失败输出保留，均没有创建watcher/session/MC。v3在owner替换后从精确source binding独立固定PROJECT，原70个launcher AST节点、actual bootstrap源/dispatch、core精确LF bytes、完整source/archive与生命周期imports通过。v3也未启动。

最终v4将每GUI控制顺序改为dry→wet，使窗口调整时可见水保留；GUI3和GUI2真实resize后，在任何下一次LOAD前保存同document ID、原source cells、原group keys的事件刷新与像素。ready_request是否相同如实记录，因为GUI改变控件size也可能改变pose，不能把不同请求冒称同一请求。原v3准备不覆盖。最终owner `water-r27-gui-scene-v4`，plan SHA `e6a3ef408d971e79a7fb37948ad4b7470a568d83e969d28648b07b54f89487c2`，host binding SHA `03fa2951e2e2a0736daf02a9b3605ff8c346ad73b303070f3f64048e134991fb`；v4静态70节点报告 SHA `936b4c7851cf9f08a869d5d24b10e47aae580882ffd1e43ce9e9746306b853bb`。此时仍无新MC。

三GUI固定计划为GUI4 `[1994,1105]`、GUI3 `[1600,900]`、GUI2 `[1280,720]`，actual GUI由SDK取整读回。每GUI的source tilted、flow_east tilted、含水fence front/tilted各保留dry/wet，24图；另有两张原文档可见水resize接缝，共26静态图。正常路径为原 `source_document → Session._loaded → owner.open_workspace → Scene`，不用诊断Panel wrapper；显式bootstrap仍不授默认生产入口。另一个独立subcontrol在Workspace关闭时真实resize，显式 `Theme.configure(3,True)` 验samefont缓存；它与正常Workspace挂载时的事件刷新观察分列。

12项新host控制在实际Python2执行原EXTRA_STATE payload，显式fake SDK/模型/UI，验证它自行解析Theme import和hidden size0；固定geometry政策拒绝错GUI、位置、尺寸、ID、surface隐藏、未ready和非有限值。实际restore helper控制证明先关Workspace，再原blueprint恢复factory/editor，最后恢复grid/Theme及profile/factory身份；合成restore IO失败仍传播而不声称恢复。report SHA `8055535eb53b6db19e9d93c7c4ace9a086a7016142116efe0a576dd97f7dec7e`。

另在真实Python2直接执行**未改的LiquidControls类**，对已经ready且相同request验证geometry先SetPosition/SetSize、后ready_request早退；不重新提交模型，稳定geometry第二次也不重复setter。两个控制通过，report SHA `36e068bc45cfd1fe7002d278b2e716508b4facf7182c84f3974d530b65e8e2df`，native setters和renderer是显式fake，不能替代真实Scene。三文件scope review实际扫描files>0；Product deployment无finding，Scene与widgets只保留原有大函数/多参数风格告警；没有新增事件监听、跨端或逐group SDK调用。

最终组复用已审ordinary stop与精确身份/helper回收链，固定Scene child900秒；场景恢复先close等待导航结束，再原blueprint RESTORE，再自有grid/Theme/profile/factory检查与独立只读actors/source。总预计12—15分钟、保留20分钟窗口。root尚未授启动窗口时不启动；正式A、最终owner/default gate与用户人工关闭数仍无变化。


## 04:35—04:40：正常Scene三GUI候选的26图与真实resize接缝

root独立重放实际70个launcher AST节点与12项host控制后，发出精确plan授权，窗口25分钟含恢复，未延长或改写冻结source/plan/host。启动前有效MC为0，可用commit超过15.5GB；唯一owner为 `water-r27-gui-scene-v4`，game `11388 / 134370885479401069`、MCDK `38808 / 134370885477639980`。group总260.5548秒，launch96.7224秒、bootstrap10.8530秒、Scene136.0921秒；六个步骤均exit0。

真实resize且Workspace关闭时的同字体子控分别在GUI4/3/2显式调用 `Theme.configure(3.,True)`，font均为5.0，cached GUI依次为4/3/2，证明字体相同的early-return路径仍刷新cache。该子控与正常Workspace挂载时由实际屏幕事件刷新分列。正常Scene的SDK logical依次为 `[499,277]`、`[533,300]`、`[641,360]`，ScreenView依次为 `[1994,1106,0,0]`、`[1600,900,0,0]`、`[1281,720,0,0]`；不将SDK取整视角冒称物理客户区。三档正常font分别为0.75/1.0/1.5。

每档source tilted、flow_east tilted、含水fence front/tilted均完成dry→wet，共24张原生全分辨率PNG；另外两张为GUI4→3与GUI3→2时原文档仍挂载、下一LOAD之前的可见水接缝。两次均保留document ID、source cells和group keys，capture前后布局不变。GUI4→3的ready_request值有变，GUI3→2则未变；报告不把二者都冒称同请求。24行各保存3次原生SDK读回，共72次：visible active skeleton位置/尺寸与stored geometry误差在原0.02 logical门内，active native ID与renderer ID一致，surface可见；hidden bank原值仍保留，不推断其应具有正尺寸。

本代理实际打开三档source、flow与含水fence正/斜湿图，以及两张resize接缝；水面/侧面与石块支撑和栅栏位置接合，GUI2没有旧约111px整组上飘。root另独立打开三档front wet及GUI2斜fence/flow/接缝，观察一致。这是静态原生可见证据，**没有由静图授动画A、用户人工验收或默认冷启资格**。原动画nontrace的593.9861ms source时间缺口、GUI2 front矩阵因子ratio1.190508及原全图debug mask污染均继续保留；没有移动flow ROI、phase fit或改阈值。

post-run只读审计 `water-gui-offset-scene-analysis-v1/scene-native-audit-v1.json`，SHA `d97cc5e2f1a4853ec23405962c52ff0a3564ed5044a06334dad33daba6f1ea5a`，重新逐SHA核过26张PNG与冻结source/aux全部5875项，原source/host/plan未回写。Scene共88个资源样本，最小可用commit12,202,954,752B，最大句柄game876/MCDK234，相邻最大正增长3/0；独立continuous guard228样本，最大game879/MCDK235，无句柄/modal breach。两条采样流分别记账，不保证采样间不存在短时峰值。

Scene finally依次关闭Workspace、执行原blueprint恢复、自有Theme/grid/profile/factory恢复，独立后读确认navigator/marker/jobs均清、world actors0、source unchanged。bootstrap marker显式retired；ordinary owner stop返回0，same-handle observer实际记录game于04:39:58.087退出 `0xC0000409`，MCDK于04:39:58.089退出0，精确身份均消失。不能将game退出码写成引擎正常退出，也不能单凭此归因于水。watcher `32484 / 134370885380827927` 已按精确创建身份回收，窗口已完整释放，无第二实例启动。

随后冻结第三份精简补充包 [v3索引](../evidence/water-size720-r27-v3/index.json)，SHA `410c9b5f71853e02ec0c23b67f38ed02168aa013c8ee03066ca87daa31ca265f`：721项、10个索引页、总18,906,873B、单件最大240,000B。覆盖v3—v6历史失败边界与reader修复、12状态/38图诊断、原全图与独立parent scope、三文件私有候选/真实Python2控制、实际root静态与host独审、v4正常Scene26图/恢复/精确退出。source archive和完整bursts不入包；大PNG只生成全分辨率有损JPEG预览，原PNG保留runtime供像素门，索引逐项标注不可还原。输出secret值0，raw及旧v1/v2索引保持原SHA。该包本身仍待root独审。

截至此处，本水专项新增用户人工关闭仍0，`formal_A_accepted`、`default_path_evidence`、`production_admission_performed`均为false。三文件只在私有源；root已要求下一步提出小范围生产diff与项目风格的同字体/legacy/geometry测试，不直接改共享生产文件，不重算或手改owner/qualification合同，不把显式bootstrap复制为默认资格。


## 05:16—05:30：v3独审纠正、窄生产修正与下一A离线准备

追加纠正前一节的“输出secret值0、待root独审”：root随后拒绝v3归档。首个session条目仍保留非标准 `[REDACTED_SESSION_TOKEN]` 占位符，而独审只接受 `[REDACTED]`；loopback `mcp_url` 也应按归档政策脱敏。只读比较确认token值本身已被替换，所涉URL没有认证参数，不能把这次拒绝写成实际认证token泄露；同样不能把v3继续写成已通过。原raw与v1/v2/v3包均保留，不回写历史bytes，新分发包必须另行生成与独审。

原离线v4 preflight对每个JSON string重复排序/编码972份registry的已知credential集合，运行超过10分钟仍无包目录。只在核对本专项PID70128、创建时间和命令路径后停止该离线进程，原脚本与失败记录保留；未启动MC、未改原raw。优化副本预编译完整credential前缀trie，对同样的JSON/base64/escape解码视图进行exact检测；root原scanner的敏感成员与pattern递归检查不改。13个正例和3个负例与原scanner逐例一致，包含重叠前缀、嵌套JSON/base64、Unicode与hex转义、标准/旧占位符及mcp_url；脱敏后均通过，负例保持bytes。控制报告SHA `f04e355de1bad0c35c814b1c8ddc01298dba68a05f318caefdf63f9491c19246`。新包仍须root独审，控制通过不等于分发包通过。

GUI修正改为保留原CRLF的v2三文件提案，patch SHA `f6527713f843b8c24bcbe087d4168bce03fb1c173f1ed1aa18ca4157e4f2f2a9`；规范化LF后的候选bytes与26图实际测试源一致，三生产文件bare LF为0。项目风格overlay6项通过，报告SHA `5eda7b7e04008c3e990ea907296c0c68aed06f23697f27f11a0b2f04ae225053`，覆盖同字体GUI缓存、invalid GUI拒绝、legacy profile、水Scene闭包无新增FFI、实际LiquidControls同request更新geometry，以及不授mismatched production合同。root已备份并应用三文件与测试，随后报告目标回归72项、ownership6项及Python2三文件compile通过；提交由root管理。本代理不再次apply，不重算或复制owner/qualification。

下一正式A的离线准备位于 `.runtime/round-20261022/water-next-A-workflow-v1/`。当前shared来源inventory v2为source4482项、aux1391项，manifest SHA `7bdfd5e2322fd9b800a343408f9fa40a5bfcf61eb9c345b8a44d4dee7a747485`，source合同 `027f11186bb5e50b4d9a0dc80a5ba4d06342104e1be4c2cc6de51a9f206bcf1a`。实际probe枚举与digest一致、读取前后source/aux/owner/qualification未变，但它不是完整传递闭包，也不是下一组的最终冻结来源。HEAD或shared后续变化必须另生成新manifest；不覆盖本份。sibling renderer `ca10356`只作metadata参考，主仓尚未切runtime依赖。

时间链reader五项synthetic控制通过。原nontrace37attempt/36valid、固定3200ms、首尾17.7829/30.7163ms；native `capture_valid=true`、`temporal_complete=false`、`ok=false`。最大source gap为28→29的593.9861ms，同pair worker before gap82.4377ms；最大worker未观察间隔在27→28，为538.3221ms，同pair source gap仅42.421ms。两最大值不在同pair，缺失readback仍为null；没有empty-poll、callback arrival、Close或COM release实测事件，不能归因game/DWM/WGC/driver。原trace不能替nontrace授A。

`NEXT_A_WORKFLOW.md`要求root合流后另冻source/host/plan与唯一owner、保留原1500ms准备/3200ms测量/150ms source-gap/512MiB/6GiB及句柄门，先解决来源与时间链可观测性，再独审新15cell计划；不原条件盲重跑，不拿静态26图授动画/默认入口资格。当前水无MC，新增用户人工关闭仍0。


## 05:30—05:36：新分发包完成与普通入口单cell重新绑定

新v4分发包 [索引](../evidence/water-size720-r27-v4/index.json) SHA `1cb4a95ef9a57ed659471ec243d34e0dc848ba40ad4f1700d146ef8a3c458deb`，742项、19,321,405B、单件最大240,000B。逐原始raw重做标准 `[REDACTED]` 敏感字段脱敏，涵盖mcp_url、递归JSON/base64/转义与1855个已知credential值的exact检测；优化版preflight完成，包含v2窄提案、13正3负控制及下一A离线说明。原v3和raw未改；包仍待root独审，不把自检findings0写成最终审查通过。

同时纠正下一A流程旧文的一个前提：当前shared的owner与qualification implementation常量都为 `ef4f709969b6e96d7675529cd84ff27043706b23b723c4ee3d399497b32f4872`，resource/rules/style也相符。运行期只比较生成常量，不读当前源码SHA，所以源码漂移不会自动阻止普通入口；独立source checker/发行核验拒绝与运行期入口必须分列。旧private则使用不同owner `d0f37c33f8e054a0e906f44361edc43f49957b26b4af7853da9f2c0ca49bf20f`，其“空Session＋拒绝后explicit bootstrap”host不能照搬。root与本代理分别只读核出这一事实；不重算owner，不将旧qualification移植为新源通过。

source4484→4482的净差是去掉五个旧诊断shader `modern_projection_r27_anchor_0.vertex`、`_15.vertex`、`_matrix.fragment`、`_matrix.vertex`、`_neutral.fragment`，增加shared的 `debug_concrete_blueprints.py`、`debug_dripleaf_blueprints.py`、`tools/check_liquid_product_owner_contract.py`。不是简单减少两个路径。当前owner合同/owner_data相较旧private的不同已有在先；qualification逐字节相同，本代理没有改这三份当前shared数据。

新独立源位于 `.runtime/projects/water-r27-merged-flow-editor-v1`，4482 source＋1391aux共5873项，从当前shared逐bytes复制，前后shared与private/source/archive逐SHA一致。source合同仍 `027f11186bb5e50b4d9a0dc80a5ba4d06342104e1be4c2cc6de51a9f206bcf1a`；新archive119,618,244B，SHA `d9f196ca951a9f2d83f254b5e4d694868f714096715d376309845141c4c8c4e5`。该显式枚举仍不是传递闭包。

新host目录 `.runtime/round-20261022/water-merged-flow-editor-v1`，plan SHA `39d8f1194e25d463bf0cdcc6c2de93e4a34f1aad88d4d6b3687cdf72b4b46543`，host binding SHA `f579019e1639cd249812dc61989bdbfa2d61b24acda30a565e4308c735f2f085`。不调用旧bootstrap，只读观察普通UiInitFinished实际Session/profile类型、callback身份、规则、引擎和module文件位置，probe使用 `--production-default` 不赋候选profile。固定flow_east/editor/wet，原pose35/25/4.6、客户区1280×720预期GUI2；每次capture/burst前按原0.02logical门核active geometry/ID/surface。原1500/3200/150ms、512MiB、6GiB和句柄门不变；finally增加profile/timing恢复后独立marker检查，ordinary stop与精确进程退出分列。

启动前只执行实际launcher前59个AST语句，到Popen前停止；两个明确fixture是watch状态和输出目录。全部5873项、原owner/qualification和hostSHA核过，实际cold payload在真实Python2 compile，且AST拒绝初始化/profile属性写入；实际lifecycle模块仅import、不调用main。静审report SHA `422f8284c37c17289ceb9cda9e9a533d79451b28e7994cb637d90aecd1218644`。此时无新MC，没有SDK/原生像素结果；待root独审并在books传输后授精确quiet窗口。单cell通过也不授完整15cell A、world A或最终资格，用户人工关闭仍0。


## 05:42 根代理独立核对新分发包

根代理从 v4 索引逐项重建742个逻辑条目，独立核对774个存储文件与全部原raw SHA/长度，723个条目可逐字节还原，3个为明确标识的有损视觉参考，22处脱敏记录。递归JSON/base64/转义敏感检查与已知credential精确检测均为0发现；原独立scanner保留解码与敏感成员检查，仅用经8项等价对照的trie替代重复substring循环。报告位于 `.runtime/round-20261022/root-water-package-v4-review/report.json`。本次只授予v4证据分发资格，拒绝的v3、原raw和旧失败保持原bytes；不授正式15cell A、默认来源D或用户人工关闭。


## 05:39—05:42：当前shared来源单格普通入口与原采样协议通过

上述新owner在root精确grant下执行一次，未调用bootstrap、未赋候选profile，普通UiInitFinished创建的实际Session/profile通过只读观察。唯一单格为flow_east/editor/wet；原pose35/25/4.6、物理客户区1280×720、SDK整数GUI2、原0.02logical几何门不变。两张static及burst前共3次SDK真实读回，各有4个可见bank；active位置/尺寸、surface、native与renderer ID门通过，static前后Scene布局不变。root实际打开两张原static和burst首末图，水与stone对齐且纹理变化可见。这只覆盖本单格，不授其余14格、world或完整A。

原生manifest保留44次attempt、42张有效PNG及2次reject：第1次frame_not_after_request、第44次frame_timestamp_in_future，有效帧为2—43；invalid记录及null PNG没有删除。原fixed-startup-v2 nontrace完整测量3200ms，首/尾gap为15.8597/20.5999ms，最大source gap为25→26的78.7975ms，最大worker未观察区间为6→7的76.6862ms，两者不是同一pair，不能归因具体机制。原150ms超限数0；1500ms preparation、512MiB cap不变，raw/accounted peak分别154,828,800/221,937,664B。native与wrapper的capture_valid、temporal_complete、ok均true。manifest SHA为e7b0535d3820b6dad711195fa82fe4c5f2e63ad74e17434d53e5917894a6fee5；只读完整QPC链分析在water-merged-flow-editor-analysis-v1/source-worker-chain-v1.json，SHA ef0ca958f9e1f14d9280ac842e3a177aafdfb44722d016e10c8869cee67cc034。root独立复核这组精确cadence，不以该结果覆盖旧593.9861ms/source或538.3221ms/worker失败。

唯一group耗时173.11243s，cold launch105.32319s、普通初始化只读观察8.71787s/9次、resize0.56908s、A host41.05979s；全部六步骤exit0、group completed true。产品report completed/restored/source_unchanged true，cleanup_errors空。独立恢复确认navigator、blueprint/profile/timing markers清，busy/jobs/projection均false、world actors0，并在结束后逐SHA核过5873项源及辅助全部未变。continuous guard142样本、game/MCDK最大875/235句柄，guard与modal breach均null，group阶段最小available commit为12,499,091,456B。

普通stop exit0，game精确身份64844/134370923585769950与MCDK14824/134370923583848155均已消失，helper按精确创建身份回收。group早读的same_handle_exit仍是MCDK尚live的partial，原group不回写；独立launch/exact-exit.json随后completed true，game于05:42:01.136780以0xC0000409退出、MCDK于05:42:02.140968以0退出。不能把game称引擎正常退出或据此归因水。当前水MC已释放。

结果原件保留在.runtime/round-20261022/water-merged-flow-editor-v1；此前已提交的v4分发包、原索引和raw不改。本单格通过原采样协议不代表当前shared来源资格已通过：完整15cell A及原方向/速度/亮度分析、world A、source release、默认最终准入继续开放，用户人工关闭仍0。


06:05根代理已独立重建[本次单格精简证据](../evidence/water-merged-flow-editor-r27-v1/index.json)：40逻辑条目／44存储文件，37份可精确还原原件、3份脱敏派生共7处替换，4张PNG均为原字节，0有损。全部原始与派生SHA、长度、300000B上限及递归凭据检测通过，8项scanner等价对照通过，发现0；独审报告随包保留。全burst图及119MBarchive不重复入仓，本包不替代完整15格A或当前来源发行资格。
