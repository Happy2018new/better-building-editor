# R23 三种不可见植物：编辑器与缺失投影补查

2026-10-19 的私有候选与正式主源冷副本均已在真实编辑器 PaperDoll 和北向缺失投影中显示金合欢树苗、脑纹珊瑚、气泡珊瑚，包含树苗 `aux=0` 与 `aux=1`；正式主源的三种植物完整投影四向也已补查。实际裁图均已查看，植物轮廓完整可见。这里验证的是固定居中交叉模型的可见性，**不是原生随机偏移、尺寸、含雪／含水或所有状态组合的验收；OB-03 仍开放，本专项关闭 0 项问题**。

正式冷副本的三张已读图联系图已逐字节保留为小型证据：[真实编辑器](evidence/plant-proxy-r23/formal-editor-20261019.png)、[北向缺失投影](evidence/plant-proxy-r23/formal-missing-north-20261019.png)、[完整投影四向](evidence/plant-proxy-r23/formal-full-four-20261019.png)，合计约0.77 MiB。没有再次缩放或重采样；原始全帧、捕获回执与详细报告的来源引用仍保留在正式JSON中。

## 含水边界补查（23:22）

**23:27用户纠正：原生水渲染早已被否决，水必须单独实现；原生岩浆已经接受。此次选择原生含水几何作为测试路线有误，以下仅为已否决旧路线的诊断，不是自制水方案的验收或再次要求用户确认原生水。下一轮必须先确认自制水renderer实际接入编辑器／投影，再验证含水珊瑚；岩浆保持已接受的原生方案。**

两种珊瑚的原生状态允许含水。16例[实际准备器核对](evidence/plant-proxy-r23/wet-cpu-boundary-20261019.json)确认，正向“珊瑚前景＋水背景”和反向逻辑层输入最终都映射到`ordinary_*`前景并保留water背景，源文档不变。`SNOW_QUALIFIED=False`只约束来源声明，不会在运行时排除含水组合；不能把它解释成湿格仍走旧路径。

随后原样主源冷副本补查真实编辑器和北向完整投影，每路包括空气、石头及两种珊瑚的两种层序，共12行显示／隐藏采样。两路实际图中脑纹珊瑚只有顶部粉色枝片明显可见，气泡珊瑚只有少量紫色顶部可见；水立方的侧面遮住大部分本体，两种层序外观相符。两层数据和实际native提交中的extra水均保留，不能据此接受完整植物外观或水渲染。

这次水几何来自ModSDK原生含水调色板合成，珊瑚为项目交叉模型，最终仍经过项目着色器／透明度。它不是原版世界直接放置的对照，也没有同源旧映射A/B，不能仅凭遮挡把问题归为原生行为或新增回归。[旧路线小包](evidence/plant-proxy-r23/wet-runtime-20261019.json)与两张联系图保留测试路径错误及数据，不提升任何水资格。发布前应在自制水renderer接入后完成含水三路径、实际占据与恢复；本轮源码保持冻结。

## 候选与实际路径

本次使用 `.runtime/projects/alpha-r23-proxy-v2` 中的私有候选，映射为 `modern_projection:diagnostic_r23_acacia_sapling`、`diagnostic_r23_brain_coral` 和 `diagnostic_r23_bubble_coral`。两种树苗状态共用同一静态模型。模型沿用已存在的居中交叉模板，保留双面 UV、两张零厚度交叉面及 atlas alpha 渲染；高度为一格，未拟合原生随机偏移。

维护源后续使用 `ordinary_` 标识；候选测试与正式资源的关联应以独立资源比较及正式冷启动结果分别记录。不能仅因标识改名就把旧实测说成正式源的实测。

真实编辑器固定 yaw 35°、pitch 25°、zoom 1.6。定位通过 Scene 的 `locate_selected()` 请求并等待实际消费，随后等待当前文档预览几何就绪；显示／隐藏针对真实 doll 控件。目标裁图来自实际视口和投影坐标，没有在游戏世界放实体冒充编辑器。

缺失投影沿用普通产品采集路径，只在私有运行时注入中明确设置 `projection_missing=True`，于全部为空气的高空 origin 检查北向显示。没有放置真实世界方块，因而不能据此接受已占用方块的消隐行为。

每条路径均包含同位空气及石头控制。表中数字为目标区域的检测信号，仅用于与控制比较；具体可见性结论来自实际原图和裁图。

| 样本 | 编辑器目标像素 | 北向缺失投影目标像素 |
| --- | ---: | ---: |
| 石头正控制 | 32,519 | 35,970 |
| 金合欢树苗 aux 0 | 15,270 | 18,371 |
| 金合欢树苗 aux 1 | 15,250 | 18,809 |
| 脑纹珊瑚 aux 0 | 15,058 | 18,757 |
| 气泡珊瑚 aux 0 | 15,117 | 17,745 |

## 可复查证据

可跟踪摘要为 `docs/evidence/plant-proxy-r23/editor-missing-v1.json`，含 12 行样本（每路径各六行）、原始显示／隐藏 PNG 与原生回执、裁图、联系图及工具 SHA256，并保留恢复和控制结果。大图仍位于本地 `.runtime`。

- 编辑器完整报告：`.runtime/round-20261019/plant-proxy-short-editor-v1.json`
- 编辑器已查看联系图：`.runtime/round-20261019/plant-proxy-short-editor-v1_contact.png`
- 缺失投影完整报告：`.runtime/round-20261019/plant-proxy-short-missing-v1.json`
- 缺失投影已查看联系图：`.runtime/round-20261019/plant-proxy-short-missing-v1_contact.png`
- 私有小型采集入口：`.runtime/plant-proxy-r23/capture_short.py`

两条路径均完成并恢复，文档、grid、选项、导航和游戏相机读回一致，无残留 active／preparing 投影，`cleanup_errors=[]`。编辑器报告包含其前后资源哈希不变。缺失投影后的资源哈希与编辑器结束时的四份快照文件一致；摘要明确记录这个跨阶段比较依据，没有将其写成缺失采集自身具有一份独立的即时采集前哈希。

本补查没有重新采集完整投影。此前主代理的完整投影四向检查属于独立报告，不能把它与本补查拼成已经完成原生外观一致性验收的结论。此前海带和牡丹北向仍未显示，也没有因这三种植物可见而被关闭。

## 正式接入与剩余工作

正式主源副本 `.runtime/projects/ordinary-final-r23-v1` 在冻结 `source-manifest.json` 后独立冷启动，owner 为 `ordinary-final-r23-v1`、game PID 48652、identity `134368939126504308`。它包含正式 `ordinary_` 植物标识和已集成的萤火虫贴图资源，使用未增加本轮 alpha 诊断补丁的主源材质；本次采集没有修改副本源码／资源，也没有重测萤火虫动画。

| 正式主源样本 | 真实编辑器 | 北向缺失投影 | 完整投影北／东／南／西 |
| --- | ---: | ---: | --- |
| 金合欢树苗 aux 0 | 15,448 | 21,827 | 20,230／23,251／24,435／18,064 |
| 金合欢树苗 aux 1 | 15,406 | 20,867 | 未在本次完整投影重测 |
| 脑纹珊瑚 aux 0 | 15,212 | 22,797 | 20,358／23,919／27,184／18,501 |
| 气泡珊瑚 aux 0 | 15,297 | 23,089 | 20,588／22,447／23,270／17,527 |

三个路径共 32 行采样：编辑器与北向缺失投影各六行，完整投影四向共 20 行，均含空气／石头控制。三张实际目标裁图联系图已查看，不以非零计数替代外观核对。正式报告依次为 `.runtime/round-20261019/plant-formal-short-editor-v1.json`、`plant-formal-short-missing-v1.json` 和 `plant-formal-full-four-v1.json`；联系图为同名前缀加 `_contact.png`。可跟踪小包为 `docs/evidence/plant-proxy-r23/formal-runtime-v1.json`，包含原图、原生回执、目标裁图及报告哈希。

新内置入口 `test.blocks.ordinary_plant_visibility`（“树苗与珊瑚 · 四向可见性”）已通过真实测试页及确认流程载入，当前编辑器几何就绪，文档精确包含四个石头支撑和四个植物状态，共八格，尺寸 16×5×8。原图 `.runtime/round-20261019/plant-formal-built-in-fixture-v1_test_blocks_ordinary_plant_visibility_native.png` 已查看，只确认载入和四组可见，不授予小构图的精细外观资格。完整入口报告为同目录 `plant-formal-built-in-fixture-v1.json`。

四份正式报告均完成、恢复并独立读回；文档、选项、导航、grid 和游戏相机恢复，无残留诊断标记、实体、active／preparing 投影。编辑器资源前后相同，完整投影所记录的 14 份源资源前后相同；编辑器结束到完整投影开始的四份共同资源哈希也相同，覆盖中间缺失采集的跨阶段比较依据。内置入口源文件未变。实例于 22:47 释放给主代理后由 `rail_renderer` 接管，未关闭游戏，之后仅整理离线证据。

正式生成器为 `tools/generate_ordinary_plant_proxies.py`，来源档案为 `tools/data/ordinary_plant_profiles_nemc_3.10.0.420447.json`，生成映射为 `behavior_pack/modern_projection/projection/ordinary_plant_data.py`。档案明确区分 NEMC 3.9 的当前方块注册表与 3.10 的纹理来源，绑定 palette／模板／纹理哈希及四个合法状态，并标记 `NATIVE_MESH_AUTHORITY=False`、`SNOW_QUALIFIED=False`。正式生成资源与候选的独立离线比较记录位于 `docs/evidence/plant-proxy-r23/formal-resource-review-v1.json`。

剩余范围包括原生尺寸与位置、原生随机偏移、含雪和含水组合、其他编辑器姿态、其他缺失投影方向、真实占用消隐及用户人工验收。`pixels_accepted=false` 保持不变，不把固定居中可见性扩展为整类树苗或珊瑚适配完成。

历史私有实例 `alpha-r23-proxy-v2` 于 2026-10-19 22:24 释放给主代理；正式主源 `ordinary-final-r23-v1` 的额外短验由主代理在 22:39 重新授予独占使用后进行，不能把两个实例的证据混写为同一次运行。
