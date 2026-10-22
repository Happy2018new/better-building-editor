# R28：最终公开蓝图的冷启动检查

本页区分最终运行源码、公开入口检查和人工验收。最终产品运行代码为 `b70ce7bf13ad6a4472f2b089ac812c162b174861`；自定义水的既有正式资格见 [水资格记录](WATER_FINAL_QUALIFICATION_R28.md)。新增三个小水蓝图后的三水卡加两书卡，现已由 v4 在普通冷启动中完成 GUI2 公共路径检查。当前人工关闭问题为 **0**。

## v1：保留首个失败，五卡检查未完成

来源为上述 b70 提交的 3,712 个运行文件及 36 个已固定的宿主辅助文件，不使用 bootstrap 或运行中替换 profile。实际只完成“水①·单水格”的一次公开载入与确认，留下卡列表和编辑器两张原图；完成的自然主帧为 **0**，其余四卡未到达。

首个失败是宿主 `assert_water_state` 的 `Complete typed water document changed`。现场游戏 Python 2 的载入前 expected、载入后 actual 和水 STATE 原始文档完全相等；宿主 Python 3 单独构建的材质表顺序不同，石头与水的索引交换，对应的压缩 chunk 编码随之变化。此事实不能把 v1 改记为成功，也不能将旧书冷测的来源资格转授到新源码。

独立只读诊断使用真实 Python 2.7 与 Python 3 的原 `Document.from_data`，解码完整 800 格，比较前景与 aux、背景与 aux、完整带类型 actor、头字段及 registry、所有声明的材质和 palette 行（含未使用行）、chunk 坐标及编码种类。两侧完整语义摘要均为 `c52a220baddc48687ce7c41c3bce4e6c03a6af19ac3cfce86ddde38873684153`，各自拒绝 12 个内容或类型错误的负控。后续新 owner 可仅修正跨解释器的水宿主比较；原始 wire 必须保留，书本同会话严格重载与缓存检查不变。

v1 的原 finally 完成两次原稿恢复审计，cleanup 为空，运行文件及 41 个绑定宿主文件前后不变。所属游戏、MCDK 与 watcher 已按 PID 和创建身份确认释放，未使用 force。游戏实际退出码为 `0xC0000409`，MCDK 为 0；正常引擎退出资格仍为 false。

精简证据位于 [v1 索引](../evidence/final-public-cold-r28-v1/evidence-index.json)，共 15 个文件、312,348 字节，含两张原 PNG、首失败状态、原 traceback、完整类型诊断、双恢复和独立释放。root 独立核对 14 个内容文件及 10 个原始来源指针，原图字节相等；实际查看编辑器原图可见水和石基座，此观察不替代未执行的主帧检查。原始大目录保留在 `.runtime/round-20261023/final-public-cold-v1/`。

## v3：一张水卡完成，保留真实的界面定位失败

v2 只完成准备，没有启动游戏。v3 使用新 owner、同一 b70 产品来源与经过独立验证的 V7 status I/O，实际完成单水格的 **1 对公开载入／确认、1 张自然主帧**。计数来自原始 `report.cards[].frames[].completed`，不是不存在的顶层 `frames`。水的完整带类型语义检查、冷启动默认 profile、native 调用来源与前后回读均已对这张卡执行；四格水池、含水栅栏及两书卡的完整检查没有完成。

第二张卡的首次失败发生在宿主全树查找 `identity=layers` 时：实际匹配了两个保留的编辑器 Inspector 控件和一个测试页控件。原始树 0006 的全局匹配数为 1，0029 为 3；测试页的 `TestBlueprints` 仍只有一个。其真实祖先已序列化 `PageMotion.page=testing` 以及 `RetainedPane(key=testing, active=true)`。原树未提供 `fiber._mounted`，没有补造此字段，也没有把本次宿主定位失败归因于产品或 V7 读写。

原 finally 的双恢复通过，cleanup 为空，全部运行文件和绑定宿主字节未变，所属进程与 watcher 已按原 PID 和创建身份释放，未使用 force。游戏实际退出 `0xC0000409`、MCDK 退出 0，正常退出资格仍为 false。独立读取 Windows Application Error 事件，仅确认同一 PID 和创建时间对应 `ucrtbase.dll` 中的 `c0000409`，没有取得原生调用栈，不能据此确定崩溃根因。

精简证据见 [v3 索引](../evidence/final-public-cold-r28-v3/evidence-index.json)，共 15 文件、669,730 字节。root 独立核对 14 个内容文件、10 个原始来源指针和三张 PNG 原字节，并实际查看全部三张原图。卡列表可见三个小水入口，编辑器与自然主帧可见水及石基座。完整五卡检查仍记录为失败，人工关闭仍为 **0**。

## v4：当前 b70 来源的五卡公共路径完成

v4 仅修正私有宿主的测试页定位：先严格确认 Session 页面与真实活动祖先，再在唯一 `TestBlueprints` 子树中执行原有唯一性检查。载入／确认回调、水与书籍 predicate、缓存重载、native 回读及恢复条件保持不变。root 独立检查 3,712 个运行文件、36 个辅助文件和 49 个宿主绑定；对两棵真实原树重放及 7 个错误场景拒绝控制通过。两次完整 main 离线回放覆盖成功及捕获失败恢复，随后另行核实上一个 owner 精确退出和新资源，给予 v4 一次独立授权。

实际冷启动使用自然 Session 默认的 ProductLiquidProfile 和 BookProfile，没有 bootstrap、profile 赋值、GUI setter 或诊断覆盖。三水卡各完成一张自然主帧；附魔台和讲台各完成自然、相反方向及公开重载后的主帧。合计 **7 对真实公开载入／确认、9 张完成主帧、23 次唯一捕获**；原 finally 的双原稿恢复通过、cleanup 为空、运行与49项宿主字节均未变。

七次公开载入顺序的当前匹配 native create 数为 `[1,1,1,1,0,1,0]`，现场累计 tile_builds 为 `[2,3,4,5,5,6,6]`。两次书卡公开重载均取得新的 Editor／Document，完整文档相等且缓存绑定到首次实际 create；不能只用 create 为0判断通过。全部七份完整来源证明与缓存／首次 create 的确定性摘要保留在包内，完整大数组留原 report。

ordinary stop 与 watcher close 均返回0，独立确认原 game／MCDK／watcher 身份不再存活。游戏实际退出仍为 **`0xC0000409`**、MCDK为0，无force，`normal_shutdown_qualified=false`；成功恢复和释放没有覆盖异常退出事实。

精简成功包见 [v4 索引](../evidence/final-public-cold-r28-v4/evidence-index.json)，28文件、2,563,359字节。root 核对27个内容hash、15个原始指针、9组PNG／捕获元数据原字节，实际查看全部9张主帧，并将原打包选择代码仅改输出目录重放；重建28文件与原包逐字节相等。水和基座、附魔台书、左空右带书讲台均可在原图辨认；小水卡和书卡可在人工查看时放大视图。

此次完成 **GUI2 编辑器公共路径 smoke**。没有重新授予水FA或世界投影矩阵、GUI4偶发空白、全部GUI／姿态、逐像素、原生对等或人工验收。v1、v3与离线准备首错仍分别保留。周末继续按[八组聚焦清单](../acceptance/2026-10-24-quick-guide.md)人工查看，新增人工关闭仍为 **0**。
