# 输入框字体合批对照实验

当前版本（2026-09-19，阶段 25）：保留原生字体和整数 GUI 字形倍率。用户确认接受仅聚焦时中性深灰底色后，原生白光标实测对比度达到 9.66:1；取消焦点恢复浅底深色文字。五种窗口、原生字号行高与键盘/中文输入/删除/重开共 166 项检查通过。以下保留早期实验和失败记录，最终实现见文末。

2026-09-18。第一轮约束：不更换字体，不新增 UI 图片，不修改字号与输入框尺寸。结论：在当前网易开发引擎上，单独关闭字体合批没有解决输入框中文的锯齿 / 细碎笔画，不能作为字体问题的正式修复。用户随后授权测试整数倍字号，当前实现及验证见文末；前面的 0.8 倍实验记录属于修改前的历史结果。

## API 与作用范围

通过已配置的 MCDK 文档工具查询：

```powershell
python -X utf8 tools/mcdk.py minecraft_docs '{"command":"api 合批 --top 8"}'
```

来源：`ModAPI/接口/自定义UI/通用.md`，134–167 行，`GameComponentClient.EnableFontBatchRender`。

```python
game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
game.EnableFontBatchRender(False)
```

该接口作用于客户端；默认 `True`，文档描述的用途是通过合批优化性能。没有返回值，也没有配套状态读取接口。它不提供选择字体、字形分辨率或抗锯齿的参数。调试结果中的 `requested` 仅记录已调用的参数，不伪装成 SDK 的状态读回。

## 实测

引擎路径版本 `3.9.0.401155`，游戏显示 `1.21.120`；客户区固定 `1920×1080`。使用建筑库的原生 Input，文字固定为 `林间白盒 · 建筑练习`，保持已有 `$font_scale_factor: 0.8`。实际 `GetEditText()`、位置和尺寸同时验证。真实点击状态栏取消输入焦点，等待点击效果结束后再截图，排除光标闪烁。

| 方式 | 实测结果 |
| --- | --- |
| 已有输入框，开启 → 关闭 → 开启 | 最终复测 on/off 裁剪画面相差 0 像素，锯齿仍在；on/on_again 存在 19 像素的小幅差异 |
| 每次切换开关后关闭并重新打开整个工作台 | on/off 相差 19 像素，on/on_again 相差 0；实际查看画面，笔画没有变平滑 |
| `UiInitFinished` 中，在首次创建工作台之前关闭 | 与先前默认开启的基线相差 0 像素，仍未改善 |

19 像素差异的范围为裁剪图 `(151, 18)–(232, 36)`，同一合批设置的重复采样也能出现，不能当作字体修复效果。输入框原生位置始终为 `(50.625, 99.60469055175781)`，尺寸为 `(343.734375, 12.65625)` UI 单位。live / remount 两组共 8 项中文内容与几何检查通过，最终游戏日志没有新增本次调试引起的 traceback。已实际打开并检查默认、关闭、重建与启动前关闭的截图。

诊断输出（不进入资源包、不提交图片）：

- `.runtime/input_font_live.json`、`.runtime/input_font_remount.json`
- `.runtime/input_font_live_on.png`、`.runtime/input_font_live_off.png`
- `.runtime/input_font_remount_on.png`、`.runtime/input_font_remount_off.png`
- `.runtime/font_batch_baseline.png`、`.runtime/font_batch_startup_off.png`
- `.runtime/font_batch_startup_off.log`、`.runtime/input_font_final.log`

## 保留的代码与复现方式

```powershell
python -X utf8 tools/verify_input_font.py
python -X utf8 tools/verify_input_font.py --remount
```

脚本使用受限的调试命令 `font_batch`，仅接受布尔值，运行后在 finally 中恢复 SDK 默认 `True` 及原草稿名称，不保存建筑库配置。`native_control` 增加 Input 的 `GetEditText()` 读回。所有接口仅通过已经启用的 Pyreact debug 通道调用。

启动前关闭的临时实验行已移除，正式工作台不调用此开关；字体、字号、资源包和输入逻辑均未改动。当前字体问题仍待解决。

## 原生定义核对

当前引擎的 `data/resource_packs/vanilla_netease/ui/ui_common.json` 中，`common.text_edit_box_label`（1333 行附近）是原生 Label，定义了 `font_size` 和 `font_scale_factor`，没有显式 `font_type`。`common.text_edit_box` 在 `centering_panel/clipper_panel` 下实例化它。按照 JsonUI 文档，未设置 `font_type` 时使用 `default`。项目的普通 Label 的 `smooth` 设置不会因继承关系自动传给这个输入框内部 Label。

这说明排查应继续关注原生输入文字自身的字形与缩放路径；并不证明单一属性就是全部原因。本轮没有改 `font_type`，也没有用字形图片覆盖输入文字，以遵守用户约束。

## 后续：保留原字形，改用 1 倍缩放

用户要求尝试整数倍缩放，仍不更换字体、不新增 UI 图片。使用 ModSDK `LabelUIControl.SetTextFontSize(scale)` 对同一个原生输入框比较 0.8、1.0、2.0。1 倍比旧版放大 25%，文字更容易辨认；2 倍会超出原有输入框。最终将 `ModernProjection.input` 的 `$font_scale_factor` 设为 `1.0`，同步修改生成器定义，没有执行字体或图片生成。未设置新的 `font_type` / `backup_font_type`，保留原来的原生字体和字体合批默认值。

仅放大字体会暴露垂直裁剪问题：原生 `centering_panel` 从输入框高度扣掉 4 个 UI 单位。在 1920×1080 下，名称框高 12.65625，旧 clipper 只有 8.65625，而 1 倍文字行高 10。现在通过 `$text_edit_clipping_panel_size: ["100%", "100% + 4px"]` 将裁剪高度恢复到输入框完整高度，保留水平内边距和原生光标滚动。材质标识符与附加值框从 25 调到 27 个设计单位高，附加值宽度从 34 调到 44，以容纳完整文字行与两位数字。

这是原生字号和裁剪修正，不是抗锯齿开关。实际打开 1920×1080 和 1280×720 的截图，1 倍保留原字形，中文仍可见点阵台阶，不能表述为完全平滑。不同窗口下游戏自身的 GUI 比例仍会变化；这里的整数倍指 Label 的 `font_scale_factor=1`，不承诺每个字形纹素和物理屏幕像素都整数对齐。2 倍仅用于实验，不保留在正式输入框中。

### 实机验证

```powershell
python -X utf8 tools/verify_input_scale.py
```

2026-09-18，当前引擎 `3.9.0.401155`，87 项检查通过：

- 1920×1080、1280×720、1366×768、1600×900、1440×1080 下，名称、尺寸坐标、工具搜索、材质标识符、附加值输入框的完整文字行均处于原生垂直裁剪范围内，原生值与受控值一致。
- 真实鼠标聚焦及当前中文输入法下的键盘输入、提交、End / Backspace 删除通过。中文 / 英文 / 数字 / 标点混合文本和长文本通过原生 `GetEditText()` 读回，长文本的原生水平滚动截图已检查。没有替用户切换输入法。
- 小窗口与大窗口先滚动属性面板，让附加值框真正进入可见区域，再查看截图，确认 `15` 完整显示。只核对隐藏控件的几何不足以验证实际字形。
- 关闭并重新打开工作台后，模板的 1 倍文字与完整裁剪范围仍然生效；测试恢复草稿名称与附加值，不保存建筑配置、不执行方块编辑。
- 最终日志无本轮脚本 traceback 或未知 JsonUI 属性；已有启动阶段的引擎错误不作为本轮 UI 回归。

诊断文件均位于忽略的 `.runtime/`：`font_scale_probe.json`、`font_scale_0.8.png` / `1.0.png` / `2.0.png`、`input_scale_checks.json`、`input_1x_1920x1080.png`、`input_1x_1280x720.png`、`input_aux_1280x720.png`、`input_long_caret.png`、`input_1x_final.png` 和 `input_integer_final.log`。这些截图没有进入资源包。生产改动只涉及原生模板及两个输入框尺寸，没有增加动画帧回调、逐帧字体设置或图片节点。

## 参考原版设置表单后的紧凑字号

用户反馈 1 倍仍然太大，并指定参考 `nemc-form-script/resource_pack/ui/`。核对 `modal_component.custom_input → future.option_text_edit → settings_common.option_text_edit_control → common.text_edit_box`，参考项目使用原生字体，没有额外抗锯齿开关或输入文字贴图。原版设置控件高度为 30 UI 单位；本编辑器的 30 是设计单位，1080p 下实际只有 12.65625 UI 单位，不能把相同的原生 1 倍字号直接放进缩小后的布局。

同控件比较 0.5 / 0.625 / 0.75 后，1080p 下 0.5 更协调，但固定 0.5 在 720p 的 GUI 倍率 2 下变成过小的字。最终模板恢复基准 1.0，应用层在挂载和窗口缩放时根据 `GetScreenViewInfo / GetScreenSize` 求出 GUI 倍率，再调用内部 Label 的 `SetTextFontSize`。目前 1080p、GUI 倍率 4 时使用 0.5，720p、GUI 倍率 2 时使用 1.0；两者保持原位图字形的 2 倍物理放大。更大的设计比例按偶数档递增。保留原生 default 字形与完整裁剪高度，不新增字体或 UI 图片，不宣称消除了原字体的点阵边缘。

五种尺寸及真实中文输入法 / 删除 / 滚动 / 重开仍共 87 项通过。已查看 `.runtime/input_current_1920x1080.png`、`input_current_1280x720.png` 和 `input_current_final.png`。验证脚本先重开工作台清除旧实验覆盖，不再调用字号实验命令或在 finally 覆盖正式字号。字体只在挂载或缩放变化时更新，没有逐帧字号设置。

## 当前字号：原位图字形 3 倍物理放大

用户反馈上面的 2 倍仍过小后，当前算法调整为 `max(3, round(designScale * 1.7 * guiScale)) / guiScale`。常用 1080p 的原生字号为 0.75，720p 为 1.5，两者均为原位图字形 3 倍物理放大，比上一版大 50%，小于先前过大的 4 倍字形。没有更换字体、添加图片或关闭字体合批。

本次再次通过五种窗口尺寸与真实键盘输入的 87 项检查，并查看 1080p/720p 中文混排截图。属性面板重构后，验证脚本滚到材质输入区域再检查附加值可见性。

## 输入焦点与光标对比度（已撤回）

继续使用原字形、3 倍物理放大，不新增图片。ModSDK TextEditBox 只有文本与长度接口，普通 `color` 在 edit_box 上被引擎报告为未知属性；文字颜色也不会改变插入光标。最终使用原生 `display_text.#text_edit_selected` 绑定驱动蓝色焦点背景，文字改为深蓝，保留白色光标。焦点背景使用已有 rounded 纹理，九块尺寸只在布局变化时更新，没有 Python 每帧焦点轮询。

原生 hover/pressed 背景不能代表持续编辑焦点，且旧九宫格贴图会产生白色边角，因此未采用该实验。正式背景位于原生文字之后；原有普通圆角控件保持默认图层 2，焦点背景使用独立参数图层 0。

短文本的实际像素检查能检测到约 22 物理像素高的白色插入竖线及闪烁，鼠标移开后焦点背景保持，其他输入框不变；真实键盘继续编辑。当前 87 项输入几何/键盘检查全部通过，但它们读取原生文本和几何，不能替代下面的长文本视觉限制。

**已知原生限制：** 额外 480 字符混排文本滚动到末尾时，内容读回完整，但原生文字或光标可能被裁掉。文字阴影、禁用字体合批和偏移 Label 均未解决，正式代码不保留这些实验。`tools/verify_input_caret.py --long` 保留为复现诊断，当前这一额外像素断言不通过；不能将“文本数据完整”误报为“超长光标正常”。普通名称、尺寸和坐标输入的焦点对比度已改善，超长文本裁剪仍需后续解决。

## 恢复原生结构并监测断言窗口

用户反馈焦点底色影响外观，并报告 `Control name could not be resolved: place_holder_control` 原生断言。根因是上面的自定义 `controls` 覆盖了 `common.text_edit_box` 完整子树，遗漏引擎依赖的 `centering_panel/clipper_panel/visibility_panel/place_holder_control`。即使 placeholder 文本为空，仍须保留此控件。现已移除整个子树覆盖和蓝色焦点背景，完整继承原生输入结构；保留字号、文字颜色和垂直裁剪参数，不新增图片或更换字体。

新启动游戏后，五种尺寸及真实键盘/中文输入/删除/重开共 87 项通过，另有 4 项原生占位节点、浅色背景和键盘检查通过。实际查看 `.runtime/input_native_restored.png` 多帧截图，蓝色背景已消失。`verify_ui.call` 在剪贴板请求前后检查原生 Assert 弹窗，`tools/check_native_dialogs.py` 可单独读取弹窗标题和正文，不自动忽略或关闭断言。此次检查未检测到弹窗；这不代表所有未执行的交互路径都已验证。

当前光标仍为原生白色，浅色背景下对比度不足尚未解决。文档接口和原版 JsonUI 定义均未发现可独立设置其颜色的属性；Cocos TextField 的 setCursorColor 不等于网易 JsonUI 接口。`verify_input_caret.py --long` 现仅保留像素诊断和输入结构检查，不再通过浅色像素数量推断光标可读性，也不声称超长文本裁剪已解决。


## 光标颜色的追加实验与像素判定（阶段 21）

本轮继续保留原字体，不添加图片。分别在新游戏进程中尝试：

1. 将原生输入框内部的 default/hover 背景恢复为既有 input_bg/input_hover，保留整个占位子树。实际光标依然为白色，并重现旧纹理的白色边角；此改动已撤回。
2. 在资源包临时覆盖 ui_invert_overlay 的混合方式，验证其是否能够改变原生光标。新进程中的实际白色光标未变化；不能据此断言引擎绝不支持覆盖，但这一方式在当前加载环境无效。临时 material 文件已删除，没有全局 UI 材质覆盖留在成品中。

新增多帧差分检测：忽略鼠标 hover 的开始过渡，寻找连续闪烁的竖线，测量实际光标和底色的线性亮度对比度。最终 1920×1080 中检测到高 22 物理像素的白色光标 `[255,255,255]`，背景 `[237,242,255]`，对比度约 **1.12:1**。`python -X utf8 tools/verify_input_caret.py caret_final_contrast --require-visible` 明确失败（要求至少 3:1）；占位节点和键盘输入检查通过与此失败分别记录，不能用前者宣称修复。三组多帧截图均已实际打开。

当前仍保留原浅色样式。中性灰色的聚焦底色仅作为向用户提出的替代设计，尚未采用；黑色原生光标的独立设置仍未找到可验证的方法。本轮未改输入框生产代码，也未伪造一个与原生 IME/中间编辑位置不同步的光标。

## 用户确认的中性灰焦点样式（阶段 25）

单独覆盖或注册原生 ui_invert_overlay / ui_fill_color 材质、恢复原生内部背景、开启文字阴影，均未将光标变黑；实验材质和阴影已经移除。用户随后明确确认“接受，仅聚焦时用中性深灰底色”。当前输入框只在原生编辑焦点有效时使用 RGB(64,69,76) 底色和浅色文字，失焦恢复原有浅色底与深色文字。不添加边框、字体或图片，不改键盘、光标位置、中文输入法、文本选择和原生水平滚动逻辑。

焦点背景复用已有圆角纹理，由原生 `display_text.#text_edit_selected` 绑定控制，不增加 Python 每帧焦点轮询。内部文字 Label 利用同一原生状态选择其普通/locked 颜色；父 edit_box 始终保持可编辑。原生控件显式保留 `centering_panel/clipper_panel/display_text` 和 `visibility_panel/place_holder_control`，焦点背景覆盖原输入框本身的完整区域，避免出现上次的内嵌色框。九块圆角只在尺寸变化时重排。

实际 1920×1080 多帧检测：光标高 22 像素，原生白色(255,255,255)，底色(64,69,76)，线性亮度对比度 **9.661:1**，通过 3:1 阈值。短文本焦点/失焦配色、原生键盘和占位节点共 8 项通过；已实际打开多帧截图检查，原生 Assert 窗口检查为空。可用 `python -X utf8 tools/verify_input_caret.py caret_final --require-visible` 复测。

字号检查发现需要遵守 `GetScreenViewInfo` 的文档语义：它返回补齐到整数 GUI 步长的画布宽高，例如 1600px 宽在 3 倍 GUI 下可能返回 1602；`GetScreenSize` 的逻辑宽度又存在取整。两者原始比值不是连续 GUI 缩放。最终使用整数 GUI 倍率计算 `max(3, round(designScale*1.7*guiScale))/guiScale`，当前五种测试尺寸均为原字形 3 倍。验证读取原生文字行高，避免只检查请求字号；166 项覆盖 1920×1080、1280×720、1366×768、1600×900、1440×1080，以及中文输入法、End/Backspace、长文本数据和工作台重开。

额外超长输入仍有限制：重复 30 次的混排文本在 End 滚动到末尾后，内容和键盘编辑仍然正确，但末尾光标未在画面中检测到；实际查看尾部截图为空白。`verify_input_caret.py caret_final_long --long --require-visible` 明确失败。焦点对比度修复解决常规输入的白光标问题，没有解决原生超长文本滚动/裁剪问题，不把 166 项字号与数据检查当成该像素问题已通过。
