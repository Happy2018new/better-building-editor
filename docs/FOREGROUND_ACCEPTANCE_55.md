# 前台验收与进度按钮修复：阶段 55

在既有受管游戏实例内完成实际前台截图和 Win32 鼠标输入，F11 切换原生触屏模拟并读回状态。保留用户原有 64×128×64 椭球的全部 20,649 个方块；不写入世界，不保存测试建筑配置。脚本检查绑定窗口的前台状态，失焦时不继续投递点击。

## 验收中修复的问题

原进度卡片用两个重叠按钮，直接切换原生可见性。语义回调测试可以通过，但真实点击“重试”可能进入下面的场景。改为一个按钮后还复现了另一个边界：鼠标不移动，连续点击“取消 → 重试”，切换状态后的按钮没有收到下一次原生点击；移开再进入则恢复。调整层级或重建控件不能可靠修复这个边界。

最终采用局部 `PreviewAction`，复用本项目既有 `PointerTracker` 的按下、松开和屏幕释放捕获，单次按下只处理一次。PC 在控件原生输入路由丢失时仍可由全局观察事件捕获；触屏使用原生触点。拖出后释放不执行操作，弹出确认、重命名、方块目录或分享框时不捕获其下的进度按钮。触屏释放后恢复正常底色，保留点击动画。

`Scene.screen_hit` 同时排除可见进度卡片的实际矩形，防止场景的全局捕获与进度按钮争用同一次输入。取消结束当前构建；重试重新请求构建，不改变建筑数据。

进度提示保留文字、右侧按钮和下方进度条，短文案使用一行并居中对齐，长计数最多两行。取消提示移除没有意义的进度轨道，取消和重试都有图标。只在显示阶段或行数改变时更新布局，数值和填色继续以最多 10 Hz 更新保留的原生控件。

## 验证结果

- `stage55_progress_checks.json`：13 项通过。PC / F11 各验证拖出不触发、取消、原地重试、两次操作均不穿透到模型、完整建筑保持一致，结束时再比较原草稿。
- `stage55_font_checks.json`：20 项通过。包括“annnn币”与分享/导入标签使用完整字形图集；256/512/1024 字符分段；重复段忽略；4:3 / 16:9 布局；无冗长缺失列表；翻页、定位缺失；最大椭球精确还原；深入 40 格提示；进度文字和窗口缩放后的保持；原草稿恢复。
- `python -m unittest discover -s tests`：228 项通过。
- `verify_orbit_polish.py --final-only`：原最大椭球逐块一致、预览已结束且无错误、SDK 输入与帧回调已恢复、全部 41 个业务模块在游戏 Python 2 内编译通过。
- 完成后 `get_latest_error_logs` 返回空列表。

实际读取的截图包括 `.runtime/stage55_progress_pc.png`、`stage55_cancelled_touch.png`、`stage55_library_font.png`、`stage55_missing_4_3.png`、`stage55_missing_16_9.png`。编号网格显示接收状态，不再拼接离散的“缺少第 … 段”长句。旧字体散图清理的数量、体积及覆盖范围见 [FONT_ATLASES.md](FONT_ATLASES.md)。

本轮系统剪贴板无法安全备份，分段传输使用内存桥接替身，测试后恢复原桥接函数；未覆盖用户剪贴板。F11 为 Windows 开发客户端触屏模拟，不代表安卓硬件测试。旋转优化的测量方法及前后数据见 [ORBIT_PERFORMANCE_54.md](ORBIT_PERFORMANCE_54.md)，本阶段没有更改模型提交或相机计算。

## 复测入口

使用实例绑定入口，先打开编辑器并将该 Minecraft 窗口留在前台。分开运行两组，以便保存独立结果：

```powershell
python -X utf8 tools/run_live_check.py --session <session.json> --owner <owner> verify_foreground_finish.py --wait-foreground --progress-only
python -X utf8 tools/run_live_check.py --session <session.json> --owner <owner> verify_foreground_finish.py --wait-foreground --font-share-only
python -X utf8 tools/run_live_check.py --session <session.json> --owner <owner> verify_orbit_polish.py --final-only
```

`--reload-ui-code` 仅用于本阶段调试：关闭页面、在嵌入 Python 中重新编译 scene/ui、重新打开，避免热替换后沿用不同顺序的 hooks。最终报告以各组成功结束并完成恢复的结果为准。
