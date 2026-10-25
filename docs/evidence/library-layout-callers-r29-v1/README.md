# R29：固定源布局 caller 的最小双解释器验证

绑定 `dcf34132ce8e33284066efe66b9693ff89dc675a` 的固定私有候选。真实 Python 2.7.13／3.13.13 分别执行宿主与候选，四路各 **33 条：22 正常＋11 拒绝**，完整输出完全一致。候选每个解释器在受测入口记录 vendor **context_position 18 次**，唯一现场为 render_context.py:257 的 prepare_context_palette。其余 8 个布局函数实际计数为 0；9 个 adapter 导出仅核对了 vendor 同一函数对象，不能称 9 函数都经过 caller。

四个实际 caller 分别验证：geometry_palette 的雪／蕨叠加带与高度常量；render_context 的完整调色板函数调用、Document builder 与局部分块常量编码；preview_depth 的真实函数内布局常量导入及深度／裁剪编码；spawner_marker 的最大高度和分离叠加带。包含高度 127／128 及 129 拒绝、X=15／16 分块边界、可见层、越界目标与负世界 render_origin。负世界原点不等于负逻辑调色板位置；当前空的位置敏感植物 profile 不证明随机偏移行为。刷怪笼仅使用显式候选 profile。

权威摘要为 summary-v2.json，四份 final-* 回执包含完整输出、真实模块路径／SHA、实际函数身份、profile 计数和执行行。候选每个解释器实际载入 60 个模块、宿主 57 个；只读源码 loader 在 compile 前验证冻结 SHA，不读取已有 pyc。732 文件候选全树前后保护通过。sys.setprofile 对生成器的 call 事件包含恢复执行；两次真实上下文准备只作输出参照，未纳入受测入口的 18 次计数。没有 SDK 导入或 stub，没有 MC／RPC／GPU 或世界访问。

preparation-history.json 保留主源 Py2 旧字节码被严格守卫拒绝、可见层 fixture 和私有 loader 准备错误；旧缓存未删除或更改。早期成功回执与对应驱动也保留。原始回执的 module_level_import_before_profile 曾用行号启发式误标 preview_depth，import-scope-correction.json 以 AST 确认其为函数内导入；原始回执、计数和输出均未改写，不为元数据勘误重跑控制。

[index.json](index.json) 保存全部 17 份小原件（含原 archive-index 和 archive-index-v2），映射为 17 个确定性 gzip 对象。逻辑原文 1,435,054B，存储 106,213B，最大对象 11,949B；不复制 project。对象文件名为 raw SHA，索引列出 raw 与 storage SHA／长度；filename 为空、mtime=0、level=9。按 references.path 恢复原名，核对 raw SHA。两份原索引、四份最终回执／驱动绑定和摘要勘误绑定已再次校验。pack.py 仅封装／核验字节，不重复 33 条、既有 115 条或 66,249 网格。

局部凭据扫描及新进程解压／重压校验见 [verification.json](verification.json)。扫描覆盖原件、JSON 解码字符串、新目录元数据和[切换前检查](../../verification/LIBRARY_CUTOVER_R29.md)。这是指定 CPU caller 缺口的证据；其余 8 函数的旧网格是历史对等控制，当前完整组合全量另见[独立证据](../library-full-current-r29-v1/README.md)。最终发布包冻结、冷启动与编辑器／完整投影／缺失投影的原生资格仍待，人工关闭 0。
