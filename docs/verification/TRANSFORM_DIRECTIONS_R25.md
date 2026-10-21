# R25：T02楼梯、半砖与附着方向公开蓝图

2026-10-21恢复窗口新增公开卡 `test.transforms.acceptance.t02`，入口为“测试蓝图 → 变换 → T02 · 楼梯、半砖与附着方向”，本地提交 `900100aa402f7442b1f1cf6cf1554f1f3d76fd14`。本次增加可直接载入的人工场景和独立方向断言，不改变生产变换算法；用户人工关闭数为0。

蓝图尺寸32×10×32，含60格：28格受测方块、28格stone支撑和4格彩色角标。初始选区为 `(1,1,1)` 至 `(21,6,30)`，使用非正方范围检查旋转包围盒。X列为3／8／13／18；从前到后依次为四向正楼梯（Z=3）、四向倒楼梯（Z=7）、上下oak_slab（Z=11，仅两格）、四向关闭／打开活板门（Z=15／19，上下半交错）、四向梯子（Z=23，facing=2／3／4／5）及六面stone_button（Z=27／29，facing=0—5）。梯子背后和按钮对应面均有支撑，按钮初始未按下。不创建原生不存在的倒置梯子状态，也不模拟红石更新。

建议人工先做Y镜像及撤销，再做Y轴90°旋转及撤销：检查楼梯与半砖上下关系、活板门开启面、梯子和按钮是否仍贴对应支撑。已有梯子或某种模型缺画时登记渲染阻塞，不把它解释成坐标变换通过或失败。入口不要求用户自己编辑NBT或搭结构。

离线新增两项业务检查，用独立的带符号矩阵与明确面法向检查六种公开Editor操作：原生合法上下半、四向梯子、六面按钮、支撑坐标及按钮不凭空按下。原有通用用例也对新卡执行合法registry／storage、逆操作、撤销／重做及无漂移检查。Python3的 `test_transform_acceptance.py` 共14项通过，`test_debug_blueprints.py` 共18项通过；MCP定点review扫描1文件、无发现。

真实Python2.7和Python3另执行公开注册、保存载回、60格及六操作历史往返，JSON结果逐项相等。首次Python2宿主因unicode工作路径与 `os.getcwd()` 组合失败，错误及空 `py2.json` 保留；仅临时host改用 `os.getcwdu()` 后保存 `py2-recovery.json`，没有修改生产代码以绕过错误。原记录位于 `.runtime/round-20261021/t02-directions-v1/`；[离线小包](../evidence/transform-directions-r25-v1/index.json)保留宿主及两份完全相同的结果。

## 13:10 正常冷源实机补证

另起正常 `git archive` 来源 `900100aa402f7442b1f1cf6cf1554f1f3d76fd14`，3708个runtime文件、780个host文件，manifest SHA256为 `031217265ecae395c239b7032a279b361671d2ee65af5f1d03789773d484ee26`。未赋候选profile、未选择书诊断alias，实际执行公开卡／确认回调载入60格及28个方向样本；未投递Windows鼠标输入，也未写世界。

`mirror_y → undo → redo → undo → rotate_y90 → undo → redo → undo` 八阶段的数据和typed语义均与冻结来源的独立host oracle相符，最终回到原fixture。编码字节比较单独记录为false，没有把等价序列化误报为字节一致。root实际打开初始编辑器、Y镜像后编辑器／完整投影、90°旋转后编辑器／完整投影共5张原PNG：总览有画，楼梯／半砖上下关系及附着布局与变换一致；部分梯子仅见边缘，按钮太小或遮挡，**28样本逐面外观、X／Z镜像实机与missing仍未验**。该结果只补齐代表editor／full冷图，不标为三路径人工包就绪。

冷host两项离线预检错误原样保留：初版将四角标也计入方向样本，得到32而非28；另一版误把undo／redo作为 `Editor.run` 名称。两者均在launch前拦下，另立wrapper使用明确五族计数及真实 `Editor.undo/redo`／`Session.action`，原冻结host未改。wrapper同时复用已核实的严格活动owner检查，只排除确实无owner的空备用PreviewTile。

两次独立恢复审计通过、源码hash不变。原生相机roll均残差约 `-1.3660377589985728e-05°`，在 `0.0001°` 语义容差内，**exact=false**。game `63648 / 134370328107798494` 最后退出 `0xC0000409`，MCDK退出0，registry为stopped，watcher精确回收，无force；不能记为正常引擎退出。

[冷源证据包](../evidence/t02-normal-cold-r25-v1/index.json)包含5张小JPEG、26份原bytes记录及1份明确脱敏的stop派生件；原PNG与原回执保留在本地 `.runtime/round-20261021/t02-normal-cold-v1/`。index保留原raw SHA，并另列派生解码SHA与脱敏字段，不把二者混称原件。[独立三包复核](../evidence/r25-final-packs-review.json)确认原件／归档hash及token脱敏边界。现有 `tools/verify_transform_runtime_r23.py` CLI仍只允许T01／T04／T05／T08，本次使用独立冻结host，没有声称该CLI已支持T02。新增用户人工关闭数仍为0。

## 14:25—14:39：c531 正常冷源近景及受控 missing 补证

新owner `r26-t02-face-missing-v1` 单独从 `c531b2f4802577e160b26105c6d73cd8322ff89f` 执行 `git archive`，没有向旧900100aa冷源注入新内容。3708个runtime文件及780个诊断host分别绑定；source manifest SHA256为 `6000ea6cec1f9712b4325a3f6db2d6a80156a2726bced1671c9882646533cd9d`。正常来源未赋候选profile、未加书诊断alias，四项自动热重载关闭。冻结生产源码及原host始终不改，后续宿主修正均另立wrapper与派生SHA。公开T02卡及确认回调真实载入60格／28方向样本，不使用Windows鼠标投递、不写世界、玩家、物品栏或持久库。

新独立 `face_plan.py` 明确记录四梯子、六按钮的位置、支撑和外法线：梯子facing=2／3／4／5；按钮facing=0—5。法向顺序为 `(0,-1,0)`、`(0,1,0)`、`(0,0,-1)`、`(0,0,1)`、`(-1,0,0)`、`(1,0,0)`，支撑等于目标位置减外法线。Y镜像独立矩阵为 `(x,7-y,z)`；Y轴90°旋转为 `(31-z,y,x)`，对应法线同步变换。离线预检对初始及两变换的全部10个附件／支撑逐点核对，并检查完整typed文档、撤销／重做／撤销，均通过。

编辑器以 `camera_focus_request` 经mounted OrbitCamera消费后再调用 `camera_view`，沿各外法线拍10张12倍近景。相机须在原目标容差内相邻两次实际pose相同，采图前后实际pose也相同，并保留请求值与实际残差。代理已打开10张原PNG：四梯子均有明确可见面，朝上的button_1能辨认小矩形；button_0及部分侧面按钮在完整场景中被遮挡或不够清楚，**不把10次流程完成解释为六面按钮像素验收通过**。

两项变换均先通过完整文档语义及严格editor状态核对，再拍完整投影与受控missing三阶段，最后各执行真实undo并再次核对。受控观察器只替换本owner临时占用读取，不向世界放方块；每步保持原60格及支撑，检查投影typed snapshot、占用snapshot、source／cache、player和原生相机不变，新状态必须有新commit。

| 代表 | 原位置 → 变换后位置 | 变换后支撑／外法线 | missing观测／commit |
| --- | --- | --- | --- |
| Y镜像：button_0 | `(3,3,27)` → `(3,4,27)` | `(3,3,27)`／`(0,1,0)` | `[1]→[2]→[1]`；`0→1→2` |
| Y轴90°旋转：ladder_2 | `(3,3,23)` → `(8,3,3)` | `(7,3,3)`／`(1,0,0)` | `[1]→[2]→[1]`；`0→1→2` |

代理实际打开两代表的full及missing empty／occupied／restored共8张原图：镜像后的按钮小矩形与旋转后的梯子均在occupied消失、restored重现，石支撑保持可见。该结果仅覆盖这两个受控代表，**没有验证原生世界占用、完整28样本的missing矩阵或X／Z镜像实机**，也没有形成用户三路径人工验收。

为区分button_0完整图不清与模型完全未生成，在同一冷实例另走公开卡回调，使用现有 `Session.layer(3)`、`Session.display_mode('single')` 显示Y3，并拍俯仰-80°／-45°；另保留full模式-45°对照。完整Document、目标 `(3,3,27)` 及原支撑 `(3,4,27)` 的值逐阶段相同，未删除支撑或修改fixture。3张原图已打开：single模式可明确看到小石按钮和厚度，full模式仍无法辨清。因此只能排除“该按钮几何完全未生成”，**完整模式下的遮挡来源与正确贴面仍待确认**，不能仅归因为低对比。诊断完成后恢复原始session及显示模式。

保留两项宿主／打包失败：v2在main执行前因 `tools/mcdk.py` 遮蔽skill的 `scripts/mcdk.py` 而无法导入Client，未进行RPC或游戏变更；v3只额外修正宿主搜索顺序，两个实际文件的SHA和定位另列，未重启MC。首次小包有4份完整UI tree在gzip后仍超过300000字节，大小门拦下；这些冗余树仅留本地raw并在index列SHA，核心语义报告、卡回调、controls和采图回执均归档。原失败及修正记录保留，没有覆写冻结源或旧证据包。

主流程前后有独立只读audit；主流程及追加诊断各有两次恢复audit，诊断后再用独立host对原baseline检查两次，严格字段均无变更、非波动performance字段相同、源码hash不变。原生相机roll残差约 `-1.3660377589985728e-05°`，在0.0001°语义容差内，exact仍为false。资源门持续要求available commit至少6GiB、handles低于250000且单步增长低于10000；本主流程最低余量约9.20GiB。watcher每次RPC前需5秒内新鲜、精确owner／host SHA匹配、无其他assert或错误，清理路径保留恢复能力。

game `35012 / 134370373915982420` 已普通stop并finalize至registry stopped，实际退出 `0xC0000409`；MCDK退出0，**normal_shutdown=false**。watcher `23620 / 134370373686133134` 随后精确回收，无force、无第二次launch。[新小包](../evidence/t02-face-missing-r26-v1/index.json)包含41张JPEG及原PNG SHA、113份gzip记录，单件最大215025字节；112份解码为原bytes，1份stop是明确脱敏派生件，原raw／归档／解码SHA及不等价标志分开列出。4份完整UI tree的原件仍留本地。新增用户人工关闭数保持0；四梯子近景及两项受控missing补证不能关闭其余按钮贴面或完整变换验收。

## 14:59 离线CPU链补查

不重启MC，按c531冷源逐字节核对7个相关生产文件，分别对全建筑full／Y3 single及目标所在Z16局部chunk重复`build_preview → prepare_palette`。四份实际结果均保留button_0为`stone_button aux0`、`facing_direction=0`、未按下；full保留Y4支撑，single按现有层过滤排除Y4支撑，Document不变。此结果只排除该离线CPU路径把按钮删除或转成其他朝向，不能代替运行时palette抓取、原生网格／深度／遮挡根因判断或六面验收。见[离线trace小包](../evidence/button0-cpu-palette-r26-v1/index.json)。下一允许窗口先保持同原生材质和按钮／支撑，单独比较送入引擎的数据及网格／深度控制，不先改公共渲染器。

## 10-22：三模型十阶段原生绘制诊断

后续在精确 `2ab5a29a` 冻结源保持原 Document／体积、按钮／支撑索引、材质、相机和两 Doll，比较 combined、button-only、support-only 及四种双 Doll 的 slot／提交顺序，实际完成三模型、十阶段。**Combined 对 support-only 的固定 ROI 有261个变化像素，bbox与button-only暗像素范围一致；四组双Doll的ROI RGB原字节相同。** 原图轮廓主观不明显不等同完全未绘制；低对比及pitch −80原生参照仍开放，Combine／depth／bounds均未归因关闭。两个历史失败、独立PNG复算、最终相机精确恢复及游戏 `0xC0000409` 异常退出、未执行的Y+4单变量方案，见[完整诊断](BUTTON_PAIR_R27.md)。本次没有产品改动或新增人工关闭，不回写此前相机exact=false或较早失败记录。
