# PyreactMC：现代化投影中的修改版本

原项目与作者：[PyreactMC / EnderWolf006](https://github.com/EnderWolf006/PyreactMC)。

- 上游基准：`9580d0123584ae8b4b4b3a7b0357250e151c54cd`，2026-09-19。
- 合入日期：2026-09-20。
- 上次导入基准：`5fe33a3`；已对初始导入提交 `d14048a` 的全部 54 个框架、模板及技能文件核对，内容一致（忽略行尾）。
- 本目录为集成到“现代化投影”的修改版本，不是未经修改的官方发行版。
- 完整上游许可与归属条件随本目录中的 `LICENSE`、`NOTICE` 分发；两者为 v1.1 原文。

**许可条件：** NOTICE 要求在发布作品详情中保留指定归属陈述；相关开发者账户的全部付费组件与全部网络游戏累计获取量合计达到或超过 1,000,000 次时，须取得原作者另行书面授权。这是上游自定义许可，不是无条件的 Apache 2.0 授权；完整适用范围及例外授权条件以随附文件为准。

本地修改文件：

| 文件 | 保留或补充的行为 |
| --- | --- |
| `reconciler.py` | 相同不可变 Element 的干净子树跳过更新；变脏的组件正常更新。纯绘制属性不触发结构提交，保留上游 ref 切换和生命周期修复；结构、布局及动画变化向祖先失效布局缓存。 |
| `layout.py` | 固定宽高容器可用 `cacheLayout` 复用未变化的测量和布局；尺寸、后代结构、透明度、变换及窗口尺寸变化失效。`display:none` 子树不构建布局节点，原生控件继续保留。 |
| `renderer.py` | 仅位置、尺寸和透明度变化时不额外调用整屏 UpdateScreen；结构变化仍正常提交。 |
| `native.py` | 保留上游中文 key 净化，但输出 ASCII `str` 控件名；网易 Python 2 SDK 克隆 Unicode 名称的容器后，后代按钮可显示却无法接收原生点击。 |
| `primitives.py` / `reconciler.py` | `apply_props` 显式返回 False 时免除仅由 props 触发的整屏刷新；默认 None 保持兼容。Button 的 builder 引用不变时只更新回调；Panel 的空 props 更新不刷新。挂载、布局及显隐仍提交。 |
| `debug.py` | 本项目原生控件、指针、输入字体及有界草稿诊断；MCDK 与剪贴板共用诊断处理。剪贴板回复重试不重复编辑，不重复解析未改变的大回复；组件的调试 ID 支持反向查询。 |
| `host.py` / `composites/safe_area.py` | 每 0.5 秒重新读取原生安全区，支持不伴随分辨率变化的安全区设置；向机审显式返回/转换 tuple。 |
| `navigator.py` / `host.py` | JSON UI 的 menu_cancel / menu_inventory_cancel / menu_exit 共用返回回调；安卓系统返回事件进入同一路由并去重，只处理当前原生栈顶。工作台先关闭顶层对话框，再播放页面退出动画。 |

配套 `resource_pack/ui/PyreactBase.json` 保留现代化投影的模板注册。
其中 `mp_pointer_tmpl` 引用 `ModernProjection.pointer`，以 `is_handle_button_move_event: true` 开启三维视口和滑条的原生触控移动事件；注册回调本身不会启用这些事件。
`mp_inventory_modal_tmpl` 引用应用内的原生 `input_panel` 模态作用域，方块目录用它隔离底层输入；避免整屏 Button 抢占 edit_box 的选择事件。输入框聚焦底色的尺寸、颜色和初始隐藏状态由原生 JSON 维护，更新结果列表不再依赖 Python 缓存的九宫格尺寸。以上属于应用模板扩展，没有修改上游 Modal 组件。
本次上游没有更改该 JSON；自定义输入模板继续保留原字体、整数 GUI 字号、原生占位子树与聚焦时深灰底色。

2026-09-25：应用的 `ModernProjection.click_observer` 增加非吞噬的 `button.multi_touch` 映射和原生交互绑定；`PointerTracker` 不再把 TouchMoveOut (6) 当作释放。手机第二触点的实际事件载荷仍须真机核验。工作台最外层是不透明全屏底色，内容容器按实际 SafeArea 尺寸计算，不让安全区 padding 与全屏内部固定宽高叠加。验证记录见 `docs/ASTRAL_STAFFS_AND_MOBILE.md`。

2026-09-23 性能补丁另让固定数值宽高的叶子直接使用声明尺寸，避免查询随后会被布局覆盖的原生尺寸；自适应文本仍正常量测。应用层静态文字 Element 使用有界缓存，动态字形池按字形差异更新，材质通道按钮保留原生命中控件。验证见 `docs/PERFORMANCE_67.md`。

同日白名单复核撤回了 `host.py` / `native.py` 对引擎内部 `gui` 模块的输入路由合并补丁，该模块不在官方允许列表中。框架现在直接使用公开 SDK，不拦截引擎输入路由。应用层曾使用的 `PendingLayers` 分帧排序导致姿态/深度不同步，已在阶段 69 删除；模型采用固定层级，通过现有透明图片的 RGB 状态和着色器共享深度完成遮挡及裁切。见 `docs/ORBIT_REGRESSION_69.md`，勿恢复分帧层级队列。

`layout.py` 对 Panel/Label 子类与绝对定位双锚点的尺寸优化仍保留，避免空动画容器触发全树第二次排版；依赖原生尺寸的叶子继续后测量。白名单与兼容验证见 `docs/WHITELIST_68.md`。

仓库内的 `docs/PYREACT_UPSTREAM.md` 记录调试工具迁移、验证结果与下一次更新方式。
