# R25：门邻域几何的目标所有权修复

2026-10-21，T08 在跨 Y=15/16 的门旋转后，完整投影正常，但 missing 投影占据下半／整门时，门底仍残留窄木条。受控 observer 的占用值、源文档、投影快照、缓存和原点均正确，因此数据检查不能替代外观检查。

原因是每个目标格都复制 27 格邻域供原生模型烘焙；地板等非门目标复制的原生门几何伸入其中心裁剪盒，即使门目标隐藏，邻居副本仍可能留下几何。隔离对照已区分两种策略：删除所有门邻居能去掉窄条，但会使门上半失去依赖而消失；仅对非门中心过滤门邻居，则完整门、上半和占据消隐都保留正确结果。

`render_context.py` 的修复只针对原生 `minecraft:*_door`：非门目标不借用门的 common／actor，extra 仍保留；门目标仍保留上下伙伴邻域。全量、增量和分块构建三条路径均传递目标语义。`_ContextWriter` 的缓存键由对象 id 改为 `(id, hide_door)`，避免同一门邻居写给门／非门目标时混用计划。新增参数默认 `None`，保留既有无目标调用的语义。没有把规则泛化到床、双格植物、活板门或自定义门。

## 有界实机结果

使用受管 owner `transform-r25-main-v1`、PID 60968、创建身份 `134369845010134425`。原冷副本保持不变；私有工具从生产源码提取 7 个确切定义／方法临时绑定同一运行时，验证后恢复原定义。**这是精确生产方法的同实例验证，不是修复后冷启。**

| 范围 | 结果与实际读图 |
| --- | --- |
| T08 原始负例 | 旋转／撤销／重做／再次撤销与锁定伙伴整笔拒绝的数据检查通过；原始 missing 图中仍有窄条，保留为失败对照。 |
| T08 简单过滤对照 | 所有目标一律删门邻居：窄条消失，上半退化；拒绝该方案。 |
| T08 目标所有权对照 | 完整门与上半保持；single_half／occupied 不留窄条；restored 回到完整门。 |
| T08 精确生产实现 | 异步 rotate_y90 及四个 missing 阶段完整类型化文档／编辑器状态检查通过。实际读取前后编辑器、完整投影和四张 missing 原图：完整门、仅上半、全消失、完整恢复符合预期；双箱、绿色标记和地板保持。 |
| T05 精确生产实现 | 同步 rotate_y90 修改 172 格，完整类型化语义与严格编辑器状态通过。v1 世界全览中四类坡道和闭环全部入画；v3 编辑器变换后重新居中，全部入画。普通轨坡顶近景可见坡道与平轨接合，受控 single_half／occupied 分别隐藏指定坡轨／坡顶平轨，恢复后接合回来。动力轨部分进入近景，不据此声称四类轨道所有像素均通过。 |
| 恢复 | T08、T05 分别另开只读检查：原 editor `1439026458408`／document `1439026458184` 恢复，原建筑名保持，所有探针标记为空，原 factory／occupancy 类恢复，投影 actor 为 0，编辑／IO／投影均空闲，工作台恢复关闭。 |

四阶段 observer 值均为 `[1,1] → [2,1] → [2,2] → [1,1]`；它只控制实际生产 occupancy 的读值，没有放置世界方块，不等同真实世界扫描。本次不增加人工关闭数，也不关闭原铁轨全部像素／连接报告。相邻双门、所有朝向／开关状态的实机外观、冷启及真实世界占据仍未穷举。

T05 v2 私有近景工具误用半格浮点 focus，生产世界坐标验证明确拒绝“世界坐标超出范围”；原始失败、工具版本和完整恢复均保留。v3 改为整数 focus 后完成。该失败不记为产品缺陷，不覆盖原记录。

## 回归与审查

在 `tests/` 运行：

```powershell
& 'D:/Program/Python/python.exe' -B -m unittest -v test_door_context_ownership
& 'D:/Program/Python/python.exe' -B -m unittest -v test_render_context test_context_cached_writes test_context_cache_lifetime test_context_batches test_context_layer_visibility_r21 test_occupancy_neighbor_context
```

新增 3 项及相关 49 项通过。新测试覆盖 4 朝向×2 铰链×2 开关、跨 Y15/16、门／非门混合目标、同一 rendered 两种写入顺序的缓存区分、extra／actor 所有权、无目标默认契约，以及床／双格植物／活板门／自定义门负例。它们验证构建数据，不能升级为所有姿态的实机像素通过。

实际 `D:/Program/Python27/python.exe` 编译 11 个定义／payload／文件检查项通过，包含完整生产 `render_context.py`、7 个抽取定义、安装／恢复脚本及新测试。MCP imports 的直接调用边界不变；定点 `review --scope modern_projection/projection/render_context` 确实扫描 1 文件、解析成功，仅保留既有 `prepare_context_batches` 10 参数提示。无新增 import、跨端初始化或动态执行进入产品源码。

## 证据与来源边界

原图和原始 JSON 保留于本地 `.runtime/round-20261021/transform-v1/`；私有工具 v1 冻结于其 `production-context-tools-v1/`，v2／v3 分别保留脚本。关键记录如下：

| 原始记录 | SHA-256 |
| --- | --- |
| `t08-main-missing-v2.json` | `e42dcb560deccb26218c52304dbbd66febecb5c002a2dc7c99aefe002c850cc9` |
| `t08-door-neighbor-ab-v1.json` | `2aee2d59086b511bab5fd78aed6743e0a86b898c3176c2a8f0371976c9573323` |
| `t08-door-neighbor-target-ab-v2.json` | `f1f4cefba30de4c420f9d542a90a672da5a4f967a25e4271287995d174691d01` |
| `t08-production-context-v1.json` | `acfddca004ff648dc1915fc5b722931307526f1d168fb9f9573130f65bbec21d` |
| `t05-production-context-v1.json` | `6429d0a1f6c36820a9ba2dda8c26a7b47566005e723e176310478b4d7bb1f0f5` |
| `t05-production-context-v2.json`，私有工具失败，全恢复 | `9c43a76b4e48c6dbf04a29ecf0e9b6f20e4f9c5295970fe6209946d72a3cdaff` |
| `t05-production-context-v3.json` | `6a32abe6aacf985d39dc65efa6f62004335cd5eca2de4c3db009d8fc50f1656c` |
| `context-production-py2-compile-v1.json` | `c4744ef3289a294eb0ae39e9833cd953a82c57422bfb8850d99ee469bcecd7e4` |
| `context-scoped-review-v1.json` | `74f5077dd789a196f7de486863937f3ecd4d3a646410e741510bbdb4e7ca4811` |

`t08-production-context-independent-restore-v1.json` 与 `t05-production-context-independent-restore-v3.json` 均通过，SHA-256 均为 `4a1fa4e8fae3a8c7229a3080cbdffbb95cd23ab1311ac8d93cf238b254a567ea`。

本次生产 `render_context.py` SHA-256 为 `1e4fe6bc29270ed04427526c2e8f8e6f15995fe3690cc774c1b9526eb4143b45`；冷副本原文件为 `300bf6bab79348deeeb457665c1f08904349b694ab14e52be7cbaed488310ab0`。该文件属于水的共享来源合同，确有生产漂移；本记录不更新水的资格指纹、不宣称正式水来源未变，水需按最终 bridge＋render_context 冻结来源补验。Config wire 存取修复的独立结果见 [CONFIG_WIRE_R25.md](CONFIG_WIRE_R25.md)。

本 owner 结束时已先完成独立恢复，再发普通关闭请求。首个请求等待超时；随后只读 status 确认两个创建身份均已不存在，日志包含 Client／Server Destroy 和 MCP stopped，再仅完成停止元数据。没有 force、重启或新实例。该过程没有保留退出码句柄，不能作为正常退出码的证明；原关闭超时和后续检查原文均保留在私有证据目录。

## 正式提交的冷源补验

同日的新实例 `portal-pure83-r25-v1` 使用提交 `83a551cf` 冻结的 3699 文件两包，manifest 为 `457ede616b391ab508fa690de53125caf60f786be0ea620bc905a52df61a8779`；没有 context 方法补丁、别名替换或 profile 赋值，自动重载均关闭。T08 的实际异步 `rotate_y90` 完整 typed 语义和 editor 状态通过；已读前后编辑器、完整世界投影及四种受控 missing 的 shown／hidden 原图。观察值仍为 `[1,1] → [2,1] → [2,2] → [1,1]`，依次显示整门、仅上半、整门消失且无底木条、整门恢复，双箱、地板和定位块保持。

该补验支持修复后冷启的上述窄场景，不替代真实世界占用扫描，也没有新跑 T04／T05 missing 组合或全部门状态。T04／T08 的真实 SDK 保存载回另见 [配置边界记录](CONFIG_WIRE_R25.md)。旧 WGC 路径错误的 v1 host 失败、其恢复及成功 v2 均保留；源文件字节未变，结束后独立恢复通过。普通停止后的实际游戏退出码 `0xC0000409`，不宣称正常退出。

新增机器记录见 `TRANSFORM_R23_RUNTIME.json` 的 `r25_cold_increment`；小型[对照图](../evidence/transform-cold-r25-v1/controls.jpg)由原图缩放拼接，仅作导航；[完整索引](../evidence/transform-cold-r25-v1/evidence-index.json)绑定原始文件。未改写原资格哈希，新增人工关闭数为 0。
