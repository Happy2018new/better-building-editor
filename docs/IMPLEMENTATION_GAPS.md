# 功能完整性审计与待实现清单

审计及开发记录复核日期：2026-10-09。主线源码基线：`7bd54956d35cc72487220225d8aa17d3e22a56bb`；首轮审计提交：`5827d86`。本清单覆盖当前建筑编辑、世界测绘、建筑库、分享、三维预览、投影、进度检查及世界写入链路，并单独标注未合并开发分支中的工作。依据是现有源码、离线复现、回归测试和历史实机报告。本次仅整理文档，没有实现以下功能，也没有重新进行游戏实机验收。

当前跟踪 **15 项功能缺口／兼容性及未交付开发工作（F01–F15）**，另有 **9 项待验收工作（V01–V09）** 和 **7 项尚未提供、需要产品范围决定的扩展能力（X01–X07）**。F14 是 `dev` 分支的未交付目标，不表示主线已经承诺或具备 RenderDragon 支持。这是截至该基线能核实的清单，不是对未知引擎行为、全部方块或全部设备无遗漏的保证。历史报告中的失败不会自动当作当前版本仍然失败，已有明确修复的项目也不重复列为未实现。

第二轮复核新增 F13–F15、V09，纠正 V01 的安卓真机证据，补充 F02、F08、F11、F12、V06、V07。逐文档覆盖范围、修复去向和分支来源见 [开发记录复核](DEVELOPMENT_RECORDS_REVIEW.md)。

优先级：P0 为数据完整性或错误写入／变换问题；P1 为现有建筑工作流的兼容性缺口；P2 为操作体验或显示完善。编号用于后续追踪，不代表每项必须单独提交。

## 一、已确认的缺口及未交付开发工作

| 编号 | 优先级 | 待实现部分 | 当前状态 |
| --- | --- | --- | --- |
| F01 | P0 | 前景层与背景层完整支持 | 每格仅一个 `(identifier, aux)`，含水／含雪复合格无法完整保存、编辑、显示和传递。 |
| F02 | P0 | 方块状态随旋转、镜像正确变换 | 白名单拒绝多数方块；普通新名称误拒绝，部分方向状态又被错误放行。 |
| F03 | P0 | 方块实体 NBT 完整支持 | 没有位置关联的方块实体负载，捕获、历史、存档、分享、渲染和写入均未贯通。 |
| F04 | P1 | 门、床、高植物等多格方块的成组编辑 | 操作按独立格进行，没有配对放置／破坏和结构完整性检查。 |
| F05 | P1 | 特殊方块外观与不可渲染内容提示 | 依赖原生几何体；有限代理之外，没有完整兼容矩阵或逐类缺失报告。 |
| F06 | P1 | 非完整立方体的精确拾取 | 射线只命中整格，不检查楼梯、薄片等实际几何表面。 |
| F07 | P2 | 按住连续绘制／擦除 | 当前为逐次点击；拖动用于操作相机，没有连续笔划事务。 |
| F08 | P1 | 导入依赖检查及跨版本／自定义状态兼容 | 分享只做格式和结构校验，没有缺失模组报告、状态版本说明或替换流程。 |
| F09 | P1 | 可用于备料的材料清单 | 当前统计方块状态的占格数，没有换算为放置物品数量，也没有剩余材料明细。 |
| F10 | P1 | 双层／NBT 感知的建造进度与投影过滤 | 完成度只比较单层名称与 aux；占用过滤只判断该格是否非空气。 |
| F11 | P0 | 完整方块数据的世界写入与失败恢复 | 写入与日志仅保存单层值；存在新建方块实体阻止自身回滚却未计入恢复失败的路径。 |
| F12 | P2 | 透明面重叠与排序兼容 | 没有通用透明面排序；历史上明确接受性能取舍，需保留兼容边界，不预设必须采用昂贵排序。 |
| F13 | P1 | 透明建筑投影与后期星点正确合成 | 主线透明投影深度仍挡住后方星点；`uncomplete` 的候选方案未通过实机验收。 |
| F14 | P1 | RenderDragon 普通附加包接入 | 仅 `dev` 实验完成离线转换；可分发附加包的运行时绑定与视觉一致性未完成，尚未合入主线。 |
| F15 | P2 | 失败／取消存档后的未引用分页清理 | 已写页没有随失败事务回收；同一编号后续保存较小内容仍可能留下尾页。 |

### F01：前景层／背景层

**依据：** [model.py](../behavior_pack/modern_projection/projection/model.py#L43) 的 `block()` 只接受长度为 2 的方块值；[storage.py](../behavior_pack/modern_projection/projection/storage.py#L139) 的 `BlockStore` 每格只有一个材质索引。[Document.palette_data](../behavior_pack/modern_projection/projection/model.py#L159) 和 [SurfacePalette.palette_data](../behavior_pack/modern_projection/projection/large_preview.py#L37) 都把 `extra`、`actor` 设为空字典。[WorldAdapter.read](../behavior_pack/modern_projection/server_system.py#L69) 只保留名称和 aux。

待完成：建立含两层方块身份及状态的格数据；定义放置、破坏、吸管、替换、蒙版、选择空气、同步空气分别作用于哪一层；让所有批量工具、内部剪贴板、复制粘贴、历史快照及计数使用同一语义。预览、投影及其缓存必须对背景层变化失效，不能只更新前景层。

世界导入、本地小配置 v1／分块 v2／分页索引 v3、网络流、MP2／MPS2 分享需要一起升级并兼容旧数据。旧配置缺失背景层时按空气迁移；不能在旧版本无法理解新字段时悄悄丢弃它们。具体含雪组合应在目标游戏版本中确认两层的实际顺序，不能把所有“雪”都硬编码成同一种背景数据。

**验收：** 含水台阶、含水植物、含雪组合、独立水／雪、普通单层方块，在编辑、撤销重做、重开、分享往返、两套显示、写入后读回中保持两层一致；单独破坏其中一层的结果明确。雪原树叶代理已修复的问题与复合格的双层存储不是同一项。

### F02：旋转／镜像的状态变换

**依据：** [Editor._transform](../behavior_pack/modern_projection/projection/model.py#L389) 与 [EditJob._transform](../behavior_pack/modern_projection/projection/jobs.py#L201) 各有一份旧名称白名单，坐标改变后仍直接复制原方块值。小文档和分帧大文档使用同一规则；首轮离线复现及第二轮白名单核对如下：

| 输入 | 水平旋转 90° 的实际结果 | 缺口 |
| --- | --- | --- |
| `minecraft:oak_stairs:0` | 明确拒绝 | 缺少方向状态变换。 |
| `minecraft:white_wool:0`、`minecraft:oak_planks:0` | 明确拒绝 | 无方向普通建材的新名称也被误拒绝。 |
| `minecraft:ice:0`、`minecraft:packed_ice:0`、`minecraft:blue_ice:0`、`minecraft:frosted_ice:0` | 白名单判断拒绝 | 四种冰的短名称均不在名单内；没有记录表明它们因方向状态而被排除。 |
| `minecraft:quartz_block:1` | 操作成功，但 `pillar_axis` 从 `x` 保持为 `x` | 应随水平旋转改变轴向，却静默保留旧轴向。 |
| `custom:stone:0` | 操作成功 | 只比较命名空间后的短名称，未知自定义方块可绕过限制。 |

上述冒号末尾数字表示 aux；石英状态由当前 [block_registry.states](../behavior_pack/modern_projection/projection/block_registry.py#L38) 核实，不沿用旧版本“石英变种编号”的假定。

**开发记录补充：** 两处白名单均为以下 16 个短名称：`stone`、`stonebrick`、`planks`、`quartz_block`、`concrete`、`wool`、`glass`、`stained_glass`、`leaves`、`grass`、`sea_lantern`、`brick_block`、`sandstone`、`air`、`dirt`、`cobblestone`；另对 `minecraft:quartz_block` 的 aux > 1 拒绝。[初始核心提交 `0fc53ec`](https://github.com/Happy2018new/better-building-editor/commit/0fc53ec49b97064eff2eedf6edaa7d783b249244) 已有这份名单，[大范围提交 `5d3bfe4`](https://github.com/Happy2018new/better-building-editor/commit/5d3bfe4e24c21242b7732d5572fb530c213456de) 将其复制到分帧路径。[开发记录](DEVELOPMENT.md) 明确记载暂时拒绝方向方块是为了避免损坏朝向；“为何恰好选这 16 项／为什么没有冰”没有找到明确说明。初始材料面板的 14 个不同方块名恰好等于名单去掉 `dirt`、`cobblestone`，所以“按早期面板收窄支持范围”只能作为推断。后来的 `0463966` 已引入权威状态表，但没有同步替换这两处判断。

待完成：统一状态变换服务，覆盖水平 90°／180°／270° 旋转和 X／Y／Z 镜像；按实际状态处理朝向、轴向、上下半部、门铰链、轨道形状等，并结合 F04 处理配对关系。以完整方块标识和能力判断替换短名称白名单；未知状态明确说明支持边界。双层状态及 NBT 中涉及方向／位置的字段也要遵循转换规则，不能只旋转格坐标。

**验收：** 非对称建筑转四次恢复、同轴镜像两次恢复；每一步的具体朝向也正确；小／大文档、跨 16³ 边界和撤销重做一致。四次恢复测试单独不足以发现“每次完全不改朝向”。

### F03：方块实体 NBT

**依据：** `Document` 没有方块实体负载；[世界捕获](../behavior_pack/modern_projection/server_system.py#L357) 仅写入 `doc.blocks[pos]`；[transfer.py](../behavior_pack/modern_projection/projection/transfer.py#L8)、[archive.py](../behavior_pack/modern_projection/projection/archive.py#L26) 与 [sharing_codec.py](../behavior_pack/modern_projection/projection/sharing_codec.py#L40) 没有相应记录。模型调色板 `actor` 恒空。`GetBlockEntityData` 目前只在 [protected()](../behavior_pack/modern_projection/server_system.py#L97) 中用于阻止覆盖已有方块实体。

待完成：按坐标保存带类型的方块实体数据，支持捕获、移动、复制、删除、撤销重做、持久化、分享及服务端传输；容器物品、告示牌文字、物品展示框内容等必须保真，位置和配对引用在平移／旋转后要正确更新。为潜影盒等方块补齐渲染所需数据／外观通道，分别验收编辑器预览和世界投影。NBT 数据保存成功不等于原生合并模型能正确显示其外观。

写回须定义可恢复字段、可写类型及必要的服务器限制；移除方块或改成别的材质时清除旧负载。扩展编解码时保留类型、大小和层级限制，不能把所有 NBT 值转成无类型普通数字或不加限制地接收。

**验收：** 同材质但不同内容的两个容器保持独立；箱子／潜影盒库存、告示牌文字等在完整往返中一致；副本编辑不修改原本的负载；NBT 单独变化也更新历史、脏块及模型缓存。支持范围需逐类说明，不能只用一种箱子证明全部方块实体可用。

### F04：多格方块与关联状态

**依据：** [model.py](../behavior_pack/modern_projection/projection/model.py) 的 `paint_at`、`_edit`、`_copy` 与 [jobs.py](../behavior_pack/modern_projection/projection/jobs.py) 按格复制／修改；没有门上下半部、床头床尾、高植物等关联模型。本次离线构造完整高草，擦除下半格后，上半格仍留在草稿中。[植物代理](../behavior_pack/modern_projection/projection/geometry_palette.py#L17) 明确独立渲染上下半部，这只是显示支持。

待完成：提供配对放置与破坏、部分选择／复制时的完整性检查、旋转镜像后的关联重建，以及跨边界、锁层、蒙版冲突的原子处理。是否保留允许编辑“半个方块”的高级模式，应明确区分。

**验收：** 门、床、高草跨选区、分块和图层时不意外留下孤立部分；不能配对时给出具体原因；世界写入顺序及读回同时验证。栅栏、墙、红石等邻接外观／状态另纳入 F05、F11 的兼容用例，不能假定单格模型一定能还原所有邻接关系。

### F05：特殊外观与渲染缺失报告

**依据：** [ClientBridge.geometry](../behavior_pack/modern_projection/projection/bridge.py#L293) 调用 `CombineBlockPaletteToGeometry(..., 0)`，允许原生跳过不支持的方块；成功拿到模型名不等于每种材质都已显示。[geometry_palette.py](../behavior_pack/modern_projection/projection/geometry_palette.py) 仅为指定树叶及草／蕨提供代理。[现有使用边界](MODERN_PROJECTION.md) 已记录液体、火、传送门及部分自定义外观限制。

待完成：建立按游戏／SDK 版本记录的方块外观兼容表，对缺失或退化的内容给出可定位的提示；对可实现类别提供渲染适配。覆盖液体、火、特殊模型、邻接模型、带自定义外观的方块实体；不能把所有类别都归结为 NBT，也不能认为补上 `actor` 就全部解决。

**验收：** 原生支持、代理支持、默认姿态、无法显示四种情况明确；稀疏及混合建筑中缺失的少数方块也能被发现。屏障、末地传送门等限制以目标版本的官方资料及实机结果为准，不为不可见方块虚构正常外观。

### F06：实际几何表面拾取

**依据：** [camera.raycast](../behavior_pack/modern_projection/projection/camera.py#L222) 以 DDA 遍历格子，遇到存在于 `document.blocks` 的格子即返回，不检查亚方块包围盒或网格面。

待完成：台阶、楼梯、栅栏、薄片等实际形状的命中／穿透，以及与渲染一致的相邻面放置；F01 后还要定义同格两层的选取方式。隐藏／不可显示方块的替代选取入口也应明确。

**验收：** 点击楼梯空缺、台阶上方空白和薄片两侧时命中符合画面；完整、切面、单层、高倍缩放及触屏保持一致。

### F07：连续笔划

**依据：** [scene.py](../behavior_pack/modern_projection/projection/scene.py#L438) 的按下／移动／抬起区分相机拖动和单次编辑，没有沿拖动路径反复绘制的逻辑；使用说明明确未提供连续涂抹。

待完成：持续放置、涂装、擦除，笔划中补齐跨过的格子、去重，并以一次笔划为撤销单位；明确绘制与旋转、平移、双指缩放之间的操作规则。

**验收：** 快速移动不漏格，移出画布和取消能正确结束，不穿透弹窗或工具栏，锁层和蒙版仍生效。

### F08：依赖与版本兼容

**依据：** [Sharing.paste](../behavior_pack/modern_projection/projection/sharing.py#L193) 解码完成后直接显示“校验通过”；[validate_materials](../behavior_pack/modern_projection/projection/sharing_codec.py#L27) 仅验证标识和数据形状。本次 `custom:missing` 可以完整分享往返，无安装依赖检查。[block_registry.canonical](../behavior_pack/modern_projection/projection/block_registry.py#L24) 拒绝表外原版值，但允许自定义名称；`states()` 对表外自定义方块返回 `None`。

待完成：导入预检分别报告缺失方块／模组、无效状态、渲染不支持和可保留但无法写入的内容；提供保留数据、替换或取消流程。原版注册表需有版本来源与升级策略，自定义方块需要可扩展状态描述。分享协议当前有 MP2 格式标识，但不携带方块状态表版本／依赖清单；格式版本不能代替游戏数据兼容性。

[权威方块表接入记录](DEVELOPMENT.md) 还明确指出：旧数据与现代状态表可能使用相同名称和 aux 表达不同状态，无法仅凭已有二元组区分。迁移需记录来源或让用户确认歧义；不能把常用别名转换已经实现写成所有历史数据都能自动无损迁移。

**验收：** 原版新旧名称、旧配置迁移、缺失依赖、同名不同状态版本和重新安装依赖均有明确结果，不因预览失败破坏原配置。已有原版 name／aux／states 映射和常用旧别名转换已经实现，不应列为“全部状态都未支持”。

### F09：材料清单语义

**依据：** [Document.materials](../behavior_pack/modern_projection/projection/model.py#L147) 返回按 `(identifier, aux)` 计数的全部非空气格；[ProjectionSettings](../behavior_pack/modern_projection/projection/panels.py#L610) 直接显示该列表。本次两种朝向的橡木楼梯被列成两行，各 1 格。

待完成：保留“方块状态统计”的同时，增加可用于备料的物品清单；合并只影响朝向的状态，换算双层台阶、门／床等多格或多物品结构，定义水／雪等背景层的材料计算方式，并按建造检查提供剩余材料。不能直接把方块格数当作所有放置物品的消耗数。

**验收：** 不同方向的同种楼梯合并，门／床不按每个占格重复计物品，双台阶等按真实放置需求换算；“全部材料”和“还缺材料”数值可对照世界状态解释。

### F10：建造完成度与双层过滤

**依据：** [read_job](../behavior_pack/modern_projection/server_system.py#L357) 比较 `adapter.read()` 与 `canonical(doc.get(pos))`；[occupancy_scan.py](../behavior_pack/modern_projection/projection/occupancy_scan.py#L35) 只消费原生调色板 `common`，编码为未知／空气／占用三种状态。

待完成：完成度比较完整两层、状态及选择纳入检查的方块实体字段，区分缺前景、缺背景、状态错误、NBT 不符。含水方块只放了实体层时不能算完整；同材质不同 NBT 也不能无条件算正确。投影需要能展示同格尚未完成的层，或明确提供完整性检查模式。

**验收：** 已放错材质、只补一层、朝向错误、NBT 不符均可定位；卸载区块保持未知。现有“任意非空气就隐藏”的功能是已实现的防重影模式，不把它说成失效，也不默认改成精确匹配模式。自动占用消隐已实现，服务端完成度仍由用户主动检查。

### F11：世界写入与失败恢复

**依据：** [WorldAdapter.write／protected](../behavior_pack/modern_projection/server_system.py#L75) 写名称和状态并保护已有方块实体；[WorldJob](../behavior_pack/modern_projection/projection/world.py#L18) 与 [Journal](../behavior_pack/modern_projection/projection/journal.py#L7) 仅记录当前位置、修改前值和修改后值。回滚遇到已变为受保护方块实体的位置会跳过；完成后 [服务端 tick](../behavior_pack/modern_projection/server_system.py#L406) 移除任务，没有恢复任务入口。

本次用离线适配器模拟当前 `protected()` 规则：在空气处先放箱子，下一格写入失败；回滚因箱子现在具有方块实体而跳过它，箱子仍存在，`recovery` 数量却为 0，只显示“已尝试恢复本次修改”。这是代码路径复现，尚未以真实箱子进行游戏内复测。原有“保护用户既存容器”应保留，需要识别本次事务新建的方块实体。

待完成：修正上述漏恢复／漏计数；用完整两层、状态和 NBT 建立快照、写入顺序、读回校验及恢复。多格方块、液体／红石／重力等世界更新引起的连带变化需要明确处理范围；未完全恢复的数据应有可检查的记录和后续处理办法。当前逐次读取新值的改进不能证明任意邻居副作用都能还原。

**崩溃边界：** [大范围开发记录](LARGE_REGIONS.md) 明确说明日志仍在内存；当前 `Journal` 也没有持久化或启动恢复入口。因此失败／取消时的在线回滚不等于进程崩溃后可恢复。跨重启的未完成世界事务恢复仍未提供，需要设计日志持久化、提交标记、重启后的冲突检查和清理策略，并明确产品是否承诺这一范围。它与 X04 的客户端草稿恢复、已移除的成功写入撤销是三件不同的事。

**验收：** 预检拒绝不写入；中途失败、取消、权限变化、离开、卸载区块能准确报告并处理剩余内容；保留其他玩家后续修改。完成后的“撤销世界写入”已经有意移除，本项要求的是失败事务恢复，不是恢复那个按钮。

### F12：透明面排序

**依据：** [README 的当前限制](../README.md)、[阶段 69 的共享深度实现](ORBIT_REGRESSION_69.md)、[scene.py](../behavior_pack/modern_projection/projection/scene.py) 的固定模型层级及 [terrain.material](../resource_pack/materials/terrain.material)。当前没有通用的逐透明面排序机制；世界投影合并成一个模型减少了分块接缝，但不等于所有透明面顺序都正确。

**历史决策：** [开发记录阶段 30](DEVELOPMENT.md) 和 [大范围说明](LARGE_REGIONS.md) 记载用户明确接受跨模型透明遮挡为性能让步。F12 保留兼容性测试与显示边界，不将“实现通用逐三角形排序”直接作为既定需求。阶段 69 的共享深度解决了另一类旋转错位，不能据此关闭 F12；F13 的投影遮住星点也需独立跟踪。

待完成：针对玻璃、冰、液体、重叠半透明投影建立实际兼容方案和可接受的显示边界，兼顾内外观察与双层叠加。是否采用特定排序技术须依据 SDK 能力和性能测试决定。

**验收：** 多方向、建筑内部、跨分块、多个透明层和不透明背景组合有连续画面证据。已经修复的棋盘错位、共享深度遮挡与这一透明混合问题分别验收，不将旧截图当作当前新复现。

### F13：透明投影与后期星点合成

**依据：** 主线 [星点动态参数记录](PARTICLE_TRANSPORT.md) 明确保留“透明投影遮挡后期星点”。当前投影在原生星点之前写入深度，使透明建筑后方的星点被当作处于实墙后方。直接关闭深度写入又会让后绘制的天空覆盖投影；早期发光与后期 alpha 补偿实验在网易 3.9.0.401155 OpenGL 上触发 `Unknown blend target: 7`（`DestAlpha`），已经撤回。

`uncomplete` 的 [合成实验 `ecd9da1`](https://github.com/Happy2018new/better-building-editor/blob/ecd9da1a4dad99a24eb825d40e080a1b8da92c7a/docs/PROJECTION_COMPOSITING.md) 也未通过：远深度保护层挡住天空，却让后绘制的远岛和水面覆盖前方石英投影。GPU 工具的 52 项断言仅验证给定绘制顺序，最终游戏场景已否决该方案；不能将它算成主线已修复，也不能直接合并其两个实体方案。

待完成：在目标后端找到可保留投影颜色、透明透视星点和真实墙体遮挡的合成路径，同时保留连续透明度、草叶镂空、UI 显示及占用过滤。现有资料没有确认 BlockGeometry 的队列／离屏目标控制接口，不能先假定可用。

**验收：** 普通世界开启美丽的天空，天空／远岛／水面均不覆盖前方投影；“相机→投影→星点→墙”可见星点，“相机→投影→墙→星点”由墙遮挡。分别检查投影表面和星点，不能以投影消失或粒子穿墙换取通过。材质修改后冷启动验收。

### F14：RenderDragon 接入（未合并开发分支）

**依据：** `dev` 的 [迁移记录 `bc376f1`](https://github.com/Happy2018new/better-building-editor/blob/bc376f15c2b8b52a0191b3efb9900e6055d073e6/docs/RENDERDRAGON_MIGRATION.md)、[试点记录](https://github.com/Happy2018new/better-building-editor/blob/bc376f15c2b8b52a0191b3efb9900e6055d073e6/docs/RENDERDRAGON_PILOT.md) 与 [工具说明](https://github.com/Happy2018new/better-building-editor/blob/bc376f15c2b8b52a0191b3efb9900e6055d073e6/tools/renderdragon/README.md)。13 个 shader 源文件的离线转换已覆盖 35 个继承材质、175 个变体、552 对顶点／片元组合，但记录仍标注 `runtime_verified=false`、`visual_parity_verified=false`。这些文件及接入实验不在主线。

原生安装资源替换曾在 RenderDragon D3D12 环境显示测试颜色／星空，然而同一份字节码放入普通附加包 `renderer/materials` 未被加载，尚未确认可分发附加包的注册／绑定入口。离线编译成功不等于普通玩家安装模组即可使用。

待完成：先确认目标客户端支持的正式加载方式，再贯通顶点布局、矩阵／骨骼、时间与额外参数、PBR 输出及深度／混合状态；逐项验证编辑器模型、世界投影、群系染色、范围框与法杖／测绘特效。是否继续这一开发分支应单独决定，不能只把它归为 V01 的“再测手机”。

**验收：** 用普通可分发附加包冷启动，无需修改游戏安装资源；实际切换目标渲染后端并确认生效。核对材质绑定、动态参数、镂空与透明度、真实遮挡和画面一致性，再谈合入主线。2026-09-27 的离线矩阵不是当前主线所有新着色器的覆盖证明。

### F15：未引用分页回收

**依据：** [分享开发记录](SHARING_ASSESSMENT.md) 已承认取消后可能留下未引用分页。[archive.save_steps](../behavior_pack/modern_projection/projection/archive.py#L26) 先写页再返回索引；[Sharing.accept](../behavior_pack/modern_projection/projection/sharing.py#L214) 最后提交库索引，`close()`／`fail()` 只关闭作业或释放 I/O，没有清理已写页。[ClientBridge.clear_archive](../behavior_pack/modern_projection/projection/bridge.py#L231) 用于已知页数的删除清空，失败存档没有相应的页数清单。

第二轮用现有测试的内存存储替身复现：索引提交失败时库仍为空、I/O 已释放，但留下 1 页；在写完 2 页后关闭保存生成器，页仍存在；同一编号改存 1 页的小建筑后，第 2 页仍未被引用。取消用例验证的是底层生成器关闭路径，没有把它称为真实 UI 或系统磁盘复测。旧索引和草稿受保护的行为已经实现；问题是存储清理不完整。

待完成：记录未提交页及事务状态，在取消、写页失败、索引提交失败、后续较小保存和重启时安全回收；不得让迟到清理删除新事务复用编号的有效页。区分可清空内容与 SDK 无删除配置接口所留下的小空文件。

**验收：** 注入各写页／索引失败点，取消并重试更小或更大的建筑，检查有效索引和内容完整、无未引用大页积累；清理重试和跨重启行为可解释。普通大建筑保存与世界选区导入复用同一底层写页器，也应覆盖。

## 二、三项底层能力必须一起贯通的链路

以下是 F01–F03 的实施检查点，不再重复计为独立功能。

| 环节 | 要同步完成的工作 | 主要模块 |
| --- | --- | --- |
| 世界捕获 | 两层、状态、方块实体、坐标关系；无法读取时报告损失 | `server_system.py`、`bridge.py` |
| 内存数据 | 空气语义、稀疏负载、复制隔离、材质身份与位置负载分离 | `model.py`、`storage.py` |
| 所有编辑操作 | 单格／批量、选择／蒙版／锁层、剪贴板、变换及历史 | `model.py`、`jobs.py`、`pasting.py`、`session.py` |
| 本地库／分享／网络 | 新格式、旧数据迁移、分包和容量校验、无损往返 | `codec.py`、`archive.py`、`transfer.py`、`sharing_codec.py` |
| 编辑器 3D | 分块提取、背景和实体外观、跨边界邻接、完整缓存键 | `large_preview.py`、`tiles.py`、`geometry_palette.py`、`bridge.py`、`scene.py` |
| 世界投影 | 小／大投影、双缓冲、占用缓存、单层变动恢复 | `bridge.py`、`world_projection.py`、`occupancy.py`、`occupancy_initial.py`、`occupancy_scan.py` |
| 建造辅助 | 材料换算、完整数据比较、缺失层与错误内容定位 | `model.py`、`panels.py`、`server_system.py` |
| 世界写入 | 权限、完整快照、顺序、校验、失败回滚和残留记录 | `server_system.py`、`world.py`、`journal.py` |

推荐顺序：先确定完整格数据与版本迁移，再让捕获／持久化／分享无损往返；随后贯通编辑事务、状态变换与两套显示；最后验收完整进度统计和世界写入。F02 的错误放行、普通名称误拒绝及 F11 的回滚漏计可以提前修复；F06–F07 也可独立推进。

## 三、待验收与历史未关闭项

| 编号 | 待完成工作 | 证据与验收边界 |
| --- | --- | --- |
| V01 | 扩展 Android／iOS 真机及完整流程覆盖 | **已有安卓真机专项证据：** [9 月 26 日记录](MOBILE_DEBUGGING.md) 验证 2400×1080 设备的安全区对称、系统 MotionEvent 双指张合与释放，并有用户真实手指缩放确认，修复已进入 `1b78abb`。仍待其他机型、横竖屏、iOS、系统返回、输入法、剪贴板和最新 GPU 特效验证，以及安装修复版本后的完整回归；不能再写成“全部只有模拟证据”。 |
| V02 | 真实双客户端、命令方块变化、维度切换及长时间多人压力 | [投影占用报告](PROJECTION_OCCUPANCY.md) 明确未做完整端到端验证。身份隔离和模拟世界变化测试不能代替真实联机。 |
| V03 | 最大范围世界写入、取消／回滚，复杂红石、液体及多格方块，跨游戏版本兼容 | [使用边界](MODERN_PROJECTION.md) 的真实写入验证是小范围；最大测绘读取通过不等于最大写入通过。依赖 F01–F04、F11 后应重建保真用例。 |
| V04 | 超长混排输入滚到末尾时的文字／光标裁剪 | [输入报告末尾](INPUT_FONT_BATCHING.md) 仍保留 `verify_input_caret.py --long --require-visible` 失败记录；常规短文本焦点对比度已修复。需当前版本复现后修复或明确限制，不宣称本次实机复现。 |
| V05 | 最大模型 60–80 ms 导航短按压力回归 | [阶段 32](EDITOR_PERFORMANCE_32.md) 的 `probe_depth_buttons.py` 曾不能稳定通过；[阶段 69](ORBIT_REGRESSION_69.md) 已移除原主要层级更新路径。需重新跑原压力用例，不能直接判定旧缺陷仍在。 |
| V06 | UI 冷启动／首次参数、原生模型就绪、连续替换、内存与低性能设备表现 | [开发记录阶段 43–46](DEVELOPMENT.md)、[性能报告](PERFORMANCE_67.md) 与 [公开 SDK 复核](WHITELIST_68.md) 仍有初始化及连续编辑提交峰值，后续架构变化后需重测，不能沿用旧数字当现值。[PreviewBuffer](../behavior_pack/modern_projection/projection/preview.py) 与 [投影报告](PROJECTION_OCCUPANCY.md) 使用等待窗口，并非 GPU 完成回调；原生合并、剪贴板及末尾拼接仍有同步部分。覆盖 F12–F13、长期编辑／撤销和双缓冲资源占用；Python 软预算不是原生调用硬上限。 |
| V07 | 最新 PC／F11 HUD、P 键移除及真实材质面板完整路径 | [交接文档](CONVERSATION_HANDOFF.md) 保留 `FOCUS_DENIED` 中断记录，需运行 `verify_entry.py`、`verify_world_tools.py`。[阶段 56](MATERIAL_AUX_AND_OUTLINES_56.md) 的连续选材只在独立卡片验证；`212985e` 后续已修复并实测滚动条，但没有找到明确覆盖“正式工作台滚到底部→连续选材”的完整记录，应补测而非断言滚动条仍坏。最新星点录像通过业务入口及 `SetFootPos` 驱动，也不能替代真实输入。 |
| V08 | 发布前游戏版本／方块表来源核验与网易机审闭环 | 本次外部原始方块表比对测试因文件缺失跳过，仓库内 1,321 个名称／15,839 条状态自检通过；[既有机审记录](ASTRAL_STAFFS_AND_MOBILE.md) 说明本地修正后尚未重提。需恢复可复现的表来源、核对目标版本并获得实际审核结果。 |
| V09 | 第三人称下的触屏世界测绘点选 | [阶段 72](SURVEY_STARDUST_72.md) 与官方 `GetChosen` 资料明确只保证第一人称准确；[当前客户端](../behavior_pack/modern_projection/client_system.py#L128) 仍通过该接口缓存屏幕命中，没有第三人称专用适配。需验证不同视角实际触点与两角点一致，必要时提供正确拾取或明确限制。特效的第三人称移动录像不能证明第三人称选点准确。 |

## 四、当前未提供、需先确定产品范围的能力

这些能力可加入后续路线图，但当前有明确范围限制，不能混同 F01–F03 的数据保真缺口，也不表示本次已经授权实现。

| 编号 | 当前缺少的能力 | 现状／依据 |
| --- | --- | --- |
| X01 | 普通实体的测绘、编辑、保存和投影 | 生物、盔甲架、画等普通实体需要单独的数据集合；`Document` 与捕获协议没有这类集合。完整建筑复制若要含这些装饰，需另建实体生命周期和变换支持。基岩版物品展示框属于方块／方块实体，归入 F03。 |
| X02 | 逐位置生物群系捕获、保存与还原 | [biomes.py](../behavior_pack/modern_projection/projection/biomes.py) 和 `Document.biome` 提供整栋统一染色预设；捕获创建文档采用默认值，没有读取选区内群系分布，也不写世界群系。统一预设本身已经实现。 |
| X03 | 标准结构文件导入导出和直接文件分享 | 当前产品入口是 MP2／MPS2 剪贴板格式，没有 `.mcstructure` 等结构格式转换和文件入口；MP2 中存在压缩数据不等于支持结构 NBT 文件。 |
| X04 | 草稿自动保存、崩溃恢复及跨重启历史 | [Session](../behavior_pack/modern_projection/projection/session.py) 的草稿、待保存测绘结果和历史在内存；本地库为用户主动保存。需要决定恢复保存的频率、容量和清理策略。 |
| X05 | 账号隔离、跨设备同步、服务器共享库／协作编辑 | [ClientBridge](../behavior_pack/modern_projection/projection/bridge.py#L148) 使用固定的本机全局配置键；当前明确是本机库、本机投影，没有账号命名空间及同步／协作协议。这些是不同产品选择，不能通过改一个存储键全部实现。 |
| X06 | 生存自动补方块和材料消耗 | 投影只是辅助显示，世界写入要求创造及权限；没有背包扣材、分步自动建造与返还事务。 |
| X07 | 语义化方块属性／内容编辑界面 | [AuxEditor](../behavior_pack/modern_projection/projection/material_browser.py#L18) 已支持合法 aux 输入／步进，但没有“朝向、上下半部、开合”等字段表单；F03 数据保真之外的容器物品、告示牌内容编辑器也需单独设计。 |

64×128×64 尺寸、32 份本地配置、50 步及约 64 MiB 历史预算，以及“成功写入世界后不提供撤销”是当前明确边界，不列为遗漏实现。是否提高容量或恢复世界撤销属于另外的产品决定。投影仅本人可见同样是既有约定。

## 五、核验记录

### 首轮源码审计（提交 `5827d86`）

- 已扫描行为包架构及 `model.py` 引用链，追踪数据层、编辑／变换、两套渲染、占用扫描、世界读写、存档、分享和相关 UI；检索历史限制并与当前源码交叉核对。
- 用 `minecraft_docs` 检索 `GetBlockNew`、`GetBlockStates`、`SerializeBlockPalette`、`CombineBlockPaletteToGeometry`、含水方块及展示框资料；`GetFrameItem` 位于方块实体组件，与仓库中的 `minecraft:frame` 方块记录相符。工具当前库为 ModSDK 3.10 Beta，历史实机多为 3.9；新接口能力不能直接当成旧客户端已可用。`GetBlockEntityData` 本次结果仅返回标题，`GetExtraBlock` 无结果，因此没有编造双层／NBT 新接口签名。
- 官方检索确认 `CombineBlockPaletteToGeometry` 的模式 0 会跳过不支持的方块；当前资料还注明自定义方块实体动画／运行时姿态限制。未来选用哪个数据／渲染接口须在目标版本继续验证。
- 离线复现 F02 的两类误判与石英轴向不变、F04 的高草孤立上半部、F08 的未知自定义 ID 无依赖检查往返、F09 的楼梯状态分行，以及 F11 的模拟新建箱子回滚漏计。均未写真实世界或用户建筑库。
- 按仓库入口执行 `python -X utf8 -m unittest discover -s tests -q`：**456 项，455 通过、1 跳过**，约 24 秒。跳过的是外部 `block_palette.json` 原始导出一致性检查。首次按模块名直接运行部分测试时，两个模块因 `tests` 未在导入搜索路径而装载失败；改用上述仓库 discovery 入口后完整通过，未把该次装载失败记为产品缺陷。
- 已有测试通过证明原有覆盖下的行为，不证明本清单中的未实现能力已具备。本次没有增加或修改生产代码与测试；新功能实施时应增加对应的行为回归，并做游戏实机验收。

以下历史事项已实现，不列为新增待办：合法原版 aux／状态映射和部分旧别名兼容、MP2／MPS2 分享及分段接收、触屏测绘 HUD、双指／返回路由与安全区代码、自动占用消隐及批量扫描、常规输入光标对比度、阶段 69 的共享深度、雪原树叶及草／蕨渲染代理。本清单保留它们的验证边界。

### 第二轮开发记录复核

- 检索审计前本地所有 Git 引用可达的 152 个提交（主线至 `5827d86` 为 121 个），核对当前 `docs/` 的 33 份其他文档、根说明及开发补充文档；识别 4 份仅存在于实验分支的记录，追踪旧命名空间文件的迁移。完整映射见 [开发记录复核](DEVELOPMENT_RECORDS_REVIEW.md)。未合并或已撤回实验不会被当成主线已交付功能。
- 重新检索官方 `GetChosen`，核实第一人称准确性限制；结合源码确认 F13、F15 及世界日志内存边界。F15 的新增复现仅使用内存替身，没有写入真实世界、系统剪贴板或用户建筑库。
- 补记已有安卓真机修复与后续滚动条修复，保留未关闭的长文本、导航短按及最新输入验收项；记录透明排序的既有性能决策。
- 本轮仅修改 Markdown，检查链接、编号、记录覆盖与 `git diff --check`；首轮 456 项测试结果保留为首轮证据，没有冒充本轮重跑，也没有新增实机验收。
