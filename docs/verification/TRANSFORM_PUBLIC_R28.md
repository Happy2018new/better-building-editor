# R28：公开变换卡、真实 SDK 保存载回与 T08 旧 host 拒绝

北京时间 2026-10-23 01:35:30—01:38:43，独立 owner `transforms-r28-public-final-v1` 从精确提交 `a6950ece68c1ae15176119e86043eb1989f79229` 完成 T01、T04、T05 三张公开卡的指定代表流程。随后 T08 在首次编辑器来源认证处被旧 v4 host 拒绝，整次运行 `completed=false`，没有重试。T08 的变换及 missing 阶段、其后的两张可选 T03 卡均未执行。**本节新增人工关闭数为 0**。

## 实际完成的范围

三卡均通过“测试蓝图 → 变换”的实际载入按钮与确认回调进入，严格对照完整 typed 文档和编辑器状态，并保留实际原生 Deserialize／Serialize、缓存来源与 UI front 的独立记录。没有用物理鼠标命中测试替代或扩大回调范围。

| 公开卡与本次操作 | 实际完成 | 证据边界 |
| --- | --- | --- |
| T01，不对称建筑，Y 轴 90°旋转 | 基线／变换／撤销／重做；编辑器前后；完整投影及隐藏对照；生产 `Session.save/load`、真实 SDK 配置写入与读回、重载后的数据及编辑器图 | 保存仅把 library/archive 键重定向到私有命名空间，并在 finally 恢复；没有验证客户端重启，也没有逐项执行卡片提示的六种操作 |
| T04，跨格双箱，沿 X 镜像 | 基线／镜像／撤销；编辑器前后；完整投影；受控 missing 的 empty、single_half、occupied、restored 四阶段 | 两格占用观察为 `[1,1] → [2,1] → [2,2] → [1,1]`。只临时替换本 owner 的占用读取，不写世界，不称原生世界实际扫描通过 |
| T05，四种铁轨，Y 轴 90°旋转 | 基线／旋转／撤销／重做；编辑器前后；完整投影；同样四阶段受控 missing；生产 `Session.save/load` 与真实 SDK 写入／读回、重载后数据及编辑器图 | SDK 保存每卡实际写入 1 次，完整语义相符；部分编码记录有材料索引／顺序差异，不称文档 raw 字节相同。世界近景只覆盖选定铁轨及坡面，不能关闭全卡全部像素或连接矩阵 |

运行实际取得 **37 张原始 PNG**：4 张公开列表、11 张编辑器图、22 张世界显示／隐藏对照；另有 11 张衍生 delta，不能重复计数。子代理逐张核对原图索引并打开未缩放的场景裁切联系图，重点原图另直接打开检查。T04 的单半阶段可见前方单箱，occupied 阶段前箱消失，restored 恢复双箱；本轮红色支撑面未见旧胸箱纹理残留。T05 编辑器可见环形轨道和四组坡道；选定世界近景的轨道在受控占用后移除、恢复后重现。这些观察是代理的限定范围检查，仍需周末人工验收。

## T08 的原始失败与离线归属证明

原始 `check/lineage/0026.json` SHA-256 为 `d082c6ceadffa9081c00596d08f9de26e9a0f5ba53cd371c100209e00abf154f`，v4 的原拒绝是 **`unmounted owner has relevant source cells`**。它发生在 `load_card → editor_preview → lineage_snapshot → certify`，早于 T08 的初始 oracle 对照、变换和 missing；没有为这份被拒绝的 raw 补造原证书。之前其他来源的 T08 结果不替代本轮结果。

v4 observer 的 `relevant` 明确定义为区域本体加六向一格邻域。实际区域 `(0,1,1)` 无 owned 格、无模型、逻辑与 prepared native 层均为空，却正确保留胸箱 `(15,15,18)` 和门上半 `(15,16,15)` 作为邻域；区域 `(1,1,1)` 同样只保留胸箱 `(16,15,18)`。旧 host 要求全部 relevant 格都为空，因而把这两种合法 context-only 空区域拒绝。

只读离线复核从原 31 格、32×36×32 文档调用精确冻结源码的 `Document.from_data`、`preview_regions.regions`、`TiledPreview.source_state` 与 `build_preview`，全分区、10 个 owner 的源快照及逻辑层相符。真实 Python 2 对完整 source snapshot、body、current cells、snapshot cells、logical palette 共 **10×5＝50 项原 typed repr 字节比较一致**。Python 3 重建另按明确 JSON 传输边界比较，不把它的不同 bytes/text repr 写成原始字节一致。

| 邻域中的原格 | 实际绘制 owner／区域尺寸 | 原始 SDK Serialize 中的索引与材料 |
| --- | --- | --- |
| 胸箱 `(15,15,18)` | `(0,0,1)`，origin `(0,0,16)`，size `(32,16,16)` | index 7922，`preview_chest_normal_north_main`；逻辑原格仍为 chest aux2、保留 typed actor |
| 胸箱 `(16,15,18)` | 同上 | index 7938，`preview_chest_normal_north_sub`；逻辑原格仍为 chest aux2、保留 typed actor |
| 门上半 `(15,16,15)` | `(0,0,0)`，origin `(0,0,0)`，size `(16,32,16)` | index 4351，`minecraft:wooden_door aux10` |

该证明支持“旧 host 把 context 与 owned 混同”的原因判断；它不能追认本次 T08 实机通过，也不把逻辑胸箱 actor 在转换为预览代理后未进入原生 actor 层写成 NBT 丢失。

独立 v5 私有候选保留全部原 source/native/cache wire、封印创建记录、实际 UI／front 和签名限制，另要求 exact 冻结分区与源格唯一归属、实际 `build_preview` 相符。只有 owned 格为 0、context 与原文档一致、完整缓存内容相符，且每个 context 格能落到其他 owner 的 current prepared／实际原生 Serialize 索引时，才允许该空 owner 未请求 UI；空 owner 始终没有可见性或像素资格。26 份原 raw 的离线回放和 58 项故障注入通过，包括协调删除实际／预备 native 胸箱索引、伪造 context／owned、完整邻域缓存变旧、把 bool／float 冒充 constant chunk 的整数 0，以及缺失真实控制。**v5 尚未在本节运行的 MC 上部署，不修改 v4 拒绝、旧冷源或主验收状态。**

## 来源、恢复与精确释放

冻结 manifest SHA-256 为 `4a85a3c158dc526280196c35b749e50fe9b0335566b0499c6b179716e93099cb`：3710 个 runtime 文件使用该提交的精确 Git blob 字节，778 个宿主文件单独冻结；没有把 CRLF 归一化称为 raw 相同。没有分配候选 profile 或改写 shared 渲染源码。原始 26 份 lineage raw、其中 25 份 v4 证书、来源绑定和失败栈均保留。

内部两次恢复审计与独立 after1／after2 均通过，后者 `changed_keys=[]`，冻结源及全部受绑定宿主保持不变。普通 owned stop 后，game PID 25704／creation identity `134371638987837718` 的原持有句柄退出为 **3221226505／`0xC0000409`**，MCDK PID 63564／identity `134371638985585477` 为 0；未 force game。精确 watcher PID 65444／identity `134371638847508879` 回收 exit0；独立查询三者原身份均已不存活，registry 为 stopped。资源释放完成，**正常引擎退出资格仍为 false**。

原 `owned-release.json` 的 manifest 字段为 null；它保持原字节，以单独补充记录关联实际 manifest，不覆盖原证据。全包原件在 `.runtime/round-20261023/transforms-public-final-v1/`，v5 候选与控制在相邻 `transforms-cache-lineage-v5/`。

后续独立新实例的 T08 与两张半组合卡结果另见 [R28 新实例补查](TRANSFORM_PUBLIC_COMPLETION_R28.md)；本节原运行的时间、拒绝和未执行范围保持不变。

[精简原件索引](../evidence/transform-public-r28-v1/index.json) SHA-256 为 `3a35fea685cd8698f035a87cba487433f9e040a0a880be813aea80c081eccd81`：115 个逻辑记录、38 个文件、8,377,830 B，单件最多 240,000 B。26 份 raw、25 份原证书、冻结源／host 绑定、恢复退出、真实 Py2 重建及 v5 离线证明按有序 gzip tar 分片保留；10 张重点原 PNG 按原始字节分片，全部 37 张原 PNG 有本地路径与 SHA。独立解包器核对全部原件与 archive SHA，并确认 4156 个完整 wire 未被脱敏修改，失败的 `0026.certificate.json` 仍不存在。对象、数组、内嵌 JSON 字符串和其他文字中的 token／凭据及转义变体递归清理，原件与衍生 SHA 分开。脱敏 raw 无法重算原配置的封印；完整原件保持在本地 ignored 目录。结构复核和精简包不替代实机或人工像素验收。
