# R25：水新来源的三次启动与接入失败

2026-10-21恢复窗口为水重新准备私有41源合同，但三次尝试均未进入G／F-editor正式检查。本记录不授予新的生产／默认资格；水动画A、最终owner与默认冷启D继续开放，新增用户人工关闭为0。此前[lifetime诊断](WATER_CAPTURE_LIFETIME_R25.md)保持独立，不能用这次启动结果解释旧636.6348ms缺口，也不能用诊断短burst替代正式A。

## 来源与准入边界

私有项目 `.runtime/projects/water-r25-final41-v2` 基于主仓 `900100aa402f7442b1f1cf6cf1554f1f3d76fd14`。冻结4479个源文件、1391个辅助文件，三次结束后均逐hash不变。source合同为 `a564563ecf20f74b786565aaf0516575ab34c448b370a2bb2199319dc6b5c194`，owner为 `d0f37c33f8e054a0e906f44361edc43f49957b26b4af7853da9f2c0ca49bf20f`。新增 `kelp_render`／`large_preview` 是已审最小增量，不宣称完整传递依赖闭包。

旧qualification文件SHA `41956f315294c7540c3c11a8e629499abdca0afa4bfbc6607c4f25a1ea508c14` 及其标志未改；新owner与旧qualification不匹配。没有通过改常量搬用旧F／B／R／G资格，也没有关闭产品水门而暴露用户已否决的原生水。私有bootstrap只是诊断候选入口，其正常函数恢复仍需实际读回；默认构造拒绝后来已在原日志确认，见下方补证，不能据此授予可用默认路径资格。

## 三次独立结果

| 证据标签 | 实际经过 | 未取得的证据 |
| --- | --- | --- |
| v3，原目录 `water-final41-r25-v2` | 10:29启动跨10:32—12:56用户中断，readiness超时。原Debug_Log仍在资源加载，后才出现launchWorld；没有UiInit／gate错误可供归因 | bootstrap未派发；G／F-editor未开始；未观察到默认拒绝。150条启动样本含巨大中断gap，post-ready watcher未启动，不能称连续守门或截止覆盖 |
| v4 | 83.7617秒到工具ready。复制host时文本读写改变core换行字节，交叉绑定断言在RPC派发前失败；这是可避免的准备错误，原失败host保留 | 没有runtime bootstrap。cleanup读到bridge=None说明工具ready早于UiInit，既不是恢复通过，也不证明水门拒绝 |
| v5-r2 | 按原bytes恢复core及绑定，离线前断言通过。116.0113秒到工具ready，三次只读观察为bridge不存在、不存在、出现，Session／HUD始终不存在；原core只派发一次，IPC返回 `JSON request timed out` | bootstrap是否部分完成及原函数是否恢复均未知；未重放；G／F-editor均未开始，没有新水可见性证据。运行汇总当时未观察到的默认拒绝，已由下方原日志后审补证 |

v5 core精确SHA为 `088ae57b8ea713b7881a01b94b4289cb7b04f7e17f791d17fc2bf2be2b49fa26`，host绑定为 `4cd81f5ba6acf424d2b5ee52336d636d7f9dcacae871fcfa9d3dc69e9fbaff2f`；root已独核源／host交叉绑定。工具ready不能取代业务初始化就绪，后续应先观测UiInit及Session构造状态，避免把三个不同阶段混为一谈。

## 原生弹窗、资源与退出

v5出现属于精确game身份的 `DisabledSkinScreenController::onEntered @47` 断言：`The disabled skin popup has been displayed but the level data has no disabled cosmetics`。没有证据证明它由水代码或bootstrap引起。独立runtime恢复读取被protected window guard拒绝，**恢复未验证**，没有绕过保护重放业务。

普通stop及对原对话框WM_CLOSE未解除阻塞；核对PID、创建身份、父对话框及忽略按钮ID后，仅为关闭点击该按钮，随后普通stop返回0，未继续测试。v5连续guard有347条样本，game／MCDK最大句柄81183／235，最大相邻增长1995／10，未触及250000／10000门槛；6GiB可用commit仅在group命令前检查，不是连续内存覆盖。

三个game精确身份分别为 `41644 / 134370234325172297`、`59832 / 134370326718313303`、`41056 / 134370331574994851`。same-handle observer均实测退出码 `0xC0000409`，MCDK均为0；registry均stopped，精确身份消失，无force、无抢焦点、无休眠。最后一个实例在13:18:37退出。普通关闭完成不等于正常引擎退出资格。

## 下轮入口

先把工具ready、UiInit完成、默认构造失败与原生皮肤弹窗分开定位，再判断是否有条件做一次已绑定的新源G／F-editor。保留原生弹窗与IPC失败，不在未知部分执行结果上重放。正式A、F-world、B、R及D仍须在最终正确owner来源下按原门完成；不反复重跑条件未变的旧A，也不改写旧qualification消除失配。

[最小证据索引](../evidence/water-final41-startup-r25-v1/index.json)收录42项原始来源对应材料、分次结果、精确v5 host、guard、弹窗及退出记录，最大单件165490字节；[root独立审核](../evidence/water-final41-startup-r25-v1/root-review.json)逐项确认原raw与派生SHA。三个session token已在仓库副本脱敏，index分别保留original raw SHA、decoded sanitized SHA和redacted_fields，明确派生件不是原bytes。原runtime回执不变，大source／burst archive不入仓。

## 13:37：关闭后的原日志与启动配置只读补证

root随后读取三个已关闭实例的项目及实际生成 `.mcdev.json`。共同海带／箱、T02与水v5的项目配置语义完全一致；生成配置在验证并替换项目／session_probe路径、世界名及端口后逐项一致，均未显式设置skin_info。游戏版本、四类热更关闭、ui preset、flat seed、debug mod及自动入世选项相同，未发现水实例独有的皮肤配置。该比较不涵盖原生默认值、独立AppData缓存或level.dat，**仍不能排除皮肤初始化问题或证明其由水引起**。

水v5原 `mcdk.log` 第2678—2685行保存事件总线调用 `UiInitFinished → Session.__init__ → liquid_deployment.production_profile → liquid_product_deployment.production_profile` 的完整ValueError，邻近错误时间为13:14:28.467，早于唯一bootstrap前的第三次只读采样13:14:28.710662。因此**实际默认构造拒绝已在原日志观察到**，这补充了原运行汇总当时的“未观察到”，不改写原汇总或准入文件。

关闭时13:18:03.244641点击精确忽略按钮后，日志13:18:03.573出现TerminalHudScreen创建，随后有原生宠物toast异常与Client Destroy。它提示超时之后仍可能有工作继续，不能把IPC超时当成未执行；同样不能据UI类创建认定bootstrap完成、Session身份正确或原函数已恢复。相同petSysClient／show_toast异常也出现在成功完成海带／箱与T02的两个控制实例启动日志中，不是水v5独有，不能单凭它解释皮肤断言或IPC超时。没有重放，也没有据此授予G／F／D资格。

[只读补证索引](../evidence/startup-readonly-r25-v1/index.json)保存完整原日志SHA／字节数、带一基行号的精确片段、三个配置的原SHA、明确的实例字段归一化规则，以及关联的bootstrap／忽略回执。未再次启动游戏，未修改任何原项目、日志、原回执或生产代码。

[独立只读审核](../evidence/startup-readonly-r25-v1/independent-review.json)已确认三份子记录、六份配置原hash、28行水日志及两组各12行控制摘录与原件一致。默认拒绝错误邻近时间先于末次pre-bootstrap采样0.243662秒；HUD创建时间晚于精确忽略回执。审核前后原raw及新包不变，令牌扫描0命中，无新实机或资格。

## 14:27—14:32：v6取得同一冻结来源的候选编辑器证据

这次是新的独立尝试，不替换上面的三次失败记录。仍使用原私有项目 `water-final41-r25-v2`、相同4479源／1391辅助文件与119610822字节source archive，source合同、41源owner、旧qualification及原bootstrap core逐字节未改。41源仍是已审最小增量，不宣称完整传递依赖闭包。新的host在 `.runtime/round-20261021/water-final41-r25-v6`，owner为 `water-r25-final41-editor-v6`，session为 `00a09c6eaa77451f84982abe02c79b1e`。

根代理独立审核后才执行唯一一组调用。host将实际使用的28项外部依赖单独冻结，不用修正后的根工具替换旧项目内的冻结字节。已知皮肤断言watcher在冷启前启动，修正为核对精确game创建身份、断言内容、父窗口和IDIGNORE=5后，只对该按钮发BM_CLICK；未知模态窗口触发普通停止。v6实际未出现已知或未知断言，没有执行恢复点击，因此这次不能证明新的恢复按钮路径已在实机走通。

冷启耗时106.6963秒；工具ready之后，三次只读采样先后看到无bridge、无bridge、bridge出现，Session／HUD均未存在。随后唯一一次bootstrap在9.2527秒host阶段内完成，RPC结果与独立只读marker一致：先取得正常生产入口的预期ValueError拒绝，再由原core完成一次候选构造；构造选择次数为1。core与外层finally均实际返回，原 `production_profile` 函数精确identity已恢复，Session／HUD均存在。结束后又验证原函数identity并删除私有marker。没有重放bootstrap，没有修改或重新颁发qualification。

| 实际范围 | 已取得证据 | 限制 |
| --- | --- | --- |
| G编辑器 | gallery湿／干两张1994×1105背景WGC；completed、restored、source_unchanged均true，cleanup_errors为空 | 默认90%相机下40×8×50全览占屏较小。已实际读图，能看到水层差异，不能据此完成逐面视觉验收 |
| F编辑器缩减集 | `source`、`flow_east`、`wet_oak_fence`、`neighbor_stone`、`transparent_overlap`共5个case；原report中14个不同row标签、30张实图；completed、restored、source_unchanged均true，cleanup_errors为空 | host的finished_rows=13统计的是已跨过的row切换，末个row单独记录为final，原报告实际是14行。保留两个原始计数，不能写成完整19case矩阵通过 |
| F控制 | 对应case保留湿／干与截面隐藏／恢复；含水栅栏另有liquid_only、water_only、rearless、empty及alpha端点／中间值／默认值控制 | 是冻结动画的编辑器证据，不能替代动画A、世界F、B／R或默认冷启D |

代理已读取原始G湿／干图，以及F的水源、含水栅栏、water_only与透明重叠图；可以确认自绘候选水已进入可见编辑器路径。含水栅栏使用正面视角，其他case视角与gallery大小不同。没有据这些图判定几何、UV、alpha或整体风格合格，原报告的四个accepted标志均保持false。新增用户人工关闭仍为0，水A／D／最终owner及默认产品准入继续开放；本次进展是取得此前缺失的新来源编辑器实图及可核对的控制组。

独立恢复读取确认客户端与世界测试marker为空，投影实体数为0，projection_active、busy、edit_job、io_job、preparing_entity均false，冻结source仍相同。连续guard从starting阶段覆盖至精确身份退出，共254条样本；game／MCDK句柄峰值140119／235，最大相邻样本增长2453／20，未触及250000／10000门槛，也无未知modal breach。6GiB可用commit仍仅在各命令前检查，不是连续内存覆盖。32次捕获均保留前后台身份与背景捕获回执；没有请求前台许可或激活游戏。

首次普通stop返回1，原错误为“Game has not closed”；same-handle observer随后实测game退出码 `0xC0000409`、MCDK退出码0，精确身份均消失，再以普通stop收口registry，返回0、state=stopped。不能把group完成写成引擎正常退出。三个辅助进程也已按精确身份核对：handle watcher与exit observer已自行结束；game／MCDK均消失后，仅对仍空等的指定Python断言watcher核对命令、解释器路径、PID与创建身份，并通过其保留进程句柄结束。此辅助进程回收与游戏的普通关闭分别记账，没有force关闭game／MCDK。

[v6证据索引](../evidence/water-final41-editor-r26-v1/index.json)记录129个原始来源对应项，保留原raw路径／SHA／字节数及派生件SHA；原runtime不改。32张JPEG是全分辨率有损审阅副本，索引保留各自原PNG SHA，不能拿JPEG做精确像素或alpha测量。大JSON先对session token脱敏，再确定性gzip；超过单件上限的gzip按索引derived_parts顺序拼接后解压，可用decoded_sanitized_sha256校验脱敏内容。它们不宣称解码回原raw；原始119MB source archive不入仓。所有仓库单件小于300000字节。

离线证据包含原core48项控制、外层receipt谓词12项、实际wrapper成功／初始化异常／二次选择3种情形、实际modal判断12项；三段真正发送的dispatch／readback／retire在Python2.7.13解释器compile通过。保留的旧10项guard报告只证明相同纯策略，其内旧watcher SHA不作为v6新watcher运行证明；当前host独立绑定与254条实机guard样本才是本次证据。上述离线控制也不替代真实生命周期、IPC或产品视觉资格。
