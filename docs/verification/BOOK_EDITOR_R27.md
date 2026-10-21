# R27：编辑器书本缺画的当前冷源与初始化对照

截至2026-10-22 00:10，生产书代码未修改，外观资格没有提升，人工新增关闭为 **0**。本次讲台完整旧流程在编辑器初始即有书，预先定义的本体隐藏与原 z 控制均没有执行；附魔台在进入编辑器前因系统 available commit 低于6GiB停止并恢复。因此旧自然缺画证据继续保留，不能称作已修复。

当前源固定在 `a62257da0635d638947533d07ff34db147b757d1`，不是后续主仓 HEAD。从 git archive 提取3708个正式 runtime 文件；私有 overlay 仅在材质及模型表追加 alias，增加不透明诊断 fragment、两个只恢复原投影 z 的 vertex alias及原生著作 loot fixture，默认注册条目不变。最终3712文件，manifest SHA256 `029ef5705882133ab61f4946262670d4d9de9b8e59bed8632315b1fe03ded1c9`。旧固定完整流程 helpers 778文件与本次20个生命周期脚本分开校验；两家族各46个 payload在真实Python2.7.13与Python3语法检查通过。

| 执行 | 实际结果与边界 |
| --- | --- |
| `lectern-full-v1` | 真实原生著作采集，full／missing、占据及恢复、层隐藏及恢复、编辑器及邻居场景，共12张原图。scene_full与scene_shown书页清楚可见，scene_hidden仅剩支撑方块。completed／restored／source unchanged均True。body setter及alias切换均0 |
| `enchanting-full-v1` | 真实原生采集及native／full／missing共3图。occupied截图前available commit为6,267,641,856 bytes（约5.84GiB），触发 `system_commit_budget`。completed=False、restored=True、source unchanged=True、cleanup errors为空。未进入编辑器，未执行任何书控制 |

讲台本次原图 `scene_full.png` 的SHA256为 `446dcf23afa8ad9ea5fa932b66ff5b830b2b49a354d129a97d290c8d0cb0b7d6`，已与旧自然阴性及R25后续自然阳性原图直接并列读取。小包保存这次full／hidden／shown三张未改变的编辑器原图；其余原图及大报告保持原地，索引仅记录路径、大小与原始SHA，没有复制session token或完整session配置。

离线对照旧自然blank讲台、R25后续cold自然阳性、本次R27自然阳性：

- 三者真实采集Document的规范data完全相等；进入scene前除只读轮询次数外，操作顺序相同。
- 最终active slot均为1、实际native model ID均5、四组native uniforms逐项相同、默认profile相同、pending均None；这些CPU与原生读回不能代替GPU像素。
- 旧阴性和旧阳性截图同为1994×1105，本次为1931×1108。因此本次viewport变化不能单独解释旧两次的相反结果。
- 本次额外捕获到初始化中间态：本体native size为0、书renderer pending且临时scale约0.38239，随后本体size变为251.04×123.36、书ready且scale约0.41648。旧阴性与旧阳性只捕到空renderer再到ready；不同轮询次数不能证明初始化竞态。
- 本次与旧body控制源941处SHA差异中926处仅CRLF／LF变化，15处实质或新增差异属于已合入的kelp／chest链。两个默认book vertex、两个原z alias vertex及诊断fragment字节逐项相同；只对这些相同字节沿用旧离线编译事实，不当成live GPU证据。

本次readback保留了实际surface、doll及其20层祖先可见、普通本体为独立native支路的事实；它不能排除GPU binding、vertex、depth或scissor。旧阴性与阳性的原生矩阵、真正GPU资源绑定和绘制调用顺序尚未采集，没有单变量因果结果。目前不修改共享渲染链，也不根据本次阳性延长冷启试验来刷复现。

两轮finally与独立readback均恢复相同原editor／document ID、完整data、fields、factory、默认profile对象、workspace false、0 projection actors及preview ready。未恢复天气持续时长的旧工具边界继续保留。owner `books-r27-editor-v1` 已普通关闭、无force；game16332／creation `134370711089566981` 实际退出 **`0xC0000409`**，MCDK21388／creation `134370711087457406` 退出0。CLI stop与registry finalize为0，exact identities均absent；不能称正常引擎退出。新版known assertion watcher仅限本owner，recoveries／unknown assertions／errors均为空，确认游戏退出后按helper creation identity回收。

小型交付见 [summary.json](../evidence/book-editor-r27-v1/summary.json)、[scene-comparison.json](../evidence/book-editor-r27-v1/scene-comparison.json)及[evidence-index.json](../evidence/book-editor-r27-v1/evidence-index.json)，单件均小于300KB；R25负例与未完成控制门槛仍见 [BOOK_EDITOR_R25.md](BOOK_EDITOR_R25.md)。
