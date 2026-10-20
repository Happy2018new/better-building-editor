# 延后 PNG 编码的 WGC 连续采集

这里保存已完成真实游戏验证的独立实现。七份编译输入逐字复制自本轮实际构建目录，旧 `tools/native_wgc` 保持原样。本轮的原始证据继续绑定实际使用的 `.runtime` 源码路径和二进制 SHA，不改写为本目录。

在 Windows x64、Visual Studio 2022 与 Windows SDK 环境构建：

```powershell
cmake -S tools/native_wgc_deferred -B .runtime/native_wgc_deferred/build -G "Visual Studio 17 2022" -A x64
cmake --build .runtime/native_wgc_deferred/build --config Release --target native_wgc_burst_capture
```

命令参数与原连续采集程序一致：

```text
native_wgc_burst_capture.exe HWND PID creation-time fresh-output-directory duration-ms max-frames max-gap-ms [--allow-user-foreground]
```

采样阶段每隔约 70 毫秒读取最新可用的合成器帧，保存独立、不可变的位图；结束 WGC 采样后才依次编码 PNG。每帧保留真实合成器 QPC 时间，采样和编码各自具有连续的窗口、进程身份、几何与可见性检查。不会激活或缩放窗口。用户手动前台观看需要显式许可，最小化与身份检查继续有效。

原始位图缓存上限为 448 MiB，另预留 64 MiB 编码空间，总计 512 MiB；同时最多保存 64 帧，单张原始位图上限为 16 MiB。容量不足、窗口保护失败或时间覆盖不足均不能返回成功。位图通过 RAII 在正常、失败和提前退出时释放。清单中的 `peak_accounted_buffer_bytes` 是位图与预留空间的核算值，不是整个进程的内存采样。

清单使用 `encoding_policy="deferred_after_capture_v1"`，后台模式 schema 为 3，允许用户前台观看时为 4。`capture_span_100ns` 与 `total_span_100ns` 分别记录采样阶段和包含后续编码的总时间。独立 Python 重放入口为 `tools/capture_native_burst_deferred.py`，由 `tools/capture_native_burst.py` 显式分派；旧 schema 的验证规则保持严格。

本轮 A-v3 实测三条渲染路径共 15 段、631 帧，最大间隔 109.0818 毫秒，核算缓存峰值 450269824 字节；15 项流向检查及 15 项反转时间负对照通过。实际使用的二进制 SHA 为 `83f7f7a26b966cb64e1910b915ae4b6f9dd8ded40cc6bd6eedac0d41a598c523`。从本目录重新构建后应重新计算并显式提供 SHA；构建路径、工具链等因素可能改变输出文件的哈希。

当前准入证据通过冻结的宿主包装脚本记录两个 reader、实际 native 编译输入与二进制的 SHA。通用 `_host_sources()` 对新版 native 源目录的显式选择将在最终冷启动验证后统一接入；此时不要把默认收集的旧 native 源目录当成新版编译输入的证明。
