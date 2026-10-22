# 末地表面 GUI 锚点：隔离候选与下一轮必需验证

本目录是 **未合入、未授资格、未冷测** 的离线候选。生产源、metadata、水39项合同没有修改。候选中的旧资格常量仅作为 exact b70 基线字节保留，不能当作新实现的资格；不得把这两个候选文件直接覆盖到正在使用的产品项目或现有冻结项目。

## 候选和已有证据的范围

基线固定为 `b70ce7bf13ad6a4472f2b089ac812c162b174861`，`baseline/` 中的 `portal_profile.py` 和 `scene.py` 来自实际 Git blob，含原始换行。`candidate/` 只包含这两份文件的最小变更，差异见 `candidate.patch`：

1. `PortalProfile` 新增 `ui_offset_for_gui(size, gui)`，采用与已有 BookProfile 一致的正整数 GUI 校验和 `min(size)/float(gui)`；旧 `ui_offset(size)` 保留。
2. Scene 的 `portal_view` 与已有 book 路径一致，先获取可选 GUI hook，缺失或为 None 时调用旧 `ui_offset(size)`。其他 Scene 代码字节保持不变。

没有改模型、材质、世界投影、蓝图、注册、profile identity、qualification 常量或导入／事件边界。Scene 的液体和书本分支没有重构。结构审查的旧 Scene／tick 长函数和 Scene 参数数告警保留，后续重构另行安排，不在本次小候选中扩大范围。

V4 的 18 张真实原图和原生读回只证明了：**在旧实现的同一个 profile 实例上临时覆盖 `ui_offset`，会得到已记录的 A/B/A 锚点变化。** V4 没有调用这个新 `ui_offset_for_gui`，也没有执行候选 Scene hook；它不构成候选冷启、候选原生 GUI 读回或候选外观验收。

## 本目录已经实际执行的离线控制

`controls-py2.json` 来自真实 CPython **2.7.13**，`controls-py3.json` 来自真实 CPython **3.13.13**。两者均返回 0，并分别记录 interpreter 路径／SHA 与被编译文件 SHA。

- 编译了基线／候选两文件共 4 份真实完整源文件，另编译和执行了 exact b70 的纯 `cell.py` 支持模块。
- 实际执行基线／候选 PortalProfile；除新增方法外 profile 完整 AST 一致，实例 models／world_models／identity 等状态一致，旧 `ui_offset` 返回不变。
- 提取候选中的真实 `portal_view` 函数进行调用。未导入完整 Scene 或调用 SDK；`group_view` 返回值、Theme GUI、camera／Session closure 是明确模拟边界。
- 8 组整数／整数浮点 GUI 公式控制，包括 GUI2／3 的更正、GUI4 与旧算法相等；额外 GUI1／5 检查没有写死 2／3／4。
- 9 组实际 callback 分派：旧 profile 缺 hook、hook 显式 None、hook 存在，分别在 GUI2／3／4 验证实际调用次数／参数和自定义返回值；有 hook 时不调用 fallback。
- 同一个 callback 连续读取 GUI `2 → 3 → 4 → 2`，确认没有缓存首次 GUI。
- 12 种非法 GUI 明确拒绝：布尔、0、负值、小数、正负无限、NaN、字符串、None、list、dict。
- 用历史 V4 的 21 组尺寸检查候选公式等于 V4 B 的缓存 offset，并调用真实候选 callback 核对公式结果。**这 21 组仍是离线公式复用，不是候选原生读回。**
- 候选 portal callback 的 AST 与基线已有 book callback 在 profile／函数名称替换后相同。
- `git apply --check` 已在独立 baseline 目录只读验证补丁可应用。

候选和 exact 基线均已用 Minecraft Python review 实际扫描 2 个文件、parse 2／2 成功。两者相同的 3 个 finding key 均位于旧 Scene：2 个长函数 warning、1 个参数数 hint，无新增 finding。首次两次单模块 scope 因 fallback-directory 模式命中 0 文件，未作为通过；随后以本候选内仅有的 2 个文件为范围完成审查。

首次准备脚本因 `scene.py` 的 Git blob 原本为 CRLF、初始替换只匹配 LF 而明确失败，原脚本／失败收据保存在 `preparation-failure-v1/`。修正仅保留各 blob 自身换行再作精确替换，没有更改基线原件。完整产品边界 45 项在准备前后逐项核 SHA 相同。

## 下一计划窗口：先重新建立源合同

下一轮必须重新审阅候选与届时主线的差异；若期间主线源发生变化，从最新批准源重新派生候选，不能无条件套用 b70 补丁。获得计划窗口中的实际 MC 槽和 owner／host 授权后，建立新的独立项目与 source／host 清单，保留本目录、V3／V4 和所有失败原件。

`projection/scene.py` 是水39项生产边界的一项。当前水合同对该项的规范化 SHA 为：

`61cac0b4578a834996a54dc8a4c2649e372ec084d6393406febd9390aaa82209`

这个候选的 Scene 规范化 SHA 为：

`1ef11e02b56caa607e1f8d1269e2c6ba59ef1a86dd0ae5990d6666e93b601fad`

规范化仅为 CRLF→LF，与官方 generator 一致。即使液体分支本身未变，39项整体合同也已经漂移，旧 owner／qualification 指纹不能声称覆盖候选。

正式实现若继续推进，需要在独立候选工程按官方流程重新生成并检查：

- `tools/data/liquid_product_owner_contract_v1.json`；
- `behavior_pack/modern_projection/projection/liquid_product_owner_data.py`；
- 在完成新源证据、冷启和审阅后，由原 `tools/qualify_water_product_r16.py` 正式生成 `liquid_product_qualification_data.py`。

工具仍使用已有 `tools/generate_liquid_product_owner_contract.py`、其 `--check` 和只读 owner checker。**本目录没有运行生成写入或 qualifier，也没有预先写入任何这三份文件。** source／resource manifest、39项源、运行辅助文件和注册资源均须绑定到实际新工程；若还存在其他共享源变化，要按实际闭包重新核算，不只记录这个两文件补丁。

## 水的 16 个正式 gate：全部需要新源处理

下表是下一轮处理要求，不是本次通过结果。现有产品保持原资格，候选的全部 gate 仍待新源验证；不得复制旧 manifest、修改旧报告 source hash，或把旧 `true` 直接改绑到新 Scene。

| 正式 gate | 下一轮须取得／核验的新源证据 |
| --- | --- |
| editor | 新 Scene 下真实编辑器路径、native GUI／cache 及可见性 |
| projection_full | 完整投影原路径和 source／owner 绑定 |
| projection_missing | missing 原路径及精确占位／撤销恢复 |
| geometry | 原 F 矩阵及各路径既定几何门；保留历史泛用诊断差异 |
| transparency | 原 F 同相位独立透明度门，不能用 D 动态失败重标替代 |
| visibility | 三路径原公共矩阵可见贡献与原 mask／ROI |
| side_uv | 原 UV 门与既有 source shapes／faces 合同 |
| budgets | 原配置／实测 model、CPU／生命周期预算 |
| lifecycle | owner 创建／发布／释放、恢复审计与资源回收 |
| animation | A 的三路径 × 东南西北下落；允许自然动画，不冻结时间 |
| biome | B 的原群系颜色控制及 missing 精确恢复 |
| neighbors | 原邻接 case／source cells／shape 一致性 |
| transparent_overlap | 原透明重叠 case 与独立可见性 |
| public_gallery | G 的完整公共全览及可见贡献；不扩大成逐 case 精确几何 |
| occupancy | 各路径既定占位、移除和撤销恢复 |
| default_path | 新源普通冷启动 D，自然初始化，不指定候选 profile／bootstrap |

按原 F/A/B/R/G/D 职责矩阵取得符合新 source closure 的报告，并通过原官方资格工具重新计算这 16 个 gate。旧证据仅能保留作历史对照；只有原官方 source 检查明确认可的证据才可输入新资格，不以“液体分支没变”自行豁免。若需要 disposable provisional admission，它只用于独立工程的冷启 D，保留 `default_path=false`，不得复制到共享产品。最后的正式 qualifier 仍需新的 default report、原生世界几何／编辑器 GUI 选项及明确审阅，由负责最终合入的 root 执行。

## portal 候选必须另做普通冷测

下一窗口的 portal 最低新增证据是：新的 source／host freeze 后，**普通冷启动自然进入产品路径**，确认实际 profile 的 GUI-aware 方法与 Scene callback 来自该源文件；不再安装 V4 的实例 `ui_offset` 覆盖，不热重载替换产品代码。

1. 对 end gateway 和 end portal，读取实际 native GUI2／3／4；保留与 V4 相同的物理客户区和可追踪相机、文档、group／model／uniform／ancestry 读回。
2. 每次 WGC 捕获前后读回实际位置、尺寸和 active front，确认新 hook 已实际调用；GUI2／3 应与已固定的更正公式一致，GUI4 相对基线保持零差异。
3. 独立打开候选原始图，确认表面与石基座关系；公式、缓存矩形或纯离线 callback 不能代替可见原生效果。
4. 对完整投影／missing／占位恢复执行必要回归，确保未把编辑器锚点修正误用于世界路径。若继续更新 portal 产品资格，按 `tools/qualify_portal_product_r16.py` 的原 12 门重新处理 editor、transform、zoom、layers、cutaway、animation、projection_full、projection_missing、occupancy、restoration、opacity、default_path；不得继承旧 profile SHA 冒充新源资格。
5. 保留两次独立恢复审计、原窗口恢复、普通 stop 返回值、完整 grace、实际异常退出码和所有精确身份释放。失败不重标、不用补拍覆盖；需要新尝试时使用新 owner 和独立授权。

本候选只解决编辑器 GUI 锚点。亮度、星点密度／速度／方向、原生候选和世界原生表面的其余未关闭问题维持原状态。**本轮默认不合入；人工关闭数 0。**
