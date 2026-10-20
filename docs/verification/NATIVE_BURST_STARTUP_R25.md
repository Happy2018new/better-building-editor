# R25：固定准备阶段的独立 WGC 连续采集协议

2026-10-21。新增 `fixed_startup_preparation_v2`／`persistent_burst_fixed_startup_v2`，供水的完整 3200ms 连续测量使用。它是显式选择的新宿主协议，不修改产品渲染，不覆盖旧 pinned helper、旧来源合同或失败报告，也不把旧测量重新标记为通过。

## 固定时间与取证范围

单个 WGC session 在 `StartCapture` 前就固定准备开始、1450ms 取帧截止、1500ms 测量开始及完整 3200ms 测量结束。最后 50ms 只检查窗口，不再取准备帧。测量仍按原时间轴检查起始、内部和尾部最大 150ms 缺口，保留原帧新鲜度、帧数与全部原始测量 PNG；没有稳定后择窗、移动起点或补时。

准备阶段记录全部取帧调用，包括空调用、调用前后 QPC、原始 source／initial observed、帧序号。调用跨过固定截止即失败，原始调用仍保留。预测显示时间晚于首次观测的准备帧，复用原 50ms 有界 future-wait，额外受固定测量起点限制；保留每次窗口检查及最终 observed，只有 `source <= final observed` 才能读回。独立 reader 核对调用和帧的一一对应、完整等待记录与尾部 chronology，不接受缺失的中间证据。

准备帧只保留首尾原生 PNG，所有被选择帧的元数据均保留。首尾位图、临时替换位图和测量位图共同计入原 448MiB raw 上限，另保留原 64MiB encoder 预算，总上限仍为 512MiB。重放会重新核对首尾及全部测量 PNG 的字节、尺寸、哈希和文件清单。

## 实现与验证

入口为 `tools/capture_native_burst.py`，新增独立 reader `capture_native_burst_startup.py` 和 `tools/native_wgc/startup/` 原生 target。旧 deferred reader 默认仍只接受旧 mode；新 mode 由显式 protocol 分派，并调用原测量 reader 验证完整测量区间。新增准备 PNG 纳入最终绑定哈希，flow analyzer 重放也会检测准备 PNG 被修改。

根代理审查阶段解析及原生循环，按候选 SHA 备份／应用 8 文件，逐项确认应用后的完整字节与冻结候选一致。Windows 行尾令原补丁直接检查失败；开启 context whitespace 容忍后，先核对规范化全文，再恢复精确候选字节，未以行尾转换修改已冻结合同。

主仓独立运行 `test_capture_native_burst*.py`：**84 项／56.855 秒／全部通过**。覆盖未知 mode／protocol、阶段移动、缺失元数据／poll／guard、仍属 future 的帧、超过 50ms 的等待、NOACTIVATE 丢失、缺失／篡改 PNG、原始 160ms 内部与 720ms 尾部缺口、缩短完整区间及 combined raw 超限等负控。原生 Release 构建通过，根代理另核实际 binary SHA256 `1bf5d8db04b339042751e4bbd954786292efd21115cd4c07e6d8d84fa530a155` 并执行 `--help`。binary 不加入 Git。

根代理最初在私有候选目录独立运行时，因该目录未冻结 `_session` 依赖而发生三个 import 失败；随后在已应用的主仓完整依赖环境运行上述 84 项。代理首轮的 combined-raw 负控也曾先触发单帧 16MiB 门，修正负控数据后才通过预期总量门。原失败及新结果均位于 `.runtime/round-20261021/water-startup-protocol-v2/`，没有把这些失败计作测试通过。

## 旧失败与因果边界

旧 A-v3 的 673.953ms 尾部缺口及 A-v4 的 1218.1806ms source 缺口保留。v1 准备协议没有接入主仓；它的第三次采集取到跨阶段的预测时间帧而失败，原始报告及独立恢复／关闭保留。v1 某次准备阶段另记录 490.9021ms source 缺口，后续完整测量最大缺口 96.9657ms；这仅说明那个准备区间确实有间断，不能证明旧缺帧的根因或产品渲染修复。

v2 正式 A 必须重新采集原定五场景 × 三路径，并由不变的方向分析器复核。协议和宿主回归通过不等于水外观、连续动画或当前产品资格通过；新报告和最终集成 D 的结果由水专项另行登记。旧 helper、旧报告、旧资格哈希保持不变。
