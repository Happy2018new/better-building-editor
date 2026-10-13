# 水面产品风格的独立验收

本轮按用户授权采用可接受的 Java 风格水面，版本为 `java_snapshot_water_v1`。它不要求逐像素复刻基岩版，也不改变 R11–R13 的原生几何、UV、alpha 失败记录。两个生产资格开关目前都为 `False`；必须完成实机验收后才启用产品风格。

## 模块边界

- `liquid_shape.py` 的产品规则读取完整建筑快照，计算四角高度、可见面与水平／下邻格流向；不模拟世界流体传播。
- `liquid_product_profile.py` 组合规则、贴图和经过校准的 UI／world 变换。相同水同时存在于前景／背景时仅绘制一次，原始双层与 actor 数据不变。
- `liquid_product_resource_data.py` 对应独立模型／材质命名空间，使用原版水贴图、单面向外三角形、alpha `.45` 和不写入液体深度的混合方式。4 个 vertex 和 6 个 fragment 的浮点、关键 varying 及 payload 保持 `highp`；实际宿主 GLES 精度为 23 位，不能据此声称安卓实机通过。
- 既有 `LiquidPreview`／`LiquidProjection` 继续拥有计划、模型和生命周期。产品 owner 指纹绑定 25 个运行时源码；资源、规则、风格和 owner 任一变化都需要重新生成并重新验收。
- `liquid_product_deployment.py` 要求八个独立 gate：编辑器、完整投影、缺失投影、透明度、几何、动画、生物群系和生命周期。宿主测试不会启用这些资格。

## 公开蓝图及对照

正常玩家可在测试蓝图分页的「水面与透明度」中打开 `test.layers.water_style`。14 个场景包含源水、低水位、对角水、下方排水、池塘、落水、四方向梯度，以及含水栅栏、玻璃板、台阶和楼梯。

`debug_product_water_blueprints.source_document(case, control)` 从相同公开蓝图抽取独立场景。含水场景有六种对照：`wet`、`dry`、`liquid_only`、`water_only`、`rearless`、`empty`。石块底座始终保留；后方金块距离为两格，删除金块不会改变水的直接邻格。透明度检查同时要求水的正向信号、无水时主体／后方金块的正向信号，以及含水时对应主体／后方金块的贡献。

## 实机执行条件与命令

目前启动诊断由主代理协调。水代理只使用一个受管实例，团队总数最多五个。禁止前台切换、窗口缩放、桌面输入和前台截图回退。WGC、无激活 DLL、MCDK 均使用已批准的固定 SHA；会话必须同时匹配 owner、项目、PID 和进程创建身份。

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

每帧检查位置／角度／FOV／引擎尺寸稳定，绑定同一会话标定的原始 FOV 和截图分辨率。编辑器检查相机、切面、平移、scene 尺寸及实际原生娃娃控件布局。全部六种同一场景的对照必须共享相机。WGC 帧检查后台状态、绑定、时间戳、PNG 尺寸和 SHA；任何缺失、漂移或恢复失败都禁止产生通过的产品 gate。

## 当前证据与剩余工作

19:10 的 `water-product-r14-v1` 在 ready 前退出。监督器在 37.19 秒内得到 `Owned game creation identity changed; refusing to bind`，后续共同诊断确认游戏访问冲突 `c0000005`。本次没有执行水探针、没有截图尝试，也没有 shader 或 Python traceback。前台保持原应用；受管 game／MCDK 的原进程创建身份已回收，配置已删除，批准二进制 SHA 未改变，清理错误为空。原始记录保存在本工作树 `.runtime/water-product-r14-v1/`；共同诊断见 `BACKGROUND_STARTUP_DIAGNOSIS_R14.md`。禁止把这种退出写成“不可靠截图”或进行相同条件盲目重启。

离线规则、相邻水连续性、实际三角形／UV／alpha 的宿主验证和 owner 测试已经完成；这些不替代游戏观察。捕获工具的 40 项相关回归通过，独立 QA 还构造了编辑器／world 各五种「各自稳定但相机不同」的对照，十种都被完整 analyzer 拒绝。

实机仍须完成：

- 首批源水、低水位、含水栅栏在编辑器与两种投影的几何、侧面裁切和主体／后方透视。
- 池塘接缝、落水、四方向流水顶面与四个侧面，以及普通贴图的持续动画节奏。
- 生物群系三种颜色预设、含水玻璃板／台阶／楼梯，以及切面、旋转、镜像和关闭／重开。
- 缺失投影中真实方块替代池塘一格后，剩余水仍使用完整源上下文；清除真实方块后恢复虚拟水。
- 实际 native 矩阵与 UI 本体绘制顺序、模型销毁、隐藏所有权、故障后保留原画面及重试。

`--extras` 当前采集动画、生物群系和缺失投影占据／恢复证据。它还没有采集四方向相机、切面及变换后的图像，因此这些项目保持待验收，不能仅凭报告完成标记关闭。

大版本升级时，更新仓库 dump 表后先运行规则／资源／owner 生成器并 diff 合同，再运行宿主规则与三角形回归，最后执行上述实机矩阵；不为新版本沿用旧资格 SHA。
