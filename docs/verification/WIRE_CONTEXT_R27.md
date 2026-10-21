# R27：铁线下方混凝土复制的私有候选

当前生产 `render_context.py` 仍只有干态 aux5 地面拉杆下方冗余混凝土复制的窄修复；铁线扩展未晋升。新增人工关闭为 **0**，混凝土邻居变色问题继续开放。候选 SHA256 为 `cd37869a6d9f1222e148e9fc7143fc51f98648e75cd31523eddaed02db76fa1a`，仅增加 `_DRY_WIRE` 和三个 helper 的干态铁线判断，保留铁线自身目标、其他邻格和完整逻辑两层。

## 新 flat 实机对照

`flat-interior-actual-v3` 在同一会话中完成 opaque top／opaque grazing／默认透明度 top，各 base／repeat／candidate／restored 共12阶段、72条实际原生记录。逐阶段完整导出有独立长度／SHA及穷尽计数，最终使用1490字节的小退场回执；完整 factory、helper、geometry、profile、cache 对象和内容恢复，独立审计 `changed_keys=[]`、无标记／actor／job。该报告的 `native_resources_reclaimed=false` 如实表示原生临时几何随后由 owned process stop 回收，不能把 Python 恢复等同原生资源已回收。

主代理实际打开六张原 PNG：opaque top／grazing 两种视角的红线形状保留；默认透明度下混凝土顶面的十字亮斑在候选中消失。opaque top 四阶段报告的 red mask／RGB 完全相同，2017像素；grazing 对应1084像素。主代理另外独立核对72条导出／12阶段／24张原PNG的实际字节与绑定。该结论只支持本次平面代表，不能继承旧会话像素数量、也不构成边界／坡道／含水／其他支撑通过。

CPU私有业务对照覆盖1024正例、1288反例和2份混合缓存文档，包括16档信号与16色混凝土；这些期望仍留runtime，没有在未晋升前修改生产测试，也不能替代原生实机对照。

## 扩展失败与保留边界

同会话第一个 `flat-boundary-actual-v3` 在首次完整 `READ_PHASE` 导出RPC20超时，阶段导出0、截图0，后续恢复请求没有成功回值，`restored=false`。其余六个扩展未执行。小包同时保留旧 `flat-interior-actual-v2` 恢复失败，不以新flat成功覆盖它。

实际确认的7个有名context parts及原调用路径，可保守推导至少21条观察记录；每条重复完整 logical／work Document。真实Python2和已部署IPC原函数的最小重建，省略native输入等其他字段后，JSON已为24,169,732字节，JSON加repr响应下界48,340,592字节，超过16MiB接收上限。**实际完整响应未捕获、实际record总数未知；这是源／已确认数据的下界重建，不是抓包，也没有原生堆栈证明游戏退出原因。**

04:20普通owned stop返回0，game PID70008／creation identity134370868214296989实际退出`0xC0000409`，MCDK PID60944／identity134370868212434035退出0；专属watcher精确身份回收，exit1。没有强杀或自动重启；同身份活进程核验均已退出。CLI成功、registry stopped与游戏正常退出是不同事实。

## 可审小包

[安全小包](../evidence/wire-flat-r27-v3-small/README.md)包含78对象、91文件、4,899,424字节，每文件不超过250000字节；manifest SHA256 `61437df65fdbca309d90323da4a27198db32d5993e56fff3cda6493fc3e0f728`。新flat完整报告、12个完整phase、退场、六张关键原PNG字节分片、主代理复核、boundary失败及退出、旧v2失败、候选差异和CPU对照分别保留。完整项目archive不重复放入Git。

主代理独立重建全部78对象，逐字节比较74份实际来源，核对全部分片／容器／内容SHA，递归检查嵌套JSON、Base64、转义文本及本地凭据相等值，零发现；3个阳性和1个阴性扫描控制通过。工作区原件未被脱敏覆盖，派生与原件SHA分开。后续分块传输仍属私有验证工具，须新来源／计划／manifest及同会话flat门，不能借本次sentinel放宽新实现资格。


## 05:54 CRC32 分块新实测与未完成的边界

实际3.10游戏在任何诊断修改前通过 `zlib.crc32('123456789') & 0xffffffff == 3421780262` 已知答案检查。游戏本身缺少hashlib.sha256；新导出仅在游戏计算CRC32，按256KiB完整分块传输，host独立重建后才计算SHA256。此前v4在首个START即因缺少sha256失败，0阶段／0截图，原失败与独立恢复结果一并保存。

新 `flat-interior-actual-v5` 完成12阶段、72条原生记录、72个实采传输分块和24张原PNG，completed/restored/source_unchanged均true，cleanup为空。root独立逐RPC重建CRC及原始JSON，并实际查看六张关键原图；本次平面线形／厚度没有可见退化，默认透明度下混凝土十字亮斑消失。此范围仅为flat，不转授边界、坡道或含水反例。

同会话 `flat-boundary-actual-v5` 完整导出前7阶段／168条记录；第8阶段创建后，在111个分块中的82个已回传时，host尚未派发下一RPC便读取watcher状态遇到JSONDecodeError。该次失败读取的原bytes未捕获，不能写成实测空文件；独立离线对照只证明原in-place publisher确有可观察截断窗口。observer共创建192条而完整导出168条，故整体completed/restored=false必须保留；另一项独立运行状态审计确认factory/helper/cache/geometry/profile及marker/jobs/actors已恢复、source不变，restored=true。两者衡量不同条件，不互相覆盖。余下六组未执行。

普通owned stop返回0，但原生同handle记录game退出 `0xC0000409`、MCDK退出0；专属watcher精确回收退出1。没有强杀game/MCDK或自动重启，也没有native堆栈证明异常退出原因。

[新精简证据](../evidence/wire-crc32-r27-v5-small/index.json)保留flat、boundary失败、旧game SHA失败三包。root分别独立重建72对象／25对象／8份旧失败原件，核对68／23／8份精确实际来源及递归凭据检测，发现0；每文件小于300000B。完整source archive和大边界原JSON不重复入Git，原始大JSON保持runtime，Git保存可无损还原的gzip。

另有v6直接os.replace、v7有界5/32/33重试、v8 ReplaceFileW三个私有状态发布候选在实际Windows并发控制失败，均未晋升。静态share-delete保留handle对照中的ReplaceFileW成功不能替代500次并发控制；v8实际Win2的更深抛出位置未被捕获，不能据此断言target名称出现空档，也未增加Win2／JSON／schema／owner／identity重试。下一步只准备新私有named-mutex状态读写控制，当前没有凭此启动MC。生产铁线候选、混凝土整项及人工关闭继续保持原状态。


## 06:22—06:37：named mutex状态传输与动画水基线拒绝

新v10私有状态named mutex路线的17项并发控制经root独立实跑通过；四份窄host diff、三个状态读取点和3908个source／archive条目已逐项复核。新owner `wire-r27-crc32-mutex-v10` 的flat完成12阶段、72实际分块与72原生记录，恢复／独立审计和来源不变均通过，读取retry事件为0。六张原图只支持平面线形与表观厚度；候选的大亮十字消失但细虚线轮廓仍在。

其后的含水反例在原实现→重复原实现阶段被原masked RGB门拒绝，尚未进入候选：1998个线像素的mask相同，其中1557个RGB改变。完整原RPC重建确认native输入、逻辑文档、相机及screen相同，hidden图中自定义水仍在动画；没有当轮water uniform或引擎clock读回，不能称逐像素因果已经证明。该轮completed=false／restored=true，独立运行状态恢复成功；其他反例、坡道和边界未执行。原报告、失败与分析分别保留。

普通exact-owner stop返回0，retained handle实际game退出0xC0000409、MCDK0，watcher精确回收exit1；没有强杀game／MCDK或自动重启。无native stack，不推断指定根因。root独立重构[动画水基线失败与mutex证据](../evidence/wire-mutex-r27-v6-small/manifest.json)：105对象、132原存储文件、99精确来源、6派生，708个ZIP成员及全部JSON／Base64／转义文本递归扫描，凭据发现0。每文件小于300000B。

## 06:53—07:20：固定水纹的独立对照

## 本次实际取得的结果

固定水纹后的含水反例完成了原定的 **12 个采集阶段**：不透明俯视、不透明低角度和默认透明度俯视，各自运行原实现、重复原实现、候选和恢复原实现。两个不透明视角内，四种模式的原严格红石线判据——ROI、线像素数、mask SHA 与 masked RGB SHA——全部相等。默认透明度仍沿原方案采集颜色与可见性，不把它冒充为同一条 RGB 全等门。

这意味着先前动画水场景在 `opaque_top_repeat` 发生的基线不稳定，在本次固定水纹对照中没有再次出现；本次也实际到达了含水候选与恢复阶段。这仍只是一组私有对照，不能因此证明先前每个变化像素的因果，也不能代表其余未运行反例已经通过。

**本次冻结 host 的最终湿场景结果仍是 `completed=true / restored=false`。** `cleanup_errors` 原样保留一条 `water_observer / AssertionError`；独立运行时状态审计则为 `restored=true`，水观察器的实际组件、类初始化函数、模块标记与模型存活账本均恢复成功。二者必须分列，不能用后续离线解码解释回填原报告。

## 离线复核明确发现的 host 解码缺陷

冻结的 `water_resource_mapping_v1.py:79` 比较参数账本时少解了一层。观察器先把实际成功 uniform 调用的 value 包装成可传输表示，随后导出完整 snapshot 时再次包装整本账本。冻结 host 解开外层后，直接拿仍然包装着的 tuple 字典与实际调用重建的 tuple 比较，因此严格拒绝。

独立的只读分析按照原始已存格式，对内部 value 再解一次。**48 份 snapshot 中累计 7,488 个参数账本条目全部与实际成功调用相等**；**288 次 active group 快照**的真实 handle、资源名、前 3 组 uniform 与可见性 uniform 全部对应。此处是对成功 native setter 回执的核对，不能称为独立 native readback，也没有引擎着色器时钟读回。

实际导出的 **864 次原生调用全部保留参数、顺序和真实返回值并成功**，包括 72 次模型创建、72 次模型删除、432 次 uniform 写入，以及位置、缩放、旋转和包围盒各 72 次。实际 `CreateFreeModel` 资源名均沿冻结的 model、material、vertex、fragment、mesh、skeleton 与 texture 文件解析到本次固定水纹片元；相关源文件 SHA 随分析保留。最终存活模型数为 0。

只读分析文件为 `fixed-water-v7-readonly-ledger-analysis.json`，SHA `8bf462a687ee54453a40469b4bf1d7aa77fd7f4fd07fce5393380a4c5d69f88b`。原始湿场景报告 SHA 为 `c5a08154aa945a5363c72bb04d672875c0fdfa6b0a5a23d296d020912270a3e0`；原报告、观察器、冻结 host、native 回执和判定均没有被改写。

## 固定输入、独立审查与干燥哨兵

新私有 owner 为 `wire-r27-fixed-water-v1`。它沿用了已独审通过的 v10 状态 mutex、原游戏 CRC32 分块、原 native palette 观察器、完整 phase JSON 和红石线候选。3,711 份项目源文件只有 3 份水片元着色器改变，每份仅把动画 clock 和相邻帧混合因子两个表达式固定为 0；没有改资源名、材质名、纹理、几何、顶点着色器、透明度、颜色和所有权。

root 逐字节独审了 3,928 个源文件／archive 条目，并独立实跑了 **14 项真实桌面 Python 2 观察器控制**和 **7 项 host 控制**。这些离线控制明确使用 fake native 或 fake transport，只验证转发、参数与返回／异常对象身份、预算拒绝、导出计数和恢复，不能冒充真实游戏功能验证。非空、嵌套包装的 uniform ledger 未被当时的 host 控制覆盖，本次真实湿场景补出了这个验证工具缺陷。

freeze SHA 为 `2cbdb2c4a90f0155530e3a733e5ddfbf55dbfc7b2ec02d2fafd3d01db68264df`，full manifest SHA 为 `c9071fb6e08a1a360a23189524c02571b1cdc0df7649d60bdd80320aa26ff2ee`。新增 243,421 字节、23 条目的 host／shader delta 继承既有 4 个 archive，没有重打约 119 MB 的完整 cold source；delta SHA 为 `d5e71ffa59d2d1b47c72e95091012d66f0132b48686445ad80f7dd37fa75c05b`。root 独审记录为 round 目录的 `root-wire-fixed-water-review-v1.json`，SHA `33f83f35917f92878481ca2ab3df2231afcf7b2dfb9bcf4cb9d72d44ed4ec56e`。

同一新会话先运行了 `flat-interior-fixed-water-actual-v7`，12 阶段完成、恢复成功、cleanup 为空、独立审计通过、源文件未变。其 report SHA 为 `0fb729faf7078d8b2305885d0493307cbfc549b66e6b48ff8444c2e2f681462c`。干燥场景 water native call 数为 0，此为合理的 dry 计数，未被拿来证明湿场景。root 打开 6 张原图后只批准线形与表观厚度哨兵，gate SHA 为 `c0ef77b19f08f6137a6d00fbd09ffc9bb050a96b74c4c42fcdac5f051a0b2665`。默认透明度的大亮十字消失，但细虚线轮廓仍在，因此不宣称完整颜色问题关闭。

## 原动画水失败与本次退场

原 v6 的 `negative-wet-wire-actual-v6` 仍保持 `completed=false / restored=true`：在候选之前的基线／重复阶段，1,998 个线像素的 mask 完全一致，但其中 1,557 个 RGB 像素改变，原严格门拒绝。原生 palette 输入、逻辑文档、相机和 screen 均一致，而隐藏原生 actor 后自定义水仍在动画。该轮没有实际 water native uniform、active group 或引擎时钟回执，所以当时只能提出动态水混合是强证据，不能声称逐像素因果已证。原 v6 证据和本次固定水纹证据分别保存，未互相覆盖。

本次在北京时间约 **07:07** 已执行普通 exact-owner stop，命令返回 0；retained native handle 实际观察到 game 退出码仍为 **`0xC0000409`**，MCDK 为 0。没有 native stack，不能将非零 game 退出归因于本候选、water observer 或其他指定组件。没有强制终止 game／MCDK，没有重启，也未启动第三个 fixture。

专属 assertion watcher 保持冻结的 **07:45 自行退出**计划，暂未修改 watcher 或提前强制结束。其最终身份和退出码将在 07:45 后保存独立补充 receipt。游戏／MCDK 的普通 stop 与 retained-handle 退出记录已保存于 `launch-v7-fixed-water`。本记录此时不提前声称 watcher 已回收，最终退出证据另行补充。

## 后续边界

本次提供了可用的固定水纹严格对照和真实 water native 调用证据，同时暴露并解释了 host 的内部值解码错误。后续应在新的 host 版本补上非空账本控制、独立审查与新冻结，再决定是否继续其他反例。本轮没有重新运行修正 host，没有放宽原门槛，没有进行生产晋升，也没有关闭人工问题。


root独立重跑只读解码分析，864调用、288组快照及7488内部值均与原结论相同，输出SHA与原8bf462a6…完全一致。root实际打开湿场景两个不透明视角和默认视角各base／candidate共六张原PNG；只核对所述线形及外观，不把动物／时钟等场景差异当作fixture逐像素相等。

root独立重构[固定水纹完整精简包](../evidence/wire-fixed-water-r27-v7-small/manifest.json)：277对象、311原存储文件、271精确来源、6派生、12张原PNG均无损；1794个ZIP成员及嵌套文本凭据扫描发现0，5项scanner等价对照通过。正式原报告仍为restored=false，不回写、不授生产候选资格。根审回执和原图审阅另附于同目录，最终watcher自退将另增supplement，原manifest保持不变。
