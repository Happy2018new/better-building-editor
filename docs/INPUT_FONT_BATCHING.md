# 输入框字体合批对照实验

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
