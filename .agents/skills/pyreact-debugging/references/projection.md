# 现代化投影：本地诊断与兼容回归

这是本项目扩展；不是上游通用 API。MCDK 与游戏内保留的剪贴板通道共用相同的有界诊断处理函数。

- 自定义指针 Primitive 可通过 `_protocol.request('pointer', node_id=ID, value={'phase': 'down|move|up|cancel|enter|leave', 'x': X, 'y': Y})` 调试；坐标为相对该原生控件左上角的 UI 单位，调用正式 `onDown/onMove/onUp/onCancel/onEnter/onLeave` 回调。拖动使用 down → 若干 move → up；与 Win32 实际鼠标输入测试配合验证绑定。
- 指针请求可加 `touch: true`，模拟触控操作方式（例如轻触直接放置、拖动只旋转）。它仍是回调模拟，不能替代手机硬件的触摸事件测试。
- 开发客户端关闭 UI 后按 **F11** 切换原生触屏模拟，F12 无效。使用实例绑定的 MCDK `mc_input /key` 发送 scan code；本机 `keybd_event` 的虚拟功能键曾无效，不能只凭投递成功判断切换。`tools/native_input_mode.py` 读回 `IsTouchWithMouse()` 确认开关，在真正触点后再核对 `PlayerView.GetToggleOption(OptionId.INPUT_MODE) == InputMode.Touch`。进入或退出 F11 模拟时，INPUT_MODE 都可能保留上一次接触的模式，直至新输入才更新；因此 Windows 以模拟开关为准，手机依原生模式判定。`verify_native_touch.py` 必须在按住未松手时多次检查角度连续变化，只检查松手后有转动会漏报缺失 move 事件。
- `native_control` 额外返回原生 `visible`；Label 返回实际绘制的 `text`，可与逻辑 content 对比，检查字形贴图与原生文字叠加等重影问题。
- `native_control` 对本项目 Pointer 额外返回 `pointerPressed` 和 `pointerPolling`，可用真实鼠标检查快速点击、离开视口和页面切换后是否仍保留拖拽。`tools/verify_pointer_release.py` 覆盖这些路径；指针 debug 模拟回调不能替代原生鼠标绑定测试。
- `tools/verify_native_buttons.py` 根据原生按钮的位置发送真实鼠标点击，覆盖六向移动、右栏页签、坐标设置、选区边界加减和全选，并核对禁用边界与模型输入隔离。游戏 Python 2 中另检验控件名称及路径均为 `str`，防止 Unicode key 的容器能显示却无法点击。语义 `click` 直接调用回调，不能发现这种原生命中问题。
- Scene 线框通过 Image 的 key 区分：`edge0..11` 是蓝框，`cursor0..11` 是渐变框，`grid*` 是工作网格；蓝/彩用相同线宽。PC 已选内容用蓝框，鼠标候选用彩框；第一点已确定时只显示渐变长方体。触屏单格、第一点和完成的区域都用彩框，保持只有一个正式选区框。检查时按 key 筛选，不能取全部图片的最后 12 个。`verify_dual_outlines.py` 要求新实例且尚未点击模型，覆盖初次悬停、双框、待定长方体与实际渐变像素；触控项经 F11 发送真实原生输入并读回模式，finally 切回鼠标，不再 mock 输入查询。仍不代表 Android/iOS 硬件验证。
- 原生 `SetButtonTouchMoveCallback` 还要求 JSON 的 `is_handle_button_move_event: true`。现代化投影使用 `ModernProjection.pointer` 专用模板，由 `mp_pointer_tmpl` 注册，服务于三维视口和自定义滑条。普通按钮沿用原模板，避免无关 move 回调。未来同步模板时必须保留这个注册。
- 网易 3.9 原生 `SetLayer` 引发的界面刷新可打断正在按住的触屏 move/up 路由，改为下一帧刷新仍会中断；最大文档下仅赋值而不强制刷新也曾复现。方向指示器在约 11° 时首次改变深度层级，曾稳定复现“只能转一小段”。触屏按住时继续更新模型/轴坐标，方向指示器及预览分块的层级赋值和刷新均延至松手；拖动期间透明重叠部分沿用此前排序。`verify_native_touch.py` 覆盖普通和最大尺寸文档的持续往返拖动、按住暂停、松手、连续点击；勿只用短距离拖动或松手后的角度判定。`TouchEvent=6` 是 SDK 的触屏松手通知，丢失普通 up 时取消残留捕获，不补造点击；按 TouchId 隔离第二触点。
- `native_control` 对 Input 也返回 `GetEditText()` 的实际 `text`，可核对中文输入和受控值同步；`screenMetrics.logical` / `physical` 分别来自 `GetScreenSize()` / `GetScreenViewInfo()`，用于核对整数 GUI 字形倍率。后者是按 GUI 步长补齐的画布，原始宽度比值不能直接当作连续字体倍率。
- Input 的 `placeholderPresent` 核对继承结构中的 `place_holder_control`。即使占位文本为空，引擎仍引用该名称，覆盖原生子树时不能遗漏。原生 Assert 弹窗可能没有写入 Python 日志；`tools/check_native_dialogs.py` 单独枚举并读取断言窗口正文，`tools/verify_ui.py` 在调试请求前后执行此检查，不自动忽略弹窗。
- `debug_component` 仅调用目标组件显式提供的 `onDebug(value)`，没有任意代码执行能力。现代化投影 Scene 的 Panel 提供有界的草稿测试样例和状态读取（`projection/diagnostics.py`）；样例替换当前未保存草稿，不写入世界或建筑库。`tools/verify_selection_scope.py` 和 `tools/verify_exact_large_render.py` 使用此接口核对真实文档坐标和大范围预览。普通组件没有该回调时命令拒绝执行。
- 对继承 `common.text_edit_box` 的 Input，`native_control` 还返回内部 `clipper` / `displayText` 的全局位置和尺寸，可检查字号变大后文字行是否被垂直裁剪。
- `_protocol.request('input_font_scale', node_id=ID, value=1.0)` 仅用于原生输入框的字号对照，调用内部 Label 的 `SetTextFontSize`，接受 0.5–2.0。返回 `requested`，不伪装成字号读回；不改变字体。实验结束须重开工作台恢复应用字号。`python tools/verify_input_scale.py` 覆盖当前应用的自适应字号（常见窗口为 3 倍物理放大）、五种尺寸、原生键盘、光标及重开检查；保留用户输入法，不假定 A/B/C 按键必然输入英文。
- `_protocol.request('font_batch', value=False)` 调用客户端 `EnableFontBatchRender(False)`，用于字体合批对照实验；`True` 恢复 SDK 默认开启状态。只接受布尔值，返回 `requested` 表示已调用，SDK 无返回值及状态读取接口。该设置作用于整个客户端，实验必须在 finally 恢复 `True`；它不是字体或抗锯齿开关。可运行 `python tools/verify_input_font.py` 和 `--remount` 比较现有 / 重建输入框的同尺寸像素。输出位于 `.runtime`，不要把诊断截图当成 UI 资源。
- `_protocol.request('native_control', node_id=ID)` 只读原生控件的位置、全局位置和大小；Image 还返回旋转角、锚点及四角坐标，可核对逐帧命令式更新与 Pyreact 布局快照的差异。

## 旧回归辅助工具

`tools/pyreact_legacy/` 保留旧版截图/Win32 输入、Tracy 与动画采样剪贴板工具，供现有回归脚本使用；普通调试使用本 skill 的 MCDK 工作流。新实例下通过 `tools/run_live_check.py --session <file> --owner <owner> <工具名.py> [参数]` 运行项目回归，该入口校验实例、绑定 PID 并持有桌面锁。不要对用户的世界运行会保存建筑库或投影的 `verify_ui.py` 主函数。
