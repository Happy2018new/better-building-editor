# R25：牡丹上下半的方向可见性修复

2026-10-21。原生牡丹在Combine路径中曾出现朝向改变后完全缺画的问题。本次将已经使用的固定居中交叉面回退扩展至牡丹两种合法状态，分别绑定原版下半和上半纹理。三条显示路径共用已有入口；建筑仍保存`minecraft:peony`及原生bool上半标记，不写隐藏代理名，不补造另一半。

生成器、profile与生成物共14文件已应用主工作区。新增两份行为／模型、两条atlas／block注册；旧11名称的22份行为／模型和77份共享材质／shader字节不变。两张工具PNG固定来源，运行时直接引用安装版本原版纹理。`NATIVE_MESH_AUTHORITY=False`、`SNOW_QUALIFIED=False`及像素验收标志不变。

## 冷源观察与边界

基于`83a551cf`及14文件overlay的不可变冷副本使用真正的`ordinary_peony_bottom/top`标识，无诊断别名。完整4472文件合同`5ef0d8cdf9faed6b6a61def9b21dfd9e9ddd99ddf59507ccfba923df19486235`。编辑器0°、180°和正北完整／缺失投影完成12组、28张可靠WGC原图，四组上下两半均有像素贡献；同位AIR重复噪声0，stone正控有贡献。19次已加载100格AIR／无液体检查、12次实际当前bank／part／model提交核对通过。三份报告独立恢复、source／host一致、cleanup为空；退出后冷源及14个主仓base SHA仍逐项一致，之后才应用主仓。

主代理实际读取[未缩放对照图](../evidence/peony-r25-v1/formal-controls-contact.png)，四视图上下两半可见。[精简结果](../evidence/peony-r25-v1/summary.json)和[14文件来源](../evidence/peony-r25-v1/source-binding.json)保留原始报告／图SHA。完整原图、冻结源码、capture receipts在`.runtime/round-20261021/peony-v1/formal-cold-v1/`；19.8MB原始交付包未加入Git。

结果仅支持固定居中可见性回退，不能授原生精确外观资格。上下半ROI重叠，不能作独立形状测量。原生随机XZ偏移、精确尺寸、亮度、其他视角、切片、孤立半格实图、实际占据、含水／含雪及广泛组合继续开放。OB-02／OB-03整项及用户人工关闭均为0；集中蓝图及最终集成包冷入口仍在准备。

普通stop首次返回1，随后持有句柄的observer记录game延迟以`0xC0000409`退出、MCDK以0退出。force入口被已退出会话守门拒绝，实际未执行force；确认两个精确身份退出后才收尾registry。渲染恢复与退出异常分别记录，不能描述为干净引擎退出。

## 检查

主仓生成器`generate_ordinary_plant_proxies.py --check`通过，29份生成物一致。30项Python3回归（ordinary plant、geometry palette、peony资源及运行时）与3项真实Python2.7运行时回归通过，覆盖原版独立上下纹理／alpha／双面UV、非法状态类型和半格错绑拒绝、孤立或裁剪半格不补造伙伴、typed NBT和无关输出保持。MCP定点review扫描`ordinary_plant_data`1文件，解析通过、0 findings。原始命令／输出在`.runtime/round-20261021/peony-main-apply-v1/checks-v1/`；应用前14文件、tracked补丁、原index及HEAD备份在同目录上级。

## 集中检查入口

主仓已追加 `test.blocks.peony_visibility`，位于“测试蓝图 → 方块表”，标题“芍药 · 整株／下半／上半”。16×6×8 的小场景从左到右为整株、孤立下半、孤立上半；孤立上半与整株上半保持同一高度，并在下方故意留空。共四个原生半格、三个石头支撑；不自动补全伙伴，原文档保留原生名称及 bool 状态。

三文件补丁按 base／candidate SHA 检查并备份后应用；两个生产文件字节完全符合候选。Git 对新增宿主测试的 CRLF 转换已另存，随后按候选原字节恢复，没有改变受保护生产文件的行尾。5 项宿主回归、真实页面函数 472 卡可达及实际 Python2 原生状态／Document 往返查询通过。宿主 unittest 使用 pathlib，不在 Python2 运行；其首次 Python2 import 失败保留，没有计作通过。Python2 的生产路径单独验证。主仓 MCP 对集中蓝图模块实际扫描 1 文件，解析通过且无 finding。

入口提交时仍等待集成冷包的实际卡片导航、孤立半格显示和恢复检查；该项已由下述独立冷启动补齐。补丁和应用备份在 `.runtime/round-20261021/peony-blueprint-v1/` 与 `peony-blueprint-main-apply-v1/`。原 R09／R10 Document、历史 471 卡顺序／metadata 保持不变。

## 集成冷包的真实入口补查

基于 `103633d06813488f2c3da563ddc0969366596f6d` 的独立 source-only 冷包，运行时 3703 文件，来源清单 SHA256 为 `21a9d5647c943f431ca8c0a8a949ee261ebbc3060256f264ccaeb5a3be7f8044`。配置和 769 个宿主文件分别冻结，不把宿主、缓存或配置混入运行时数量。检查期间没有热重载、候选/profile 赋值、资源别名或真实世界写入；运行时、配置、原宿主和重试宿主均前后不变。

实际挂载的分类控件、卡片载入按钮和确认按钮回调成功载入 `test.blocks.peony_visibility`，保留全部 7 格及原生 bool 状态。当前原生提交包含正式 `ordinary_peony_bottom/top` 两种资源。六个编辑器视图覆盖整株、孤立下半及孤立上半的 0°／180°，两种纹理分别可见，没有补造伙伴。450% 视图仍含同一整排，pivot 修改没有独立重居中目标，故只能描述为整排近景，不能算独立裁切场景或精确网格测量。

主代理复核全部十张原图的字节与 SHA，并实际读取[十图对照](../evidence/peony-entry-r25-v1/controls.jpg)。[证据索引](../evidence/peony-entry-r25-v1/evidence-index.json)保留原图与报告来源；原始 `live-v3/report.json` SHA256 为 `a8abacbdeeeb95f3d41f54ce035a294fc4fa5fafff874209e891a03e684df7fd`。本次支持 `manual_review_ready=true`，人工关闭仍为 **0**。实际控件回调未投递 Windows 鼠标事件，不替代原生鼠标命中或用户外观验收。

同轮 R08 压力板卡片通过真实挂载回调和确认流程载入，24 格文档与当前原生提交保持，编辑器有显示。但载入前截图已滚过该卡，不能证明该卡当时在屏幕上可见，也未验收压力板厚度或红石行为；R09／R10 本次未重测。

首次启动在生成进程后的 manifest 原子替换遇到 WinError 5，旧 manifest、待替换临时文件和精确身份回收记录保留。独立重试宿主只增加有界替换重试；原运行时及旧输入不变。第二次采图因冻结宿主缺少非平面 `tools/native_wgc` 来源依赖失败并独立恢复，之后新增独立 capture-host-v3，才取得本次成功结果，未覆盖失败记录。

独立恢复成功，两个 owner 均已停止。成功 owner `peony-r25-entry-v2` 普通 stop 返回 1，完整等待后 game 以 `0xC0000409`、MCDK 以 0 退出；未执行 force，精确身份复核为 inactive 后 registry 收尾返回 0。该异常退出与入口／恢复成功分别记录。完整冻结包、十张原图和清理回执位于 `.runtime/round-20261021/peony-entry-v1/`。
