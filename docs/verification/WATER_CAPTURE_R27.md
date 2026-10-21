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

## 主代理归档复核

root 已独立核验[初包](../evidence/water-size720-r27-v1/index.json)212项与[补充包](../evidence/water-size720-r27-v2/index.json)281项：原raw SHA、所有压缩分片／解压SHA、4个原始session凭据的实际脱敏、PNG原样与JPEG有损标记、索引页及单件尺寸均通过，最大单件240,000B；两个包分别5,753,556B及5,950,703B。JPEG只作预览，不用于像素门。独立回执位于`.runtime/round-20261022/root-water-package-review/report.json`。root实际打开旧GUI4、新GUI2锚点叠图和原flow ROI图，确认图中存在明显的产品水面错位，仍需中性几何校准来检验公式，不能直接修改ROI追逐纹理。

这两个包冻结的是上述历史尝试与anchor v1／v2准备；后续host修订和实机运行必须另包，不回写这些索引。正式采集失败和所有原门保持，新增人工关闭0。
