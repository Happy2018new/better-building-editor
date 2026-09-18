# 现代化投影开发记录

## 阶段 1：编辑内核与开发环境

- Pyreact-MC 保持项目已有实现，业务代码位于 `behavior_pack/HelloScript/projection`。
- 文档体积上限 32768 格、单轴 64 格，所有草稿编辑限定在文档长方体内。
- 64 个工具集中定义在 `catalog.py`，由 `Editor.run` 执行；界面、搜索和测试共用目录。
- 原子提交、最多 50 步 / 262144 个变更格的历史；失败的越界操作不会部分生效。
- 单元验证：`python -m unittest discover -s tests -v`，13 项通过。
- 方向性方块的旋转/镜像暂时明确拒绝，避免在未实现状态转换时损坏楼梯、门等朝向。

## 本地资料库

已下载 `https://github.com/GitHub-Zero123/mcdk-assistant`：

- 源码资料：`.tools/mcdk-assistant`，commit `481f461d589847b9dceed762a9d8557bcd278e81`。
- Windows LITE 二进制：`.tools/mcdk-runtime`，release `v0.2.6`。
- 项目 MCP 配置：`.codex/config.toml`。配置方法参考 <https://developers.openai.com/codex/mcp/>。
- 当前任务可直接使用 `python tools/mcdk.py list` 和 `python tools/mcdk.py minecraft_docs '{"command":"api CombineBlockPaletteToGeometry"}'`。
- `.tools` 为开发机器缓存，不随模组打包。

## 开发依赖

Python 3、Pillow、requests、psutil、pyperclip；游戏内代码兼容 ModSDK Python 2.7。
当前机器 `python3` 是 Windows Store 空别名，调试命令使用 PATH 中实际可用的 `python`。
所有命令均通过 PATH 查找解释器，不硬编码解释器安装路径。

字体方案参考用户指定的 AddOn 示例：OFL Noto Sans SC 高清离线栅格化，静态短句贴图复用，动态文本按字形拼接，未知字形回退原生平滑字体。


## 阶段 2：工作台与游戏桥接

- 新增 app-local Pyreact 工作台、高清文字资源、圆角控件、弹性反馈、逐层编辑、建筑库、透明投影和实际世界操作。
- `bridge.py` 隔离客户端 API；`world.py` 提供可测试的分批预检查、写入、回滚和撤销事务；服务端以 `__id__` 识别事件发送者。
- 调色板布局通过实际 SDK 的 `GetLocalPosListOfBlocks` 验证：`volume=(Z,X,Y)`，索引 `Y*sizeX*sizeZ + X*sizeZ + Z`。非对称 volume `(2,3,4)` 中 1→(0,0,1)、4→(2,0,0)、6→(0,1,0)。
- 游戏内字符串 API 按 UTF-8 边界处理；原生 Input 返回字节串必须先解码再截取名称。
- Session 每次 emit 增加 ui_revision，并显式传入依赖会话的组件，避免框架 props 复用导致内容不刷新。
- 三维控件在工作台内部持续保留；确认弹窗使用固定根上的 Modal。逐层画布分页控制在 144 个交互格子。
- UI 资源生成：`python tools/generate_assets.py --font .tools/fonts/NotoSansSC.ttf`；OFL 许可保留在资源目录。
- 单元测试：`python -m unittest discover -s tests -v`。
- 真实游戏回归：`python -X utf8 tools/verify_ui.py`（16 项交互检查）、`python -X utf8 tools/verify_world.py`（27 格可逆世界写入）、`python -X utf8 tools/verify_layout.py`（20:9 / 4:3 / 16:10 / 16:9）。
- 运行快照、日志、截图与 JSON 检查结果保存在 `.runtime/`，该目录不提交。

## 阶段 3：真实游戏回归与渲染修正

- 2026-09-17，网易 Windows 开发引擎 1.21.120：26 项单元测试、16 项 UI 交互、3 项真实按键/选区检查全部通过。
- `tools/verify_entry.py` 使用指定 Minecraft 窗口的 Win32 消息触发 P、F6、F7；确认重开工作台、标记第二角点并读取选区。它不向其他程序发送键盘输入。
- `tools/verify_world.py` 在预先确认的空中空气区域写入 27 格，再撤销并重新检查全部为空气；4 项断言通过。
- `tools/verify_layout.py` 的 20:9、4:3、16:10、16:9 共 16 项比例与列边界断言通过。
- 对 1307 格庭院模型逐材质核对原生调色板坐标，全部等于文档坐标。PaperDoll 的初始观察轴与世界实体不同；本阶段首次调整了视角。阶段 4 的逐面校准发现该版俯视仍会显示地板底面，最终映射见下文。
- 新建客户端实体须延后到后续帧再挂方块几何体；同帧调用会返回 True 却不渲染。正式流程延后 0.2 秒挂载，生成完成后才替换旧投影；关闭、维度切换和重复更新会取消尚未挂载的实体。4 项生命周期单元测试覆盖这条链路。
- 在真实世界观察了 3×5×2 的半透明模型；投影不放置真实方块。最新工作台及投影截图位于 `.runtime/modern_projection_workspace_final.png`、`.runtime/projection_final_visible.png`。
- 后台 PrintWindow 在这台机器上有时输出全白，但交互树仍正常；最终视觉检查使用确认游戏为前台窗口后的客户区截图。仅输出截图路径不算视觉通过。
- MCDK review：业务目录 10 个 Python 文件全部可解析；仍有参数数量、函数长度及 `sys` 导入的静态提示。`sys` 仅用于 Python 2/3 字符串边界判断，已在实际引擎中验证。
- 本轮临时 SDK 探针与热重载入口已删除。字体贴图和全部资源 JSON 已验证可读。

## 阶段 4：三维直接编辑与交互修正

- `camera.py` 提供与 SDK 无关的轨道相机、时间阻尼和网格 DDA；`scene.py` 使用稳定的单个 PaperDoll 与指针平面，逐帧更新相机，不逐帧重建 Pyreact 工作台或方块几何体。
- 实际引擎校准：`init_rot_x=-90+pitch`、`init_rot_z=yaw`；正视从 Z 正方向观察，俯视 X 向右、Z 向下。原生几何体每格为 `10 * scale` UI 单位，中心位于文档尺寸的一半；渲染与拾取共用按视图尺寸计算的单位长度。
- 直接点击支持单格选择、相邻面放置、涂装、擦除、吸管与两点框选，沿用文档事务、蒙版和图层锁；拖动阈值、取消事件及页面/弹窗切换防止误编辑。预览尚未完成时暂缓点击，避免画面和文档版本不一致。
- `PointerPrimitive` 是应用局部扩展：SDK 的 touch move 仅支持触屏，因此 PC 在按住按钮期间逐帧读取 ActorMotion.GetMousePosition；触屏使用原生 move 回调。悬停先调用 AddHoverEventParams。调试协议增加 `pointer` 命令，技能文档已补充坐标与事件语义；真实鼠标验证防止只测回调而漏掉原生输入差异。
- 横滑条增加端点内边距并统一半入取整；竖向条复用原生滚动内容，单独绘制比例滑块，禁用旧原生小方块。参数按工具实际使用情况展示，切换工具重置滚动位置，分段文字居中且保留切换动画。
- 验证入口：`tools/verify_interaction.py`（点击、拖动分离、编辑、吸管、框选、滑条和参数上下文）；`tools/verify_native_pointer.py`（前台游戏实际鼠标点击、双轴拖动、滚轮、横竖滑条）。运行实际鼠标脚本时应让游戏窗口保持可操作。
- 网格拾取使用完整方块包围盒；特殊几何体的亚方块表面，以及原生方块几何体不支持的外观，仍需逐层编辑辅助。
- 调试剪贴板写入短暂失败后，旧协议已经认领 seq 却不再返回回执，导致自动检查超时。现在缓存响应并在相同 seq 上仅补发回执；不会重复执行点击或编辑。独立测试覆盖写入第一次失败、第二次成功且编辑只执行一次。
- 原生 Image.Rotate 设置绝对角度，正方向为逆时针；UI 的 Y 向下，因此屏幕 atan2 结果需要取负。新增只读 `native_control` 调试命令，使用 GetRotateRect 验证选中框的全部 12 条边都连接到投影后的方块角点，误差小于 0.15 UI 单位。
- 2026-09-18 完成验证：36 项单元测试、19 项三维与控件交互检查、6 项真实鼠标检查、原有 16 项 UI 回归，以及四种窗口比例下的 20 项布局/命中断言全部通过。MCDK review 的 12 个业务 Python 文件全部可解析，保留函数长度、参数数量和原有 sys 导入的静态建议。
- 最终像素检查已读取 `.runtime/modern_projection_interaction_final.png` 和 `.runtime/modern_projection_controls_final.png`，确认闭合选中框、横向端点及竖向比例滚动条。测试结束恢复了庭院示例和动态效果，游戏保留在工作台放置模式。

## 阶段 5：预览连续性、帧率和专注编辑

- 调试剪贴板保留上一次 dump_tree 回执时，旧代码每个逻辑 tick 都重新解析整棵 UI 树。现在先识别自身已缓存的回执，并缓存非请求内容；相同 seq 的未送达请求仍只补发回执，不重复编辑。
- `Scene` 独占原生模型提交，app-local `PaperDollPrimitive.managed` 禁止 reconciliation 再提交相同模型。滚轮直接驱动相机，停止滚动 180 ms 后才刷新工作台上的百分比；发布前同步实际角度，避免与紧接着的拖动竞争。
- 选中框和自绘滚动条记录上次应用的状态，未变化时不重复写入原生控件。SDK 没有文档化的方块 PaperDoll 独立相机变换接口，因此旋转继续使用官方 RenderBlockGeometryModel，不臆造 GetModelId/骨骼模型变换接口。
- `PreviewBuffer` 持有两个始终挂载的透明预览控件。新几何体在旧图像仍显示时提交、预热，然后隐藏旧控件；空文档、被后续更新替换、提交失败和撤销取消均有生命周期测试。空闲时不重新提交模型，通常只显示一个渲染器。
- 实测隐藏 PaperDoll 会推迟初始化，带不透明背景的第二表面会遮住旧画面；因此预热表面必须可见且透明。也不在切换时调用默认同步 SetLayer，避免额外的 UI 刷新。
- **SDK 限制**：RenderBlockGeometryModel 返回的是提交成功，没有方块几何体 GPU 就绪回调。当前采用至少 3 个渲染机会且不少于 75 ms 的预热窗口，已在庭院连续放置中验证；这不是对所有硬件/所有规模建筑都无闪帧的保证。预览尚未追上文档时暂停新的点击编辑，仍允许旋转/缩放。
- 专注编辑保留相同 Scene 和两个 PaperDoll，收起工具箱/分类/页签，支持独立展开属性面板。1920×1080 下三维操作区从约 1019×525 像素扩大为 1880×656 像素，面积为 2.31 倍；还原后尺寸和原生指针 ID 不变。
- 验证工具：`tools/profile_viewport.py LABEL` 在已确认前台的 Minecraft 窗口制造 10 秒真实拖动和滚轮负载并采集 Tracy；`tools/verify_preview_frames.py LABEL` 使用 `mss`/Pillow 连续采样游戏视图，检查四次真实放置及模型像素覆盖，输出帧序列拼图和 JSON。调用前会载入庭院示例以建立确定的基线，适用于开发测试世界。
- `tools/verify_focus.py` 检查展开后的直接放置、撤销、材质、图层、历史、逐层网格和还原；`tools/verify_layout.py` 扩展为四种比例下共 44 项布局/命中检查。测试报告、Tracy 采样、日志和连续帧图片保存在 `.runtime/`，下载的 Tracy 二进制不提交。

## 阶段 6：控件帧率、皮肤与过渡

- 优先处理拖滑条、切换选项和切换页面的整树重排/透明度继承开销，原生圆角背景合并成一个布局节点，点击粒子用序列帧图片绘制。数据即时写入，界面通知合并，不延迟执行工具所读的参数。
- 纯 transform/opacity 使用直接原生绘制提交；不可变 Element 的干净子树可以跳过 reconcile。已更新 UI skill 的样式性能说明。
- 输入框使用透明原生编辑控件与固定圆角外壳；按钮悬停/按下改变同一外壳颜色。选项在父页面提交后启动完整位移，确认弹窗保留进入/退出阶段。
- 三维独立裁剪框对齐整数 UI 坐标，模型容器反向补偿原点，解决遮罩下的白边；不关闭 scissor，大倍率仍保留裁剪。`verify_layout.py` 增加原生边界与模型原点检查，四种比例共 52 项。
- `tools/profile_controls.py slider|segments|pages LABEL` 运行 10 秒真实鼠标负载；`tools/verify_motion.py` 采集实际原生中间位置，检查反向选择和弹窗出入场。性能数据、环境和适用范围见 `docs/CONTROLS_PERFORMANCE.md`。

## 阶段 7：缩放重影、跟手旋转与全页反馈

- 字体重影来自字号改变时 Base Label 重新写入原生文字，而字形贴图仍在显示。应用 Label 现在把传给原生实现的 content 始终设为空，保留 fiber 上的逻辑内容，原生字体回退仍正常。调试协议 `native_control` 可读取实际 text/visible。
- 部分组件 props 没变化，缩放时被复用，导致关闭按钮、分段框等留在旧尺寸。应用组件通过 `use_theme` 订阅 scale/motion 变化，只在主题改变时更新；不重建 Scene 或 PaperDoll。窗口尺寸通知合并到 50 ms 内，跳过相同尺寸。
- 分段框改成 4 格圆角的淡蓝底与细下划线，沿用父组件提交后开始的 300 ms 移动动画。顶部草稿状态、保存、关闭统一为 32 格高度。
- 水平拖动按“抓住建筑”方向旋转，惯性使用相同符号。新增五个朝向、左右两种拖动及松手后的投影方向测试；原生鼠标验证明确检查右拖后的负 yaw 增量。
- 点击反馈改成独立的 `ClickEffects`，全页共用 6 个常驻 Image，每次点击在实际指针处播放 112×112 设计单位、480 ms 的环与十个粒子。按帧更新贴图，不通过 Workspace state 重排；尺寸变化、减少动态效果和卸载均清理活动特效。
- 全局点击监听采用原生 `input_panel` 的 `button.menu_select` global mapping，mapping 上 `consume_event=false`。普通 `OnKeyPressInGame` 不能覆盖 UI 点击，覆盖页面的 Button 会抢点击；input_panel 与 ScreenNode binding 组合已验证页面切换、输入框、三维点选/拖动、滑条、滚动条和弹窗。SDK 对同一次 down 有重复派发，20 ms 内同坐标同触点去重。
- `tools/verify_resize.py` 改变窗口宽高和实际字体缩放，覆盖 1280×720、1600×900、1440×1080、1920×1080、1366×768 后还原，共 31 项文字/回退/预览身份/可见性/顶部对齐检查。此前只改变宽高比、固定高度的测试无法稳定触发此次错误。
- `tools/verify_click_effects.py` 用真实鼠标检查空白处、页签、输入框打字、弹窗、连点、减少动态效果，并读取原生特效位置与实际像素。480 ms 特效不能依赖 6 次串行剪贴板请求之后的 visible 值判断，截图先于坐标采样。
- 本轮单元测试 43 项、实际鼠标 7 项、位移/弹窗动画 6 项、全页特效 9 项通过；特效测试包含关闭工作台后用 P 重新打开，检查原生绑定清理与重新绑定。最终游戏日志没有本轮代码的 traceback 或未知 JsonUI 属性。Windows PC 实机验证；移动触控坐标已有回退，尚未在移动设备实测。

### 分段选项对齐补修

- 用户的“历史”选中截图暴露了 `surface(padding=3)` 内再次使用绝对 `top=3/left=4` 的重复偏移：背景相对点击目标向右、向下偏了 3 个设计单位，底边留白变成 0。Segments 改成不带 padding 的共同父坐标系，背景与按钮行各自只应用一次 inset；保留稳定的动画节点与原生位移路径。
- 圆角遮罩的完全透明像素原先 RGB 为黑色，双线性采样会在小圆角上混出暗点。生成脚本为圆角遮罩保留全白 RGB，仅使用 alpha 定义轮廓。应用到共享圆角贴图，未增加控件或动画开销。
- `verify_motion.py` 增加原生选中背景与点击目标的中心对齐、上下正留白相等断言；旧版本首先失败，新版本共 14 项通过。1280×720 / 1440×1080 / 1920×1080 下分别选参数、图层、历史，28 项附加几何检查通过。实际像素对比保存在 `.runtime/segments_before.png`、`.runtime/segments_after.png`。
