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

2026-10-23 01:32正式默认源补充：以`a6950ece68c1ae15176119e86043eb1989f79229`的已合并生产runtime增量冻结3714文件，manifest SHA256为`c6997654b7d9e9c253272196d23817e27c7d516a0481381159799d4c30fe99b7`。同一冷启实例先执行附魔台GUI2／3／4，再执行讲台GUI2；这次没有实例方法替换，正式Scene的book_view调用新增接口。附魔台14图、讲台13图，两份报告completed、restored、source unchanged均为true，cleanup errors为空。两runner各46份实际payload真实Python2／Python3编译通过。

| 正式默认Scene | 实际GUI | 实际前台模型ID | Doll与所属surface交集（logical宽×高） | 原图结果 |
| --- | ---: | ---: | --- | --- |
| 附魔台 | 2 | 5 | 340.625 × 92.056213 | 书位于台面上方、完整可见，无先前顶缘错位 |
| 附魔台 | 3 | 6 | 282.6875 × 102.284668 | 自然可见，未出现高位脱离 |
| 附魔台 | 4 | 5 | 267.878113 × 106.248199 | 自然可见；不据此关闭旧间歇空白 |
| 讲台 | 2 | 13 | 339.625 × 92.056213 | 打开的书贴在讲台斜面，完整可见 |

四张正式GUI原图及两个原生参考均已实际打开检查；四阶段捕获前后几何逐值稳定，真实前台ID与四组uniform读回匹配，实际surface祖先均visible，交集为正。原生canvas分别保留四元组、逻辑screen保留二元组，不把canvas取整误差推成分数GUI。profile始终为原同一默认对象，identity为`(1, 3.10.0.420447, native_artwork_idle_book_v1, 128)`，无实例ui_offset／ui_offset_for_gui覆盖。实际资源选择为`modern_projection_book_enchanting_table`或`modern_projection_book_lectern`，四次自然正例均按约定跳过body及原z控制。此次完成了正式接线的有限GUI验证，仍不覆盖任意平移裁切、所有姿态或书表面像素资格。

**来源边界更正：该冷源不是完整纯Git HEAD字节副本。** 它继承6项已声明overlay：额外的`behavior_pack/loot_tables/modern_projection/r21_signed_book.json`、诊断fragment、两份raw-z vertex，以及`entity.material`／`netease_models.json`的诊断注册追加。完整Git blob审计核对3710个Git运行时文件：1730文件逐字节相同，1978文件仅CRLF／LF行尾不同；两个注册表各仅新增4个`peony_r25_book_*` alias，0个既有entry修改或删除；另有上述4个额外文件，无缺失文件。默认book和product liquid模型／材质entry与Git解析值相同，其他生产文件没有实质内容差异。没有选择peony诊断alias；liquid这里只核对来源闭包，不计流体实图验证。首版原字节closure因行尾差异而拒绝的失败记录完整保留，分类后没有修改live副本；原始副本、manifest与报告均保留。后续报告不得把本次写成无overlay的纯Git冷测。

全部29个采集资源边界最低commit余量12.762GiB，附魔台game最高872 handles，讲台最高829，相邻最大增长均为1。两个夹具finally均恢复原editor／document／profile对象、data、fields与factory，workspace关闭、投影actor0、原preview ready，窗口恢复1280×720；原旧冻结3714文件也逐项复核未变。普通stop首次CLI为1，45秒内自行退出、无force；exact game退出仍为`0xC0000409`，MCDK为0，registry finalize为0，两个创建身份absent，watcher精确回收exit0。恢复完成、进程释放与正常引擎退出资格分别记录，旧GUI4间歇空白继续开放，新增人工关闭0。

本次精简[正式GUI汇总](../evidence/book-formal-gui-r28-v1/summary.json)、[四阶段原生读回](../evidence/book-formal-gui-r28-v1/formal-gui-readback.json)、[完整来源闭包](../evidence/book-formal-gui-r28-v1/source-closure.json)和[原始证据索引](../evidence/book-formal-gui-r28-v1/evidence-index.json)共20文件，单文件最大238032字节。四张正式GUI及两个原生参考PNG／回执保持原字节，四份视觉判定绑定原图SHA；完整27图和两份报告留在`.runtime/round-20261023/books-formal-gui-v1/`，未复制session token。
