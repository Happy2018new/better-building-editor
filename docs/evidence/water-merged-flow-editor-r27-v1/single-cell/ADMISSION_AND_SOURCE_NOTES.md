# 新合流源的普通初始化与单 cell 采样边界

这份说明补充并纠正先前 `water-next-A-workflow-v1/NEXT_A_WORKFLOW.md` 的普通入口前提。历史文档和原包不回写。

当前 shared 的 `liquid_product_owner_data.py` 与资格文件都保留 implementation 常量 `ef4f709969b6e96d7675529cd84ff27043706b23b723c4ee3d399497b32f4872`，resource/rules/style 常量也相符。普通运行期构造只比较这些生成常量，不读取当前源文件计算 SHA。因此，源码变化不会自动让运行期默认入口拒绝；独立 source checker 和发行核验仍应检测实际来源漂移。此处既不重算 owner，也不复制旧资格作为新源通过结论。

旧私有 GUI 源曾保留不同的 owner implementation `d0f37c33f8e054a0e906f44361edc43f49957b26b4af7853da9f2c0ca49bf20f`，所以旧 host 的“正常构造已拒绝、空 Session、再 explicit bootstrap”前置不能照搬。新 host 使用普通 `UiInitFinished` 的实际 Session，额外 payload 只读取 profile 类型、callback 函数身份、规则、引擎、owner/qualification 常量和模块文件位置，明确不调用初始化、不赋 profile、不修改资格。

source 数量 4484→4482 是净差：新 shared 去掉旧诊断的五个 `modern_projection_r27_anchor_*` shader，新增 `debug_concrete_blueprints.py`、`debug_dripleaf_blueprints.py` 与 `tools/check_liquid_product_owner_contract.py`。不是仅有两个路径被移除。新 source4482、aux1391共5873个显式输入均复制为独立新源，archive逐项解包核SHA；它仍不是完整传递依赖闭包，sibling renderer metadata不作实际运行依赖。

单 cell 固定为 `flow_east / editor / wet`，原 pose `(35,25,4.6)`，物理客户区1280×720、预期整数GUI2。采集用 `--production-default` 保留实际 Session profile。每次静态capture与burst前只读核SDK GUI缓存、active skeleton位置与尺寸（原0.02 logical门）、surface可见与native/renderer ID一致。该额外geometry读回在测量之前执行，不在burst测量内添加RPC。

原 nontrace startup helper、1500ms准备、3200ms测量、150ms最大source gap、512MiB总量、6GiB可用commit、250000句柄和10000相邻增长均不改。原失败manifest、28→29 source gap593.9861ms、27→28 worker未观察间隔538.3221ms及GUI2矩阵因子ratio1.190508均保留。此处没有裁burst、改ROI、拟合phase/offset或放宽门。

`run_group.py` 需要root对精确plan SHA的限时grant。root统一确认books大phase传输结束和quiet窗口后才启动。group正常与异常分支都执行Workspace关闭、blueprint恢复、额外profile/timing marker恢复、独立后读、source核验、ordinary owner stop、精确game/MCDK退出观察和watcher退休。stop返回码与实际engine退出码分列。

本组只检查新的普通初始化、GUI几何和一个完整nontrace采样协议cell。即使该cell通过，仍不能授完整15cell动画A、world A、最终资格、发行准入或用户人工关闭；所有这些字段继续false/0。前置静审执行59个实际launcher AST语句到Popen之前，仅watch状态和输出目录有显式fixture；不冒称真实SDK/像素已通过。
