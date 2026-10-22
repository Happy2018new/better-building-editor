# R28：T02 冻结接口修正与 Y+4 实验前资源门拒绝

2026-10-22 23:47—23:51，北京时间。此次新 owner `r28-button-shift-v2` 的正常冷启动就绪，但独立 `before` 审计在可用 commit 必须不少于 6 GiB 的条件处停止，尚未发出该审计的游戏 RPC，也未调用诊断 host。**实际诊断模型创建 0 次、Y+4 阶段 0 个、位移原图 0 张。** 未降低门槛、未重放。本次不能提供 occupied-bounds、depth 或按钮贴面的新实机结论，T02 仍保持开放，新增人工关闭 0。

前轮的 261 个低对比差异像素、四组双 Doll 一致性及失败记录继续以 [R27 原记录](BUTTON_PAIR_R27.md)为准。不得把此次资源拒绝写成字段问题复现，也不得把私有宿主离线修正写成产品修复。

## 私有诊断已修正的内容

产品继续使用精确冻结 `2ab5a29a21f68bac607637b10d4afb42ac9caaa6` 的既有副本；3710 个 runtime 文件、781 个 host 文件及 `.mcdev.json` 均未写入。新 source manifest SHA-256 为 `87b9e3956b48e8709f115c152b6d4d84d7afadd57df9d3c0aa90a996f494d720`。

新校准读取实际 `GetScreenSize()` 二元 tuple、`GetScreenViewInfo()` 四元 tuple，再使用冻结 `Theme.configure` 的同一 GUI 公式。它不再依赖冻结旧版不存在的 `Theme.native_gui_scale`。仍读取挂载 Scene 的既有相机缓存、UI/scissor 和实际 WGC 原件元数据，不把这些 CPU/UI 读数称为 GPU 矩阵或 GPU scissor 读回。

真 Python 2.7／Python 3 的离线控制从冻结 `widgets.py` 原字节提取完整 Theme 类，保持缓存字段不存在并实际调用 configure；GUI 1／2／3／4 和七种错误 API 形状均已执行。旧 reader 在同一真实形状的 Theme 上准确重现缺失字段错误。每版原合同 43 个负控、capture binder 18 个负控、新 schema 26 个负控、五种 host finally 边界及 47 份生成 RPC 的真 Python 2 编译通过。另有原 decoder 六个正控／六个旧裸字符串负控，以及来源绑定 23 个负控。这些全部为离线控制，无原生模型或像素资格。

最初旧 reader 的 Python 2 重放控制使用另一类的未绑定方法，先触发 TypeError；仅修正控制调用为原 `im_func` 后才取得缺失字段复现。原失败不影响产品，不能用修正后的控制覆盖真实 R27 失败。

## 资源门、退出和证据边界

| 读取位置 | Commit total | Commit limit | 可用 commit |
| --- | ---: | ---: | ---: |
| 23:47:30 启动前原记录 | 37,536,247,808 B | 46,100,955,136 B | 8,564,707,328 B |
| 关闭后独立读取 | 28,601,954,304 B | 46,100,955,136 B | 17,499,000,832 B |

`before` 的代码先计算内存再 assert，拒绝发生在写 `face-restore-before.json` 之前，因此没有保留该时点的具体数值；只能证明它低于 6,442,450,944 B，不能用关闭后的数值补造。两端 limit 相同，不能据此声称发生页文件扩容。

普通 owned stop 已完成。原持有句柄记录 game PID `30696`／creation identity `134371576592288754` 的退出为 `3221226505 / 0xC0000409`，MCDK PID `29848`／identity `134371576590319113` 为 0；独立读取两身份均已不存活。专属 watcher PID `36060`／identity `134371576393478392` 精确回收，原句柄 exit 0。没有 force game，正常引擎退出资格仍为 false。

冷启动回执另有 `foreground_unchanged=false` 和 `foreground_before_still_valid=false`，没有执行 Windows 输入，也不授启动前台保持资格。此次没有诊断采图，不把它包装成 WGC 通过或失败。

原件留在 `.runtime/round-20261023/button-shift-lifecycle-v2/`：`launch/report.json`、`audit-before-stderr.txt`、`sequence-receipt.json`、`stop/report.json`、`assert-watch-close.json`、`owned-release-verification.json` 和 `memory-boundary-comparison.json`。私有源码及控制在相邻 `button-shift-diagnostic-v2/`。后续只有资源条件实质改变且重新绑定 owner 后，才可能另做一次窄验证；当前未安排重试，先交付周末可用的变换代表。

[精简原件索引](../evidence/button-shift-resource-r28-v2/index.json)仅保留资源拒绝 stderr、两端内存记录、精确释放／退出、冻结接口控制回执和客户端 reader 窄差异。八份 payload 共 7,696 B，逐件重新打开核对 SHA-256 与本地原件字节；不包含世界、会话配置或大 manifest，也不把离线控制升级为实机结果。
