# R25：本机建筑配置的 SDK 文本边界修复

2026-10-21，T04 跨格双箱完成镜像后，真实 `Session.save()` 成功，但从 `ConfigCompClient.GetConfigData` 读回再调用 `Session.load(1)` 失败，提示“语义方块格式或来源方块表版本无效”。IO 已结束，原 editor/document 仍在，撤销历史仍为 1；不能把“IO 空闲”当作载回成功。

根因已在实际游戏 Python 2 取证：SDK 读回的 registry 版本、SHA-256、材质名、状态名和 wire 文本是 `str`，生产 `semantic_wire` 要求解码后的 `unicode`；`cellVersion` 仍为 `int`，registry 仍为 `dict`，保存前后 JSON 值相等。网络接收路径已有 `transfer._wire_text` 解码，这三个 ConfigClient 读取入口缺少相同边界处理。

`bridge.py` 仅在 `load_library`、`load_archive_page`、`load_preferences` 的 SDK 返回处复用 `_wire_text`。偏好 v2 的常用方块同样调用 `semantic_wire.validate_header/decode_material`，因此属于相同 wire 格式。只解码序列化树中的 UTF-8 文本；actor 中的二进制内容仍通过带标签的 base64 wire 数据恢复。没有修改 `semantic_wire`、`cell`、方块表解析或其严格类型校验；非法 UTF-8 继续明确拒绝。

## 实机结果与边界

同一个受管实例 `transform-r25-main-v1`（PID 60968，创建身份 `134369845010134425`）保留最初冷副本。修复验证从当前生产源码提取上述三个方法并临时绑定到该 bridge，复用冷副本中逐字节相同的 `transfer._wire_text`；之后全部恢复。**这是精确源码方法的同实例 SDK 验证，不是修复后冷启动或客户端重启验证。**

实际 SDK 存取使用唯一的 `modern_projection_r25_<uuid>_` 命名空间，适配器仅重定向建筑库和分页存储 key，其他 API 委托原组件。真实生产 `Session.save/load`、codec 和 archive 路径未被替换；用户原建筑库 key 的前后读回相等。结束后临时 key 写入 `{}` 并读回确认，属于 tombstone，不宣称物理删除配置文件。

| 用例 | 实际路径与结果 |
| --- | --- |
| T04，32×10×24 | X 镜像后，v6 内联文档真实 SDK 写入 1 次、读回、异步载回通过；新 editor/document，完整坐标、前景、背景、带类型 actor 语义相等；undo/redo 为 0，选区等于新 Editor 的默认全建筑选区。 |
| T08，32×36×32 | 90°旋转后，v7 分页索引＋1 页，真实 SDK 写入 2 次；保存和载回均走异步 IO。新 editor/document、完整语义与新 Editor 状态检查通过。 |
| 读图 | 两张载回后的 WGC 原图均已实际读取，双箱／门可见；该检查不关闭门在 missing 投影中留下窄木条的独立问题。 |
| 独立恢复复核 | 两例结束后另开只读检查：projection、prepare、busy、edit、IO 均空闲，所有本探针标记为空，原 factory/occupancy 类恢复，投影 actor 为 0。 |

本次未增加人工验收关闭数。未验证修复后的冷启动、真实用户库原 key 写入、客户端重启或所有格式／状态；原始冷副本的 bridge 与生产修复文件存在明确源差异，不将其计作整包冷启或正式水源重新资格认证。

## 回归与证据

在仓库 `tests/` 目录运行：

```powershell
& 'D:/Program/Python/python.exe' -B -m unittest -v test_bridge test_session test_semantic_serialization test_complete_cells test_config_wire_boundary
```

128 项通过，包含 4 项新 Config 边界回归。新回归用真实 `D:/Program/Python27/python.exe` 执行 `Session.save → SDK 字节树 → Session.load`，覆盖内联和分页、中文名称、前后景、二进制 NBT、text／bytes、bool／int／float、list／tuple、非法 UTF-8；坏 header 类型、坏来源指纹和非规范 NBT 数值仍被拒绝。定点 `minecraft_py imports` 与 `review --scope modern_projection/projection/bridge` 扫描到 1 文件、解析成功；6 条既有结构提示位于未改的 follow/geometry/capture/receive 方法。

原始文件保留于仓库本地 `.runtime/round-20261021/transform-v1/`，不覆盖失败记录：

| 原始记录 | SHA-256 |
| --- | --- |
| `t04-storage-v1.json`：首次 SDK 载回失败，全恢复 | `9dc39bf1389cb0ea20acb16748953473f68d7814b6c31487c7827dadba5a8366` |
| `t04-storage-type-v2.json`：实际 SDK str/unicode 类型取证，失败重现 | `685b161b26a0bc61acae70c73d396d962f1f3c10935cfc75461f44ab87e22d1c` |
| `t04-storage-fixed-v3.json`：修复后内联通过 | `b502f2f6afe98561e1905208057af7916b57416a729040ac9ebde8dcbab43b95` |
| `t04-fixed-independent-restore-v1.json`：独立恢复通过 | `4a1fa4e8fae3a8c7229a3080cbdffbb95cd23ab1311ac8d93cf238b254a567ea` |
| `t08-storage-fixed-v1.json`：诊断工具误读分页索引的 materials 字段，停止并全恢复 | `af9aff37346a9ab926cea3f7b470a06b2ad3532733ff6fa21ad3974e9bdc2f29` |
| `t08-storage-fixed-v2.json`：修正工具后分页通过 | `33a5fa9b16df817af065aaa24812bd0ce34cedc4aa865cdeb4b16fbd9db4065b` |

取证时生产 `bridge.py` SHA-256 为 `c61c4fbdac9eb62fcb5a98a94de790a3e3707dd52364836cc6af90e0b8ba42d8`；冷副本原 bridge 为 `ee48886d1c43d24dd719420be61765a0c6c0e94887c8f81dcf5df439a531dd23`；共同的 `transfer.py` 为 `3311a07e89943bd21e0fa42a29e1140486d3e7e1ec423202a0de678de07d11da`。三个方法的独立源码指纹、私有存储调用、SDK 返回类型与恢复结果均写入成功报告。

## 修复提交后的冷源补验

同日另从正式提交 `83a551cf819a41f5b55302e6f1f45f4da8858498` 冻结两包 3699 文件，manifest SHA-256 为 `457ede616b391ab508fa690de53125caf60f786be0ea620bc905a52df61a8779`，四种自动重载关闭；在新的 `portal-pure83-r25-v1` 中使用未经运行时替换的生产 bridge 重做 T04 镜像内联和 T08 旋转分页。两例真实 `Session.save/load`、完整 typed 文档语义、严格 editor 状态与嵌套 storage 完成／恢复断言均通过，SDK 写入分别为 1 次、2 次。两张载回后的原图已读，双箱、门与定位块可见。独立只读审计确认原对象／文档／状态、factory、临时标记恢复，冻结源不变。

此增量补上“修复后冷启”的窄范围；仍未验证跨客户端重启持久性。SDK key 仍是 UUID 私有 namespace，用户库前后相同，临时 key tombstone 已读回，不宣称写过用户真实建筑库或物理删除配置文件。普通停止后游戏退出码 `0xC0000409`、MCDK 为 0，已退出并完成元数据清理，不能计作正常退出。

原始失败与上方同实例方法补丁记录保持。新三份报告、六份独立只读检查和 14 张已读原图的路径／SHA 见 [冷源证据索引](../evidence/transform-cold-r25-v1/evidence-index.json)；根代理另核对索引全部 28 项文件字节和 SHA 无差异。本次新增人工关闭数为 0。
