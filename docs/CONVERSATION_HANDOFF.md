# 新对话交接：现代化投影建筑编辑器

更新于 2026-09-25，工作区 `D:/Happy2018newの个人文件/GitHub/better-building-editor`，本轮以 `1af6a65` 的交接及 `998218a` 的功能为基线。此文档用于把当前项目和近期对话带入新任务；具体行为以当前源码为准。`docs/` 中的阶段报告保留当时的实现与测试记录，部分旧措辞已过期。

## 最新增量：法杖与手机适配

完整实现和证据见 `ASTRAL_STAFFS_AND_MOBILE.md`，手机连接资料见 `MOBILE_DEBUGGING.md`。本轮修正机审报告的缓存初始化/tuple 推断、安全区排版及全屏底色、JSON UI/安卓返回路由、触控移出误释放；新增非吞噬多触点入口。两种物品升级为带视差星空宝石和悬浮晶簇的三维法杖，手持时有六类 GPU 魔法效果。点击动画已经再次修改：**每颗黄色晶体从自己的中心生长，完成后进入常驻运动**，下文旧的“碎片聚拢”描述仅代表 `b8e0922` 历史版本。

最新本地验证为 **323 项单元测试通过，84 运行时文件白名单无违规，并在游戏 Python 2 中编译通过**。真实 Esc 和 F11 单指拖动通过；注入双触点缩放/释放及返回去重通过，安全矩形 `(48,13,408,235)` 和全屏背景通过原生尺寸/截图核验。**安卓真机双指、系统返回、刘海和手机 shader 尚待设备测试，不能把回调注入当成真机通过。** 尚未重新提交网易机审。

最后冷启动实例 owner 为 `astral-review`，session 为 `C:/Users/Happy2018new/.pyreact-debug/instances/68d93463687e49ad8d3f89866916ac24/session.json`，使用前先查 status。`fragments-final` 和中间 `astral-staff-final` 已停止。不要在需要仅重载新 shader 时再次调用整套资源热重载；本机开发客户端完整重载会触发原版 PBR shader 错误及执行通道失效，单独的公开 `ReloadOneShader` 已成功。

## 项目与约束

- 项目是网易 Minecraft 基岩版 ModSDK 建筑编辑器，行为包在 `behavior_pack/`，资源包在 `resource_pack/`。游戏内 Python 为 2.7；宿主测试和工具为 Python 3。
- 工作台通过可合成的投影终端打开（右键或手持 HUD 按钮），已移除 P 键入口；另一件可合成物品是投影测绘器。工作台提供三维编辑、建筑库、世界投影、材料目录和字符串分享/导入。
- 文档最大尺寸为 **64×128×64**，编辑视图始终显示整栋建筑，底层以 **16³** 分块维护原生模型；不要重新做成玩家必须切换分块的界面，也不要为相机旋转重建方块模型。
- 触屏模式跟随游戏原生输入状态；Windows 开发客户端用 **F11** 模拟切换，**不是 F12**。PC 与触屏的点击/拖动语义不同，应分别验证。Windows F11 模拟不能等同安卓真机。
- **只有 `behavior_pack/` 下的 Python 受网易模块白名单约束**；`tools/` 不受该要求限制。运行 `python tools/audit_runtime_imports.py` 检查。只用本地客户端实体绘制选区、投影与特效，不让其他玩家看见；世界写入和测绘导入由服务端按实际玩家身份鉴权。
- 本机建筑库经客户端配置保存，不是服务端多人共享库。世界测绘导入新建库条目并处理重名/满库，不覆盖当前草稿或已有配置。分享码使用压缩、Base64 和校验；它不是可信权限凭证。
- 项目 UI 使用内置的 Pyreact-MC 和原生 JsonUI，已同步过 Pyreact upstream 并保留本地兼容补丁。先看 `.agents/skills/pyreact-ui-building/SKILL.md`；实机调试先看 `.agents/skills/pyreact-debugging/SKILL.md`。

## 当前视觉与交互约定

- 建筑世界投影外框默认 **炫彩**，玩家也可选 **金色** 或 **星空**；每种风格各自保存流速、亮度、线宽等参数，金色/星空还支持环绕速度和晶体密度。三种主框默认实体棱线宽一致，正常世界前景仍应遮挡后方棱线。
- 测绘器的两点世界选区**固定金色**，不随投影外框设置改变。框线带 GPU 驱动的晶体、星芒与拖尾；两个选点有入场动画和常驻效果。点击原生方块面经过服务端验证后传回，不应随相机移动而改变。
- 测绘器选区已移除白色逐格覆盖和白色面，只保留金色框线与特效。主框线有细亮芯和流动高光；环绕光点、星芒、拖尾使用独立叠加发光材质，不写深度但保留深度测试，晶体沿用原来的透明深度材质。环绕粒子的实际尺寸已放大。点击端点使用 **1.8 秒**发光碎片形成动画：逐片出现、旋转聚拢、在选点融合，然后保留常驻环绕效果。复用 strike 模型原有空闲四边形，不新增实体。
- 投影终端和测绘器手持 HUD 使用原版灰色按钮图集，按钮均为 50×20 UI 单位；无论 PC/F11 触屏状态，相关按钮均显示。测绘器始终显示“导入选区”“清除”，未选满两点点导入会给提示。框选提示是按钮上方独立的 Actionbar 风格短时消息，PC 同时保留右键选点、左键导入、潜行＋右键清除的操作说明，切换触屏时隐藏鼠标说明。已删除读取选区和导入成功的两条左上角通知。提示用原版 `hud_tip_text_background` 贴图；此前直接调用客户端 `SetTipMessage` 返回成功但实机截图未显示，因此没有依赖它。
- 世界测绘 PC 用右键选两点、左键导入；触屏轻触实际方块选两点，拖动只转视角。投影终端可右键打开工作台。现有代码仍拦截手持工具破坏方块。
- `docs/survey_golden_wireframe_preview.html` 是先前用户认可的金色线框 HTML 参考；游戏实现此后又调整了晶体亮度、线宽、点击面、环绕星光和碎片动画。旧版星空特效单独导出到 `extras/astral_survey_v1/` 和 `dist/astral_survey_v1.zip`，供其他模组迁移，勿误删。

## 关键代码位置

| 职责 | 路径 |
| --- | --- |
| 游戏输入、PC/触屏工具事件、UI 入口 | `behavior_pack/HelloScript/HelloClientSystem.py` |
| 服务端测绘选点与导入权限 | `behavior_pack/HelloScript/HelloServerSystem.py` |
| 测绘请求、客户端选区、捕获与投影桥接 | `behavior_pack/HelloScript/projection/bridge.py` |
| 工具 HUD 按钮与 Actionbar 风格提示 | `behavior_pack/HelloScript/projection/tool_hud.py`、`resource_pack/ui/ModernProjectionTools.json` |
| 金色测绘/金色和星空投影效果 | `behavior_pack/HelloScript/projection/survey_effects.py`、`resource_pack/shaders/glsl/modern_projection_survey_stars.*` |
| 投影外框与独立风格参数 | `behavior_pack/HelloScript/projection/projection_outline.py`、`outline_settings.py`、`resource_pack/shaders/glsl/modern_projection_*outline.*` |
| 草稿、建筑库和编辑状态 | `behavior_pack/HelloScript/projection/model.py`、`session.py`、`ui.py` |
| 聚焦测试与真实输入回归 | `tests/test_survey_effects.py`、`tests/test_bridge.py`、`tests/test_server_stream.py`、`tools/verify_world_tools.py` |

## 最近提交和验证

| 提交 | 内容 |
| --- | --- |
| `998218a` | 白色逐格测绘覆盖、原版风格工具按钮、客户端 Actionbar 风格提示、加快点击特效。 |
| `5e39214` | 三种可配置的投影外框、金色测绘效果、点击面识别、线宽/透明背景修正及旧特效迁移包。 |
| `cac5397` | 金色线框 HTML 预览。 |

`998218a` 的历史验证（非本轮最终状态）：`python -m unittest tests.test_survey_effects tests.test_bridge tests.test_server_stream -q` 为 **59 项通过**；`python tools/audit_runtime_imports.py` 为 **83 个运行时 Python 文件、违规 0**；JSON 和 `git diff --check` 通过。独立开发游戏截图确认白色逐格覆盖、金色框、按钮和 Actionbar 风格提示可见；最新 MCDK 错误日志为空。游戏资源更新需要重新加载；仅 Python 热更新或旧着色器缓存不足以证明最终观感。

本轮验证（2026-09-25）：`python -m unittest tests.test_client_entry tests.test_tool_hud tests.test_survey_effects tests.test_bridge tests.test_server_stream tests.test_tool_assets tests.test_tool_import tests.test_session tests.test_selection_outline -q` **111 项通过**；运行时模块审计 **83 文件、违规 0**，改动的 Python/JSON/材质语法及 `git diff --check` 通过。独立实例冷启动后，实机录屏确认较大的发光碎片出现、翻转、聚拢，并以同一端点实体重播；金色和星光外框均拍摄静态及动态证据，星芒的大小、明暗随时间变化。星光配色现在也保留共用亮芯和流动高光。最新版 MCDK 错误日志为空。旧实例曾有 `xupdate` 递归异常与旧资源残留，不能拿旧实例的录屏证明新着色器已加载。

原生 HUD 读回：两个按钮均为 **50×20**，顶边 Y=220；双行提示为 **159×26**，底边 Y=210，间隔 **10 UI 单位**，截图确认无重叠且 PC 操作说明可见。入口单元测试验证没有世界按键订阅、终端右键仍打开且不会重复入栈；运行时确认旧 `key` 方法已不存在。

**仍需复测：**真实 P 键与最新 PC/F11 HUD 点击未完成整轮端到端验证。`verify_entry.py` 本轮尝试真实按键时，Windows 以 `FOCUS_DENIED` 拒绝切回游戏，不能记为真实输入通过。`TerminalHudScreen.Create` 已包含 HUD 重建时清除旧显隐缓存的修正；需在有前台焦点时运行 `verify_entry.py` 和 `verify_world_tools.py`。不要把阶段 71/72 的旧 F11 通过记录当成最新版本的验证。旧回归工具的界面准备已改为显式工作台入口，只有 `verify_entry.py` 保留 P 键的负向检查。

## 调试与工作区状态

- 受管 MCDK 独立测试实例最近为 owner `fragments-final`，session 文件：`C:/Users/Happy2018new/.pyreact-debug/instances/2f32f8143bb84397801614103e842f9a/session.json`；旧 `golden-targeted92` 实例已正常停止。跨对话**先查 `instances.py status`**，不要假设它仍在运行；不要直接用默认 19133 端口或无绑定 MCP 调用。真实鼠标/键盘输入要确认当前窗口焦点，工具返回“已发送”也必须检查业务状态或截图。
- 最近证据在忽略 Git 的 `.runtime/`：`survey_fragment_formation.mp4`、`survey_fragment_preview.webp`、`survey_orbit_large_golden.png`、`survey_orbit_large_starry.png`、两种颜色同名前缀的 `.mp4`、`hud_final_verified.jpg`。可用 `tools/verify_survey_fragments.py` 重新录制；脚本只创建客户端临时特效并恢复相机和选点，不写世界方块或建筑库。
- 本轮将粒子、金色/星光框、HUD、文案与 P 键移除一并提交。用户自己的未跟踪文件 `GPT提示词-网易MC星穹线框方盒特效.md` 未纳入提交。**保留该文件，不要顺手提交、删除或覆盖。**
- 若继续修改效果，先读 `docs/OUTLINE_EFFECTS_ACCEPTANCE.md` 的历史验收矩阵，但以当前源码和本文件的最新状态为准；窄改动优先聚焦测试，扩展到渲染共享行为时再扩大实机范围。相关历史背景另见 `docs/MODERN_PROJECTION.md`、`docs/WORLD_TOOLS_71.md`、`docs/SURVEY_STARDUST_72.md`、`docs/VIEWPORT_PERFORMANCE.md`。
