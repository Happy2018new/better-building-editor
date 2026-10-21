# R25：双箱占据后支撑面的木纹残留

2026-10-21，T04 的箱体消隐后木纹残留已得到 **A→B→A 方法级因果支持及整合源码的冷启动复查**：原 A 中占据单半或双半箱体后，红混凝土支撑顶面仍有平面木纹；仅替换邻域所有权判定和对应 writer 后，B 露出正确红色支撑；精确恢复原方法后，返回 A 的木纹再次出现。生产修复随后在与海带共用的冻结冷源上重现正确消隐／恢复。本轮新增人工关闭数仍为 **0**。

## 修正范围

静态箱代理可能被复制到邻格 target 的上下文中。箱模型的 cube 从 y=0 开始，其边界面落在支撑 target 的闭裁剪边界上；这解释了为何主体已经隐藏，支撑面仍可留木纹。这里没有 GPU 面 ID 追踪，因此不把该平面断言为箱盖或箱底。

候选延续门的邻域归属规则：非箱 target 不再借用已注册静态箱代理的 common 和 actor；extra 水继续保留。箱 target 仍有自身与 partner 的邻域，原始 NBT 和完整 typed Document 不修改。共享 writer 的缓存 key 区分同一 rendered 对象写入普通 target 与箱 target 的两种计划，避免写入顺序改变结果。规则只覆盖 `CHEST_PROXIES` 的已注册代理，包括普通、陷阱、末影和铜箱；不按名称模糊匹配其他自定义方块。

## CPU 与实机证据

原 T04 的第一双箱镜像后位于 `(17,2,4)+(16,2,4)`。离线使用实机报告冻结的完整34格 typed snapshot，对 `empty → single_half → occupied → restored` 四阶段检查：基线每阶段有36个落入非箱 target 的静态箱拷贝，候选为0；存活箱 target 自身和 partner 拷贝分别保留8、6、4、8。同步和增量 palette 相等，完整 Document data 不变。既有四套窄回归25 tests 全过。

新增普通单测候选有4个方法，覆盖正式 T04 build 加镜像后的四阶段、红支撑材质、局部与全局 packing、自身与 partner、同步与增量相等、所有注册箱代理、actor 去除、extra 保留、writer 两种写入顺序及非箱家族保持。候选4方法全过；原基线在前三个目标方法产生232个 subtest failures，非箱家族保持方法通过，0 errors。该负控证明测试可以识别原缺陷。

实机三段均从正式测试页与 T04 卡片进入，使用相同镜像动作、相机和四阶段观察值 `[1,1] → [2,1] → [2,2] → [1,1]`。三个报告均 `completed=true`、`restored=true`、`cleanup_errors=[]`，完整 typed snapshot 逐项相等，12个阶段的 source/model owner、serial、origin、cache 绑定均有效。

B 仅向原模块绑定三个函数和一个常量，没有改磁盘源码或 reload 整个模块。函数仍引用原模块 globals；finally 恢复原模块完整 key 集、每个 value 的对象 identity 和原 writer.put 函数对象。此结果支持候选修正的因果关系，**不代表最终冷源码资格**。

该实验使用受控 occupancy observer，没有在真实世界放置占据方块，`native_world_occupancy=false`；不能据此关闭原生世界扫描或所有箱类型／朝向的验收。实际逐张读取的是三段各 `single_half`、`occupied` 的6张完整原 WGC，A 两段都有木纹，B 两张无木纹且红支撑可见。其余阶段原图和 hidden 对照均保留，未宣称全部完成视觉验收。

六张关键原图的[缩略导航](../evidence/chest-context-r25-v1/controls.jpg)只用于定位；[证据索引](../evidence/chest-context-r25-v1/evidence-index.json)绑定原 PNG、三份报告、方法记录、CPU 结果及恢复／退出回执的 SHA-256。原始 T04 负例仍见 [TRANSFORM_MISSING_R25.md](TRANSFORM_MISSING_R25.md)，不随候选阳性改写。

## 恢复与退出

三段完成后独立只读核验：原 editor/document IDs、1307格原草稿完整 data、workspace 关闭、factory 与 occupancy 原类、0 actors、无编辑／IO／投影工作、相机 locks 及探针 markers 均恢复；候选 helper/常量已移除。3707个冷源文件逐项 SHA 不变，源 manifest 为 `99c4bdcb389b81d542f0b170dff815ede2efe37b5036f1f3046b8f4cb182e8a5`。

实例退出保留了真实失败：普通 stop 首次 returncode=1，原因是10秒内未关闭；随后 exact observer 记录游戏于05:25:52以 `0xC0000409` 退出，MCDK 以0退出。独立确认精确 PID 与 creation identities 均不存在后，第二次普通 finalize returncode=0，registry stopped，全程没有 force。清理完成不能写成正常退出通过，异常退出也不覆盖此前的恢复证据。

原始证据在本地 `.runtime/round-20261021/chest-context-ownership-v1/`。生产集成应应用小 diff 并保留其他邻域修改；随后对最终共同来源冷启复查自身与 partner、支撑残面及占据恢复。


## 整合来源与最终共同冷验

邻域小修正已整合到生产提交 `5b5209dcbc839b6afa04d3f3ad7010014e1056f3`，并保留前一海带提交 `a76cd73ac054a1aa18ef3c0597e6f02ad6ead892` 的完整来源邻居判定。主仓 context／door／kelp／chest 相关整合回归 **69项通过**；MCP scoped review（files=1）仅有既有参数告警。新增箱体测试已进入主仓测试集。这些属于生产整合后的离线验证，原 A／B／A 的来源仍为前述3707文件冷源加受控方法绑定，不倒写其来源提交、manifest或任何原图／报告hash。

共同冷源绑定 `7c7c32f05fbc6d4eb0e7e9895f060f1f39b8860c`，包含箱修复、海带修复和公开海带卡。3708个runtime文件的manifest为 `7872491a970fd54d3331f2bdaf89dd04f87224ec184d612123749e74e82a65fa`。四项热更新均关闭，没有书诊断alias、候选profile赋值或运行时context补丁。

正式T04入口镜像后，受控occupancy四阶段为 `[1,1] → [2,1] → [2,2] → [1,1]`。主代理已独立打开前后编辑器、完整投影及四阶段missing共7张原图：单半占据仅去除对应半箱，双半占据后红支撑顶面干净，蓝色对照双箱保持，恢复后红组双箱完整返回。报告 `completed`、`restored`、`source_unchanged` 均为true，`context_patch=false`。这是整合后的生产路径窄证据，**受控observer不等于真实世界占据扫描**；其他箱型、朝向和跨客户端重启持久性仍待。

原宿主按当前工作区字节比冷源时，`rail_render_profile.py` 的LF／CRLF差异阻断预检；原失败保留。续验逐项绑定冻结manifest，记录CRLF转LF文本相等，不改变冷源。首次独立恢复审计还记录了预览重建耗时 `previewWall` 从1.749秒变为1.051秒；新版审计将该实测耗时单列，其余Session／Editor／Document、设置、profiles、相机及performance字段保持严格比较，两次读回 `changed_keys=[]`、相机exact恢复。

海带公开卡在同一冷源完成入口和编辑器／missing部位补查，见[海带专项](KELP_VISIBILITY_R25.md)。该实例没有另跑T05或所有门状态；它们沿用各自来源的已有窄证据与CPU整合回归，不搬作本冷源的新实机结果。

[共同冷源小包](../evidence/final-kelp-chest-r25-v1/summary.json)保存11张JPEG、28份原失败／报告／恢复／来源记录；大JSON以gzip无损保存。主代理独立重算原文件、gzip解包及JPEG哈希，索引SHA256为 `f7f351288401664de052cb3f70955f7323359341d3790c620f92fc7e1c902fd1`。实例普通stop及registry finalize完成，游戏真实退出仍为 `0xC0000409`、MCDK为0，所属watcher按PID与creation identity精确退出0，全程无force；不称正常引擎退出。

归档字节补充：27份记录保留原始字节；停止回执的本地会话token已从仓库副本移除，改为明确标注的脱敏派生gzip，并同时绑定原始raw及脱敏解包SHA。原始回执留在本地.runtime，不改变退出、身份或恢复数据。索引不把该脱敏副本宣称为原raw字节。
