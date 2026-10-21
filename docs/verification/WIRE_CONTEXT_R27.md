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
