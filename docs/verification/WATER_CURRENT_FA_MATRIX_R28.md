# R28 当前合源水：F 三路径与 A 通过，B 尚未采样

2026-10-23 凌晨，包含水池 GUI 几何修正和书本 GUI 回调的同一冻结共享源，已经完成 F 三路径的原固定矩阵和 A 可见动画／物理方向检查。root 已独立复核限定范围结果与关键原图。**整套当前水产品资格仍未完成，正式 owner／资格常量未修改，人工关闭数增加 0。**

此前 [水池私有候选专项](WATER_POOL_GEOMETRY_COLD_R28.md) 与 [旧 A 重放／F 水池失败](WATER_A_AND_POOL_READINESS_R28.md) 保留各自原结论与原始失败。本记录使用新的当前合源实测，不把旧私有 Scene 或旧 A 源重标成当前源接受。

## 同源、正常冷启动和原图

冻结共享基准提交为 `d6b4626cfc4397b23374e3cffdb479ae95bb8129`；source contract 为 `4e4eb7fff2b3dd8d6519ce70c7290c911f6c54ff2c9dbd0e7d3cf160a6b54749`。4,483 项源文件、1,391 项辅助文件逐字核对。已跟踪生产源对应该提交；既有未跟踪工具沿用原 raw SHA 单列冻结，**没有声称全部冻结文件都是 Git commit blobs**。

119,618,244B 的基 ZIP 复用，只叠加当前共享源的精确小 overlay，新项目逐字重构，没有硬链接。启动前后继续核对全部原 SHA。实际为正常冷启动、普通 Session 初始化、GUI2、物理窗口 1280 × 720；没有 bootstrap、没有在正式源预授全资格。每个阶段后独立恢复 Scene、世界与相机。

| 阶段 | 实际覆盖 | 原始静态 PNG | 原门结果 |
| --- | --- | --- | --- |
| F editor | 19 case、54 行 | 116 | 几何／透明度／alpha 有效，无失败 |
| F full | 19 case、54 行 | 116 | 几何／透明度／alpha 有效，无失败 |
| F missing | 19 case、54 行 | 116 | 几何／透明度／alpha 有效，无失败 |
| A | 三 route × 东／南／西／北／下落，15 cells | 30 | 可见动画与物理方向 15／15 通过 |

A 另有 15 段 3,200ms burst，每段 42 个有效帧，共 **630 张有效 PNG**。固定准备阶段保留首尾锚点 PNG 共 30 张；14 个请求前帧按原协议被拒，保留对应 receipt，没有算入 630 个有效帧。每段原最大帧间隔门仍为 150ms，分析 `capture_failures=[]`、`missing_requested_bursts=[]`。实际速度幅值与原生 RGB 完全一致均未作主张。

## F 合并原门与明确分析器

三份 F 由原 `qualifier.frozen_matrix` 合并，`passed=true`，19 case × 三 route 共 **57 coverage cells**：

| 项目 | 结果 |
| --- | --- |
| 南／东侧面 UV | 6／6 通过，mirrored／constant／wrong phase 负控均拒绝 |
| 独立隐藏／恢复可见性 | 54／54 通过 |
| 世界生命周期 | 108／108 通过 |
| 最大实际模型组 | 8，原模型预算通过 |
| `LiquidControls.update` | 334,044 样本；max 9.0001ms，p99 1.0002ms，原预算通过 |
| `LiquidPreview.advance` | 334,044 样本；max 7.9999ms，原预算通过 |
| `LiquidProjection.advance` | 1,497,824 样本；max 11.9998ms，原预算通过 |
| `WorldLiquidRenderer.advance` | 1,497,805 样本；max 11.9998ms，原预算通过 |

各单 route 的 `side_visibility_acceptance` 总值仍保持 false：editor 报告没有世界 owner／lifecycle 样本，world 报告没有 editor owner 样本。已有样本未测得超预算；没有手工把单 route 总值改成 true。上表的整体通过来自三 route 的原合并工具。

editor 池南／东侧面 correlation 约 `0.95620 / 0.95654`，RGB RMSE 约 `2.89458 / 2.96503`；full 与 missing 的 actual native API 南／东侧面 correlation 约 `0.96042 / 0.93330`，RGB RMSE 约 `2.61143 / 3.34762`。旧 analytic side 诊断仍保留，不拿它替换已声明的 actual native API 门。

第一版离线 driver 没有显式激活捕获前已绑定、已审核的单像素 AA seam extractor，F-full 分析因此报 `Native camera API hull disagrees with visible stone pixels`。原拒绝摘要没有覆盖。v2 driver 显式核对并激活原 extractor 与 3 正／9 负控，校验本次同会话 stone camera 的 12 项真实观测，并显式加载原 startup-v2 validator，root 再独立审核后重放。

本次 camera front／right silhouette IoU 为 `0.9800039`，tilted 为 `0.9647012`；camera `passed/completed/restored=true`。v2 没有改生产源、门限、ROI 或算法，没有用水像素拟合几何、RGB 或速度。editor 全链显式使用实际 SDK integer GUI 与 cached GUI 一致性；world 几何使用已审同会话 native stone 模型。独立 flow、biome、frozen visibility 等采样协议仍保留原接口与已声明边界。

| 原始／分析对象 | SHA-256 |
| --- | --- |
| F editor 原报告 | `81e63ef7f82cbc52c71f86f1d3d70591f21fabaa71f3492cea90b7b8af31f587` |
| F full 原报告 | `804e2d7d34742e5bfadce52de35116cb68c36cc8755f22df2b28acf0975df49a` |
| F missing 原报告 | `e8aa04f2757d3cd5bad22d9e192880d482d88fb9813c2171039b6c98336a538d` |
| A 原报告 | `eeb6b5fb80488df3e01a1dbcbcb1e358262369b52f62219f83ceabd0f45b36d9` |
| F 三路径合并分析 | `c70f532ef6c784ef9963d8c1981caa7540b14b94158f14d6a82392b82559820e` |
| A 方向分析 | `63588e391fa3647ba2cddf5b944ada2c9353c515b77349d494efc63cf6cb87e8` |
| F/A v3 摘要 | `a7198961984ea9dcd19de6e89ca7d09793034709f54ec3b6a9163d2133bc7a6f` |

## 首次 B 是 host 路径拒绝，未运行产品采样

F/A 后进入 B 时，旧 A 专用 host 的 `OUT` 仍固定为已有 `product-v2-a-v1.json`，fresh output 检查在 0.196 秒内拒绝：

> ValueError: Use fresh immutable result paths

B 没有发出产品采样 RPC，R/G 也没有执行。整个 group 的 `completed=false` 继续保留；不能写成 B 产品失败或整个 F/A/B/R/G 已通过。离线还发现同一 host 的 G routes 固定为三路径，没有按原计划限定 editor。

新独立 owner `water-r28-final-brg-v3` 只修正 stage→独立 OUT 和 G→editor-only 的 host 映射，逐字重构同源项目，保留旧 host 和失败报告。四 stage 的实际 AST 映射已经离线执行，核对 case／route 与 12 个独立、fresh 的结果／HANDLE／host 路径；group 只安排新同会话 camera→B→R→G，不重拍已通过 F/A。

root 已核对新 binding 的 28 个 host、49 个外部依赖、4,483 项源与 1,391 项辅助文件；这仍是静态准备，等待 root 另授 MC 槽。新 plan SHA 为 `f0475253b5ecfb76ca1ddacc5ababa2720c3a10673d93a55c9889bc6188b5f97`，host binding SHA 为 `650ccf133e74a3950f40e9d6a2a0897ca2386a7a404d10097ac75a550dcd51ef`。

## 恢复、退出与资源边界

camera、三个 F、A 各自独立恢复及最终恢复均为 true，源保持原字节。普通 stop 首次报告游戏未关闭；随后同句柄观察得到游戏退出码 **`0xC0000409`**、MCDK **`0x00000000`**，最终两个精确 creation identity absent。没有把 identity 消失解释为游戏以 code 0 正常退出。

registry 收尾与 helper retirement 均 exit 0；另外核对 observer、assert watcher、launcher 和 continuous HANDLE guard 的原 PID／creation identity，六个精确身份全部 absent。最终精确 release 审计 SHA 为 `398f305e39203089a370f8940c1087e45e3277986feade89bc1d28ff51970eda`。固定可用 commit、单进程 handles 与增长门没有放宽。

## 精简证据与后续

[本次证据索引](../evidence/water-current-FA-r28-v1/index.json) SHA 为 `ef62d338771f07204327f0a8508c662e3534f5a96302b938b08638fb38f1e307`。79 个对象、97 个存储文件，共 **6,532,301B**；最大单件 **239,000B**，5 张精选原 PNG 保持原字节，大图仅按原字节分块。四份完整捕获 JSON 与分析、原拒绝、恢复／退出、host、源 provenance 采用确定性压缩与必要脱敏，原始 SHA 与派生 SHA 分列。

378 张静态原图和 15 段 burst 的全部路径／字节数／SHA 均列入 runtime artifact 索引；630 张有效帧与 30 张 preparation 锚点只留 runtime，没有复制整套 burst 或大源码 ZIP。另路重构比对 77 个未变对象、重新计算 2 个脱敏对象，并核对 2,114 个精确 runtime 引用。root 独立重构全部对象，扫描 17,284 个 JSON／base64／转义解码对象，凭据发现数为 0。

当前仍须完成并审核 B 群系／missing 占位恢复、R 反向邻接／透明重叠、G 公共全览，再走 disposable provisional admission、正常冷启 D 和最终正式资格。D 需要新的独立 host：camera 保留 single-stone 观测，D 使用实际 Scene／GUI 读回，不把非单方块的产品测试套进石头夹具断言。静态准备不生成 owner 或资格，具体顺序见 [默认路径重新准入计划](WATER_DEFAULT_REQUALIFICATION_R28.md)。
