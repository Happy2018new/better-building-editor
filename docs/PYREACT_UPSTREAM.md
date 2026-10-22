# PyreactMC 上游同步（2026-09-20）

本项目使用 PyreactMC 客户端 UI 框架。

本次从原导入基准 `5fe33a3` 更新到 [9580d0123584ae8b4b4b3a7b0357250e151c54cd](https://github.com/EnderWolf006/PyreactMC/commit/9580d0123584ae8b4b4b3a7b0357250e151c54cd)。框架以 vendored 文件集成，采用三方内容合并，没有把上游独立仓库的历史合并到模组主线。

## 合入内容

- 状态 setter 保持稳定；父组件先于子组件更新，同一轮已更新的子组件不重复渲染；渲染期间设置的状态保留到下一轮。
- 卸载移除待处理更新，副作用清理不重复执行；根节点重新挂载、失败回滚及动态输入/滑块回调清理。
- Primitive 引用变更、显式 key 与位置 key 的区分、中文文本、被移除的原生属性恢复默认值。
- 隐藏节点停止量测，支持原生控件作为布局根，修正变换缓存与透明度；SafeArea 与 Modal 随窗口尺寸更新。
- 列表不再修改调用者传入的 Element，保留多元素列表项；动画时长等数值拒绝 NaN/Infinity。
- 同步两个技能的上游文档、MCDK 工具与 v1.1 `LICENSE` / `NOTICE` 原文。发布作品详情时的归属文字要求见 `NOTICE`；许可文件位于框架目录，不表示整个模组采用该许可。

## 保留的项目补丁

运行时 `debug.py`、`reconciler.py`、`renderer.py`、`native.py` 含本地差异，详见打包目录中的 `behavior_pack/modern_projection/pyreact/UPSTREAM.md`。没有覆盖业务 UI、输入模板、字体或模型渲染器。

同步后的原生点击回归另见 `DEVELOPMENT.md` 阶段 35：控件名称在 Unicode key 净化后转换为 ASCII `str`，避免网易 Python 2 SDK 克隆容器时只正确显示、不接收其内部按钮的鼠标事件。普通 `click` 诊断直接调用 Python 回调，不能代替真实原生点击验证。

上游新增的组件 ID 现在也能通过 `find_fiber_by_id` 反查。上游默认 MCDK 桥接只认识通用控件命令，本项目补充转发原来的有界诊断，便于继续检查原生光标、网格和指针状态。

## 调试环境迁移

已安装官方 MCDevTool v1.6.1，由上游安装脚本校验固定 SHA-256，保存在用户目录 `.pyreact-debug/tools/mcdk/v1.6.1`。它与本项目原有的 `tools/mcdk.py`（mcdk-assistant 知识工具）用途不同。无需修改 PATH 或全局 MCP 配置。

本机已创建被 Git 忽略的 `.mcdev.json`，指定现有开发游戏路径、项目包与热更新选项。其他机器需按技能的首次安装流程选择其游戏路径，不会从 Git 取得本机绝对路径。

启动与诊断以 `.agents/skills/pyreact-debugging/SKILL.md` 为准。开发游戏使用本机原有的 `3.9.0.401155`；示例中的 `GAME_EXE` 换成实际路径：

```powershell
$scripts = '.agents/skills/pyreact-debugging/scripts'
$instance = python -X utf8 "$scripts/instances.py" start --project . --owner editor-check --game-exe GAME_EXE --preset ui | ConvertFrom-Json
python -X utf8 "$scripts/instances.py" exec --session $instance.session_file --owner editor-check -- diagnostics.py --pyreact
python -X utf8 tools/run_live_check.py --session $instance.session_file --owner editor-check verify_layout.py --large
```

`run_live_check.py` 校验项目、owner、两个进程的创建时间，再为既有回归绑定 MCP 和窗口 PID；真实桌面操作持有与上游相同的锁。子进程 resize 仅在持锁父进程的身份仍有效时复用该锁，避免自锁。请求超时不重放编辑操作；MCDK 的树回复也不再需要额外写剪贴板 ping。

上游启动器在本机重定向 AppData 下移动包含目录联接的世界失败。已改为先移动生成世界，再在目标世界下创建资源包联接，避免跨文件系统回退复制时遍历整个资源包。不会覆盖已有同名世界。

原回归仍使用的三个旧工具移到 `tools/pyreact_legacy/`，普通通信已走 MCDK。剪贴板动画采样是历史兼容入口，不适用于多游戏实例。历史文档中的旧 `--port`、日志服务器等启动命令已被新技能流程取代。

## 验证

- `python -X utf8 -m unittest discover -s tests`：146 项通过，其中新增 9 项框架合并回归。
- `verify_editor_depth.py`：12 项通过，覆盖真实鼠标框选/悬停、进入封闭体、内部方块编辑与撤销、复位中间动画与跨页保持。
- `verify_layout.py --large`：20:9、4:3、16:10、16:9 共 60 项通过，覆盖列布局、展开/还原、裁剪、模型原点与拾取。
- `verify_rapid_placement.py .1 64,128,64`：最大尺寸下 40 次真实鼠标放置全部完成，点击阶段约 4.16 秒；跨分块、最终选中格及独立撤销共 3 项断言通过。此为当前场景结果，没有本次升级前的同环境性能对照。
- `verify_input_caret.py pyreact_upstream_caret --require-visible`：8 项通过，包括原生占位控件、焦点/失焦背景和文字、真实键盘与光标。多帧检测到 22 像素光标，对比度 9.66:1；截图已实际查看。
- 在游戏 Python 2.7.13 中编译全部 23 个框架源码文件：无语法错误。宿主调试工具的 Python 3 编译检查通过；框架保留 Python 2 原有语法，不以宿主 Python 3 编译结果判断兼容性。
- 最终独立原生断言窗口检查为空；工作台与多帧光标截图已实际查看。启动日志在 AppReady 之前存在引擎自身 `user_mgr` 初始化异常，UI 就绪之后未发现新增框架 traceback 或控件名称解析错误。

实机使用新建的独立测试世界和未保存草稿，不写玩家世界方块或保存/删除建筑库。第一次框选检查受源码热更新影响而中断，重新打开界面后 12 项完整重测通过；不把中断轮次计为通过。启动器首次目录联接失败也已修复并验证新实例正常进入世界。

原生界面与键鼠测试仅代表 Windows 网易开发游戏，不代表 Android/iOS 触摸硬件验证；本次回归不意味着之前记录的大尺寸短按、长文本末尾光标等边界问题已经解决。

## 后续更新

1. 获取上游新提交，以本文件记录的完整 SHA 为旧基准比较。
2. 映射 `pyreact/` 到 `behavior_pack/modern_projection/pyreact/`，`jsonui/PyreactBase.json` 到资源包 UI；技能路径保持不变。
3. 三方合并 `UPSTREAM.md` 列出的运行时补丁，以及本地技能中的 `projection.md`、MCDK 诊断桥接、实例启动与回归桌面锁补充。
4. 检查许可与配套工具的删除/迁移，运行单元测试和实机回归，再更新 SHA、验证记录并提交。

## 滚动控件兼容补丁（2026-09-22 修正）

`ScrollViewPrimitive._get_scroll_view` 优先从模板根创建 SDK 包装对象，并用非空 `GetScrollViewContentPath()` 验证后缓存。SDK 内部自己拼接 touch/mouse 子路径；阶段 51 改为对内部 `scroll_view` 转换后，路径重复，造成读回零和写入无效。不能恢复该错误优化。百分比 setter 传入限制在 0–100 的整数；缓存依附当前控件，重挂载失效，没有新增对外 props。实机验证需检查内容真实位置，不能仅检查 asScrollView 返回非空。

## 实例清单原子替换补丁（2026-10-21）

牡丹入口冷启动时，MCDK 与游戏已创建，但保存进程绑定的 `os.replace(..., session.json)` 返回 `WinError 5`，造成启动器抛错而清单尚未记下新 PID。该失败轮次保留；先用生成配置、父进程和创建时间核对两个进程，再恢复仅供清理的清单、普通关闭并确认退出，未将半启动状态标为 ready。

本地 `_session.write_json` 现在只重试同一个已完整写入的 UUID 临时文件的原子替换。仅 Windows `PermissionError.winerror` 为 5、32、33 时允许最多 5 次尝试，间隔为 0.05、0.1、0.2、0.4 秒，共 0.75 秒；每次可重试失败均记录 warning。不会重放调用方或再次创建进程。其他权限错误立即抛出，最终仍失败时保留旧清单与包含新绑定的完整临时文件，供明确身份后的恢复使用。

`tests/test_mcdk_session_atomic_write.py` 的 4 项回归通过：同一完整写入的临时共享失败、达到上限后保留恢复信息、无关权限错误不重试，以及真实 Windows `CreateFileW` 读者未开放 `FILE_SHARE_DELETE`、解除占用后替换成功。真实共享测试证明这种 OS 条件能触发并解除失败；未证明原启动时的占用者身份。原始冻结 host 不追改，后续冷启动使用独立 retry-host 版本并另记 helper SHA。本补丁只属于宿主实例工具，不更改游戏业务或 Pyreact 运行时。

## 实例清单读取补丁（2026-10-23，R28）

末地 GUI 诊断的冻结启动监督器直接读取已分配 `session.json` 时发生 `PermissionError(errno=13)`，尚未进入实际采样。原异常没有 Win32 错误码，不能追认为已证实的共享冲突；该轮失败、恢复及异常引擎退出记录继续保留。本补丁不追改它的冻结文件，也不改变游戏渲染或水的 39 份来源合同。

本地 `_session.read_json` 在 Windows 使用 `CreateFileW`，开放 read／write／delete sharing，并始终通过同一个 retained handle 读完各个 64 KiB 数据块；`load_session` 改用该入口。原生 API 保留真实 Win32 失败码，只有读操作的 **32（共享冲突）和 33（锁冲突）**允许最多五次尝试，四次间隔合计 0.75 秒。每次可重试失败记录 warning；5（拒绝访问）、没有原生码的 errno13、其他 OS 错误、JSON／UTF-8 内容错误均立即失败。schema、清单路径、owner、ready 状态和实际进程创建身份验证仍在读取后执行，不重试验证，不使用旧清单，不重放启动或游戏 RPC。

真实 Windows 测试额外确认了一项限制：即使 reader 开放 `FILE_SHARE_DELETE`，本机 `os.replace(new, open_target)` 仍会返回 WinError5。因此没有承诺开放共享就保证替换成功，既有写端有界重试继续保留。首个过强的替换测试失败后，分别验证了共享打开的旧文件可 rename-away、在原路径发布新文件后当前 handle 仍完整读到旧快照，以及真实并发 `write_json` 在 reader 关闭后完成原子替换。读取内容不会混合两版；下一次读取看到新版本。

新增 `tests/test_mcdk_session_read.py` 九项测试覆盖真实共享／字节锁的 32／33、解除锁后的恢复、持续冲突上限、未知权限码和内容错误不重试、owner／schema／路径／状态／进程身份不放宽、UTF-8 大文件跨块读取，以及上述两种文件替换时序。连同旧写端、IPC 和执行前身份守门，`python -B -X utf8 -m unittest discover -s tests -p test_mcdk*.py -v` 本次实际运行 **38 项，全部通过**。这些是宿主文件／协议测试，不是新的 MC 画面或正常引擎退出资格；尚未替换其他历史监督器中各自直接读取 JSON 的代码。
