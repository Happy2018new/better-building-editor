# R27 红石线固定水纹对照：中文证据草稿

本文件仅供 root 审核后整理进正式开发文档。正式生产候选、人工验收与原始结果均未修改；本子任务人工关闭数仍为 **0**。

## 本次实际取得的结果

固定水纹后的含水反例完成了原定的 **12 个采集阶段**：不透明俯视、不透明低角度和默认透明度俯视，各自运行原实现、重复原实现、候选和恢复原实现。两个不透明视角内，四种模式的原严格红石线判据——ROI、线像素数、mask SHA 与 masked RGB SHA——全部相等。默认透明度仍沿原方案采集颜色与可见性，不把它冒充为同一条 RGB 全等门。

这意味着先前动画水场景在 `opaque_top_repeat` 发生的基线不稳定，在本次固定水纹对照中没有再次出现；本次也实际到达了含水候选与恢复阶段。这仍只是一组私有对照，不能因此证明先前每个变化像素的因果，也不能代表其余未运行反例已经通过。

**本次冻结 host 的最终湿场景结果仍是 `completed=true / restored=false`。** `cleanup_errors` 原样保留一条 `water_observer / AssertionError`；独立运行时状态审计则为 `restored=true`，水观察器的实际组件、类初始化函数、模块标记与模型存活账本均恢复成功。二者必须分列，不能用后续离线解码解释回填原报告。

## 离线复核明确发现的 host 解码缺陷

冻结的 `water_resource_mapping_v1.py:79` 比较参数账本时少解了一层。观察器先把实际成功 uniform 调用的 value 包装成可传输表示，随后导出完整 snapshot 时再次包装整本账本。冻结 host 解开外层后，直接拿仍然包装着的 tuple 字典与实际调用重建的 tuple 比较，因此严格拒绝。

独立的只读分析按照原始已存格式，对内部 value 再解一次。**48 份 snapshot 中累计 7,488 个参数账本条目全部与实际成功调用相等**；**288 次 active group 快照**的真实 handle、资源名、前 3 组 uniform 与可见性 uniform 全部对应。此处是对成功 native setter 回执的核对，不能称为独立 native readback，也没有引擎着色器时钟读回。

实际导出的 **864 次原生调用全部保留参数、顺序和真实返回值并成功**，包括 72 次模型创建、72 次模型删除、432 次 uniform 写入，以及位置、缩放、旋转和包围盒各 72 次。实际 `CreateFreeModel` 资源名均沿冻结的 model、material、vertex、fragment、mesh、skeleton 与 texture 文件解析到本次固定水纹片元；相关源文件 SHA 随分析保留。最终存活模型数为 0。

只读分析文件为 `fixed-water-v7-readonly-ledger-analysis.json`，SHA `8bf462a687ee54453a40469b4bf1d7aa77fd7f4fd07fce5393380a4c5d69f88b`。原始湿场景报告 SHA 为 `c5a08154aa945a5363c72bb04d672875c0fdfa6b0a5a23d296d020912270a3e0`；原报告、观察器、冻结 host、native 回执和判定均没有被改写。

## 固定输入、独立审查与干燥哨兵

新私有 owner 为 `wire-r27-fixed-water-v1`。它沿用了已独审通过的 v10 状态 mutex、原游戏 CRC32 分块、原 native palette 观察器、完整 phase JSON 和红石线候选。3,711 份项目源文件只有 3 份水片元着色器改变，每份仅把动画 clock 和相邻帧混合因子两个表达式固定为 0；没有改资源名、材质名、纹理、几何、顶点着色器、透明度、颜色和所有权。

root 逐字节独审了 3,928 个源文件／archive 条目，并独立实跑了 **14 项真实桌面 Python 2 观察器控制**和 **7 项 host 控制**。这些离线控制明确使用 fake native 或 fake transport，只验证转发、参数与返回／异常对象身份、预算拒绝、导出计数和恢复，不能冒充真实游戏功能验证。非空、嵌套包装的 uniform ledger 未被当时的 host 控制覆盖，本次真实湿场景补出了这个验证工具缺陷。

freeze SHA 为 `2cbdb2c4a90f0155530e3a733e5ddfbf55dbfc7b2ec02d2fafd3d01db68264df`，full manifest SHA 为 `c9071fb6e08a1a360a23189524c02571b1cdc0df7649d60bdd80320aa26ff2ee`。新增 243,421 字节、23 条目的 host／shader delta 继承既有 4 个 archive，没有重打约 119 MB 的完整 cold source；delta SHA 为 `d5e71ffa59d2d1b47c72e95091012d66f0132b48686445ad80f7dd37fa75c05b`。root 独审记录为 round 目录的 `root-wire-fixed-water-review-v1.json`，SHA `33f83f35917f92878481ca2ab3df2231afcf7b2dfb9bcf4cb9d72d44ed4ec56e`。

同一新会话先运行了 `flat-interior-fixed-water-actual-v7`，12 阶段完成、恢复成功、cleanup 为空、独立审计通过、源文件未变。其 report SHA 为 `0fb729faf7078d8b2305885d0493307cbfc549b66e6b48ff8444c2e2f681462c`。干燥场景 water native call 数为 0，此为合理的 dry 计数，未被拿来证明湿场景。root 打开 6 张原图后只批准线形与表观厚度哨兵，gate SHA 为 `c0ef77b19f08f6137a6d00fbd09ffc9bb050a96b74c4c42fcdac5f051a0b2665`。默认透明度的大亮十字消失，但细虚线轮廓仍在，因此不宣称完整颜色问题关闭。

## 原动画水失败与本次退场

原 v6 的 `negative-wet-wire-actual-v6` 仍保持 `completed=false / restored=true`：在候选之前的基线／重复阶段，1,998 个线像素的 mask 完全一致，但其中 1,557 个 RGB 像素改变，原严格门拒绝。原生 palette 输入、逻辑文档、相机和 screen 均一致，而隐藏原生 actor 后自定义水仍在动画。该轮没有实际 water native uniform、active group 或引擎时钟回执，所以当时只能提出动态水混合是强证据，不能声称逐像素因果已证。原 v6 证据和本次固定水纹证据分别保存，未互相覆盖。

本次在北京时间约 **07:07** 已执行普通 exact-owner stop，命令返回 0；retained native handle 实际观察到 game 退出码仍为 **`0xC0000409`**，MCDK 为 0。没有 native stack，不能将非零 game 退出归因于本候选、water observer 或其他指定组件。没有强制终止 game／MCDK，没有重启，也未启动第三个 fixture。

专属 assertion watcher 保持冻结的 **07:45 自行退出**计划，暂未修改 watcher 或提前强制结束。其最终身份和退出码将在 07:45 后保存独立补充 receipt。游戏／MCDK 的普通 stop 与 retained-handle 退出记录已保存于 `launch-v7-fixed-water`。本草稿不提前声称 watcher 已回收。

## 后续边界

本次提供了可用的固定水纹严格对照和真实 water native 调用证据，同时暴露并解释了 host 的内部值解码错误。后续应在新的 host 版本补上非空账本控制、独立审查与新冻结，再决定是否继续其他反例。本轮没有重新运行修正 host，没有放宽原门槛，没有进行生产晋升，也没有关闭人工问题。
