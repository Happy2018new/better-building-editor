# R28：看护状态文件的并发读写

R28 的 ordinary-alpha A4 在启动看护脚本后、启动游戏前失败：消费者确认 `status.json` 存在后立即读取，但历史 V5 writer 会先截断公开路径，再写 JSON，读取到了不完整内容。此尝试没有启动 MC，也没有正式植物样本。原错误及看护进程的精确退休记录保留。

V6 先将写端改为同目录临时文件完整写入、flush／fsync／close 后再替换。真实 Windows 替换可能返回 Win32 5；仅在 `PermissionError.winerror` 为 5／32／33 时最多尝试五次，等待依次为 .05／.1／.2／.4 秒，合计 .75 秒，始终使用同一完整临时文件。V6 的前 12 个控制通过，但第 13 个并发控制在原 `Path.read_bytes` 读端出现未知 errno 13 后失败，只发布到 seq 2；原失败及未发布 temp 保留，不称 V6 全通过。

V7 保留上述完整发布，同时给公开 status 消费端接入 `94598a69` 已验证的 retained-handle reader。三个函数与该提交的源码逐文本一致：使用 read／write／delete 共享的同一 Win32 句柄读完全部 chunk；只重试真实 Win32 32／33，最多五次、总等待 .75 秒。Win5、缺少原生码的 errno 13、JSON／UTF-8 错误立即失败；owner、身份、来源和新鲜度检查仍在读取之后执行，没有旧值回退。

V7 的九项定点控制实际通过，包含旧截断 writer 的 JSON 错误负控、真实独占句柄、持久失败上限、未知错误即时失败和多 chunk 并发。原执行完成 100 次原子发布及 6074 次原生读取；root 用原控制脚本独立重放，仅改变输出目录，完成 100 次发布及 4857 次读取。两次都读取完整 131074 字符 payload、观察到 seq 0 和 100，无读写错误。V7 watcher 相比 V5 只有 import 和 status 发布调用两处变化，撤销两处后完整 AST 相等；native session reader 未改。

root 的首次 AST 归一脚本错误地假定历史变量叫 `state`、编码为 utf8，因而在运行控制前失败；读回历史源码后改为实际 `status`／ascii，才通过上述比较。该宿主核验失误保留在 root 回执中，与 V6 的实际并发失败分列。

离线封印目录为 `.runtime/round-20261023/water-anchor-watcher-v7/`，索引 SHA256 为 `5d8df77dd69d3a5057e1995e46ccabb9ba2c1a1f6b3f9ea6e4ee3193e7d7b949`，列出 26 个对象。启动入口及运行中的每一个公开 status 消费点都必须使用该 reader；只修改首启不能解决周期发布时的同类冲突。此结果没有启动看护或 MC，不替代后续实机检查。

仓库常用 `tools/watch_owned_disabled_skin_assert_r20.py` 也接回共享 `_session.read_json` 与 `write_json`，用于 registry 读取和完整 status 发布；共享 writer 的原策略为 Win5／32／33 五次有界替换，它与 V7 的 fsync writer 分别记录，不混称相同字节。已运行该工具的 11 项定点测试，包括真实 Windows registry 临时独占锁、原子发布前的完整 JSON 及损坏 manifest 继续记录错误。此前共享 session／IPC／执行预检共 38 项通过；本次未改这些共享实现，也未重跑或扩大此前 3485 项整合回归的来源资格。

所有旧 owner、已封印源码及首次失败保持；新检查另用新 owner 和绑定。没有自动重放 RPC、重复启动游戏、忽略其他断言或新增人工关闭问题。
