# 旧回归工具兼容层

这些工具来自 PyreactMC `5fe33a3`，上游 `9580d01` 已迁移到 MCDK。
许可及归属见 `../../behavior_pack/modern_projection/pyreact/LICENSE` 与 `NOTICE`。

- `capture_screen.py`：原有回归使用的 Win32 截图、窗口与真实输入辅助函数。绑定实例时强制匹配 `MCDEV_GAME_PID` 和 `Minecraft.Windows.exe`。
- `tracy.py`：历史性能脚本的 CLI，继续复用原来已安装并校验的二进制目录。新性能调查使用 MCDK `mc_profiler`。
- `clipboard_ipc.py`：仅供旧 `verify_motion.py` 的短间隔动画采样。剪贴板不能隔离多个游戏实例；运行该历史脚本前必须确保只有一个启用 Pyreact 调试的游戏。普通项目回归已走 MCDK。

本目录不是默认的 Pyreact 调试通道。使用 `tools/run_live_check.py` 绑定 session 运行项目回归；上游技能脚本使用 `instances.py exec`。
