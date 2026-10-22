# R28：附魔台书自然可见与独立 GUI 锚点问题

2026-10-22 23:45检查点。本次生产书代码、资源选择及资格数据均未修改，新增用户人工关闭为0。附魔台完整旧流程成功取得11张原图；编辑器中的书自然可见，但GUI2下明显位于台体上方并被Scene上边缘裁切。按预先约定跳过自然缺画的本体隐藏及原z控制，没有通过反复冷启寻找阳性或负例。该结果不能解释或关闭R25的GUI4间歇空白。

当前正式runtime基准为 `582e53517f949d1e2e351d40c531217a5b1e39f3`。复用R27已逐字核对的3712文件冷副本，应用8份正式runtime差异，得到3714文件；既有私有诊断alias只注册、不选择。没有重新制作大archive，source manifest SHA256为 `727b3c23589ed20d4faf6561a45dc16219239f41cdb1afcaece558dc1c47c1a8`。46个模板在真实Python2和Python3编译通过，STATE仅增加Theme缓存及实际Doll位置／大小的只读查询。

实机owner为 `books-r28-editor-v1`，原生附魔台采集、完整／缺失投影、实际占据／清除、层隐藏／恢复、编辑器隐藏／恢复及邻居场景共11图。completed、restored、source unchanged均为true，独立审计恢复原editor／document／profile对象、完整data、fields及factory，workspace关闭、投影actor0，原preview ready。没有执行body setter或模型alias切换，GUI2的A→按实际倍率→A也未在此实例中执行。

GUI2是单独的定位缺陷线索：实际书Doll短边约184.0797 logical，固定`/4`与`/2`相差46.0199 logical，即约92.0399原图像素。书与台体的分离和裁切量级一致，但尚未取得这条公式的书本单变量像素因果结果。旧R25负例与阳例均为GUI4，因而不能把这个线索归因为旧间歇空白。后续隔离候选仅为BookProfile的可选GUI回调及Scene书分支接线，主源未合入。

普通stop首次CLI返回1，原错误为游戏尚未在短时限内退出；随后在完整45秒宽限内自行退出，没有force，registry finalize返回0且exact identities均absent。保留句柄实际观察到game退出 `0xC0000409`、MCDK退出0，不能称正常引擎退出或推断根因。所属assert watcher没有已知恢复、未知断言或错误，游戏退出后按创建身份精确回收，exit0。

精简交付见[summary.json](../evidence/book-editor-r28-v1/summary.json)、[实际Doll读回](../evidence/book-editor-r28-v1/scene-readback.json)及[原图索引](../evidence/book-editor-r28-v1/evidence-index.json)。三张编辑器原PNG和捕获回执保持原字节；其余原图、765KB完整报告及来源manifest留在`.runtime/round-20261023/books-editor-v1/`，不把session配置或token入仓。

2026-10-23 00:26更新：同一讲台实例完成预先声明的GUI2／3／4各一次A→B→A。A保留原固定`min(size)/4`；B仅替换同一BookProfile对象的实例方法，使用`min(size)/Theme.native_gui_scale`；A-return精确恢复继承方法。每阶段不换书资源、不改uniform、不重试renderer、不更换document／groups／camera，窗口变更后台执行并最后恢复原1280×720。该实例共21张原图，其中9张为GUI控制图；completed、restored、source unchanged均为true，cleanup errors为空。

| 实际GUI／原图 | B相对A纵向位移（logical） | 对应原图像素 | 原图观察与回退 |
| --- | ---: | ---: | --- |
| 2／1280×720 | +46.028102 | +92.056205 | A的书被顶缘裁切；B贴回讲台斜面；A-return恢复原错位 |
| 3／1600×900 | +12.785584 | +38.356752 | A的书悬在讲台上方；B贴回斜面；A-return恢复原错位 |
| 4／1994×1105 | 0 | 0 | A、B、A-return均可见并保持原贴合位置 |

九阶段在捕获前后实际Doll几何均逐值不变，各GUI内部A／B／A的实际前台ID、四组uniform及ready request不变；GUI2为ID5，GUI3为ID6，GUI4为ID5。GUI2和3的位移与公式逐值相符，GUI4严格恒等，A-return的完整几何与A逐值相等。所有实际surface祖先visible且Doll矩形与所属surface相交，因此本实验没有出现水分组中观察到的整个矩形离开viewport导致ID−1的情形；这不涵盖任意平移／缩放下的矩形裁切，也不解释R25实际ID5的旧GUI4间歇空白。九张原图已逐张查看。

正式窄修只新增`BookProfile.ui_offset_for_gui(size, gui)`并在Scene的book_view读取Theme已缓存的原生倍率；保留旧ui_offset及旧profile fallback。原生倍率需为有限正整数，未知／布尔／分数拒绝，避免静默使用错误锚点。ui_pose、资源名、world渲染、资格数据均未改。正式两文件与预先隔离候选逐字节一致，SHA256分别为`f56a9bfa35a8d961392c4b49b11149eea511d026d3badbacb261828562c35a5e`和`5f349249fd36f30100acc06bc9656d64f66ff35c978b076c2581ee1365c33048`；本次实机是等价算式的实例方法控制，**尚未以这两份最终源码重新冷启**，也尚未对附魔台执行对应九阶段。不得将此修复写成旧间歇空白已关闭或全部书外观已验收。

新增`tests/test_book_gui_anchor.py`的5项回归覆盖GUI2／3实测位移、GUI4恒等、GUI1与5、宽高互换、非法／未初始化倍率、同一Scene闭包2→3→4→2读取缓存，以及不提供新接口的旧profile。完整`test_book*.py`共57项通过；缺失模型负例的预期ValueError仍按原行为打印。两份生产源码真实Python2和Python3编译通过，MCP book_profile解析1文件无发现，Scene范围解析2文件仅有既有的两处大函数warning和一处参数hint。没有新增SDK调用、跨端导入或监听生命周期。

GUI实例owner为`books-r28-gui-v1`，冻结来源manifest SHA256为`0392ad9f72b277818f455846c969e6af4b16b48749625ecc540bae6a615b0033`，3714文件运行后逐字核对未变。22个资源边界最低commit余量13.135GiB，所属game最多851 handles，相邻最多增长6。finally恢复原editor／document／profile、data、fields、factory，workspace关闭、投影actor0、原preview ready。普通stop首次CLI仍返回1，45秒内自行退出且force=false；exact game退出`0xC0000409`、MCDK退出0，registry finalize返回0，两创建身份absent，watcher精确回收exit0。普通关闭完成与正常引擎退出资格分别记录。

本补充关闭了GUI2／3书锚点错位的原因调查并合入窄修；新增用户人工关闭仍为0，旧GUI4间歇空白继续开放。精简[GUI汇总](../evidence/book-gui-r28-v1/summary.json)、[九阶段实际读回](../evidence/book-gui-r28-v1/gui-native-readback.json)、[实现与实测边界](../evidence/book-gui-r28-v1/implementation-binding.json)和[原图索引](../evidence/book-gui-r28-v1/evidence-index.json)共22文件，9原PNG与捕获回执原字节保留，单文件最大248219字节；完整报告、源码manifest及原始退出失败记录保留在runtime，不复制session token。
