# 现代化投影：本地诊断与兼容回归

这是本项目扩展；不是上游通用 API。MCDK 与游戏内保留的剪贴板通道共用相同的有界诊断处理函数。

- 自定义指针 Primitive 可通过 `_protocol.request('pointer', node_id=ID, value={'phase': 'down|move|up|cancel|enter|leave', 'x': X, 'y': Y})` 调试；坐标为相对该原生控件左上角的 UI 单位，调用正式 `onDown/onMove/onUp/onCancel/onEnter/onLeave` 回调。拖动使用 down → 若干 move → up；与 Win32 实际鼠标输入测试配合验证绑定。
- 指针请求可加 `touch: true`，模拟触控操作方式（例如轻触直接放置、拖动只旋转）。它仍是回调模拟，不能替代手机硬件的触摸事件测试。
- 开发客户端关闭 UI 后按 **F11** 切换原生触屏模拟，F12 无效。使用实例绑定的 MCDK `mc_input /key` 发送 scan code；本机 `keybd_event` 的虚拟功能键曾无效，不能只凭投递成功判断切换。`tools/native_input_mode.py` 读回 `IsTouchWithMouse()` 确认开关，在真正触点后再核对 `PlayerView.GetToggleOption(OptionId.INPUT_MODE) == InputMode.Touch`。进入或退出 F11 模拟时，INPUT_MODE 都可能保留上一次接触的模式，直至新输入才更新；因此 Windows 以模拟开关为准，手机依原生模式判定。`verify_native_touch.py` 必须在按住未松手时多次检查角度连续变化，只检查松手后有转动会漏报缺失 move 事件。
- `native_control` 额外返回原生 `visible`；Label 返回实际绘制的 `text`，可与逻辑 content 对比，检查字形贴图与原生文字叠加等重影问题。
- `native_control` 对本项目 Pointer 额外返回 `pointerPressed` 和 `pointerPolling`，可用真实鼠标检查快速点击、离开视口和页面切换后是否仍保留拖拽。`tools/verify_pointer_release.py` 覆盖这些路径；指针 debug 模拟回调不能替代原生鼠标绑定测试。
- `tools/verify_native_buttons.py` 根据原生按钮的位置发送真实鼠标点击，覆盖六向移动、右栏页签、坐标设置、选区边界加减和全选，并核对禁用边界与模型输入隔离。游戏 Python 2 中另检验控件名称及路径均为 `str`，防止 Unicode key 的容器能显示却无法点击。语义 `click` 直接调用回调，不能发现这种原生命中问题。
- `tools/verify_materials_paste.py` 验证方块目录的原生 + 按钮、分类、选用、常用列表排序/移除、设置存取、完整粘贴预览及 F11 触屏确认；中文搜索文本使用 `set_input` 语义入口，不能当作手机中文输入法验证。`GetLoadBlocks` 只在服务端提供，客户端收到列表后分帧查询 `GetItemBasicInfo` 的本地化名称。新版本的拆分 ID（例如 red_concrete）可能代替旧 aux ID，检查物品数据时以实际点击格的 identifier/aux 为准。测试在 finally 恢复原常用列表和炫彩速度，不改世界方块或建筑库。
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

`tools/verify_catalogue_input.py` 使用真实点击和键盘覆盖目录、工具箱及 F11 模拟的搜索输入，采样快速输入/删除及等待过滤完成的聚焦底色，并检查中文原生文本注入、整数物理字号、弹窗阻挡底层导航和关闭后恢复输入。中文注入仍不是手机 IME 硬件验证。目录保留空格子的组件但隐藏其 Button；筛选可见格子时还需检查内部 Button，不能只按 JellyButton 的 key 统计。`tools/profile_catalogue.py` 在游戏线程测量界面提交耗时及 Clone 数，finally 恢复临时计时包装；不把 IPC 往返时间或截图 FPS 当作提交成本。

`tools/profile_editor_switches.py` 同样统计七种视图模式、批量工具及目录开关的提交耗时/Clone 数；`--baseline` 保存修改前记录。`verify_editor_switches.py` 用真实点击验证分类、工具和模式联动，检查空气的空心图标、目录开关的原生中间位置、重开复用输入框及重复框选起点清除。目录现在在工作台中保留隐藏控件，判断是否打开须使用过滤可见性的树；不要把原始 Fiber 中仍有 BlockInventory 判作未关闭。鼠标停在第一行工具处时不要只用 session.choose_group 来替代真实分类导航后立即点击同一坐标，优先按实际操作先点分类按钮，再点工具。

`tools/profile_workspace_open.py` 使用真实 P 重开三次，分别计时同步 `_mount_element` 和后续 `_pyreact_flush`，统计原生 Clone 总数。首批界面挂载时间不等于全部编辑控件就绪时间；工作台按帧创建场景、工具栏和属性栏，入场结束后通过共享 PreparationQueue 分批准备其余页签和方块目录，每帧最多一个批次。原生输入框聚焦、指针按住、模型拖动和弹窗动画期间暂停后台创建。`profile_pane_switches.py` 比较首次/再次页签切换的提交耗时和 Clone 数，测量包含该窗口内的后台准备，不能当成单个切换回调耗时。分类与搜索共用一组原生工具按钮，不能为了减少首次创建量在每次筛选时删除按钮，否则可能丢失原生 edit_box 焦点；修改后须跑 `verify_catalogue_input.py` 的快速输入/删除回归。

`tools/verify_library_workflow.py` 在内存中替换建筑列表及 save_library，finally 恢复，避免写入用户配置；检查 4:3/16:9 列表可见面积、独立重命名弹窗的原生输入/占位控件、保存/取消与草稿名称隔离、右侧选区操作。`verify_click_effects.py` 检查真实像素、六个粒子控件复用、弹窗层级、原生输入焦点，以及 F11 下实际触点位置。触屏坐标须来自事件，不能优先读取鼠标坐标；仍需区分开发客户端模拟和手机硬件验证。

`tools/verify_presence_motion.py` 采样实际原生容器位置，检查工作台 P 入场/右上角退出、三种共用 DialogMotion 的弹窗、快速反向开合、减少动态效果以及分类上下居中。工作台动画等待分帧编辑控件挂载完成后开始；退出动画结束才出栈。`--visual` 抓取桌面中间帧，`--workspace-only` 仅测工作台；截图需覆盖首次控件准备和动画的总时间，不能仅录制 300 ms 后把世界画面误判成动画失效。测试临时确认/重命名不会执行实际持久化操作。原生位置提交与桌面画面呈现有时间差，接触表的百分比是容器位置采样参考，不是显示器呈现时间的精确标定。

阶段 44 起工作台改为右侧滑入/滑出，弹窗上下最大偏移为 18 设计像素，两者均对内容和遮罩渐变。应用本地 Fade 使用无纹理 image 的 `propagate_alpha`，由原生容器传播 alpha；不要恢复为整页 Style.opacity，后者每帧遍历全部后代。稳定的 fade 引用在 transform 的 apply_layout 路径写入 alpha，不触发每帧 props 更新的整屏 UpdateScreen。原生 SDK 没有 GetAlpha；测试读取已提交的 motion_alpha 记录，并结合实际截图验证，不能声称 alpha 原生读回。采样缓存四个动画 Fiber，避免每次 flush 遍历全页影响测量。`verify_press_feedback.py` 通过真实 PC / F11 点击测量 Action 和 JellyButton 的压缩、回弹和精确复位，并检查减少动态效果。

阶段 45 将工作台的整屏水平位移缩短到 12 设计像素，参照 `c3d96fe` 的 PageMotion 距离和 280 ms 入场节奏；退出仍为 200 ms，弹窗仍为 18 像素。旧版并没有独立 WorkspaceMotion，不能把它描述成原封不动回滚整个工作台。`SetAlpha` 文档只保证 image/label；原生方块模型在父容器渐隐时仍完全不透明，单靠已提交 alpha 的断言会漏报。预览片元着色器仅在正交 UI 中乘 CURRENT_COLOR.a，并为方块几何体开启混合；Scene 在模型的最小层级 50 之前用现有透明贴图绘制一个 1 像素、层级 49 的节点，传入继承的 alpha，防止沿用工作网格的半透明值。零 alpha 时隐藏 Fade 容器，避免引擎跳过图片后遗留模型。保持模型层级及这张透明图片的绘制顺序；深度裁剪、亮度和世界投影的透明度路径保持原逻辑。`verify_model_fade.py` 比较实际像素：网格开关不改变不透明表面、多个透明度档位、零透明度无模型、显示恢复。渐变由绘制状态完成，不调用 Combine 或逐帧重建模型。不能用多层建筑的像素差除以最终颜色差，来声称测得精确原生 alpha；透明面叠加和底色都会影响结果。

`verify_work_plane.py` 使用未保存庭院草稿，在树木上方 Y=8 的网格进行 PC/F11 实际悬停、点选、两点框选和直接放置；关闭网格恢复选择树叶，位于网格前方的方块仍优先。`camera.pick_target` 比较射线到可见网格和实际方块的距离，而不是总先命中实际方块；换材质/擦除/吸管仍只命中实际方块。修改拾取后还要检查真实拖动的旋转支点，不能只验证俯视坐标。

后台 PreparationQueue 在按钮回弹、选项与页面动画期间暂停，不仅依靠 250 ms 的点击冷却；恢复后最多每 1/30 秒一批，固定尺寸 Scroll 使用现有布局缓存隔离隐藏页签的准备。Scene/Scroll/Range 的常驻轮询不能作为暂停条件，否则后台准备永远无法完成。输入焦点和原生按住回归仍按前文要求进行。

`tools/pyreact_legacy/` 保留旧版截图/Win32 输入、Tracy 与动画采样剪贴板工具，供现有回归脚本使用；普通调试使用本 skill 的 MCDK 工作流。新实例下通过 `tools/run_live_check.py --session <file> --owner <owner> <工具名.py> [参数]` 运行项目回归，该入口校验实例、绑定 PID 并持有桌面锁。不要对用户的世界运行会保存建筑库或投影的 `verify_ui.py` 主函数。

阶段 46：视口 PointerTracker 仅在提供 onPinch 时追踪多 TouchId；第二触点取消单指点击，直到所有触点结束都禁止误编辑。多指 move 沿用原生 SetButtonTouchMoveCallback；全局观察器只补充第二指 down/up，不能补造原生没有投递的 move。F11 是单触点模拟，文档也没有明示同一按钮多指的保证；verify_layer_pinch.py 直接注入 tracker 多指回调验证相机与编辑隔离，必须与手机硬件测试分开报告。触点为零距离、交换/替换、cancel、TouchEvent=6、重复 global/local up 均应检查。缩放直接改变 OrbitCamera.zoom/pan，按住期间 camera_dragging 保持 true，末指释放后一次 emit('view')，继续延迟 SetLayer 避免打断原生触摸。Scene 工具切换无需重构原生树，但 tick 必须清理上一个模式候选框。

工具切换性能需同时检查稳定按钮池和参数区；ToolChoice 的布尔 selected 保证只有前后按钮更新，SelectionParameters/ModificationMask 将无关参数从工具切换中隔离。固定字体布局缓存不能用于替换输入框字体，也不能省略 resize/聚焦回归。阶段 46 的底部重复 Y 控件已移除，自动化应操作 Viewport 内唯一 Input；其标签随显示模式为网格 Y / 切面 Y / 单层 Y。

阶段 48 的世界炫彩范围框为独立客户端实体，ExtraUniform1 传入三轴尺寸和色相速度；顶点先在模型坐标（每 16 单位一格）扩展，再做原生骨骼变换。根骨骼也可能包含平移与轴反转，不能把已经变换的实体坐标当单位方框直接扩展。世界 AddActorBlockGeometry 实测需要 offset=(-0.5,0,-0.5)、rotation=(0,180,0) 才与 origin+文档坐标一致；单体与分块必须相同。

细棱的小轴尺寸不足一个模型单位时，自动 UV 曾导致部分侧面丢失；接近平视顶部时水平棱几乎不可见，单纯加粗无效。即便片元 shader 不采样贴图，也需给六面提供显式非零 uv_size，确保原生模型生成完整的面。检查实际像素，不能仅用实体存在或 uniform 数值判断渲染正确。

`verify_projection_outline.py` 验证世界外框的尺寸、开关、速度、清理和 PC/F11 按钮，并拍摄实际投影及分块接缝。仅移动离体相机不会让原生 actor 所在区域加载，不能据此判断投影丢失；测试临时移动独立世界测试玩家并开启飞行，在 finally 恢复位置、飞行、相机和渲染距离。execute_code 内安装跨帧诊断包装时，用闭包捕获 API 与原函数，后续服务端代码可能重绑定全局 api；否则异步回调会误用服务端 API，产生仅测试脚本导致的异常。偏好保存使用内存替身，不修改用户建筑库或世界方块。

`verify_projection_workflow.py` **会临时写入独立测试世界**，并切换测试玩家权限，不能用于用户建筑所在地；finally 恢复预先确认为空气的 24 格测试区、权限和草稿。检验完整网络路径、服务器鉴权、旧版方块转换、空气同步和客户端实体隔离。阶段 50 已移除世界撤销入口及协议，工具改为检查入口不存在；仍保留失败/取消写入的自动恢复。`verify_projection_controls.py` 用真实 Esc 检查聚焦输入/弹窗，检查 4:3/16:9 的速度控件及 F11 点击后的底色像素；`verify_press_feedback.py` 验证回弹仍然存在。Action/JellyButton 的反馈 state 当前在 hooks[3]，hooks[2] 是动画进度，二者不可混用；原生 Input 焦点读取 displayText.properties['#text_edit_selected']。

`verify_projection_filter.py` 同样仅用于独立世界。先寻找已加载的空气测试区，临时写入旧标识对应的当前木板、羊毛、原木以及错误材质，在 finally 恢复所有测试格。验证 PC/F11 的缺失过滤即时刷新、旧标识规范化、全部完成后保留范围和最大尺寸跨分块过滤。测试强制开启范围框并恢复原偏好，不能把用户已关闭外框误判为实体丢失。服务端 `resolve` 只返回至多 64 项规范化材质，不写方块或创建实体；结束投影必须阻止仍在返回中的结果重新开启投影。客户端遇到未加载位置应重试，不能将对应分块缓存为已完成。

`assess_clipboard_sharing.py` / `assess_clipboard_runtime.py` 是分享方案评估，未注册产品导出/导入功能。运行时工具通过已绑定 MCDK 注入编码测试，再调用 SDK 剪贴板接口，不使用剪贴板传送调试命令。Windows 工具先备份当前全部可支持格式，使用隐藏原生窗口作为恢复时的剪贴板所有者，结束时恢复；遇到无法备份的格式时跳过写入。结果不含用户剪贴板内容。合成材质和随机极端样例仅用于数据容量测试，不提交原生几何，也不代表手机硬件或聊天软件容量。

SetBlockNew 的最后两参数依次为 **isLegacy、updateNeighbors**。GetBlockNew 返回的传统 aux 需用 isLegacy=True 写回；现代 spruce_log 的 x/z 轴分别为 1/2，不能沿用旧 log 的 4/8 位。GetBlockStatesFromAuxValue 对旧拆分 ID 会丢失物种、原木轴和树叶标志，GetItemInfoByBlockName 只提供物品别名，不能无条件把技术方块换成其掉落物。树叶可能在批量撤销中自然改变附加值，即使 updateNeighbors=False；这种后来变化应保留，不能把整个撤销回滚。GetBlockEntityData 在 BlockInfo 与 BlockEntityData 组件均有同名接口，前者可检查原版方块实体，不能只凭接口名认定组件用错。
