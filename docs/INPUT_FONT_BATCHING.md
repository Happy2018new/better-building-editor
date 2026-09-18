# 输入框字体合批对照实验

2026-09-18。约束：不更换字体，不新增 UI 图片，不修改字号与输入框尺寸。结论：在当前网易开发引擎上，单独关闭字体合批没有解决输入框中文的锯齿 / 细碎笔画，不能作为字体问题的正式修复。

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
