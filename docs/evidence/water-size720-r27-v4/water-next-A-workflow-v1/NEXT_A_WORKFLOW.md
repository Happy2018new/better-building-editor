# 下一正式水动画 A 的离线准备

本目录没有启动 Minecraft，也没有修改 shared source、owner、qualification、原 plan、原 manifest 或原帧。当前工作仅提供可复核的来源 inventory 和时间链读取。静态 26 图不提供动画 A 或默认入口资格。

## 当前可用材料与边界

- `merged-input-inventory-v2.json`：source 4482 项、auxiliary 1391 项，SHA `7bdfd5e2322fd9b800a343408f9fa40a5bfcf61eb9c345b8a44d4dee7a747485`，显式 source 合同 `027f11186bb5e50b4d9a0dc80a5ba4d06342104e1be4c2cc6de51a9f206bcf1a`。这是读取时 shared 的逐项来源枚举，`is_complete_transitive_dependency_closure=false`。
- inventory 记录的 HEAD 为 `543f3cf305a6746451ec8fb251d230b2202af6dc`；root 后续合流、提交或改动后必须生成新 inventory，不改写本份。内容 SHA 相同也不代表最终 host/plan 已冻结。
- `freeze_inputs_v2.py` 复用实际 probe 的 `snapshot_sources` 和摘要计算，读取前后核对 source/auxiliary/owner/qualification；初版缺少 tools 导入路径的失败脚本保留。
- 原 host binding 为 `water-startup-protocol-v2/host-contract-v1.json`。动态导入、绝对路径、exe 与 host source 必须按下一组实际使用值重冻，不能仅复制旧 host SHA。
- sibling renderer 的 `snapshot_manifest.json` 与 `docs/SOURCE_INVENTORY.md` 只是 metadata 参考。renderer `ca10356` 属于 sibling 仓库，当前主仓未依赖该库；`actual_runtime_dependency=false`，不得把该 metadata 当作运行期闭包。

## 原 nontrace 时间链

`inspect_timeline.py` 只读取原 manifest，区分 source QPC、worker before、readback 与 capture guard。未记录的 readback 为 null，不能把 raw 的 0 变成实际观测。`test_timeline.py` 的五项 synthetic controls 覆盖不同最大 pair、missing readback、invalid attempt、固定头尾与空序列。

原 manifest SHA `b0c07c94bd3347fd26bae806f7295a532ee4823f63920162fdcddf14e945c232`；37 attempts、36 valid，request QPC `3112494919037`，固定终点 `3112526919037`，测量全长 3200 ms，首尾 gap 分别 17.7829/30.7163 ms。native `capture_valid=true`、`temporal_complete=false`、`ok=false`，不得与上层 wrapper 的拒绝状态混写。

- 最大 source gap 为 #28→#29 的 593.9861 ms；同 pair worker before gap 82.4377 ms，前 guard→后 before 79.7914 ms。
- 最大 worker 未观察间隔为 #27→#28 的 538.3221 ms；worker before gap 540.4115 ms，同 pair source gap仅 42.421 ms。
- #28 source 在 poll 时 age 532.802 ms，虽未越过原单帧 1000 ms age 门，仍不能豁免完整 source gap 门。

以上两种 maxima 不在同一 pair。nontrace 没有 empty-poll、callback arrival、Close 或 COM release 的实际事件，不能归因为 game、DWM、WGC 或 driver。trace 的调度与结果不同，不能回授 nontrace A。

## 下一次实机之前

1. 等 root 完成生产合流，再从实际 shared 生成新的私有 source、manifest、archive 与唯一 owner；不复用旧 qualified owner，不手算或复制旧 qualification。
2. 枚举并冻结实际 source/auxiliary，另核 host 的 imports、绝对路径、exe 和实际加载来源；显式记录尚未证明的传递依赖。计划、来源与 host 都在启动前独审，之后不得改写。
3. 真实默认冷启继续走原资格拒绝链。显式诊断 bootstrap 不提供默认生产入口资格，静态 Scene 的 26 图不提供动画资格。
4. 先修正采集时间链可观测性，或提交能解释原 gap 的独立证据；不要在原条件下反复重跑。若增加 instrumentation，明确其扰动与 nontrace 的区别。
5. 正式 A 原矩阵仍须完整覆盖 15 cells，不删失败 cell、不裁掉首尾、不从 burst 中挑有利片段。准备 1500 ms、测量 3200 ms、最大 source gap 150 ms、总量 512 MiB、有效可用 commit 6 GiB、句柄与相邻增长门保持原值。
6. 核对 active Scene geometry、同 GUI 缓存、source/host/plan 前后 SHA、资源 guards、完整恢复与精确 PID/创建身份退出。stop 返回 0 与实际 game exit code 分列。
7. 由 root 统一安排新 MC；本专项目前没有运行中 MC，也没有新启动授权。07:30 不开长实验、07:45 收尾、07:55 向 root 交付；08:00 休眠仅由 root 执行。

原 GUI2 front 矩阵因子 ratio 1.190508、全图 debug mask 污染、nontrace 593.9861 ms source gap 继续保留。不得调 geometry/phase/FOV/ROI 或量化门制造通过。自定义水仍无原生 fallback，新增用户人工关闭为 0。
