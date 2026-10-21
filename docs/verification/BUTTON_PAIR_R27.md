# R27：T02 原生按钮与支撑块的十阶段诊断

2026-10-22 早间对 T02 的按钮 `(3,3,27)` 与石支撑 `(3,4,27)` 完成三份原生模型、十阶段的独立绘制诊断。**Combined 对 support-only 有 261 个变化像素，范围与 button-only 的暗像素范围一致；四组双 Doll 的固定区域 RGB 原字节完全相同。** 原图中按钮轮廓主观不明显，不能据此声称按钮完全未绘制。本次没有产品修复，人工关闭数为 **0**；T02 的完整贴面、六面外观及变换验收继续开放。

前置的公开卡、12 阶段 full／single 相机比较见[普通公开卡与按钮观察](ORDINARY_PUBLIC_R27.md)，较早的方向数据和受控 missing 代表见[T02 方向记录](TRANSFORM_DIRECTIONS_R25.md)。本次补充保持同一冻结产品树，只增加私有诊断宿主，不改生产着色器、材质或变换算法。

## 固定来源与实验条件

| 项目 | 实际值及边界 |
| --- | --- |
| 冻结产品提交 | `2ab5a29a21f68bac607637b10d4afb42ac9caaa6`，复用既有 `.runtime/projects/r27-ordinary-public-v1`；不重新复制产品 |
| 最终 owner | `r27-button-separate-v3`；私有宿主 `button-separate-diagnostic-v3`，生命周期 `button-separate-lifecycle-v4` |
| Source manifest SHA-256 | `ff7bcee4290ea25261d9e736be6ae39f0fe2697fba383e61b75bf88f26e3f74e` |
| 最终 client／host SHA-256 | `ad525918ae5a14a2c5cf7e254f17b9a48f72b7ba2d00d9e4002cc76761dc6deb`／`27a7ea1119fda1fb461108dddf19d77078ac24d1646d00a815149f3b6aa22244` |
| 公开入口与文档 | 真实 `test.transforms.acceptance.t02` 及确认回调载入 60 格，正常 erase 58 格，只保留按钮和支撑；保持同一 editor／Document 及尺寸 `32×10×32` |
| 原生体积和输入 | 三份模型均为 `(Z,X,Y)=(16,16,10)`；button index `827`、support index `1083`。按钮为 `stone_button aux0`，`facing_direction=0`、`button_pressed_bit=False`；支撑为 `stone aux0` |
| 三份派生模型 | combined 保留原双格输入；button-only／support-only 仅过滤另一种 `common` 与对应 `states`，不缩小体积、不改保留格索引、状态或 flags。`eliminateAir=True`、`void=False`，`extra`／`extraStates`／`actor` 均空 |
| 固定显示状态 | full、yaw `35°`、pitch `−80°`、zoom `12`、depth `0`；原布局、相机 pan／pivot、tile tint packet、surface 和 pose 保持一致，复用原 tile 已挂载的两个 Doll |
| 资格边界 | 实际输入、原生创建返回、UI 提交与 frame gate 有记录；私有派生输入明确不具有生产 source certificate／自动像素验收资格。不写世界、玩家、物品栏或持久库 |

## 两次失败及修正

第一次 owner `r27-button-separate-v1` 使用 `diagnostic-v1`／`lifecycle-v2`，客户端构造阶段要求 `len(all owner tiles)==1`，在第 123 行失败；**原生模型创建 0 次、诊断阶段 0 个**。原 raw 显示完整尺寸仍有四个有效 owner，目标 `(0,0,1)` 含两格，其余三个为空 owner，不能把完整 Document 错当成只有一个 tile。失败原 raw SHA-256 为 `dfdab658e6de72bae6a51fc0886e282037213d22b2e67090bac4d11dd304b3e5`。后续只按严格来源链的 `source_link.owner_key` 选择唯一目标，保留 region membership 及其余来源绑定，未删除三个合法空 owner，也未收缩 Document。原 37 项控制加 3 项目标选择负控共 40 项在真正 Python 2.7 和 Python 3 通过，另有真实四 owner 形状的正例。

第二次 owner `r27-button-separate-v2` 使用 `diagnostic-v2`／`lifecycle-v3`，已准备 **3 份模型**；客户端完成首次 `combined_before` 提交并记录 **1 个部分阶段**，但宿主阶段记录 **0 个、阶段 PNG 0 张**。原因是 `submit_next()` 返回裸字符串标签，基类 `BlueprintCheck.run` 对字符串执行 `json.loads`，私有宿主遗漏了 `json.dumps`，产生 `JSONDecodeError`。这不是 watcher status 读取失败；原 transport 响应字节没有被捕获，不能把事后推导的标签称为已恢复的原 transport 响应。

最终 v3 私有宿主只修正该返回值封装并使用新 owner；客户端与第二次相同。实际基类 decoder 的两种 transport envelope、十标签共 20 个正控通过，对应旧裸标签 20 个负控均被拒绝；35 份生成 RPC 通过真正 Python 2.7 编译，构造／prepare／submit／restore 四个失败边界的 finally 清理控制通过。两次失败均独立恢复、普通 stop 并精确释放；游戏均以 `0xC0000409` 退出，MCDK 退出 0，均无 force，不能计为正常引擎退出或成功实机阶段。旧 raw、错误和派生修正保留在[历史失败及前检包](../evidence/button-pair-preflight-r27-v1/index.json)，不以最终成功覆盖失败记录。

## 实际完成的十阶段

下表顺序与最终 `button-separate-report.json` 及 `button_pair_<label>.png` 原件一致。root 与 transforms_r27 均打开全部十张原 PNG，后续另用独立 Pillow 脚本从原字节复算固定 ROI；ROI 指全图像素范围 `[575,300,715,450)`，不是整张图，也不是自动验收。

| 阶段 | Label | 实际绘制内容 | 原图／固定 ROI 观察 |
| --- | --- | --- | --- |
| 1 | `combined_before` | slot0：combined | 按钮轮廓主观不明显；对 support-only 有 261 个变化像素 |
| 2 | `button_slot0` | slot0：button-only | 按钮可见，保留单独 footprint 参照 |
| 3 | `button_slot1` | slot1：button-only | 按钮可见；与阶段 2 的 ROI RGB 原字节相同 |
| 4 | `support_slot0` | slot0：support-only | 支撑可见，作为固定差分基准 |
| 5 | `support_slot1` | slot1：support-only | 支撑可见；与阶段 4 的 ROI RGB 原字节相同 |
| 6 | `button0_support1_draw01` | 先 slot0 button，再 slot1 support | 按钮轮廓主观不明显；与阶段 7／8／9 的 ROI 原字节相同 |
| 7 | `button0_support1_draw10` | 先 slot1 support，再 slot0 button | 同上，改变提交顺序未改变该 ROI |
| 8 | `support0_button1_draw01` | 先 slot0 support，再 slot1 button | 同上，交换 slot 分配未改变该 ROI |
| 9 | `support0_button1_draw10` | 先 slot1 button，再 slot0 support | 同上，再改变提交顺序未改变该 ROI |
| 10 | `combined_after` | slot0：combined | 与阶段 1 的 ROI RGB 原字节相同 |

Combined 对 support-only 的 **261** 个变化像素位于全图 bbox `[627,366,665,402)`，最大 RGB 通道绝对差 **22**；该 bbox 与 button-only 按阈值 180 记录的暗像素 bbox 一致。四组双 Doll 各对 support-only 也有 261 个变化像素；四组之间的 ROI SHA-256 均为 `84029c064f336d1496aa77baf81d08ee5307664c032c9a63cabb2174b7fb9d85`。四组各对 combined 有 **71** 个变化像素、最大通道差 **20**，差异 bbox 为 `[627,366,665,385)`。这些事实支持按钮 footprint 有非零 RGB 影响，不支持“原图完全没有按钮 fragments”。

十张原图的 SHA、上述变化数、bbox、通道差、四组 ROI 原字节一致性及单模型换 slot／combined 前后一致性，已独立从保存原 PNG 复算。复算回执 SHA-256 为 `1f722a870c41ebd581c962cc8f084220b7dda2de1a54189690c1f0d63ceca7b5`，随最终包保存。原图主观观察与像素差量分别记录，两者都不能单独判定正确贴面或关闭用户验收。

## 归因仍未关闭

独立模型与 combined 都保留非零 footprint 影响，四种双 Doll 排列又给出相同 ROI，**仅凭 Combine 合并剔面不足以解释当前轮廓不明显**。但这不是原生顶点读回；没有实际 WORLDVIEW／GPU uniform 或 native vertex 数据，不能进一步认定删除了哪些面、depth 符号有错、模型按占用 bbox 重居中，或 UI 合成存在某个确定缺陷。

石按钮与石支撑的低对比，以及 pitch `−80°` 下侧面很窄，也仍是开放解释。后续首先需要匹配姿态的原生按钮贴石支撑参照，确认原生外观是否本就如此；不能因为当前尚未人工验收，就把该外观直接当成已证明缺画。上述观察也不扩展到全部六面按钮、全部 28 方向样本、X／Z 镜像、真实世界占用扫描或投影全部路径。

## 恢复与实际退出

最终诊断先恢复两个 Doll 及原模型／buffer，再执行真实 undo 回完整 60 格。主流程两次内部恢复审计均为 `session_restored=True`、`fields_equal=True`、factory／profile 相同；本次两次 `native_camera_exact=True`，旋转差 `[0,0,0]`。额外独立只读 after1 完成，`changed_keys=[]`、`camera_rotation_exact=True`、旋转差 `[0,0,0]`、`source_unchanged=True`。这是最终这次运行的精确结果，不回写此前曾有 roll 语义容差、exact=false 的历史运行。

随后普通 owned stop，通过同一进程句柄记录 game PID `55892`、creation identity `134370953162411880` 的实际退出码 **3221226505／`0xC0000409`**；MCDK PID `17328`、identity `134370953160040440` 退出 0。Registry finalize 和精确 watcher 回收完成，独立身份核验两进程均 `same_identity_live=false`、`resources_released=True`，`game_force_executed=False`。因此恢复／资源释放通过，**`normal_shutdown_qualified=False`**，不把普通 stop 返回成功等同正常引擎退出。

## 下一单变量方案：尚未实现或执行

下一允许窗口可保持原 native volume `(16,16,10)`，只把 support-only 占用沿逻辑 **Y+4** 平移，原 button 模型不变。原索引公式为 `index=y*16*16+x*16+z`：support 从 `1083`／local `(3,4,11)`／Document `(3,4,27)` 改为 `2107`／local `(3,8,11)`／Document `(3,8,27)`；button 仍为 `827`／local `(3,3,11)`。高度 8 在 native height 10 内。仅生成新的私有几何名，不覆盖既有模型，不改变生产 Document，也不为派生输入签发生产来源资格。

固定 shader／material、状态与 flags、相机／pan／pivot、Doll／surface／tint／pose、native volume 及提交顺序，只改这一格的索引。按现有 Camera.basis／projection，yaw35、pitch−80 的预期 affine 位移为 `dx=0`、`dy=−4*cos(−80°)*cell_unit≈−0.6945927107*cell_unit`，camera-toward 差约 `−3.939231012`。选择 Y 轴是为了降低水平四格平移越出 scissor 的风险；这是源码逻辑预期，不是已测 native GPU／像素位移。

实测前必须把原 cell unit、UI global layout、有效 DPI／客户区、capture metadata 与 scissor 绑定，不能直接由 zoom12 或 native scale4.31325 推算像素。最少比较同 slot 的原 support-only、Y+4 support-only、恢复原 support-only 三阶段并独立审计。不移动／位移不符时先排除裁切、比例和状态差异；匹配位移只会削弱 occupied-bounds 居中解释，并不证明 depth 正负或修复原贴面。本轮没有新启动该实验。

## 可重建的小证据包

| 包 | Index SHA-256 | 内容与大小 |
| --- | --- | --- |
| [历史失败及前检](../evidence/button-pair-preflight-r27-v1/index.json) | `9f5184abf49146c1d507ac070e12ab05585a7357fd147336bcbc55430692ffaf` | 187 条逻辑记录、15 文件、3,031,482 字节，最大 240,000 字节；含两次失败、恢复、宿主修正与返回协议控制，4 张原 PNG 无损 |
| [最终十阶段](../evidence/button-pair-runtime-r27-v1/index.json) | `17721cbd1fcdeeefc218aad8825d9bcbdd7ff82b5205da7171d36874e25fa174` | 83 条逻辑记录、71 个归档成员、18 文件、2,587,218 字节，最大 240,000 字节；12 张无损原 PNG 含十阶段与 baseline／restored，附独立像素复算及未执行方案 |

原件与脱敏派生件分开列 SHA，PNG 按原字节分片；最终包只引用历史包指纹，不重复打入历史 payload。两个包均已独立重建核对原件／内容／容器／分片哈希，并以真实凭据集合检查递归对象、嵌套 JSON 字符串及普通文本转义变体；嵌套与普通文本两个负控均被拒绝。安全打包和结构完整性不赋予像素验收资格，原 raw／未入包的完整 UI tree 继续留本地。本次不调整剩余产品工作量，也不增加人工关闭数。
