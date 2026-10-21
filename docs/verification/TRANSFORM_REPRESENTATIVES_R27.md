# R27：T03／T06 实机代表、T02 原生提交窄查与 T07 双层卡

2026-10-21 23:30 开始的窗口先补齐此前尚无公开入口的门／床／双格植物和连接代表。生产改动仅在 `debug_transform_acceptance.py` 添加候选及现有伙伴闭合规则的入口；没有修改变换、邻域、相机或共用渲染算法。两个文件已由主代理独立复查并提交为 `7015c9c470f5cbb1144b2565a8eb740ac8f3e7e0`。新增人工关闭数为 **0**。

## 新公开卡

均位于“测试蓝图 → 变换”，载入前沿用现有确认对话框。每张卡可重新载入原例；不能直接覆盖用户建筑而不提示。三卡尺寸均为 32×10×32，自动预选规定范围并显示操作说明。

| 入口 | 构成与默认范围 | 首个代表操作 | 预期数据与人工重点 |
| --- | --- | --- | --- |
| `test.transforms.acceptance.t03` | 30 格：两组门、四向床、两组双格植物及支撑／角标；选区 `(2,1,2)`—`(20,5,23)` | Y 轴 90°旋转、撤销 | 两门分别为 north／关／左铰链与 east／开／右铰链；四向床头脚完整；高草／向日葵上下半完整。门下半 `(4,2,4)` 旋转到 `(21,2,4)`，上半同步；床的完整 typed Bed 数据和根位置跟随移动 |
| `test.transforms.acceptance.t03_half` | 与 T03 相同原例，只请求上半门单格 `(4,3,4)`；现有规则补选为 `(4,2,4)`—`(4,3,4)` | 镜像 X、撤销 | 门仍为完整两格且铰链按原生状态变化；其他门／床／植物与支撑不变化。入口明确区分请求单格与闭合后的实际选区，不实现半门破坏式变换 |
| `test.transforms.acceptance.t06` | 48 格：正／倒楼梯各一内角和外角、栅栏＋门、墙、玻璃板、铁栏杆与支撑／角标；选区 `(2,1,2)`—`(20,5,27)` | Y 轴 90°旋转、撤销 | 相邻几何随实际位置形成角形；gate、pane／栏杆跨 X=15/16，墙跨 X/Z=15/16。玻璃板目标 `(15,2,22)` 旋转到 `(7,2,15)`；墙中心 `(15,2,16)` 到 `(13,2,15)` |

T03 默认四向床的脚坐标为 `(4,2,10)`、`(9,2,10)`、`(14,2,10)`、`(19,2,10)`；床头分别为 `(4,2,11)`、`(8,2,10)`、`(14,2,9)`、`(20,2,10)`，每半均有支撑。独立局部选区检查另覆盖床头 `(4,2,11)` 和植物上半 `(4,3,17)`；它们由离线业务检查执行，公开边界卡默认先演示门。

T06 楼梯中心／相邻控制分别为外角 `(4,2,4)`／`(4,2,3)`、内角 `(10,2,4)`／`(10,2,5)`；倒置对应 `(4,3,9)`／`(4,3,8)` 和 `(10,3,9)`／`(10,3,10)`。这里只提供有明确输入关系的代表，不能把其存在当作原生角形外观验收通过。

## 离线验证与来源边界

新增三项业务检查分别核对原生门／床／植物的明确状态、只选门／床／植物一半后的伙伴闭合及六种变换、不相关格不变、撤销／重做／逆操作，以及 T06 的跨格构成与墙连接方向。原有六种操作通用检查会自动覆盖新卡。定点 `test_transform_acceptance.py` 17 项通过；包含五个既有模块的整体前检共 50 项通过，公开注册无遗漏。MCP 定点 review 扫描 1 文件、无发现。主代理另独跑 17 项及真 Python2 编译。

真 Python2.7 与 Python3 宿主对三卡各六种操作执行 typed 保存载回、逆操作和可用撤销／重做，两端 JSON 逐项相同，初始及每次变换的文档摘要 SHA 相同。输出 raw bytes 不同，**不称字节一致**。首次宿主导入误用了不存在的 `encode_cell`，在构建 fixture 前失败；原 host 保留，v2 只改为现有 `encode as encode_cell`。原失败不涉及游戏或生产代码修改。

离线前检运行时记录的是提交前 HEAD，之后明确与 `7015c9c4` 冷源逐文件绑定：12 个 runtime／host 依赖均相符，其中 `debug_transform_acceptance.py` 工作树 CRLF 与 git archive LF 的实际 SHA 不同，换行归一化后相同；其余 raw 一致。6 个本地测试文件分别保存 SHA。没有把换行归一化结果描述为 raw bytes 相等。

原始记录在 `.runtime/round-20261022/transforms-runtime-v1/`：`offline-preflight.json`、`offline-source-binding.json`、`py2-v2.json`、`py3-v2.json` 和 `dual-host-comparison.json`。这部分仅证明数据／状态／事务，编辑器、完整投影、缺失投影及人工验收仍分别记录。

## 冷源实机结果与当前边界

独立 owner `r27-transform-runtime-v1` 已从 `7015c9c4` 以 git archive 冻结正常 source-only 副本，3708 个 runtime 文件、780 个 host 文件，manifest SHA256 为 `4f284dad0cf1d1cd5357f4bcd78a395427a98e9375c920d7fdb0305404a0c4a6`。不赋候选 profile，不加书诊断 alias，关闭四项自动热重载。旧冷源及原证据均不修改。

T02 复用既有 SDK Combine 调用前的 `SerializeBlockPalette` 委托探针，实际完成 full → Y3 single → full，保持同一 60 格 typed Document、按钮与支撑数据、相机不变。目标 `(3,3,27)` 在三阶段实际提交材料中均为 `stone_button aux0`；Y4 支撑在 full 存在、Y3 single 不存在、回 full 后恢复。三阶段新增 native record 数分别为 5、3、0；A′ 使用 A 的同一已提交模型，明确为缓存复用。原始截图已打开：single 可见按钮厚度，两张 full 可见支撑面但按钮仍被遮蔽。因此范围缩小到原生合并几何／遮挡／深度或场景关系，**full 可见性仍未关闭**，不能仅称低对比度，也没有改动渲染器。

| 公开代表 | 实际取得的结果 | 尚不能据此关闭的部分 |
| --- | --- | --- |
| T03，Y 轴旋转 90° | 实际公开卡及确认回调、30 格 typed 基线／旋转／撤销对照相符；编辑器前后、完整投影及受控 missing 均有截图。完整投影记录当前源的原生提交；门两半目标缺失观察 `[1,1] → [2,1] → [2,2] → [1,1]`，提交代次 `0 → 1 → 2 → 3`。占满时两半一起消失，恢复时一起出现，支撑及另一门保留 | 受控占用只临时替换本 owner 的读取，未写世界，不等同原生世界实际扫描。概览中有对象被裁切，不能算门／四向床／双格植物所有外观、全部操作或组合均通过 |
| T06，Y 轴旋转 90° | 实际公开卡及确认回调、48 格 typed 基线／旋转／撤销对照相符；编辑器前后、完整投影及受控 missing 均有截图。完整投影记录当前源的原生提交；中心玻璃板缺失观察 `[1] → [2] → [1]`，提交代次 `0 → 1 → 2`。占满后中心板消失、恢复后重现，相邻板／铁栏杆／墙／栅栏门仍存在 | 概览裁掉部分楼梯；不能据此声称正倒内外角全部像素或全部镜像／旋转矩阵已验收。仍待周末人工检查 |
| T03_half，镜像 X | 公开卡和伙伴闭合后的 typed 镜像结果与离线 oracle 相符，变换前编辑器图已留存 | 变换后的严格预检超时，未取得 after／完整／missing 资格。局部改变后远端未改变块保留原 revision signature，现有 host 要求每块完整当前 signature；同时跨卡缓存复用会触发原 host 的 nonce 约束。v3 曾放宽 nonce，**不能以此宣称已证明旧模型复用**；需绑定先前不变模型、完整 prepared／实际序列化 palette 及当前 source／cache／signature 后再验证 |

T03／T06 运行对照严格比较解码后的文档语义与编辑器状态；运行报告中部分 `encoded_equal=false`，不能称序列化字节相同。两例的当前源／缓存、占用快照、原文档和玩家不变均另有断言，临时占用观察器最终恢复。上述代表成功也不替代人工像素验收；新增人工关闭数保持 **0**。

原失败均保留：首次 host 用门双格均值 `(21,2.5,4)` 作投影焦点，被 `world.coordinate` 拒绝，未写世界；v2 仅改为实际门下半整数焦点后完成 T03，随后遇 T03_half nonce 预检；v3 的半门变换后严格缓存预检阻塞；v4 使用原严格 nonce／source／cache 检查单独完成 T06。没有为了使数据通过而修改生产渲染路径。

最后获准的两格按钮实验拟通过实际 erase 暂时移除另 58 格、保留同一 Document／体积／相机，执行 full／single／full 并 undo 复原。新增只读原生序列化 SHA 探针在载入初始公开 T02 时因游戏 Python 的 `hashlib` 无 `sha256` 而失败；**尚未执行 erase，三阶段均未执行**。该实验不能列为完成，也未追加新 shader／raw 探索。失败宿主及 traceback、两个内部恢复审计均保留。

测试结束恢复原 session／Document／factory／工具／profile／相机并清除临时标记。外部独立只读审计 before、after1、after2、最终 after3 均完成；三个 after 的严格 `changed_keys=[]`、相机旋转差为零、冻结源不变。真实游戏 PID `33388`／creation identity `134370718244040380`、MCDK PID `45844`／identity `134370718238651123` 均经同句柄核验后普通停止；游戏实际退出 **`0xC0000409`**、MCDK 退出 0。虽然 registry 最终为 stopped，**不记为正常引擎退出**，未强杀游戏。只回收本 owner 的已核验 assertion watcher；无已知或未知 assertion 记录。00:15 释放实例给水专项。

## 可审阅证据与周末检查

仓库证据在 [`docs/evidence/transform-representatives-r27-v1/`](../evidence/transform-representatives-r27-v1/)：`summary.json` 区分代表完成／宿主失败／缓存复用和人工资格，`index.json` 逐个记录原始文件、压缩包、解压内容的 SHA256。共 131 份压缩记录、49 张 JPEG 预览，合计 4,506,678 字节，最大单文件 214,930 字节；12 份完整 UI 树仅在 `.runtime` 保留原件及摘要。唯一含凭据的 stop 记录只归档标明脱敏的衍生版本；其原始 SHA 与解压内容 SHA 分列，不称原样一致。JPEG 是有损衍生图，原 PNG 的路径／SHA／尺寸另列，像素差计算仍来自本地原 PNG。

周末先载入 T03 检查两组门铰链／开关、四向床和双格植物整组旋转／撤销，再载入 T03_half 检查单格请求的伙伴闭合与镜像铰链，最后载入 T06 检查正倒楼梯四种角形和跨 X/Z=15/16 的连接。人工需分别观察编辑器、完整投影及缺失投影，记录具体方块和操作；代表卡已可用不代表所有矩阵自动通过。T03_half 的 after 运行预检阻塞及 T02 full 按钮可见性继续列待办。

## 后续 T07：小型双层与 typed 文字代表

T03／T06 冷源关闭后，经主代理确认，新增 `test.transforms.acceptance.t07`。这项后续改动独立于前述 `7015c9c4` 的冷源实机证据；不能把旧冷源的运行资格转给 T07。生产仅扩展同一公开 fixture 文件及对应业务测试，沿用现有变换算法。入口经现有 metadata／builder 自动注册检查，**尚未启动 T07 实机公开卡／确认回调或三路径像素检查**。

T07 为 32×10×32、19 格：8 个主体、8 个支撑、两个选区角标及一个区外紫标 `(24,1,24)`。选区 `(2,1,2)`—`(14,5,18)` 为不对称 13×5×17，焦点 `(8,2,10)`。所有主体从现有 fixture 实际查询并完整复制两层；带 NBT 的仅重定位 tagged 根坐标，没有手写或制造 aux。源对应为：

| 主体 | 原公开 fixture／源格 | T07 目标格 | 明确预期 |
| --- | --- | --- | --- |
| 干楼梯 | `test.layers.water`／`(18,1,3)` | `(4,2,4)` | 前景 oak_stairs，`weirdo_direction=0`／非倒置；背景 air |
| 含水楼梯 | `test.layers.water`／`(18,1,6)` | `(8,2,4)` | 相同楼梯；背景 water，`liquid_depth=0` |
| 仅背景水 | `test.layers.water`／`(3,1,9)` | `(12,2,4)` | 前景 air、背景 water，层顺序不交换 |
| 薄雪罂粟 | `test.layers.snow`／`(18,1,9)` | `(4,2,10)` | 前景 snow_layer，`height=0`／`covered_bit=true`；背景 poppy |
| 厚雪罂粟 | `test.layers.snow`／`(18,1,16)` | `(8,2,10)` | 前景 snow_layer，`height=5`／`covered_bit=true`；背景 poppy |
| 干罂粟 | `test.layers.snow`／`(18,1,3)` | `(12,2,10)` | 前景 poppy、背景 air，作为无雪对照 |
| 干告示牌 | `test.entities.signs`／`(5,1,7)` | `(4,2,16)` | 原生观察双面 typed NBT；前景 standing_sign／背景 air |
| 含水告示牌 | `test.entities.signs`／`(3,1,7)` | `(10,2,16)` | 同一文字样式；背景 water，保留完整 FrontText／BackText、颜色、发光、格式及其他非空间标签 |

首个建议操作为 Y 轴 90°旋转，其独立坐标预期为 `(x,y,z) → (20-z,y,x)`：含水楼梯到 `(16,2,8)`，含水告示牌到 `(4,2,10)`。之后撤销，再镜像 X／撤销、镜像 Z／撤销；区外紫标始终不动。薄／厚雪只用于区分层与高度，不授予含雪植物新的外观资格。

新增两项业务检查在源格逐对照外，使用独立坐标矩阵和明确方向表检查六种操作。楼梯初始朝东，六操作的新 direction 分别为 `2,1,3,1,0,0`，仅镜像 Y 改变倒置；告示牌初始 rotation 0，对应 `4,8,12,0,0,8`。同时检查前后层完整材料、雪高度、typed 根坐标和全部非空间 NBT 不变，保存载回以及撤销／重做相符。定点共 **19 项通过**，真正 Python2 编译通过，MCP review 最终定点扫描 1 文件／无发现。通用 palette 检查原先假定渲染体积等于逻辑体积，首轮遇 T07 的既有雪植物 overlay 而失败；现为 T07 明确断言实际渲染体积 `(32,32,266)`，逻辑尺寸仍为 `(32,10,32)`，没有修改 renderer。

真正 Python2.7／Python3 宿主对 T07 各六种操作通过 typed 保存载回、逆操作、可用撤销／重做；两端 JSON 与文档摘要一致，raw 输出 SHA 不同，**不称字节一致**。另包 [`docs/evidence/transform-t07-offline-r27-v1/`](../evidence/transform-t07-offline-r27-v1/) 保留源码快照与 SHA、实际源格／完整 tagged 根、两宿主结果、最终测试及 review，以及首轮诊断的明确节选和修正原因。10 份压缩记录、总 39,356 字节、最大单文件 12,432 字节；不覆盖前述冷源或小包。

## 后续严格链路：半门、双层卡和两格按钮

本节更新前述未完成状态，但保留此前失败及来源边界。新实机使用精确集成提交 `87327491cea2d7d83e2728907a35d35d76642d16`，单独 owner `r27-transform-lineage-v4`，manifest SHA256 `deb63c578c671cbb11329eb513d3ddadc235f49c8b2c64ae55915508408a4138`。产品归档 SHA256 `47407eb4103da862009594a1d1223b4ae76bc850cacd94b960665b3430bd0768`，3709 个 runtime／781 个 host 文件均逐项检查；四项热重载关闭，无候选 profile 赋值。新人工关闭仍为 **0**。

原严格 host v2 的首次实机，在 T03_half 公共卡首帧遇到 Python2 profile identity 的 bytes 经宿主 JSON 规范化报错；原 typed wire 正确保留了 bytes，不能把该失败解释为产品渲染失败。失败 raw、报告、恢复及异常退出原件均保留。新严格 host v3 仅在 `Session.preview_signature()` 的明确传输边界允许 typed tuple 对应 JSON array、严格 UTF-8 bytes/text 对应 JSON text；完整源、NBT、native palette 仍按原始 typed wire 字节比较。不同内容、非法编码、容器替换、bool/int/float 混同等 18 项边界控制及原 27 项链路控制全部通过，主代理独跑复核；没有修改原始 false signature。

生命周期 v3 只完成准备，未启动 MC。另建生命周期 v4 使用主代理审过的私人 watcher／Win32 manifest reader，单独 SHA 绑定，生产 tools 不变。读锁只对实际 Windows 5／32／33 做有界整次重读；没有把仅 errno13 的所有 PermissionError 当作可重试。两个私人 host 的锁／schema／owner／identity 控制由主代理另行独跑；实机此次 watcher 无错误／断言／恢复／读重试事件。启动器写端曾出现一次 atomic replacement WinError5 重试，保留原 stderr。

| 代表 | 新取得的严格数据／模型来源结果 | 仍待解决的实图问题 |
| --- | --- | --- |
| T03_half，镜像 X | 只请求门上半后实际伙伴闭合为两格；公开卡和确认回调、typed mirror／undo、完整投影和四阶段受控 missing 均完成。变换后一个 owner 为当前新提交，三个未变 owner 保留原始 `signature_current=false`，但完整创建、source／face halo／prepared native／实际 Deserialize／Serialize／cache 及实际 UI front 链相符 | 主代理打开原图，孤立上下代表可见，但下缘床部分裁挡。不能据此关闭全部门床植物的全部外观或矩阵 |
| T07，Y 轴 90° | 公共卡和确认回调、typed rotate／undo、完整投影及四阶段受控 missing 完成。楼梯、仅背景水、薄／厚雪植物、干／含水告示牌完整两层与 tagged 根坐标及非空间 NBT 均对照 oracle；区外标记不动。变换后一个未变 owner 的原始 false signature 保留，并通过完整来源链 | 主代理打开 `t07_after.png`，编辑器水面明显悬空，水位置／外观继续开放，交水专项处理；本节不授予水渲染新资格 |
| T02，两格 full／Y3 single／full | 从公开 60 格卡用普通 erase 暂去 58 格，保留同一 Document／editor、逻辑尺寸、相机 Pose／Pivot／Pan，按钮 `(3,3,27)` 与 Y4 支撑 `(3,4,27)` 不变；三阶段实际原生 Serialize 均有 stone_button aux0，支撑为 stone aux0／无／stone aux0。A 创建 serial60，B61，A2 精确复用 A 的 serial60 和完整原生数据；随后 undo 回同一 Document 的全部60格 | 主代理打开 A／B／A2 原PNG，full／A2 只有可辨石头大面，按钮不可辨；single 显示小按钮。full 可见性继续开放。遮挡、原生合并剔面、aux 朝向或空间关系均只是待证假设，未默认归因缓存 |

T07 使用实际 session 的 liquid profile 交给原渲染路径，没有赋候选值。冻结生产源码会选择 `ProductLiquidProfile`，运行 signature 的 ownership 为 `minecraft:flowing_water`／`minecraft:water`；本轮未单独导出 live class name，故把 Product 类型描述限定为冻结源的选择证据。完整 typed 两层／NBT 通过不意味着水表面像素通过。13 个运行阶段存在材料索引插入顺序／压缩块不同，解码后的文档语义和编辑器状态相符；不称 raw 文档字节一致。

共取得30份完整原始 lineage raw和30份独立 certificate。实际 parent surfaces、front index／name、child doll、tracked visibility、poses、depth-hidden／suspended 均观察。可见 front须符合完整提交；屏外／深度隐藏 owner仅标为 `source_proven_offscreen_or_depth_hidden`，无像素／可见性资格。受控 missing 临时替换本 owner 读取，不写世界，不能充当真实世界占用扫描或物理鼠标命中验收。

两次内部恢复与独立 before／after1 审计通过，after1 `changed_keys=[]`，原 session／Document／factory／geometry覆盖／profile对象／工具／相机和标记恢复，guard源及所有绑定 host不变。运行最高 game handles857，最少可用 commit11,213,438,976字节。02:31 提前释放实例。普通 owned stop记录游戏实际 **`0xC0000409`**、MCDK0，仍不算正常引擎退出；未强杀游戏。仅回收核验 PID／creation identity 相符的 watcher，exit0。

小包 `docs/evidence/transform-lineage-r27-v4-v2-small/` 的 `index.json` SHA256为 `fcc780bc91f10a36fa21923ed76eb739efe71f587954da84d8e67eeb5ae6e515`：106逻辑记录／40文件，8,600,146字节，最大单件240,000字节。JSON／源码放入 gzip tar 的有序分片，索引分别记录原件、脱敏衍生内容、容器和分片SHA；v1小包发现stdout内嵌JSON仍有敏感字段后，原包完整移入runtime历史，未进入提交；此v2对对象、列表、字符串内嵌JSON及普通文本中的凭据／JSON转义变体递归脱敏。7张重点原PNG按原始字节分片保存，43张原PNG全部有本地路径／SHA索引，其余36张明确只留本地原件。原UI完整树仅本地保留。独立解包核对106条内容／99归档成员、原件SHA、内嵌JSON敏感字段及凭据文本均通过；同一独立验证器会拒绝v1原包的2个泄漏JSON记录。结构证书不代替打开原图，新增人工关闭保持0。
