# R29：Scene 与固定库的私有联合候选

本包精简保存 `.runtime/library-scene-joint-r29-v1` 的全部31份顶层回执／driver／patch／控制脚本、实际5个delta源、必要baseline原字节、三份metadata的候选与baseline原字节、历史driver与最终58回执、独立只读复核及打包／扫描程序。**不收733文件／8,200,531 B工程树，不收119 MB或326 MB运行工程**。来源提交仍是 `dcf34132ce8e33284066efe66b9693ff89dc675a`，本包没有把候选合入产品。

独审对实际733文件小树与原732项manifest核对，只有5处差异：Scene替换、scene_owner新增、三份有限源清单各新增一个helper字符串。两份Scene候选与既有 `scene-owner-current-r29-v1` 封存原字节一致；把5个owner函数体和唯一helper import还原后，整个Scene AST等于原版。三份工具各删除新增字符串后，raw字节和完整AST均恢复原版。

旧library provenance的32项unchanged_candidates包含这3份工具；本次准确口径是**其中29项原SHA保持，另3项只增加helper清单项**，不是32项全部原字节不动。既有 `library-current-r29-v1`、`library-final-source-r29-v1`、`scene-owner-current-r29-v1` 的index原字节及SHA在本包绑定，历史失败与资格沿用原包，不重写成联合资格。29项源本身不重复归档，仍需原私有工程或相应封存来源。

## 原有执行回执与本次独审

联合候选既有真实CPython **2.7.13／3.13.13各58例**回执，分别8个构造hook场景与50个owner effect闭包场景。完整case结果和实际源SHA在双解释器间一致，case结果还逐项等于历史最终58回执。独审和本次打包**没有重跑58、115、66k矩阵、完整发现或9个CLI**。

旧driver仅变ROOT、PRODUCT和raw读取路径绑定；其余完整AST、**27个assert节点**以及外部输出target代码原样，源SHA改由新路径的实际raw字节自然计算。它只编译／执行提取的真实Scene前缀及实际helper，使用fake hook scheduler、native factory和资源close边界，**没有导入完整Scene、真实Pyreact effect、vendor adapter、SDK、游戏或GPU**。58通过不证明库import路径、包冷启动或原生表现。既有compile-only回执也只绑定两个Scene文件的Py2/Py3编译和3个宿主工具的Py3编译，没有宣称宿主工具兼容Py2。

源清单由实际候选AST独立读取：**water64／book-owner46／portal-code44+resources8=52，book BODY36不变**；三个owner清单中Scene和新helper各出现一次，BODY不含二者。书／末地source-only快照逐项对实际候选SHA，缺helper和漂移的原stderr／退出码全部保留。

**水旧合同的正常联合候选原本就exit1**：已有多个源、generator和artifact差异，不能把漂移后的拒绝归因于helper一项。缺helper时原CLI明确报告对应源错误；漂移时报告helper的actual SHA改变。这里证明清单绑定和故障可观测，**没有声称水漂移是唯一拒绝原因**，也没有生成新合同、metadata或qualification。三份metadata与原baseline逐字节相同，故障注入后helper已恢复且临时held文件不存在。

原before／after记录的4527项guard相等；独审只比较这两个历史map，没有再次读取4527份主源。独审另实读733文件小树，与manifest完全一致，并末次回读31顶层记录加5delta与3metadata共39项无变化。该有限只读结论不替代后续完整联合runtime包、普通游戏冷启动及编辑器／完整投影／缺失投影三路径验证。**MC／RPC／世界写入0、人工问题关闭0、发布／原生资格新增0。**

## 归档与复核

本包57份逻辑引用、54个唯一gzip对象；逻辑原文5,007,676 B，去重原文5,000,889 B，gzip 1,077,623 B，最大对象361,232 B。filename为空、mtime=0、level=9，重复压缩字节相同；index同时记录raw与stored SHA／长度。独立新进程解压回读全部对象，对实际选定源字节、确定性重压缩、封存index绑定、三工具与Scene／driver AST、58既有回执和metadata原字节再核，局部凭据扫描覆盖原文、JSON解码字符串与元数据。

若要复查本包，请按index引用路径还原gzip原文；SHA相同的逻辑引用共享对象。`review.py` 是先前对真实小树的只读审计程序，`pack.py --verify` 是本次精简归档的回读程序。旧driver需要原私有工程与fresh输出目标，直接执行会拒绝覆盖已有回执。本包不含完整733树，不能单独重建完整产品或取得原生资格。
