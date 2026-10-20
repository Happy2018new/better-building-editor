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
