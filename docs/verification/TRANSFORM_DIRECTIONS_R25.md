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
