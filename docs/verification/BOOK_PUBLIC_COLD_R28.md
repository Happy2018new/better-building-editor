# R28 两张书公共卡冷启动验证

本页记录 R28 的一次完成运行及其前面三次真实失败。完成运行 v4 在原生编辑器中从公共蓝图入口加载附魔台、讲台各两次，取得六张主帧，验证了新文档的严格缓存复用与原稿恢复。**资格只绑定冻结源 `48dedf14f2025f289a8d138382dc47b62b7a6f06`。** v1–v4 没有修改生产渲染器；v4 修复的是私有验证 host 对有效缓存命中的判断。

本次人工问题关闭 **0**，`runtime_pixels_qualified=false`。既有 GUI4 偶发空白、GUI 全矩阵、逐像素一致性及其他投影场景继续保持开放。

## 最终证据与来源

最终小包为 [book-public-cold-r28-v4](../evidence/book-public-cold-r28-v4/README.md)：原交付 24 个文件、1,392,563 字节，包含六张本次原 PNG、六份原 capture 元数据、四次缓存证明摘要、两次原稿恢复、独立退出复核、来源索引和前三次失败摘要。历史图片混入数量为 0。完整原始 source/cache/halo/native-create 数组保留在原始 report，包内以确定性摘要关联，避免复制大数组。

| 绑定项 | 值 |
| --- | --- |
| 本次 owner | `books-r28-public-cold-v4` |
| 冻结生产源 | `48dedf14f2025f289a8d138382dc47b62b7a6f06` |
| 精确 Git 运行时 | 3,711 个文件，另有 36 个 Git helpers；旧六份诊断 overlay 均未加入 |
| source manifest SHA-256 | `d9f9a35965835658d322905874f6931d5f5535d5a9940aece15e2e10cd85128f` |
| 53-file private host binding SHA-256 | `37e801b2d9eb1d3a492883b0c60d5ecbe15a98bf91c8cdebabdbf7bbd4474336` |
| 最终包 summary SHA-256 | `83ffbc401620dc0b16bcd6033f638631a9348f81fee4c0da67bdc91423371e58` |
| 独立退出复核 SHA-256 | `de79a58611aa7169ed747702b3f488733687e0a3777ce87bc2dc5986a2528af3` |

原始 host 位于 `.runtime/round-20261023/books-public-cold-v4/`，只读冻结项目为 `.runtime/projects/books-r28-public-cold-v1/`。具体文件与摘要见 [source-provenance.json](../evidence/book-public-cold-r28-v4/source-provenance.json)、[evidence-index.json](../evidence/book-public-cold-r28-v4/evidence-index.json) 与 [summary.json](../evidence/book-public-cold-r28-v4/summary.json)。实际运行前 root 审阅 host、入口、生命周期及缓存语义，独立重放完整离线 main，再执行只读预检并单独授予一次 MC 启动；预检本身不授予启动。

## 三次真实失败

下列失败均原位保留，没有把后续成功回填为此前通过。四轮始终使用同一份冻结生产源。

| 版本 | 已实际完成 | 首个失败及边界 | 后续 host 修正 |
| --- | --- | --- | --- |
| v1 | 首张附魔台自然方向；反方向原图也已取得 | 反方向截图前后实际相机姿态严格相等断言失败。旧就绪门 `.03/.003` 可在 `OrbitCamera` 的 `.0001` 最终吸附前返回。失败姿态数值没有持久化，无法补造实际偏差。重载与讲台未执行 | 私有探针只读获取已挂载 Scene 的实际活动相机回调闭包；等实际姿态精确到达目标，未冻结或替换相机 |
| v2 | 附魔台自然、反方向两张精确相机主帧 | 首张卡公开重载的 load/confirm **尚未派发**，其前置卡片截图重复既有文件名；原 helper 拒绝已有 PNG，报 `ValueError: Choose a fresh PNG output`。讲台未执行 | 截图路径加全局单调前缀；保留原 helper 的 fresh-output 拒绝 |
| v3 | 附魔台自然、反方向；第二次真实公开 load/confirm；新 Editor/Document 且完整 typed 内容相等 | 正常缓存命中，当前 nonce 没有新 create。旧 controls 仍要求 tile 名来自当前 nonce 的 create；实际 RPC `check/rpc/0049.py:32` 的 `assert part['name'] in names` 拒绝了复用。未完成重载主帧与讲台 | v4 加严格首次创建和缓存来源证书，不再把“必须当前 nonce 新建”当成有效复用的必要条件 |

v3 失败 RPC SHA-256 为 `fa342143ec4204d590d2b5fa1c5f9c299c5ebe76cff30b53ba858a0ac9b1073c`。原 `TiledPreview.source_state`、`restore_cached`、`submit` 允许内容相等时跨 Editor 身份复用，这是实际运行时行为。v3 当时未序列化完整 cache/source/data/bank，**不能事后把该次现场提升为严格来源证明通过**。其旧离线 fixture 没有执行真实 client controls 断言，确实漏掉了该问题。

三个版本均完成双恢复、源未改、精确 owner 的 ordinary stop、registry stopped 与 watcher 退休；其游戏退出码均为 `0xC0000409`、MCDK 为 0，均不属于正常引擎退出资格。原失败摘要见 [v1](../evidence/book-public-cold-r28-v4/prior-v1-run-summary.json)、[v2](../evidence/book-public-cold-r28-v4/prior-v2-run-summary.json)、[v3](../evidence/book-public-cold-r28-v4/prior-v3-run-summary.json)。

## v4 私有证明的变化

v4 仅增强私有 host：`cache_certificate_payload.py`、探针的真实 native palette 导出、`EntryCheck.CONTROLS` 与 main 的探针安装。生产 runtime、相机实现、截图 helper 及原 finally 路径保持原字节。证书存在既有 `sys._book_public_r28` 私有快照内，并由原 finally REMOVE 删除。

首次创建证明绑定实际 name/result、nonce、Editor/Document、当前 fixture 与完整原生 palette。公开重载的复用证明还要求同一 Session/Tiles/key/name/bank、完整 typed Document/context/source/halo/data/count 一致，重建当前纯 surface 的结果相等，并回溯同一份未改的唯一首次 create。完整源及 COW 所有权在前后只读检查中相等。仅持有一个旧 name 不足以通过。

实际 raw chunk 是 `IntegerBuffer`，导出保留 typecode、itemsize 与全部整数；dict/list/tuple/int/bool 分别保留类型。只在 SDK native palette 比较处归一化 tuple/list。该处理没有对含 `_struct.Struct` 的 IntegerBuffer 做通用 deepcopy，也未为了通过检查改变生产 cache。

## v4 实际公共路径结果

两张卡是 `test.entities.book_enchanting` 与 `test.entities.book_lectern`。每张经过真实公开加载和确认，再从同一公开入口重载一次；共 **4 对 load/confirm、14 次全部使用唯一文件名的 capture、6 张主帧**。两次重载均产生新 Editor 和新 Document，完整 typed 内容相等。

| 顺序 | 公共卡 | tile 对应本次 native create | 所有当前 nonce native create（含网格/轮廓） | 累计 tile_builds | 已证实路径 |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | 附魔台首次加载 | 1 | 3 | 2 | `current_exact_native_create` |
| 2 | 附魔台公开重载 | 0 | 0 | 2 | `strict_equal_document_cache_reuse` |
| 3 | 讲台首次加载 | 1 | 1 | 3 | `current_exact_native_create` |
| 4 | 讲台公开重载 | 0 | 0 | 3 | `strict_equal_document_cache_reuse` |

这里的零 create 来自现场当前 nonce 的实际记录。`tile_builds` 是实际累计值：首次卡检查前已有一次 build，因此现场为 `[2,2,3,3]`，不能把去掉基线后的值标作累计。不能把“tile 对应创建”与包括网格/轮廓在内的所有创建计数混为一谈。完整选中公共卡行为见 [public-cards.json](../evidence/book-public-cold-r28-v4/public-cards.json)，四份来源证书摘要见 [cache-proofs.json](../evidence/book-public-cold-r28-v4/cache-proofs.json)。

每张主帧都执行截图前后实际相机姿态精确相等、实际 native book ID/uniform、可见祖先和 preview 就绪门；没有替换 renderer/profile，也没有实例 GUI offset 覆盖。实际默认 GUI2、capture 为 1280×720。下列六张均为本轮原始图片，child 与 root 均打开审阅：

| 卡 | 自然方向 | 反方向 | 公开重载 |
| --- | --- | --- | --- |
| 附魔台 | [0003](../evidence/book-public-cold-r28-v4/0003_book_enchanting_natural.png) | [0004](../evidence/book-public-cold-r28-v4/0004_book_enchanting_opposite.png) | [0007](../evidence/book-public-cold-r28-v4/0007_book_enchanting_reloaded.png) |
| 讲台 | [0010](../evidence/book-public-cold-r28-v4/0010_book_lectern_natural.png) | [0011](../evidence/book-public-cold-r28-v4/0011_book_lectern_opposite.png) | [0014](../evidence/book-public-cold-r28-v4/0014_book_lectern_reloaded.png) |

本组原图中附魔台书在三帧均可见，空讲台与有书讲台可区分，反方向及重载后书仍可见，未观察到早先 GUI2 的高位截断。该观察覆盖这六个视角与本次状态；不等于所有姿态、GUI 尺度、投影或像素验收。

## 恢复、退出与独立复核

原 finally 的 [第一次恢复](../evidence/book-public-cold-r28-v4/restore-audit-1.json) 与 [第二次恢复](../evidence/book-public-cold-r28-v4/restore-audit-2.json) 均通过：完整草稿及 typed 文档、profiles、library 对象/语义与存储、undo/redo/selection、字段及 preview_ready。`cleanup_errors=[]`，运行后 3,711+36 源及 53 host 文件仍相等。

启动、public-book-cards、ordinary-stop、watcher-close 均返回 0；没有 force，没有同 owner 重试。实际游戏 PID 70616、MCDK PID 34048，创建身份见独立回执。游戏实际退出为 **3221226505 / `0xC0000409`**，MCDK 为 0，因此 `normal_shutdown_qualified=false`。registry stopped 与 watcher retired 已记录。

结束后独立只读复核精确 PID/CIM 创建身份：归属进程已不存在，或仅剩零线程、零句柄、空 exe 的墓碑；没有存活的本 owner 游戏/MCDK。结束时间为北京时间 **2026-10-23 04:26:32.410059**。见 [independent-release.json](../evidence/book-public-cold-r28-v4/independent-release.json)。这证明 slot 已释放，不把异常游戏退出解释成正常引擎停机。

root 另在原 host 下生成 `root-package-review-v1.json`，独立对齐原 report、四份完整 proof canonical digest、选中公共卡、六 PNG/capture、双恢复及退出回执，24-file 包审通过，凭据扫描为 0。

## 离线验证及其实际边界

`verify_full_workflow.py`、`real_cache_fixture.py`、`cache_rejection_controls.py` 的最终输出位于 `.runtime/round-20261023/book-v4-workflow-controls-final/`。执行的是冻结 Session 签名、实际 `TiledPreview.refresh/advance/cache`、Bridge geometry/prepare_palette、真实探针与 client controls；包括以下三例：

1. v3 原失败 RPC 对真实 cache hit 仍拒绝，证实旧 host 缺陷可重现。
2. v4 实际完整 main 完成四对 load/confirm、14 capture 调用、56 条唯一输出路径及六主帧。
3. 注入讲台自然帧 WGC 失败，完整 main 仍经过 finally 和双恢复模型。

其中 engine UI 派发/native book 可视读回、SDK endpoint、资源和进程观察、WGC 像素均为 fake。**完整 main 中的原 restore/AUDIT 使用边界模型，并非完整原生活动对象恢复。** 原生双恢复通过来自前一节真实现场，离线例不得替代它。

每卡 3 个 fresh 加 11 个 reuse 错源用例，共 28 个，覆盖实际文档、halo、context、data、cache/source/bank/key、native provenance/full palette、异 Session、真实旧名没有对应证书等，并核对每次精确恢复。旧名负例是“真实旧名无严格证书”，**未直接篡改 `part['name']`**；不宣称完成后者的测试。

六个原 capture helper 拒绝用例确认已有 PNG 与 capture-report marker 字节不变。真实 Python 2.7.13 与 Python 3.13.13 各编译同一份 14-payload inventory，含 EntryCheck STATE 与 CONTROLS。最终回执为原 host 内的 `syntax-final-py2.json`、`syntax-final-py3.json`。

离线准备的前五次失败均原位保留：前两次缺 fake time 全局，第三次缺 fake renderer heartbeat，第四次 tuple-key native palette 不能直接做 STATUS JSON，第五次通用 deepcopy IntegerBuffer 失败。第六次完整三例通过，第七次加入 28 个错源负例，最终版补 count/source-COW 只读检查。它们属于 fixture/导出准备记录，不能记为原生运行通过。

## v4 与后续源的只读差异

另对冻结 v4 与明确 Git 快照 `50a93dd3e360421c3d8de752e1fb638d8499bdd4` 做了精确 blob 比较：3,711 个 runtime 路径无增删，**仅两路径、3 行替换**，3,709 个文件完全相同，resource_pack 变化为 0。

| 路径 | 变化 |
| --- | --- |
| `behavior_pack/modern_projection/projection/liquid_product_owner_data.py` | `IMPLEMENTATION_CONTRACT_SHA256` 从 `ef4f7099…` 改为 `f54d64cd…` |
| `behavior_pack/modern_projection/projection/liquid_product_qualification_data.py` | `QUALIFICATION_SHA256` 从 `a324df78…` 改为 `2f827d28…`；implementation 摘要同步 |

两版均保留 `PRODUCT_QUALIFIED=True`、product stage、引擎 `3.10.0.420447`、resource/rules/style 指纹及同一组 16 个通过门。非 runtime 的 `tools/data/liquid_product_owner_contract_v1.json` 同步变化。完整 SHA、map 摘要与原始只读回执保存在 `.runtime/round-20261023/book-v4-to-current-runtime-diff.json`（SHA-256 `7b53b27821783bdeab266404d9d6d5fe4483a8b6a9ace0767d6522f90822abb3`）。

比较明确使用 Git blob，没有把工作树字节冒充该快照。首次比较错误地对 raw worktree 做期望断言而失败，已保留独立失败回执；复核确认 1,067 个文件只是 CRLF/LF 差异。当时另有 root 正在开发的 `debug_blueprints.py` 改动与新 `debug_water_focus_blueprints.py`，它们不属于 `50a93dd3` 快照，也不纳入上述“两路径”的结论。

正常 `Session.__init__` 先执行 `liquid_deployment.production_profile`，它进入 `liquid_product_deployment.production_profile`，会读入上述两份水 metadata 并验证；随后才独立取得 `book_profile.production_profile`。书 qualification、Scene 的 BookPreview 与 LiquidControls 挂载、共享 LiquidPreview、TiledPreview、Bridge 和书 resources 均在这两个 Git 快照间保持相同。TiledPreview 使用的 liquid ownership identity 来自支持的 WATER/LAVA 名称，不直接使用 qualification SHA。

冻结源实际 builder 产出的两卡均无 water/lava：附魔台尺寸 `[8,6,8]`、2 格；讲台 `[12,6,8]`、4 格。前景为 cyan_concrete 加对应附魔台/讲台，背景均 air。**干书卡静态路径未变也不能把 v4 原生资格转授当前源**，因为正常 Session 冷启动仍执行已变化的水资格初始化。新增水聚焦卡等后续 runtime 变化更需独立绑定新源验证。

如进行最终 candidate smoke，应另用 root 选定新源的精确冻结项目、host binding、新 owner 与单独 MC 授权，从公共入口验证三张水聚焦卡及两张书卡、真实 typed 文档/聚焦/native 前台/原图、原稿恢复与精确退出。此处仅规定范围；本只读比较没有启动 MC，也没有赋予当前源新的原生或像素资格。
