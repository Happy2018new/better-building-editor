# R28 水池裁剪修正：专项冷源结果与正式源边界

2026-10-23 凌晨，产品水的最小几何回调已通过一次正常冷启动的编辑器水池 wet/dry 专项：8 组水模型全部就绪，原先失败的 2 组取得有效 native ID，原始有水／无水图片完整显示水体和石台。**这只关闭该候选的水池就绪阻塞，当前整套水产品发布资格仍未完成，人工关闭数增加 0。**

此前的 A 原图重放、F 原始失败、根因推导和负控，继续保存在 [上一份专项记录](WATER_A_AND_POOL_READINESS_R28.md)。原失败报告未覆盖，也没有通过延长就绪超时绕过问题。

## 实际读回与画面

本次使用私有候选 `water-r28-pool-geometry-v1`，正常冷启动、普通 Session 初始化、GUI2、物理窗口 1280 × 720；没有 bootstrap，也没有给正式源预先授齐资格。源码基档复用旧 ZIP，仅叠加 2 个精确源文件，全部 5,873 项逐字核对。

| 检查 | 结果 |
| --- | --- |
| 水池 wet／dry | 完成 2 行、2 张原始 PNG，已实际打开检查 |
| 活跃水模型 | 8／8 request ready，native ID 与 renderer ID 一致，分别为 1—8 |
| 原失败批次 `(4, 0, 4)` | 2／2 就绪，renderer error 为 null |
| 实际 canvas | size `(340.625, 159.75)`，global `(153, 115.875)` |
| 实际 clip | size `(340, 159)`，global `(153, 116)`；保留原生取整差异 |
| 原推导 viewport | 与此次实际 canvas 一致；没有将实际 clip 的取整值冒充旧推导值 |
| 原失败框与此次实际 clip | 交集为 0；新框 8／8 与实际 clip 相交 |
| 逐组候选几何 | 与已审候选一致，误差小于 `1e-7` |
| 有效像素单位 | `scale × min(size) = 52.9092`，保持不变 |
| 原水池 geometry 门 | 通过 |
| 南／东侧面纹理 | correlation `0.95435 / 0.95537`，RGB RMSE `2.97831 / 3.07028`，原门限通过 |
| 反向纹理／常量纹理／错误相位负控 | 均被原门限拒绝 |

新失败框 geometry 为 position `(0, 0)`、size 约 `(366.6114, 780.4534)`。扩大的是承载水模型的 PaperDoll 矩形；Scene 用新尺寸重新计算 pose，因此原生模型的屏幕锚点和有效像素单位保持不变。

产品分析原报告有效、无捕获失败。完整 acceptance 的总值仍为 false：这场限定 editor pool 的专项没有生成 `LiquidProjection.advance`、`WorldLiquidRenderer.advance` 世界路径样本，亦未覆盖整套 visibility／lifecycle 矩阵，不能据此授齐门。实际已有编辑器 owner 样本均通过原预算，不能把“未采样”写成“已测超时”。

## 恢复与退出

独立恢复为 true，Scene、profile、timing、世界、相机锁及旋转、自有 markers／actors 均恢复，源码保持原字节。普通 stop 首次报告尚未关闭，随后精确 creation identity 均释放、registry 收尾和 helper retirement 完成。

同句柄观察最终记录游戏退出码 **`0xC0000409`**、MCDK 退出码 **`0x00000000`**。这是恢复完成后的实际退出事实；没有将身份消失写成游戏以 code 0 正常退出。未触发固定 handle／modal 资源门。

## 正式源最小合入与回归

正式产品水新增可选 `ui_geometry_for_gui(position, size, gui)` 回调。Scene 只在 liquid 分支优先调用它；没有几何回调的旧 profile，继续使用已有 GUI offset 或 legacy offset。当前 book 分支与 Scene 的其他文本均保持原样。没有全局改 `group_view()`，没有修改岩浆路径，资格和 owner 指纹数据未提前修改。

新增回归使用原失败矩形和实际 clip 检查，覆盖 GUI1／2／3／4／8／16／256、横竖比例、屏幕锚点、有效像素单位、非法 GUI／几何、回调优先级及两层 legacy fallback。通过执行当前 Scene 的实际 `liquid_view`／`liquid_pose` AST，同时验证新尺寸确实传给 pose。另有负控确认保留旧 raw scale 会改变 landscape 例的像素大小。

- Python 3 定点 57 项通过，包含书 GUI、液体 viewport 和产品 profile 既有回归。
- 真实 Python 2.7 的新 5 项通过，包含当前 Scene 的实际回调；两生产文件编译通过。
- 非零范围 review：product 文件 1 个、findings 0；Scene 范围文件 2 个，保留既有大函数 2 项和参数数目提示 1 项。

私有冷候选的 ProductWater 源文本与正式源修正相同；行尾原始字节分别记录。**私有 Scene 仍来自原 R27，只含 water hook，没有后来正式 book GUI 改动。** 因此这场私有冷测试不能直接授予最终合源版本的水资格。

## 保留证据与后续边界

[本次证据索引](../evidence/water-pool-geometry-cold-r28-v1/index.json) 的 SHA256 为 `b80ed8da25981f4f528ddb9b3001ab2b9495272338204b755be50b79eb3cdf5e`。97 个对象、103 个存储文件，共 2,599,682B；单文件不超过 240,000B，未收入大源码 ZIP。两张 PNG 保持原字节，原始与脱敏 SHA 分列，递归 JSON／base64／转义／本地凭据扫描无待处理项。root 在提交前另行独立审查。

原捕获报告 SHA256：`ad38db02fd590ba9157328ccc6a40fbf0310de20ed8feb7a6d52ba9ad3708156`。旧 A 与旧 F 证据仅按原 SHA 引用，不重新包装成新源结果。

资格工具的 `source_closure` 同时检查 `scene.py` 和 `liquid_product_deployment.py`，正式合源后需用当前冻结源补完整 F 三路径、当前 A 动画与方向、B 群系及 missing 占位恢复、R 反向邻接、G 公开全览；各门实际通过后才可走 disposable provisional admission，再做正常冷启动 D。已有离线算法、负控及资源可以复用，旧原图不能冒充新的源码接受证据。
