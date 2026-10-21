# R27：普通公开卡与按钮相机诊断

本次使用精确提交 `2ab5a29a21f68bac607637b10d4afb42ac9caaa6` 的既有冻结产品树，未再次复制产品、修改渲染器或赋值候选 profile。新 owner 为 `r27-ordinary-public-v3`，辅助 manifest SHA256 为 `d3b14b5fe3006c946890229a57ad332f8229fca4b6a18931bc70b13ff19c28c8`；产品 archive SHA256 保持 `99047ecf32ac7f2c12af4a7834eb169a174e623e0a2720448d43cda33d185171`。3710 个 runtime／781 个 host 文件和四项关闭的热重载配置均逐项检查。实际采集时间为 10-22 04:27:52—04:32:20，新增人工关闭仍为 **0**。

## 空 padding owner 的证据修正

前一 owner `r27-ordinary-public-v2` 在首次 OB10 公共卡预检中报 `missing actual PreviewTile control`。只读原 raw 显示，文档边界内三个逻辑 owner 是空 padding；生产 `render_keys` 只请求有占用的 chunk，因此这些 padding 从未请求挂载 PreviewTile。前一原 raw 没有新 census、也没有空 owner 的完整 prepared native 输入，**它仍被新证书拒绝**，原 SHA256 `fcba439ba0eaaaf548d1109af8f82afd5fe26b0627f838efb6dc7faf9f0e0090` 保持不变。离线补充字段的重放正例明确没有实机资格。

本次 collector v4 对每个逻辑 owner 导出完整 prepared native 输入，并只读观察实际 `tiles.render_keys`、Scene／PreviewModels 的真实 Fiber identity、requested keys、实际 PreviewTile child keys 和 registry keys。host 仅对完整 source／前景／背景／actor／prepared 都空、name/cache model 为 None、count 为严格整数 0、pending 为 False、同一来源没有任何 native 创建尝试，且不在实际请求／Fiber／registry 内的逻辑 padding，允许没有 PreviewTile。非空 owner、实际 native 创建或任何 UI 矛盾继续拒绝；已挂载的可见、空模型、屏外／深度隐藏控件沿用原检查。

空 padding 只标 `verified_empty_owner`／`source_proven_empty_owner_unmounted`，`actual_native_front_observed`、模型可见及像素资格均为 false。原 27 项来源链与 18 项 signature 边界控制保留通过；新增 50 个逐条件破坏反例全部实际 `Rejected`，旧原 raw 仍拒绝，真正 Python2 stub collector 六阶段通过。主代理已独审窄 diff，独跑新增控制及配置 schema 正例／13 反例。实采 53 份证书中累计 15 个空 padding 观察走该窄路径，均没有 native front／可见性资格。

## 本次三项范围

| 公开卡／诊断 | 新取得的数据与入口证据 | 仍开放的外观范围 |
| --- | --- | --- |
| OB10 `test.blocks.concrete_neighbors` | 经真实 registry 分类、实际载入和确认按钮回调载入 66 格；完整 typed Document 对同源 builder 一致。保存编辑器和原生完整投影；受控 missing 对 `(4,1,8)` 混凝土支撑和 `(4,2,8)` 拉杆执行空／单格占用／两格占用／恢复空四阶段，各有 shown／hidden 原 PNG | 固定整体视角可见模型，但不是颜色匹配局部对照；不能关闭所有上方附着／红石邻居引起的颜色变化 |
| OB07 `test.blocks.dripleaf_states` | 经相同真实公开入口载入 104 格；编辑器、完整投影分别保留叶头 `(3,2,3)` 与孤立茎 `(3,2,23)` 视角；两格受控 missing 四阶段均有叶头／茎的 shown／hidden 原 PNG。前后完整 typed Document 不变 | 原编辑器 zoom2 为全场概览，各格像素不足以判局部几何；随后独立四张zoom12近景已补，主代理已读，两目标在yaw35／215均可见，见[近景补证](DRIPLEAF_CLOSEUP_R27.md)。不扩展为全部44组、茎叶关系或全部方向通过 |
| T02 两格相机诊断 | 从真实 60 格卡普通 erase 58 格，保持同一 Document／editor／尺寸，保留按钮 `(3,3,27)` 与 Y4 支撑 `(3,4,27)`；pitch −80→0→+80→−80，每角 full／singleY3／full 共12阶段。每阶段实际 native Serialize 均有 stone_button aux0；full 另有 stone aux0 支撑，single 无支撑。每角保存完整实际相机、原生 Scene 尺寸、actual UI front／poses、完整 native 序列化、原 PNG 及生产 OrbitCamera.ray 的明确重建结果。最后 undo 回全部60格 | 代表原图中 full 仅有明显支撑面，single 可辨小按钮；改变 pitch 后 full 可见性仍未解决。继续开放，未确认缓存、原生合并剔面、遮挡、aux 朝向或空间关系中的具体原因。重建 ray 不是原生渲染方向的直接观测 |

这12个 T02 阶段的完整 typed 语义均相同，原导出编码在**本次**也恰好相同；此前准备阶段 `chunks` 编码变化而 typed 语义相同的失败与诊断仍保留，不将本次结果推广为所有保存编码或原生 wire 字节一致。

总计 53 份完整 lineage raw／53 份 certificate、66 张原 PNG；累计 owner 观察包括110个可见 front、108个已挂载空 front、15个未请求挂载的空 padding、2个屏外／深度隐藏 owner。后两类都没有像素资格。受控 missing 临时替换此 owner 的读取，并不写世界，也不能代替真实世界占用扫描、玩家物理鼠标命中或周末人工验收。

## 恢复、实际退出与证据包

两次内部恢复审计通过；独立 before／after1 审计的 `changed_keys=[]`，相机语义与原 Document／editor／factory／profile／geometry覆盖／工具／工作区／标记恢复，冻结源和绑定 host 不变。运行最高 game handles869，最少可用 commit12,325,474,304字节。

04:33 执行普通 owned stop，未强杀游戏。保留同一进程句柄核验 game PID67824／creation identity134370879254792705 的实际退出 **`0xC0000409`**，MCDK PID16312／identity134370879252857769 退出0；因此 `normal_shutdown_qualified=false`。随后独立核验二者 `same_identity_live=false`，再仅回收 PID69520／对应创建 identity 的 watcher，exit0。进程对象可能暂时因保留句柄仍可枚举，不能把可枚举等同仍在运行，也不能将 stopped registry 记为正常引擎退出。

仓库安全小包为 `docs/evidence/ordinary-public-r27-v3-small/`，index SHA256 `ee6ebcf4d755d4f991354bd412f6ea42610630269ffbb26f544566ac2faddf8a`。196 条逻辑记录／86 个文件，总17,727,744字节、最大单件240,000字节。完整 raw／certificate、三个分报告、旧失败原 raw、私人 host／精确 diff／绑定与恢复记录均归档；18张重点原 PNG 保留字节一致的分片，66张原 PNG 全部列路径与原SHA，其余48张明确仅留本地。大型原 UI tree 只留本地，另有原路径／SHA／大小索引。

JSON 对象、列表、字符串中的 JSON 以及普通文本里的实际凭据和 JSON 转义变体均递归脱敏。索引分开记录原件与脱敏衍生内容 SHA；独立重建验证196条内容、178个归档成员、原件／内容／容器／分片SHA均通过，且实际凭据的嵌套JSON与普通文本两个负控均被拒绝。结构证书、图像差量和安全包核验均不能代替打开原 PNG 进行外观判断。

周末人工检查仍需分别记录 OB10 上方附着／邻居颜色，OB07 叶头、孤立茎、连接和各方向，以及 T02 full／single的按钮与支撑关系。本次没有新增产品修复，不应据此扣减产品外观待办或宣称新人工关闭。
