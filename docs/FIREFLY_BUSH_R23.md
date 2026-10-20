# R23 萤火虫灌木动态调查（2026-10-19）

**OB-01 仍开放；本轮关闭 0 项完整问题。** C v3 三文件候选已在独立冷副本中完成实测：真实编辑器 PaperDoll 和完整投影东南西北四向均可见灌木上的亮点随时间变化，对应隐藏对照均为 0 动态像素。原生 magma 动画哨兵也保留了变化。这支持贴图动画的窄范围集成，仍不代表独立飞虫、缺失投影或原版速度／亮度一致性已验收。

冷测项目为 `.runtime/projects/firefly-r23-c-v1`，owner 为 `firefly-r23-c-v1`，游戏 PID 30616／创建身份 `134368891915996568`。6 份报告全部完成、恢复成功、资源哈希不变，恢复读回相符、清理错误为空；没有写入世界方块或发射粒子。21:38 已交还实例。运行摘要及原始报告、逐帧回执、联系图和工具的哈希索引见 `docs/evidence/firefly-bush-r23/cold-runtime-v1.json`。下文保留离线候选和兼容修正的来源记录；早期“尚未运行”均指该阶段的历史状态。

## 已接入主资源的最小实现

本轮已通过 `tools/generate_firefly_bush_animation.py` 将三份冷测资源接入主资源。安装前逐份核对与上述冷副本完全相同：atlas SHA256 为 `1f4d510bd48c0fe6dad79b78517d65924c4f54d0f84779b84a41bb0034dcd881`，flipbook 为 `e543fdd20b4d2f4496edc8cef75895df6f6d2f75a6aadb76b3aacb82c3488808`，807 字节的 strip 为 `02724cb3a6218e044a58726fa5e953d6a407b86d91c0c13997694bfe8cb20bf0`。原资源备份及安装记录为 `.runtime/round-20261019/firefly-stable-integration-v1.json`。

原生四份输入共 30,951 字节，冻结在 `tools/data/firefly_bush_animation_nemc_3.10.0.420447/`，manifest 记录每份源路径、长度、SHA256、版本和原生帧速。只将原3.9居中模型的 carried 透明轮廓与3.10原生图片逐像素一致性作为几何关联，不借此升级整个3.9方块表的3.10资格。`generate_centered_plant_profiles.py` 继续生成原几何与雪覆盖边界，仅为该灌木绑定动态短名。

完整80条原版声明（含有意重复的 variant）保持原顺序，本地条目随后保留，项目声明最后追加。生成器重复执行不重复添加；本地同名冲突、重复声明、源哈希改变、几何透明轮廓来源不符和非严格 JSON 均会拒绝。7项新增语义测试和8项既有居中植物测试通过；统一 `check_version_bundle.py` 已加入该生成器的 `--check`。原始JSON及三份生成资源的换行按 `.gitattributes` 保留冷测字节，避免提交时转换导致来源指纹失效。

运行 `python -X utf8 tools/generate_firefly_bush_animation.py --check` 可只读复核，省略 `--check` 则重新生成三份资源。此接入提供已观察到的贴图亮点运动，OB-01 的缺失投影、独立飞虫、速度／亮度对照及含雪／切面回归继续开放。

## 冷测实际结果

每段请求连续采集 3.3 秒，接受的首帧到末帧均超过 3 秒，最大帧间隔均不超过 150 毫秒。ROI 在连续采集前固定，逐帧检查原始物理 PNG／WGC 回执；相机、玩家、模型／文档身份、原生提交及哨兵在每段前后保持不变。查看器重新校验原始证据，没有通过降低门槛接受采集。

| 样本／路线 | 可见帧数／实际跨度 | 固定目标内动态像素 | 隐藏对照动态像素 | 原始画面结论 |
| --- | --- | --- | --- | --- |
| C 产品完整投影北 | 31／3.2060 秒 | 207 | 0 | 静止灌木上少量亮点改变，支持贴图动画接入 |
| C 产品完整投影东 | 30／3.2424 秒 | 255 | 0 | 本体可见，亮点改变 |
| C 产品完整投影南 | 32／3.2666 秒 | 228 | 0 | 本体可见，亮点改变 |
| C 产品完整投影西 | 32／3.2424 秒 | 310 | 0 | 本体可见，亮点改变 |
| C 产品真实编辑器 | 96／3.2605 秒 | 882 | 0 | 原有 PaperDoll 内亮点改变；zoom 3.5 时下部被视口／按钮裁挡，不能记为完整外观通过 |
| 原生 raw_loaded 灌木北 | 31／3.1818 秒 | 0 | 0 | 原图只看到支撑石头，没有可见灌木；不能凭 0 运动认定原生动画冻结 |
| 原生 raw_loaded magma 北 | 32／3.2727 秒 | 11,626 | 0 | 原生岩浆块面上的纹理连续变化；只覆盖 magma，不推广到水／火 |

已逐一查看编辑器、产品四向和 magma 的真实联系图，以及北向产品／原生路线与编辑器的完整原图。完整画面中的动物等背景活动在目标 ROI 外；同目标的隐藏连续段均为 0。联系图按 0.15 秒就近选择真实帧，标签保留实际时间，没有补帧或插值。亮点时间变化集中在灌木的少量像素上；本轮没有把全屏差分当作动画证据。

精确报告及离线可逐帧查看的位置：

- `.runtime/round-20261019/firefly-c-full-v1.json`，查看器 `firefly-c-full-v1-review/index.html`：产品北向与原生北向两条路线。
- `.runtime/round-20261019/firefly-c-editor-v1.json`，查看器 `firefly-c-editor-v1-review/index.html`：真实编辑器。
- `.runtime/round-20261019/firefly-c-full-east-v1.json`、`firefly-c-full-south-v1.json`、`firefly-c-full-west-v1.json`：另外三向；各有同名 `-review/index.html`。
- `.runtime/round-20261019/magma-native-sentinel-v1.json`，查看器 `magma-native-sentinel-v1-review/index.html`：原生动画保留哨兵。

14 个连续段共 571 个有效原始帧，原始 PNG、逐帧原生回执及 wrapper 回执保留在上述 `.runtime` 目录，没有把大批截图直接纳入仓库。全部报告的 `animation_accepted` 仍为 false。当前支持的是“候选贴图动画在这些实际渲染路径中播放”，尚未与可见的原版世界灌木做相同场景、相位、速度和亮度对照；独立飞虫、缺失投影、其他编辑器姿态、旋转／镜像、切面、含雪、占用消隐与生命周期组合仍待完成。

## 需要分别验收的三部分

| 部分 | 已确认事实 | 当前状态 |
| --- | --- | --- |
| 灌木本体 | 原生 `textures/blocks/firefly_bush.png` 为 16×16；现有居中交叉模型有本体 | C 冷副本完整投影四向可见；编辑器下部裁挡，其他组合仍待验收 |
| 灌木上的闪烁亮点 | 原生独立 16×160 贴图，10 个不同帧，每帧 3 ticks | C 冷副本真实编辑器及完整投影四向已有亮点变化；缺失投影与原版一致性仍待验证 |
| 离开灌木的独立飞虫 | 原生 `minecraft:firefly_particle` 有独立运动、碰撞及渐变 | 不是上述 flipbook；目前尚未接入，也未获得原生方块发射调度的来源 |

当前用户明确要求萤火虫灌木动态。旧文档 `CENTERED_SNOW_PRODUCT_R14.md` 中的 “does not simulate ... firefly animation” 与 `NEMC310_RENDER_COMPATIBILITY_INVENTORY.md` 旧表中的“独立 firefly 粒子；后者不实现”不能作为本轮关闭或排除动态的依据。贴图动画和独立飞虫分开保留，不用旧粒子排除覆盖新要求。

## 已核实的原生路径

本机源版本为 `3.10.0.420447`，资源根目录：

`D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data/resource_packs/vanilla`

1. `blocks.json` 的 `firefly_bush` 使用 `textures: firefly_bush`，物品形式另用 `carried_textures: firefly_bush_carried`。
2. `textures/terrain_texture.json` 的 `firefly_bush.textures` 是两项数组：索引 0 为静态灌木，索引 1 为 `textures/blocks/firefly_bush_firefly`。
3. `textures/flipbook_textures.json` 的该条目明确为：

   ```json
   {
     "flipbook_texture": "textures/blocks/firefly_bush_firefly",
     "atlas_tile": "firefly_bush",
     "atlas_index": 1,
     "ticks_per_frame": 3
   }
   ```

4. 16×160 strip 实际拆出 10 个不同 16×16 帧；每帧有 2 或 3 个不透明亮点。文档按 20 ticks/秒定义，因此名义每帧 0.15 秒、完整一轮 1.5 秒。条目没有显式 `frames` 或 `blend_frames`，候选保留这一缺省，不自行改成逐帧硬切或改速。
5. 所有亮点像素均与静态灌木的不透明像素重叠。将本体与亮点直接放在同一平面的两个面上会有深度竞争风险；不能认为“叠一张面”就必然正确。
6. 调查起点的 `generate_centered_plant_profiles.py` 将 `firefly_bush` 放入 `CARRIED`，只接受非空的 16×16 静态图；`centered_firefly_bush` 最终指向 `textures/items/firefly_bush`。这解释了原先的静态来源；冷副本 C 已证明 Combine 和真实 PaperDoll 可以播放专用 atlas 贴图动画，维护生成器由主代理单独接入。

本体源 SHA256：`cdbe8e8d2ac7988655a4f2cfc4aa4595ca9a5719182c031aff59f836022b6f90`。

动态 strip SHA256：`717f53c55b6ad630a37e83a5f7729eaa8ca0f3557c9bdec6e2ee51f049840486`。

物品源 SHA256：`1844250d2441b77b777e2a923e12b95a8541ddbdc067d0cb8710062aca6ace7f`。

完整源文件哈希、逐帧像素及候选哈希位于 `.runtime/firefly-bush-r23-v1/manifest.json`；可跟踪摘要位于 `docs/evidence/firefly-bush-r23/offline-sources.json`。

## MCP 核对与可用字段

已通过 `minecraft_docs` 读取以下真实路径：

- `NeteaseGuide/mcguide/20-玩法开发/15-自定义游戏内容/2-自定义方块/5-自定义方块模型.md`：`description.textures` 指向 terrain atlas 名称；骨骼、cube、单面的 `texture: int` 指向该数组下标，并逐层继承。模型格式 `1.13.0`；`netease:render_layer` 应用于整个模型。文档的模型贴图长宽上限为 64。
- 同目录 `2-功能.md`：自定义方块可通过 `resource/textures/flipbook_textures.json` 获得动画纹理；动态纹理不适用自定义群系颜色。
- `BedrockWiki/blocks/flipbook-textures.md`：`atlas_index` 是 terrain atlas 条目内部 `textures` 数组下标；动画以 atlas 短名绑定；`ticks_per_frame` 按 20 ticks/秒解释。国际版 `minecraft:material_instances` 示例只用于理解 atlas 机制，没有把该组件当作网易模型格式使用。
- `ModAPI/接口/特效/微软粒子.md`：`CreateParticleSystem(None).Create(effect_name, offset, rotation)` 可创建微软粒子，0 表示失败；`Remove(id)` 按句柄销毁；`CreateBindEntityNew`、`BindModel` 有局部绑定路径。未绑定到实体的循环发射器只播放一次或一个周期。
- `GameAssets/resource_packs/vanilla/particles/firefly_particle.json` 与 `GameAssets/resource_packs/vanilla/textures/flipbook_textures.json`：与本机 3.10 对应字段交叉核对。
- API 检索 `CombineBlockPaletteToGeometry`：公开接口将调色板转为实体几何；自定义方块实体外观动画不支持，不等于所有 atlas 动画也不支持。屏障与两类末地表面列入不支持清单，萤火虫灌木未列入；未列入不能视作已通过。

**不要混淆两个索引。** 模型中 `texture: 1` 选择 `description.textures` 的第二个 atlas 名称；它不能据此选择 `firefly_bush` 内部的 `atlas_index: 1`。本轮未找到一个有文档来源的 NetEase 模型字段来直接指定后者，因此候选将动态图片绑定到独立、单项的 atlas 短名，不编造 atlas 索引选择字段。

## 三种最小候选与选择顺序

| 路径 | 准备情况 | 价值与限制 |
| --- | --- | --- |
| A：保留原生 `minecraft:firefly_bush` 网格 | 已描述隔离诊断：仅对该名称临时绕过 `PLANT_PROXIES`，没有修改产品映射 | 应先检查能否直接保留原生 atlas 动画。可能重新遇到原生植物不可见、随机偏移或雪覆盖问题；仅从接口文档不能判定 |
| B：静态本体层＋原生动态亮点层 | 私有 `modern_projection:r23_firefly_layered_diagnostic`，原模板的交叉骨骼复制两份，以文档 `texture: 0/1` 分层；专用 atlas 引用原生图片，专用 flipbook 保留原速 | 无须新粒子系统，能独立检查自定义模型能否获得动画 atlas。两个面共面，且亮点全部覆盖本体，深度问题未解决；只作诊断，不直接发布 |
| C：逐帧合成本体与亮点 | 私有 `modern_projection:r23_firefly_composited`；10 帧原版 source-over 合成到 16×160，保留现有两张交叉面的坐标、UV、朝向和 alpha | 无第二层共面问题；10 帧均不同，逐帧 alpha 与本体完全一致。通过 atlas flipbook 播放，不需脚本每 tick 重新生成几何。仍须验证动画注册、亮度及深度；不能声称保留了原版分层的独立 emissive 行为 |

离线资源片段位于 `.runtime/firefly-bush-r23-v1/candidate-overlay/`。它包含 BP/RP 的 JSON 片段、两个模型和一张新合成 strip，共 8 个文件；**这是待合并到新的停用快照的 overlay，不是可启动项目，也不应覆盖整个现有 blocks/terrain JSON**。所有诊断标识均使用项目专用前缀，没有改写原版短名。

当前源文件逐字节哈希在生成前后相等。离线检查确认 10 个源帧、10 个合成帧互不相同，合成帧 alpha 全部等于静态本体 alpha；生成预览已目视检查。合成不是原版 carried 贴图的重复播放：没有任何一个合成帧与 carried 图逐字节相同。

冷测已回答：该 16×160 strip 能在此自定义方块 atlas／Combine 与真实 PaperDoll 路径中播放，产品完整投影四向可见。64 像素限制的通用含义没有据此扩大解释；其他原生动画、缺失投影及组合仍应分别核对。不能拿文件存在或成功返回几何名称替代像素证据。

## C 方案的三文件最小 overlay

进一步检查确认，当前 carried 贴图与静态灌木本体的 alpha 逐像素完全相同，仅有 3 个 RGBA 像素不同。因此 C 无须替换模型、修改 `blocks.json`、注册新 BP 方块或更改产品映射；既有 `centered_firefly_bush` 模型及方块登记可以保留。最小改动只有：

1. 新增 `resource_pack/textures/blocks/modern_projection_r23_firefly_composited.png`：16×160，10 帧逐帧 source-over 合成，807 字节。
2. 修改 `resource_pack/textures/terrain_texture.json` 中**唯一**条目 `modern_projection_centered_firefly_bush.textures`，由 carried 图片改为上述新 strip 路径；所有其他 atlas 条目及字段原样保留。
3. 新增／合并 `resource_pack/textures/flipbook_textures.json`，以该既有短名注册 `atlas_index=0`、`ticks_per_frame=3` 的动画；如输入已有 flipbook 条目，全部保留后追加，发生同短名冲突就拒绝。

可重复生成工具为 `.runtime/firefly-bush-r23-c-v2/prepare.py`。它只读输入项目及原生 RP，只能向其私有目录的全新子目录生成输出；不提供安装或运行游戏命令，也拒绝覆盖已有输出。`verify` 会校验所有源哈希、仅有三份输出、atlas 只改变目标条目、旧动画保留、原生播放策略不变、逐帧像素正确及本体／当前 carried 的 alpha 相等。

```powershell
python -B .runtime/firefly-bush-r23-c-v2/prepare.py prepare --project <待冷测的完整停用快照> --native-rp D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data/resource_packs/vanilla --output .runtime/firefly-bush-r23-c-v2/<全新输出目录>
python -B .runtime/firefly-bush-r23-c-v2/prepare.py verify --output .runtime/firefly-bush-r23-c-v2/<同一输出目录>
```

当前实际输出为 `.runtime/firefly-bush-r23-c-v2/output-v1/overlay/`，来源是本轮主仓资源的只读快照。这个版本替代前节同时包含 B/C 的八文件候选作为 **C 最小冷测候选**；前一候选与证据保留。对最终停用项目应重新运行生成器，使 manifest 绑定最终输入，而非无条件把已有整份 atlas 覆盖进不同版本。

两次独立生成的三份输出逐字节相同。另以重新计算候选哈希后的篡改检查验证：改动无关 atlas、改帧速、改图像像素、丢弃既有 flipbook 均被语义检查拒绝；向非私有路径输出及覆盖原输出也被拒绝，共 6 项反例通过。带有原 `magma` 动画条目的输入副本确认该条目被保留。证据为 `docs/evidence/firefly-bush-r23/composited-overlay-offline.json`。

三份输出的 SHA-256 分别为：atlas `1f4d510bd48c0fe6dad79b78517d65924c4f54d0f84779b84a41bb0034dcd881`；flipbook `0fe75110748e5e541daba49eec7650be6975ea18e8ccdecfa05d97063aa53aa2`；strip `02724cb3a6218e044a58726fa5e953d6a407b86d91c0c13997694bfe8cb20bf0`。主仓模型、方块登记、BP 和所有输入资源在生成前后哈希相同。尚未启动或访问 MC，仍关闭 0 项问题。

## 原版覆盖规则证据与 C v3 兼容修正

上节仅含 1 个自定义 flipbook 条目的第一版候选已被替代，不能直接用于冷启动。进一步读取本机 3.10 自带的 `data/resource_packs/chemistry/textures/flipbook_textures.json`，第 2 行明确写有：

```text
// All the same as Vanilla, but not defining them here removes them all
```

这个原版文件实际重新列出水、岩浆、火等原版动画。其 SHA256 为 `214430ed3e23644703a976fa172e72075df050af775ccc4ef519a9fa1ce93144`。这是与当前游戏一起发布的直接资源证据，支持不能依赖单个本地条目自动保留 vanilla 动画。SDK 的相关文档说明了动画注册及 atlas 绑定，但没有给出 flipbook 跨包自动合并保证；`_ui_defs` 或材质的合并说明不能据此推广到 flipbook。

生成器已备份旧版本为 `.runtime/firefly-bush-r23-c-v2/prepare.before-vanilla-compat-v3.py`，并修正为严格保留 **完整 80 条 vanilla 声明，随后完整保留已有本地列表，最后追加 1 条项目专用声明**。原版列表有同 atlas 的不同 variant 或其他有意重复，全部保留原始字段和顺序，不按 atlas 名去重。正例另外保留了 2 条本地声明，包括既有 magma 本地覆盖的次序。

新候选为 `.runtime/firefly-bush-r23-c-v2/compat-output-v3/`，原副本 `.runtime/projects/firefly-r23-c-v1` 只更新了 flipbook 文件，其余两份 C 资源、10 份捕获依赖及方块／模型／BP 均未改变。新 flipbook SHA256 为 `e543fdd20b4d2f4496edc8cef75895df6f6d2f75a6aadb76b3aacb82c3488808`；旧文件已另外备份。旧新哈希、来源与复核保存在 `.runtime/round-20261019/firefly-cold-compat-applied-v3.json`，不修改原历史 source-manifest。

严格 JSON 解析拒绝重复字段、NaN、Infinity、注释及尾逗号；4 项重新计算输出哈希后的语义反例（删原版条目、重排原版条目、改速、改无关 atlas）仍被拒绝，另有本地条目完整保留正例。10 个合成帧逐像素复核仍等于原生 source-over，alpha 不变，`ticks_per_frame=3`、10 帧／名义 1.5 秒一轮、缺省混帧与帧序策略均未改。离线摘要为 `docs/evidence/firefly-bush-r23/flipbook-compat-v3.json`。

这次修正降低了声明缺失风险，仍须在冷启动后检查原版水／火／岩浆连续动画哨兵；它不等于引擎加载实现或像素回归已验收。当前仍关闭 0 项问题。

## 独立飞虫的最小后续工作

原生 `firefly_particle.json` 的有来源参数包括：一次产生 1 粒子、寿命随机 10–15 秒、初速 0.5、随机加速度、阻力 3、billboard 大小 0.0375、碰撞半径 0.0375、弹性 2，以及随寿命淡入淡出的颜色。**一次发射器产生 1 粒子不等于原生灌木每秒产生 1 粒子。** 原生方块触发频率、区域、时段和距离条件未在这些 JSON 中给出，本轮不臆造。

完整／缺失投影可以先隔离验证 `Create("minecraft:firefly_particle", position, rotation)`，保留每个句柄，用 `Remove` 与 `Exist` 检查关闭、移动、切维度、清空、替换蓝图后的回收。不要使用 `RemoveByName` 清掉世界里其他同名原生飞虫。公开 API 支持并不代表原生这一 identifier 已经在实际实例成功创建。

编辑器是另一道门槛：普通世界粒子不会因为绑定了某个模型就自动进入编辑器的 UI 模型渲染、缩放和裁剪链。需要在其实际渲染控件中做正反对照；若不能使用原生粒子，就需要编辑器可裁剪的几何／材质动态叠加，而不是往编辑器后面的游戏世界随意发射粒子。当前没有来源或像素证据证明 UI 接入已成立。

## 连续采集工具与剩余验收

已准备 `tools/capture_firefly_motion_r23.py` 作为第一道最短连续实测。它不启动游戏、不安装资源、不写世界，也不发射粒子；必须提供明确的 session、owner、project、单帧捕获程序及连续捕获程序 SHA256。对冷快照使用其内部逐字节核对过的 `capture_native_burst.py`，保留既有 ROOT／project 的强绑定检查。

默认是北向完整投影，先产品代理、后原生 `raw_loaded` 网格；`--view` 可明确选择东、南、西，`--route product` 可仅测产品路线。每条路线先做同位空气／石头与隐藏控制，再对萤火虫灌木可见、隐藏状态各持续采集 3.3 秒。目标 ROI 由八个方块角点在原始物理 PNG 中固定，坐标不按逻辑屏幕尺寸缩放；连续帧、原始 PNG、逐帧 WGC 回执与 QPC 时间戳全部保留。要求被接受的第一帧到最后一帧跨度至少 3 秒；采集区间内的相机、玩家、实体、文档身份、哨兵和原生网格提交必须不变。恢复后另读回文档、玩家、origin、选项、导航及哨兵。

该入口只记录目标内部的运动信号，并提供隐藏对照，始终保持 `animation_accepted=false`；连续采集完整不能自动证明动画节奏、亮度或原版一致性。最初入口的 8 项离线检查覆盖静态无运动、目标内运动、目标外运动不能冒充、原图／回执篡改、实际跨度不足、无效／不连续 burst，以及物理坐标不缩放；当时 19 段注入已使用真实 Python 2.7.13 编译通过。加入 magma 后扩展为 9 项检查与两组 38 段编译；各阶段摘要和工具哈希保留在 `docs/evidence/firefly-bush-r23/temporal-tool-offline.json`，不将旧结果伪写为覆盖后来源码。

本轮再增加 `--mode editor` 与 `tools/capture_firefly_editor_r23.py`，只允许产品灌木样本。它复用真实编辑器的既有 PreviewTile／PaperDoll，等待当前文档的实际预览资源就绪，固定姿态 35°／25°、zoom 3.5，并对原生 doll 控件本身执行显示／隐藏；不把世界实体放在 UI 后方冒充编辑器。ROI 来源为实际 Scene 视口内的静态模型显示／隐藏差分边界，随后固定，不追踪亮点。27 段编辑器注入用真实 Python 2.7.13 编译通过，恢复包含原控件可见性、grid、文档、相机和导航。本轮实际采集验证了该路径，9 项离线检查也再次通过。

采集后运行 `python -B tools/review_firefly_motion_r23.py <capture.json> --output <全新查看目录>`，可获得离线 `index.html`、固定 ROI 时间变化图及按 0.15 秒就近选择原始帧的联系图。查看器按实际 QPC 间隔播放并支持逐帧滑动，逐帧链接完整原始 PNG 和原生回执；可见与隐藏段各自以首帧为零，不假定相位对齐。它重新核对图像／回执哈希、wrapper 完整内容、owner／project、石头校准及前后场景／提交稳定性，只读原始证据。合成例中 17 帧的目标内运动被保留，目标外运动被排除；5 类污染反例被拒绝，JavaScript 已通过 `node --check`，联系图已目视检查。该合成检查没有访问 MC，也不提供动画验收。

原生动画回归先准备了最小 magma 哨兵：同一入口添加 `--sample magma`，默认并限定为 `raw_loaded` 路线，使用原生 `minecraft:magma` aux 0，不经过产品流体着色器，也不放置真实世界方块。原生 strip 为 16×48 的 3 个不同帧，原声明 `ticks_per_frame=10`，名义每帧 0.5 秒、一轮 1.5 秒，因此相同的 3.3 秒可见／隐藏连续采集可以覆盖两轮。原始 strip SHA256 为 `da2efdd3b8d71d8980bb0a8b520b9ac8146e07b5ec5cce4126358a1e65b81049`。计划为 `.runtime/round-20261019/magma-native-sentinel-plan-v1.json`；查看器会按 sample 显示岩浆哨兵标题。此哨兵同样要求空气／石头控制、完整时间线及恢复，不把非零运动直接当作正确动画。

加入哨兵后，最新离线检查为 **9 项通过**，萤火虫和 magma 两组共 **38 段注入使用实际 Python 2.7.13 编译通过**。萤火虫默认样本与路线不变，原生哨兵有单独报告；水和火的哨兵仍待后续安排，不能从 magma 一项推广。

用于上述实测的 C 冷副本为 `.runtime/projects/firefly-r23-c-v1`。连续捕获只需的 10 份工具依赖已逐字节补入，新增清单及哈希保存在 `.runtime/round-20261019/firefly-cold-burst-dependencies-v1.json`；不复制整个 tools，不改资源，也不回写原 source-manifest。启动、实例所有权和资源集成均由主代理协调。

1. 接入维护生成器时保持本次已测 C v3 资源的字节／语义，避免居中植物生成器把 atlas 再写回 carried；不要将首版单条 flipbook 当作正确输入。
2. 补缺失投影和其他编辑器姿态，在有效构图中核对完整本体，并与可见的原版世界灌木对照速度／亮度。不能以全屏差分、天空或动物运动认定灌木在动。
3. 检查旋转／镜像、切面、含雪遮挡、占用消隐与恢复；继续原生水／火动画保留哨兵，不能只凭 magma 一项推广。
4. 独立飞虫另行研究 UI 与投影接入和句柄回收，不能把贴图亮点变化当作离体飞虫完成。分别记录贴图动画、独立飞虫及各渲染路线；OB-01 仍开放。
