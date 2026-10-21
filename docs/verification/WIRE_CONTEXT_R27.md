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
