# R25：编辑器书本间歇缺画的冷源对照

截至2026-10-21 04:50，**未修改生产书代码或开启新的资格门**。完整旧采集流程已在独立冷进程中自然复现讲台及附魔台编辑器缺书；随后另一冷进程的相同默认模型又从初始可见。因此继续按生命周期／GPU显示问题调查，不把一次阳性或CPU参数一致写成修复。

## 已复现的冷源负例

基准为 `103633d06813488f2c3da563ddc0969366596f6d` 的3703个正式runtime文件；四文件私有overlay只追加两份材质／模型alias、诊断fragment和原生著作loot。最终3705文件，独立helpers778文件。完整manifest SHA-256为 `2dd9f89392a6cf1e1c747db74cd420df322bfed67fb23769b30d82bd66e8266d`。默认vertex、mesh、skeleton、texture与material states均保持，B只把默认fragment的discard分支换成有优先级的不透明诊断颜色。

| 执行 | 观察及边界 |
| --- | --- |
| `book-fragment-diag-v1/lectern-live-v1` | 完整原生著作采集、full／missing与占据恢复、editor流程；A5→B6→A5均缺书及诊断色。原生书和世界投影书可见。14图，completed／restored／source unchanged均True |
| `book-fragment-diag-v1/enchanting-live-v1` | scene_full自然缺书。未及时提交90秒检查点决定，host超时；8图，未执行B／A。迟写决定不算已执行 |
| `book-fragment-ancestry-v1/enchanting-repeat-v1` | 只读祖先payload在无UI时对None screen取属性失败，尚未到Scene；1图，原失败保留 |
| `book-fragment-ancestry-v1/enchanting-repeat-v2` | 明确repeat，修正无UI只读分支。A18→B19→A18均缺书，无返回阳性。13图，completed／restored／source unchanged均True |

两次完整A／B／A中，每阶段实际native ID及四组native uniform均匹配缓存；返回A复用原RenderGroup。profile、Document、signature和camera保持，没有retry、invalidate或重开workspace。enchanting repeat还从实际surface Ref找到唯一Fiber，沿其真实原生路径读取至 `/root`：surface、doll、缓存visibility和全部20个ancestor均visible，active size约267.88×122.92。它只排除本次enchanting的父surface隐藏，首次lectern没有相同直接祖先读回。

主代理独立核对四份report及摘要内七张阶段PNG的SHA，生成四页审阅图并实际查看11张来源图：讲台三阶段、native_authored、full、missing、scene_shown；附魔台首次scene_full及repeat三阶段。世界书清楚可见，编辑器本体显示而书缺失，B无不透明诊断色。审阅联系图和索引在 `.runtime/round-20261021/book-fragment-root-review-v1/`，原PNG未修改。

私有fragment在GLES2／3共12个compile/link组合、36个分支像素通过；首次Playwright缺默认browser在建立GL前失败，v2用已有Edge，失败保留。**这些宿主结果和native参数读回均不能证明实际GPU绑定、vertex执行、深度或scissor正确；B无像素也不能定位某个fragment分支。**

四次fixture均独立恢复，3705 runtime、配置、778 helpers、原hosts与manifest不变。原工具没有恢复天气持续时长，这一边界保留。owner `peony-r25-book-diag-v1`已普通停止，game52820实际退出 `0xC0000409`、MCDK59784退出0；exact identities均absent、finalize0、无force，不称正常引擎退出。

## 下一冷源的默认阳性

`book-body-depth-control-v1`预先准备两个最小私有控制：先只隐藏Scene普通PreviewModels实际根A→hidden→A；仍自然blank才在同一诊断fragment下做B→仅恢复WORLDVIEWPROJ原z的C→B。两家族vertex只多保存／恢复原z两行，x／y／w、clip、visible、动画、mesh与states保持。GLES2／3共16个compile/link组合通过，两个host各46模板在真Py2／Py3编译通过。

新冷runtime为3707文件，manifest SHA为 `99c4bdcb389b81d542f0b170dff815ede2efe37b5036f1f3046b8f4cb182e8a5`。讲台和附魔台各自完整旧流程的scene_full默认即有书；按预先规则跳过body及vertex控制，**实际setter／alias切换均为0**。两轮各12／11图，completed／restored／source unchanged均True，原对象恢复。不能把未选择的追加alias当成修复，也不能宣称原负例已消失。

04:50:01完成独立恢复并停止全部IPC，把同一MC交给主代理复用T04／T05。game5336、MCDK32624精确身份和source manifest见私有 `handoff-live.json`；当时仍ready，后续退出状态另记，不能提前声称已关闭。

## 仍开放的门槛

需要在自然blank发生时取得有区分力的body-only／原z对照，或通过其他明确根因形成窄修复；若始终默认阳性，不通过refresh／retry刷出想要的结论。修复后仍须补正式原标识、编辑器与full／missing、隐藏恢复、动画／台体遮挡及最终共同来源的冷启。正式书资格和周末人工验收不从本页诊断提升，本轮新增人工关闭为0。
