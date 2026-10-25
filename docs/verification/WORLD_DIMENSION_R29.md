# R29：确认写入、首包与维度查询

R29 已在当前产品源修复“确认后切换维度，尚未开始的写入却落到新维度原坐标”的窗口，并把五处新增维度查询的已复现 SDK RuntimeError 转成可读原因，释放操作状态。`a4fe04356bfde423acd95a2e9f2641134664f5e5` 完成确认／分帧准备／首包的原维度绑定；`dcf34132ce8e33284066efe66b9693ff89dc675a` 补齐查询失败处理。最终选定 CPU 回归 23 条全过，实际 CPython 2.7.13 与 3.13.13 各通过 19 项对照。没有新增 MC 或人工验收，人工关闭 0。

## 确认和首次接收之间的窗口

先前 [WORLD_APPLY_LIFECYCLE_R29.md](WORLD_APPLY_LIFECYCLE_R29.md) 对应的 `af9c628c` 在已开始 apply 的每批前核对玩家在线和原维度，停止后续写入并保留已写前缀。若玩家在服务端收到首包前已切维度，服务端当时新建的 adapter 只能看到新维度，原守卫无法知道确认时的维度。这次补的是该窗口，原已排队任务的结论另存，不叠加计算。

`WorldApplyConfirmation` 随文档、原点、投影变换和 includeAir 一起冻结确认时维度。已发布投影与未发布草稿均在接受确认时重新读取当前维度。维度事件只永久作废相应写入确认，其他确认保留；即使回到原维度，native 队列中保留的旧确认 callback 也继续无效。

未完成的 `ProjectionPreparation` 每次 advance 在准备或发送首包前核对冻结维度。check／apply 新请求带 `expectedDimension`，服务端在创建 Receiver／执行世界写入前核对首包，并在上传完成入口再核对同一冻结字段。后续包不能替换首包字段。显式值必须严格为 int，比较时等于 0 的 bool／字符串／float 仍拒绝；旧请求省略字段时保留原传输兼容。正常原生维度及自定义维度均按声明维度写入。

check 请求状态另包含投影变换和当前维度，迟到终包不恢复旧 progress；从建筑库载入新文档时 `Session._loaded` 清除旧 progress。

## 五处维度查询失败

在 a4 产品源实际注入五个 GetCurrentDimension RuntimeError 点：确认构造、接受确认、start 预检、分帧 Preparation、check done 当前状态比较。前四者中 Preparation 已有捕获；其余四处会向外逃逸。原五例均未写入，也没有观察到卡忙，不能把异常逃逸夸写成原先已经卡忙。

dcf 新增 `current_dimension(bridge)`，只将这个原生维度查询的 RuntimeError 转为带 `error_text` 原始详情的中文 ValueError；TypeError／ValueError 继续沿原语义处理。receive 在 check 状态比较处局部捕获 ValueError／TypeError，保持先释放 pending／busy 的时序。修复后五处均无逃逸、中文原因可读、无 recorder 写入，且 pending／busy、确认、服务端 jobs／uploads 均已释放。

覆盖仅限上述五个查询边界，不代表全部 SDK 调用已处理。现有 `dimension_changed` 中 loaded-chunk 查询不在这五点声明内；原 F11 与开始时一次授权语义不变，没有新增逐格权限查询或回滚。

## 实际回归与计数

最终 `query-v2-merged-focused-result.json` 和原始日志记录 `Ran 23 tests in 0.213s / OK`：

| 选定组 | 数量 | 主要覆盖 |
| --- | ---: | --- |
| `test_projection_dimension_r29` | 16 | 已发布／未发布的事件取消、accept 原生复查、同维度正常写入，未完成 Preparation、首包竞争、迟到 check、无关确认、库载入清进度，以及五处查询故障 |
| `test_world_request_dimension_r29.WorldRequestDimensionTests` | 6 | 首包创建 Receiver 前拒绝及下一请求恢复、完成入口冻结维度、后包不可替换、legacy 省略兼容、显式类型拒绝、原生／自定义维度正常写入 |
| 既有冻结确认回归 | 1 | 确认前冻结 document／origin／operations／includeAir |

真实 CPython 2.7.13 与 3.13.13 直接导入最终主仓产品函数，各跑 14 正常控制及 5 query 故障控制，合计每种 19 项。两个解释器结果与产品源 SHA 一致；正常控制包含保留旧 callback 后维度往返、首包拒绝后同 host 下一请求恢复、正常 check、迟到 check 等。相对原正常基线，只允许 `late_check_reply.message` 从“草稿或原点已改变，请重新读取或检查”改为“草稿、原点、投影变换或维度已改变，请重新检查”，其余记录字段相同。

这些对照以纯内存 SDK recorder 连接真实生产客户端上传与服务端处理。没有 MC 实例、RPC、GUI、窗口／键鼠、原生世界写入、GPU、真实事件时序或人工确认。本次证据整理不重跑测试，不将其他 CPU 总表、旧 21 生命周期矩阵、旧 280 床组合授予本专项。

## 失败记录和持久来源

[精简证据索引](../evidence/world-dimension-r29-v1/index.json) 保存原 37 件、V2 16 件、两个原索引，另附当前四产品和六个相关测试／fixture 源及打包程序。输入原字节、raw SHA 与压缩 storage SHA 均可核验，确定性 gzip 按 raw SHA 去重；[独立回读](../evidence/world-dimension-r29-v1/verification.json) 记录新进程解压复核、原索引和全部原输入未变、当前源码绑定及局部凭据扫描。没有遍历打包全部历史 runtime。

保留的失败和计数边界为：

- `candidate-network-gap.json` 是客户端单独修复后仍在维度 1 写入的一条真实失败；早期客户端 10 条通过明确排除了该首包测试，不能算已解决服务端窗口。
- `pre-query-fix-*` 保留原 14 正常控制与五处 query 故障，其中四处 RuntimeError 逃逸；最终结果不覆盖这些原件。
- `preliminary22-*` 导入旧测试类导致五条重复，仅作历史记录；修正后的早期 17 条与最终 23 条不累计成新覆盖。
- `baseline-observations.json` 实际有 9 条 observation，旧 README 叙述“10 定点、7 失败／3 正常”与原 JSON 数量不符，原字节均保留；不补造缺失记录。`candidate-observations.json` 实际 8 条，也不与 10 条测试结果混用。
- `py27-*-driver-preparation-error*.json` 属于驱动编码／compile 包装准备错误，保留供复查，不当作产品回归。
- 原 `archive-index.json` 的 `pending_main_change` 与原 README 的“候选尚未合入”是历史状态；当前状态以 V2 最终比较及 dcf 提交绑定为准。

最终比较绑定的四个产品 raw SHA-256 如下；当前测试快照与提交内容的绑定另见索引，保留实际 CRLF 字节。

| 产品源 | raw SHA-256 |
| --- | --- |
| `projection_target.py` | `b66e0da700b350fb603eeededf9a53dc5445cae124d7bbb0010d577f24f059e4` |
| `bridge.py` | `ca5264b1fc4597e99ae664b02035f45a7f25fdbc459e04bd09bb0d72b5fcb942` |
| `session.py` | `b114cd99e2429bdfa1e017e1ed1e6db4fd7a18ede10ba7b1c70d295142e47d15` |
| `server_system.py` | `bf52ce153f4e8f3dac1dd316d2313f8915b7dfb8d18bd2a7baed88e4bc506086` |

后续若产品源变化，应增量重新绑定来源后再用于原生验收。本包只支持已执行的 CPU 结论，不授予当前水、其他渲染或 native／manual 资格。
