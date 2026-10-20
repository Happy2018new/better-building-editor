# R23 变换实机验证：就绪条件与夹具类型修正

日期：2026-10-19。详细回执见 [TRANSFORM_R23_RUNTIME.json](verification/TRANSFORM_R23_RUNTIME.json)。本页记录验证工具与夹具修正，不计为用户问题关闭；编辑器、完整投影和缺失投影的人工验收仍分开。

## 空分块的旧签名

冻结失败报告 `.runtime/round-20261019/transform-runtime-v3c.json` 发生在 T01 旋转后的预览等待。当前文档为 43 格，文档和编辑器身份一致，整个模型 revision 已更新，dirty 为 0，构建、预览挂载、编辑任务、IO 任务均未运行，renderer 最近仍有提交。四个 owner 的摘要如下。

| Owner | 内容数 | 模型名 | 签名为当前 | 缓存一致 | Pending |
| --- | ---: | --- | --- | --- | --- |
| `(0,0,0)` | 43 | 有 | 是 | 是 | 否 |
| `(0,0,1)` | 0 | 无 | 是 | 是 | 否 |
| `(1,0,0)` | 0 | 无 | 是 | 是 | 否 |
| `(1,0,1)` | 0 | 无 | 否 | 是 | 否 |

原因是 `TiledPreview.refresh()` 按实际改动和六个直接邻居更新 dirty；该旋转没有碰到对角空分块。`restore_cached()` 和 `submit()` 只更新实际处理过的 owner 签名，而 `advance()` 在任务耗尽后发布整个预览的当前 revision。对角分块保留旧签名，未保留旧网格。

工具继续输出原始 `current_signature` 和 `all_parts_current`，另加严格的 `ready` / `all_parts_ready`。仅当旧签名 owner 同时满足没有模型名、没有 pending、缓存来源与内容一致、全部前景/背景/actor 计数为 0，且扫描 `region_bounds()` 给出的实际区域后确认当前权威文档中没有任何格，才接受其空区域就绪。不能用固定 16 格边界替代实际 owner 区域；背景层、NBT 格、非空旧模型、失效缓存或全局任务未结束均不能走该条件。

该变更只在 QA 工具。七个测试通过真实 Session 和 TiledPreview 重现旧对角签名，并覆盖上述负例；原来源、挂载和相机验证 26 测继续通过。v4 的 T01 与 v5 的全部四例已通过实际等待，v5 T01 仍明确记录旧对角签名和 `empty_source_current=true`。

## T04/T08 的两解释器输入差异

冻结 v4 报告的 T01 已通过 loaded、rotate、undo、redo、undo_again 五阶段。后续 T04 loaded 因完整 typed document 比较失败停止，恢复成功。

夹具 `_paired_chests()` 使用 `dict(Name=..., Count=..., Damage=..., Slot=...)`。Python 2 的关键字名是 bytes，即使启用 `unicode_literals` 也不会变成 unicode；Python 3 的同名关键字是文本。因此两端输入在 Count/Damage/Name/Slot 键的类型上确有差异。现改为显式 unicode 字面量键，T04 与 T08 共用该工厂。完整 typed 比较器保留，不把 bytes/text 当作等价。

修正后的文件 SHA256 为 `a97c9622898eb6d73a2729d495aafa8ec0dbad9164ec54c7ba587b5bc5736b28`。冷副本同步回执为 `.runtime/round-20261019/transform-fixture-cold-amendments-v1.json`。真实 Python 2.7 与 Python 3 对四夹具、六种变换及撤销/重做的 100 个状态通过完整语义比较；选择、起止坐标、历史深度和 revision 等字段仍严格相等。11 个 runtime-tool 测试还覆盖 NBT 键 bytes/text、值类型、标签类型、列表顺序、背景、坐标、size/name/biome 的差异拒绝。

## v5 四例实机与外观边界

v5 在 `alpha-r23-cull-v1` 冷副本完成 T01/T04/T05/T08 共 21 个数据阶段，包括 T08 锁定伙伴层后整笔拒绝；报告 `completed=true`、`restored=true`，cleanup errors 为空。世界、玩家、物品栏和库文件未写入。该副本使用私有 culling terrain 声明，不能据此给主材质外观验收升级。

已实际打开四例的全部 12 张主原图。T01 的编辑器旋转前后及完整投影主体可见；T04 的编辑器与投影只见红蓝底座，箱体不可见；T08 同样未见门与箱体；T05 编辑器能看到旋转后的四排轨道，但完整投影部分出画，不能作为全体几何验证。隐藏图保留在报告中，不由整体像素变化数替代目标形状判定。

## 缺失投影的受控观察

工具新增显式 `--missing` 开关，默认四例流程保持原行为。受控 observer 只提供逻辑格的占用观察，不放置真实方块。目标限定为 T01 紫色上角、T04 一对跨格双箱、T05 首组坡轨与坡顶、T08 跨 Y=15/16 的门。双格主体分别记录单半、双半及恢复；每阶段保存 shown/hidden 原图、owner/work serial、cache/origin 来源、编辑器身份/revision 和文档语义。

首个 v6 在 T01 missing_empty 被 snapshot 比较拒绝，随后 observer 与所有临时状态恢复成功，未接受任何 missing 阶段。该历史失败保持原样。旧 helper 未保存判定失败时的 raw state，因此不能声称拥有该次 exact diff。离线源码与测试确认 `WorldProjection` 和 `ProjectionOccupancy` 的快照合同为 `Document(source.size, biome=source.biome)` 后复制 blocks，显示名称为默认“未命名建筑”。

修正后的 helper 按此合同构造独立预期，仍严格比较快照的 size、biome、默认名称、两层材质、位置及全部 typed actor；编辑器原名称和历史继续按原完整比较器验证。新 helper 在判定前保存原始阶段 state，避免下一次失败丢失诊断数据。八个离线测试通过，另覆盖安装回执丢失后的受控恢复及拒绝清理其他任务的 observer。

## 主材质短复验与 T01 缺失投影

后续 `firefly-r23-c-v1` 冷副本使用主 terrain（SHA256 `b20079f22bb9272d036f1ca4c1c148ab2a0a9c05ad0cf894b644db93ebd5971b`），不沿用 v5 私有 DisableCulling 声明。v7 的 T04 通过 loaded、mirror_x、undo、redo、undo_again 五阶段，`completed=true`、`restored=true`。已实际打开前后编辑器、完整投影与隐藏参照四张原图；两组双箱均完整可见，隐藏参照去除了投影。该结果支持把 v5 的箱体不可见归入候选材质污染，不能继续作为主材质箱体消失结论；T08 主材质外观仍未复验。

v8 的 T01 通过原五阶段以及修正后 `--missing` 的 empty、occupied、restored 三阶段。目标是旋转后的紫色上角 `(6,5,2)`；观察值依次为 `[1]`、`[2]`、`[1]`，work/occupancy 两份快照、编辑器原文档、revision 和 source/cache/origin 身份检查均通过。`completed=true`、`restored=true`、`missing_projection_checked=true`，observer 恢复为原类且 cleanup errors 为空。

已实际打开这三个阶段的六张 shown/hidden 原图：紫色目标格在 occupied 时消失，在 restored 时返回；各阶段 hidden 参照均不含投影主体。此处没有把 v8 的其他编辑器/完整投影原图计入已读图范围。独立只读恢复报告 `transform-runtime-v8-restored-status.json` 确认 projection inactive、无 preparing entity/busy/transition、entity 为 None、factory 恢复原生类，所有 QA/visual/missing 标记均已清除。随后该实例释放给下一位独占测试者，不再由本任务访问。

该受控检查没有在真实世界放置方块，不能替代真实世界占用扫描与 T04/T05/T08 的单半／双半组合验收。v3c/v4/v5/v6 原始报告保持不变，已关闭的用户问题数仍为 0。

## 连接诊断的坡轨例外

`check_blueprint_neighbor_context.py` 的旧诊断要求所有轨道都完整复制邻域，并禁止独立 overlay。当前四类 `rail_direction=2..5` 坡轨已采用独立主体，因此旧 oracle 错把当前合法提交判为缺格；19 个产品用例的闭包、擦除、保留其他主体及撤销/重做本身仍通过。

工具现在用独立的四类轨道名和方向字面量核对该窄路由：坡轨目标必须恰在自己的 overlay 提交正确主体；邻域不得重复坡轨前景，但仍保留 secondary layer；平轨和弯轨保持 context 检查。逐层同槽重复、冲突材质、缺主体、错误主体、重复 context 和缺 secondary 的负例均拒绝。17 个连接矩阵测试通过，不增加产品外观关闭数。

## 2026-10-21 冷源补验增量

正式 `83a551cf` 独立冻结包补做 T08 异步旋转、默认主材质完整投影和四种受控 missing 门像素，以及 T04 镜像内联、T08 旋转分页的真实 ConfigClient 保存载回。三份报告及嵌套存储恢复均通过，独立恢复和 source 字节不变检查通过；14 张原图已读。门的缺失阶段不再留下底木条，保存载回保留完整 typed 语义。详见[配置边界记录](verification/CONFIG_WIRE_R25.md)、[门所有权记录](verification/DOOR_CONTEXT_R25.md)及[冷源索引](evidence/transform-cold-r25-v1/evidence-index.json)。

此增量仅提升明确覆盖的自动验证状态，不回写旧 v3c—v8 记录。T05、本轮未覆盖的组合、真实世界占用扫描、跨客户端重启持久性及玩家人工验收仍待完成；新增人工关闭 0。实例普通关闭后游戏异常退出 `0xC0000409`，已确认身份消失并 finalize，未取得正常退出资格。
