# 水面产品风格的独立验收

本轮按用户授权采用可接受的 Java 风格水面，版本为 `java_snapshot_water_v1`。它不要求逐像素复刻基岩版，也不改变 R11–R13 的原生几何、UV、alpha 失败记录。两个生产资格开关目前都为 `False`；必须完成实机验收后才启用产品风格。

## 模块边界

- `liquid_shape.py` 的产品规则读取完整建筑快照，计算四角高度、可见面与水平／下邻格流向；不模拟世界流体传播。
- `liquid_product_profile.py` 组合规则、贴图和经过校准的 UI／world 变换。相同水同时存在于前景／背景时仅绘制一次，原始双层与 actor 数据不变。
- `liquid_product_resource_data.py` 对应独立模型／材质命名空间，使用原版水贴图、单面向外三角形、alpha `.45` 和不写入液体深度的混合方式。4 个 vertex 和 6 个 fragment 的浮点、关键 varying 及 payload 保持 `highp`；实际宿主 GLES 精度为 23 位，不能据此声称安卓实机通过。
- 既有 `LiquidPreview`／`LiquidProjection` 继续拥有计划、模型和生命周期。产品 owner 指纹绑定生成器列出的运行时源码（当前 root 集成版本为 26 个，包含 `projection_companions.py`）；资源、规则、风格和 owner 任一变化都需要重新生成并重新验收。不得用旧工作树的 25-source 指纹验收新集成版本。
- `liquid_product_deployment.py` 要求八个独立 gate：编辑器、完整投影、缺失投影、透明度、几何、动画、生物群系和生命周期。宿主测试不会启用这些资格。

## 公开蓝图及对照

正常玩家可在测试蓝图分页的「水面与透明度」中打开 `test.layers.water_style`。14 个场景包含源水、低水位、对角水、下方排水、池塘、落水、四方向梯度，以及含水栅栏、玻璃板、台阶和楼梯。

`debug_product_water_blueprints.source_document(case, control)` 从相同公开蓝图抽取独立场景。含水场景有六种对照：`wet`、`dry`、`liquid_only`、`water_only`、`rearless`、`empty`。石块底座始终保留；后方金块距离为两格，删除金块不会改变水的直接邻格。透明度检查同时要求水的正向信号、无水时主体／后方金块的正向信号，以及含水时对应主体／后方金块的贡献。

## 实机执行条件与命令

目前启动诊断由主代理协调。水代理只使用一个受管实例，团队总数最多五个。测试程序禁止主动切换前台、窗口缩放、桌面输入和前台截图回退。用户可以随时手动将游戏切到前台；这不会暂停测试，也不会成为关闭游戏的理由。通过显式 `MCDEV_ALLOW_USER_FOREGROUND=1` 允许这一行为，默认测试仍要求后台。允许前台的帧必须如实记录前台策略和窗口状态，不得标成后台帧。WGC、无激活 DLL、MCDK 均使用已批准的固定 SHA；会话必须同时匹配 owner、项目、PID 和进程创建身份。最小化、进程身份变化、失去无激活窗口样式或无法取得可信 WGC 帧仍是失败。

游戏启动前，监督器调用 `probe_product_water.snapshot_sources(project_root)` 保存 `launch-inputs.json`。快照覆盖完整 BP／RP、顶层宿主工具及调试 skill 脚本，排除 Python 缓存。不得在游戏启动后修改这些输入，再把新代码归入旧进程的验收。探针开始／恢复后都检查这份快照。

先在同一个会话运行石块相机标定：

```powershell
python -X utf8 tools/verify_camera_projection.py <camera.json> --native-resolution --fixture-lift-y -6
```

监督器需要设定 `MCDEV_SESSION_FILE`、`MCDEV_OWNER`、`MCDEV_NATIVE_CAPTURE_HELPER`（本项目 `tools/capture_native_window.py`）和批准的 `MCDEV_NATIVE_CAPTURE_EXE`。标定必须通过、恢复成功、无清理错误，且对应同一个受管 session。

第一批冻结纹理烟雾检查：

```powershell
python -X utf8 tools/probe_product_water.py --session <session.json> --owner <owner> --capture-exe <approved-wgc.exe> --launch-inputs <launch-inputs.json> --camera-calibration <camera.json> --output <water-frozen.json> --case source --case low --case wet_oak_fence --frozen --max-seconds 650
python -X utf8 tools/analyze_product_water.py <water-frozen.json> <water-frozen-analysis.json>
```

探针通过普通 Scene 和投影 owner 运行编辑器／完整／缺失三条路径。world fixture 位于玩家脚部上方两格，预留 216 个已验证为空的格子，不改玩家位置；仅缺失投影占据测试写入真实方块。finally 恢复工作区、profile、网格、投影、世界、流动开关、天气、时间、相机、HUD 和云设置，并保留恢复错误。

每帧检查位置／角度／FOV／引擎尺寸稳定，绑定同一会话标定的原始 FOV 和截图分辨率。编辑器检查相机、切面、平移、scene 尺寸及实际原生娃娃控件布局。全部六种同一场景的对照必须共享相机。WGC 帧检查明确的前台策略、窗口状态、绑定、时间戳、PNG 尺寸和 SHA；任何缺失、漂移或恢复失败都禁止产生通过的产品 gate。旧格式的后台帧不因新策略而获得豁免。

尺寸有三种单位，不能互相当作同一数值：Windows 默认 Python 线程可能读取逻辑客户区尺寸；WGC 返回物理客户区像素；游戏 `GetScreenSize` 返回 UI 尺寸并受 GUI scale 影响。捕获端需在局部 per-monitor-v2 DPI 线程上下文读取物理客户区并与 WGC／PNG 严格比较，之后恢复原线程上下文，不按显示缩放猜测或放宽容差。相机合同分别保存游戏 `engine_screen` 与物理 `capture_size`；world 几何使用截图像素，editor 原生 UI 坐标按各自完整视口转换，两种视口均必须在配对捕获期间稳定。

## 当前证据与剩余工作

19:10 的 `water-product-r14-v1` 在 ready 前退出。监督器在 37.19 秒内得到 `Owned game creation identity changed; refusing to bind`，后续共同诊断确认游戏访问冲突 `c0000005`。本次没有执行水探针、没有截图尝试，也没有 shader 或 Python traceback。前台保持原应用；受管 game／MCDK 的原进程创建身份已回收，配置已删除，批准二进制 SHA 未改变，清理错误为空。原始记录保存在本工作树 `.runtime/water-product-r14-v1/`；共同诊断见 `BACKGROUND_STARTUP_DIAGNOSIS_R14.md`。禁止把这种退出写成“不可靠截图”或进行相同条件盲目重启。

20:05 的 root 项目 `water-product-r14-v2-root` 已进入实际世界和工作区，并取得六张有效 WGC 石块标定截图（front／right／tilted 的 shown＋hidden）。用户手动将游戏切到前台后，旧监督器在 104.95 秒时把前台状态错误地当作护栏失败，即使无激活样式仍有效。它随后发起 WM_CLOSE，再在正常关闭超时后回收精确匹配身份的自有进程；115.86 秒结束，清理错误为空、原配置按字节恢复、game／MCDK 身份均已消失、二进制 pins 不变。20:05:46 的 `ucrtbase.dll c0000409` 出现在监督器发起关闭之后，不能作为未解释的水资源启动崩溃。该次相机报告仅登记了 front／right，`passed`、`completed`、`restored` 均未通过，水探针尚未执行。原件保留在 root `.runtime/water-product-r14-v2-root/`，不会与之后的重试混用。

20:30 的 `water-product-r14-v3-root` 在新前台策略下进入世界，首次石块 shown 捕获取得 fresh、非空的 `1994×1105` WGC PNG。新增尺寸门控将 Python 默认 DPI 线程下的 `1329×736` 逻辑客户区错误地与实际像素比较并拒绝，因此相机 `views` 为空、水探针未执行。相机自身全部恢复成功；监督器 94.32 秒结束，清理错误为空、原配置按字节恢复、game／MCDK 的准确创建身份均已回收、pins 不变。已实际查看 PNG，石块可见，画面显示 GUI scale 为 `4.0`；前一次 v2 相机 `GetScreenSize=[499,277]` 也说明 UI／截图并非同一种尺寸。原件保留在 root `.runtime/water-product-r14-v3-root/`；这是一项捕获工具的单位错误，不能归因于水材质或算作水验收成功。

20:41 的 `water-product-r14-v4-root` 使用局部物理 DPI 上下文后，取得完整六张石块截图并完成 front／right／tilted 三视角独立标定：`completed/restored/passed=True`，清理错误为空，实际有效垂直 FOV 为 `66.5` 度，SDK 原始 FOV 为 `60`，游戏 UI 视口为 `499×277`、物理 PNG 为 `1994×1105`。该标定只属于当次受管会话，其他会话须重新运行，不能借用成功标志或仅复制标量。

v4 水探针在第一次编辑器截图前被精确姿态门控拒绝：首次 `scene_ready` 的 zoom 为 `4.599760046768113`，随后相机动画精确到位为 `4.6`，导致几何和原生 doll 坐标正常变化。并非 tuple／list 格式问题，没有产生有效水 PNG。相机和水探针均恢复成功，134.65 秒内完成精确实例回收，原配置恢复、清理错误为空、来源指纹不变。修复后的探针要求相机与 pan 精确达到请求值，且两次连续原生布局完全相同，再冻结 ready 状态；捕获前后及全部对照的原有精确门控保持不变。三项新回归包含当次动画数字、原生坐标轻微变化、后端重新 pending 和错误视角；不放宽数值容差。原件保留在 root `.runtime/water-product-r14-v4-root/`。

20:55 的 `water-product-r14-v5-root` 首次完整取得水证据：同会话石块标定通过，源水取得六张 wet／dry 截图，低水位和含水橡木栅栏取得二十四张截图，覆盖编辑器、完整投影、缺失投影。两份报告均 `completed/restored/source_unchanged=True`、清理错误为空；两份 analyzer 均 `evidence_valid/captures_verified=True`、捕获失败为空。监督器在 264.68 秒结束，原配置按字节恢复、game `24912` 与 MCDK `26448` 的准确创建身份均已回收、pins 不变。证据原件位于 root `.runtime/water-product-r14-v5-root/`。

v5 的源水三路线 IoU 分别为 `.670586/.630662/.630662`，编辑器外缘最大误差为 `42` 像素；低水位分别为 `.327884/.264177/.284137`，均未通过几何门控。实际查看编辑器和完整投影的源水 PNG，水呈现顶面缺失、近侧面未显示的壳状外观。当前假设是原生正面剔除约定与宿主 GLES 验证不同，尚未确认；不能通过放宽几何容差或启用双面绘制把它标成通过。含水栅栏六种独立对照的主体和后方贡献三路线通过：编辑器主体／后方均分别有 `560/440` 个有效贡献像素，两种投影分别有 `300/210` 个。该结果仅证明这次错误几何下可以看到主体和后方，修复剔除后必须重新验证透明度，不启用任何生产资格。

剔除核对的原生依据是安装版 `vanilla/materials/shadows.material` 的 `shadow_back` 和 `vanilla_netease/materials/entity.material` 的 `netease_entity_outline`，二者明确使用 `InvertCulling`；原生 `entity_for_skeleton_alpha` 只设置 `Blending/DisableDepthWrite`。当前产品模型沿用共享诊断 mesh 的 `(0,2,1)/(0,3,2)` 索引，产品材质无 `InvertCulling`；world shader 还包含 Z 轴反号。宿主实际三角形测试明确使用 `gl.frontFace(gl.CCW)`，不能由此推断原生正面约定。修正须限定产品材质或独立产品模型，保留共享诊断资源及旧失败合同。

离线规则、相邻水连续性、实际三角形／UV／alpha 的宿主验证和 owner 测试已经完成；这些不替代游戏观察。捕获工具的 40 项相关回归通过，独立 QA 还构造了编辑器／world 各五种「各自稳定但相机不同」的对照，十种都被完整 analyzer 拒绝。

实机仍须完成：

- 首批源水、低水位、含水栅栏在编辑器与两种投影的几何、侧面裁切和主体／后方透视。
- 池塘接缝、落水、四方向流水顶面与四个侧面，以及普通贴图的持续动画节奏。
- 生物群系三种颜色预设、含水玻璃板／台阶／楼梯，以及切面、旋转、镜像和关闭／重开。
- 缺失投影中真实方块替代池塘一格后，剩余水仍使用完整源上下文；清除真实方块后恢复虚拟水。
- 实际 native 矩阵与 UI 本体绘制顺序、模型销毁、隐藏所有权、故障后保留原画面及重试。

`--extras` 当前采集动画、生物群系和缺失投影占据／恢复证据。它还没有采集四方向相机、切面及变换后的图像，因此这些项目保持待验收，不能仅凭报告完成标记关闭。

大版本升级时，更新仓库 dump 表后先运行规则／资源／owner 生成器并 diff 合同，再运行宿主规则与三角形回归，最后执行上述实机矩阵；不为新版本沿用旧资格 SHA。
