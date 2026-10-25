# R29 两库生产切换前的最小缺口

本页补充[拆库计划](../REPOSITORY_SPLIT_AND_MIGRATION.md)，不改变既定决策、验证或冻结时间。主程序仍使用宿主实现，接库候选没有进入生产。最新私有工程以 `dcf34132ce8e33284066efe66b9693ff89dc675a` 和 CPU-v8 的 6333 个输入绑定：原 93 条加新增客户端／库 16 条、服务端 6 条，共 **115 条通过**；219 个实际产品／测试导入均来自新工程，adapter 与固定 vendor 对象身份一致。原件见[最终源接入包](../evidence/library-final-source-r29-v1/README.md)。

当前固定 dcf 组合已有一次完整私有 CPU 回归，布局实际调用方的最小双解释器缺口也已补齐；最终发布包冻结与新源原生资格仍待验证。下表分别记录已完成的 CPU 范围与切换前剩余工作，未达门则保留私有候选，不在周末验收后替换依赖。

| 顺序 | 最小工作 | 完成依据 |
| --- | --- | --- |
| 1．私有运行包的物理字节已核，最终发布组合仍待冻结 | 已按 3716 个 host runtime 加 29 份 runtime overlay（覆盖 7、新增 22）打成真实 ZIP，合计 3738 runtime＋2许可＋1回执。实际包中的锁、manifest、13库模块、保留的宿主依赖、入口及3资源逐字节核验。 | [运行包证据](../evidence/library-runtime-package-r29-v1/README.md)记录47,280,551B ZIP、5种实际异常包拒绝及真Py2／3各60个包内产品模块导入，未借用邻仓／SDK桩。独立外部审计另将全部runtime绑定到CPU-v8和完整组合的成功记录、前后清单及实际p源码。modMain只验存在与字节，未执行SDK入口、游戏冷启或三路径；仍不能称最终发布冻结。 |
| 2．候选完整 CPU 回归已执行 | 当前 dcf 私有完整组合完成 **3613 tests／10 skip／OK**；保留两处 book capture fixture 修补及原 32 份候选字节，不含 Scene 私有重构。随后对缺少档案的 9 条历史回放及原 census 基线执行独立定点，结果 **9 通过／1 skip**。 | [当前完整组合证据](../evidence/library-full-current-r29-v1/README.md)绑定 6989 项输入、326,464,656B 前后不变与 404 个实际私有产品导入。原全量仍记 skip10，不能改写为 skip1 或合计成 3623 个独立测试；唯一未补的 census 输入缺失见下文。旧 7021 的 3547 项／33 ERROR／10 skip 及后续 54 项定点作为历史保留，不再代替本次 dcf 全量。 |
| 3．实际布局 caller 的最小 CPU 缺口已补齐 | 真实 Python 2.7.13／3.13.13 分别运行宿主与固定候选，四路各 **33 条：22 正常＋11 拒绝**，完整输出一致。四个真实 caller 的常量消费及实际入口均覆盖；候选每个解释器在受测入口中记录到 vendor **context_position 18 次**，另外 8 个布局函数为 0 次。9 个 adapter 导出均核对 vendor 函数对象身份。 | [布局 caller 证据](../evidence/library-layout-callers-r29-v1/README.md)包含逐模块真实路径／SHA、入口事件、调用现场和完整结果。其余 8 函数沿用旧固定字节的 66,249 次布局对等，不能称为本次经 caller 调用或重跑；54 份 Document 控制同样是历史证据。最终包的编辑器／完整投影／缺失投影及冷启动原生检查仍待完成。 |
| 4．冻结新源资格 | 完成上述源、工具与包边界后，再按下文重验水、书和末地。 | 三份旧 metadata 原字节保留；当前 63-source owner checker 及旧 book／portal snapshot 仍明确拒绝。不得先改哈希、放宽拒绝或复制旧资格。 |

完整组合全量的 unittest 耗时为 454.072 秒，总耗时 473.296630 秒；之后的独立定点耗时分别为 29.505 秒和 36.778753 秒。9 条历史回放中，2 条正常重放保留原 V2 的 FAIL、V4b 的 OBSERVED 及两者 production_qualified=false，另外 7 条核验篡改、缺失来源及替换计划的预期拒绝；共 92 项实际历史源码绑定。唯一剩余 skip 为 `test_special_item_capabilities.InstalledSourceTests.test_checked_in_census_preserves_known_overlap_and_scope`，原因为 `Generated exact-version source census has not been created`。该全量与档案补验均未生成census来取得通过。后来独立的[40ID私有来源调查](../evidence/special-item-source-census-r29-v1/README.md)在私有fixture执行这1条测试，但没有补入默认路径或证明精确版本映射，不能改写原全量skip。这限制了来源普查范围，不影响已实际执行的CPU结果，也不能据此授予完整发布资格。

布局补验分别覆盖四个调用方的真实用途：`geometry_palette.prepare_palette` 消费 `MAX_LOGICAL_HEIGHT`／`OVERLAY_BASE`，验证雪／蕨的局部与全局叠加带；`render_context.prepare_context_palette` 调用 vendor `context_position`，而 Document builder 与局部分块 builder 使用导入的高度、上下文、叠加带和本地 schema 常量内联编码，不调用 `local_*` 函数；`preview_depth.depth_color` 实际执行函数内布局常量导入，验证普通／局部／全局布局包和距离裁剪；`spawner_marker.append_markers` 消费最大高度常量并校验传入叠加基线，只使用显式候选 profile。测试包含高度 127／128 及 129 拒绝、X=15／16 边界、可见层、越界目标和负世界 `render_origin`。逻辑调色板位置仍受非负边界约束，空的位置敏感植物 profile 没有提供随机偏移行为证据。

这次布局计数来自 `sys.setprofile`，生成器的 call 事件包含恢复执行；另两次真实上下文准备只作输出参照，未纳入受测入口的 18 次计数。只读源码 loader 在编译前核对冻结 SHA，避免已有 `.pyc` 混入，并保留原缓存。主源 Py2 的旧缓存拒绝、驱动准备错误和函数内导入范围的 AST 勘误均随原件保存，四路最终回执的执行计数与完整输出未被改写。没有 SDK stub、原生绘制或世界访问。

运行包v1构建器与独立外部来源审计分开记录：v1构建器绑定CPU before、封存overlay及物理文件；后来外部审计才核对CPU-v8成功／after、完整组合成功／before／after、404个实际导入与实际p文件。不能倒写为v1原本已具备这些门禁。初构建的许可换行拒绝、Py2驱动两次准备失败及最终v3原件均保留；五个ZIP负控未重复。状态库仍为3.9来源，3.10引擎资格不由此取得。47MB ZIP仅留私有目录，精简证据以清单和SHA引用，不复制大型运行包；复建仍需所记录的物理源及overlay。

新源验收先共用一次最终来源冻结和普通冷启动准备，再按 **水 → 书 → 末地** 执行，各自记录独立来源与结果。先跑来源拒绝负控和各家的 CPU 准备／生命周期检查；需要产生新合同或资格时，使用各家既有生成与验收流程，不手改生成常量。水优先覆盖既有产品门、动画与水池就绪，再完成编辑器／完整／缺失及隐藏恢复；书先复验两张公共卡、缓存／GUI 锚点和原稿恢复，再验三路径、台体遮挡与动画；末地覆盖 GUI 锚点、默认冷启、三路径与生命周期。最后以同一发布组合做普通冷启、保存／分享／撤销、typed NBT、旋转／镜像确认冻结与世界放置的小卡回归。旧专项阳性只保留为历史证据，不替新组合授予资格。水池与书的既有边界分别见[水池记录](WATER_POOL_GEOMETRY_COLD_R28.md)、[书公共卡记录](BOOK_PUBLIC_COLD_R28.md)，末地见[GUI 锚点记录](PORTAL_GUI_ANCHOR_R29.md)。

回退以完整包和明确 import 边界为单位：保留切换前宿主模块、相应资源／metadata、锁和候选证据；首批仅切固定纯状态与纯布局，不改 Document、Cell、NBT schema、保存格式或世界事务。校验或验收失败时回到切换前完整组合，禁止混用旧 metadata 与新实现，也不以静默 fallback 掩盖拒绝。已有真实世界写入保留原有“保留已写前缀、不回滚”合同，代码回退不能撤销玩家世界改动。按原计划，两个连续更新通过后才评估删除宿主重复实现。

本页和证据封装没有切换生产依赖、刷新 metadata、启动 MC 或新增人工关闭。预算、工期与更新排程仍由原计划统一管理。
