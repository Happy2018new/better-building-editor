# R28：附魔台书自然可见与独立 GUI 锚点问题

2026-10-22 23:45检查点。本次生产书代码、资源选择及资格数据均未修改，新增用户人工关闭为0。附魔台完整旧流程成功取得11张原图；编辑器中的书自然可见，但GUI2下明显位于台体上方并被Scene上边缘裁切。按预先约定跳过自然缺画的本体隐藏及原z控制，没有通过反复冷启寻找阳性或负例。该结果不能解释或关闭R25的GUI4间歇空白。

当前正式runtime基准为 `582e53517f949d1e2e351d40c531217a5b1e39f3`。复用R27已逐字核对的3712文件冷副本，应用8份正式runtime差异，得到3714文件；既有私有诊断alias只注册、不选择。没有重新制作大archive，source manifest SHA256为 `727b3c23589ed20d4faf6561a45dc16219239f41cdb1afcaece558dc1c47c1a8`。46个模板在真实Python2和Python3编译通过，STATE仅增加Theme缓存及实际Doll位置／大小的只读查询。

实机owner为 `books-r28-editor-v1`，原生附魔台采集、完整／缺失投影、实际占据／清除、层隐藏／恢复、编辑器隐藏／恢复及邻居场景共11图。completed、restored、source unchanged均为true，独立审计恢复原editor／document／profile对象、完整data、fields及factory，workspace关闭、投影actor0，原preview ready。没有执行body setter或模型alias切换，GUI2的A→按实际倍率→A也未在此实例中执行。

GUI2是单独的定位缺陷线索：实际书Doll短边约184.0797 logical，固定`/4`与`/2`相差46.0199 logical，即约92.0399原图像素。书与台体的分离和裁切量级一致，但尚未取得这条公式的书本单变量像素因果结果。旧R25负例与阳例均为GUI4，因而不能把这个线索归因为旧间歇空白。后续隔离候选仅为BookProfile的可选GUI回调及Scene书分支接线，主源未合入。

普通stop首次CLI返回1，原错误为游戏尚未在短时限内退出；随后在完整45秒宽限内自行退出，没有force，registry finalize返回0且exact identities均absent。保留句柄实际观察到game退出 `0xC0000409`、MCDK退出0，不能称正常引擎退出或推断根因。所属assert watcher没有已知恢复、未知断言或错误，游戏退出后按创建身份精确回收，exit0。

精简交付见[summary.json](../evidence/book-editor-r28-v1/summary.json)、[实际Doll读回](../evidence/book-editor-r28-v1/scene-readback.json)及[原图索引](../evidence/book-editor-r28-v1/evidence-index.json)。三张编辑器原PNG和捕获回执保持原字节；其余原图、765KB完整报告及来源manifest留在`.runtime/round-20261023/books-editor-v1/`，不把session配置或token入仓。
