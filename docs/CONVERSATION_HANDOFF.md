# 新对话交接：现代化投影建筑编辑器

更新于 2026-09-24，工作区 `D:/Happy2018newの个人文件/GitHub/better-building-editor`，基于 `main` 的 `998218a`。此文档用于把当前项目和近期对话带入新任务；具体行为以当前源码为准。`docs/` 中的阶段报告保留当时的实现与测试记录，部分旧措辞已过期。

## 项目与约束

- 项目是网易 Minecraft 基岩版 ModSDK 建筑编辑器，行为包在 `behavior_pack/`，资源包在 `resource_pack/`。游戏内 Python 为 2.7；宿主测试和工具为 Python 3。
- 工作台可按 P 或使用可合成的投影终端打开；另一件可合成物品是投影测绘器。工作台提供三维编辑、建筑库、世界投影、材料目录和字符串分享/导入。
- 文档最大尺寸为 **64×128×64**，编辑视图始终显示整栋建筑，底层以 **16³** 分块维护原生模型；不要重新做成玩家必须切换分块的界面，也不要为相机旋转重建方块模型。
- 触屏模式跟随游戏原生输入状态；Windows 开发客户端用 **F11** 模拟切换，**不是 F12**。PC 与触屏的点击/拖动语义不同，应分别验证。Windows F11 模拟不能等同安卓真机。
- **只有 `behavior_pack/` 下的 Python 受网易模块白名单约束**；`tools/` 不受该要求限制。运行 `python tools/audit_runtime_imports.py` 检查。只用本地客户端实体绘制选区、投影与特效，不让其他玩家看见；世界写入和测绘导入由服务端按实际玩家身份鉴权。
- 本机建筑库经客户端配置保存，不是服务端多人共享库。世界测绘导入新建库条目并处理重名/满库，不覆盖当前草稿或已有配置。分享码使用压缩、Base64 和校验；它不是可信权限凭证。
- 项目 UI 使用内置的 Pyreact-MC 和原生 JsonUI，已同步过 Pyreact upstream 并保留本地兼容补丁。先看 `.agents/skills/pyreact-ui-building/SKILL.md`；实机调试先看 `.agents/skills/pyreact-debugging/SKILL.md`。

## 当前视觉与交互约定

- 建筑世界投影外框默认 **炫彩**，玩家也可选 **金色** 或 **星空**；每种风格各自保存流速、亮度、线宽等参数，金色/星空还支持环绕速度和晶体密度。三种主框默认实体棱线宽一致，正常世界前景仍应遮挡后方棱线。
- 测绘器的两点世界选区**固定金色**，不随投影外框设置改变。框线带 GPU 驱动的晶体、星芒与拖尾；两个选点有入场动画和常驻效果。点击原生方块面经过服务端验证后传回，不应随相机移动而改变。
- 最新提交恢复了测绘器选区的**半透明白色逐格覆盖**：复用本地测绘 guide 实体的 6 个透明面，不创建世界方块、不碰撞，也不新增实体。测绘 guide 以负密度标记启用覆盖；普通金色/星空投影 guide 不显示白罩。点击端点展开时长从 1.2 秒降到 **0.55 秒**。
- 投影终端和测绘器手持 HUD 使用原版灰色按钮贴图；无论 PC/F11 触屏状态，相关按钮均显示。测绘器始终显示“导入选区”“清除”，未选满两点点导入会给提示。框选提示是客户端 HUD 中 Actionbar 风格的短时消息，用原版 `hud_tip_text_background` 贴图；此前直接调用客户端 `SetTipMessage` 返回成功但实机截图未显示，因此没有依赖它。
- 世界测绘 PC 用右键选两点、左键导入；触屏轻触实际方块选两点，拖动只转视角。投影终端可右键打开工作台。现有代码仍拦截手持工具破坏方块。
- `docs/survey_golden_wireframe_preview.html` 是先前用户认可的金色线框 HTML 参考；游戏实现此后又调整了晶体亮度、线宽、点击面和白罩。旧版星空特效单独导出到 `extras/astral_survey_v1/` 和 `dist/astral_survey_v1.zip`，供其他模组迁移，勿误删。

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

最新提交验证：`python -m unittest tests.test_survey_effects tests.test_bridge tests.test_server_stream -q` 为 **59 项通过**；`python tools/audit_runtime_imports.py` 为 **83 个运行时 Python 文件、违规 0**；JSON 和 `git diff --check` 通过。独立开发游戏截图确认白色逐格覆盖、金色框、按钮和 Actionbar 风格提示可见；最新 MCDK 错误日志为空。游戏资源更新需要重新加载；仅 Python 热更新或旧着色器缓存不足以证明最终观感。

**仍需复测：**最新按钮改版后，PC/F11 的真正 HUD 点击没有完成整轮端到端验证。实机截图和运行时状态表明两个按钮可见；直接调用“未选满两点时导入”的业务入口会显示提示。但一次桌面点击未触发回调，随后 Windows 又以 `FOCUS_DENIED` 拒绝切回游戏，无法把它记作真实点击通过。`TerminalHudScreen.Create` 已加入 HUD 重建时清除旧显隐缓存的修正，仍应在游戏有前台焦点时重新验证按钮命中、清除与导入。不要把阶段 71/72 的旧 F11 通过记录当成最新 HUD 版本的验证。

## 调试与工作区状态

- 受管 MCDK 独立测试实例最近为 owner `golden-targeted92`，session 文件：`C:/Users/Happy2018new/.pyreact-debug/instances/d721184c9bd34af7b0e2407494dbf288/session.json`。跨对话**先查 `instances.py status`**，不要假设它仍在运行；不要直接用默认 19133 端口或无绑定 MCP 调用。真实鼠标/键盘输入要确认当前窗口焦点，工具返回“已发送”也必须检查业务状态或截图。
- 最近截图在忽略 Git 的 `.runtime/`，例如 `.runtime/survey_tiled.jpg`（逐格覆盖）和 `.runtime/survey_actionbar_final.jpg`（提示）；它们是本机临时证据，不是可移植产品文件。实机脚本只在独立开发世界运行，避免修改用户世界或库。
- 交接所依据的功能代码提交是 `998218a`；写文档前，工作区只剩用户自己的未跟踪文件 `GPT提示词-网易MC星穹线框方盒特效.md`。**保留该文件，不要顺手提交、删除或覆盖。**
- 若继续修改效果，先读 `docs/OUTLINE_EFFECTS_ACCEPTANCE.md` 的历史验收矩阵，但以当前源码和本文件的最新状态为准；窄改动优先聚焦测试，扩展到渲染共享行为时再扩大实机范围。相关历史背景另见 `docs/MODERN_PROJECTION.md`、`docs/WORLD_TOOLS_71.md`、`docs/SURVEY_STARDUST_72.md`、`docs/VIEWPORT_PERFORMANCE.md`。
