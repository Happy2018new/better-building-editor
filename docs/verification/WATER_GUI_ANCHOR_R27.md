# R27：自定义水的编辑器 GUI 锚点修复

此前水预览把所有 GUI 档位的垂直补偿都固定为控件短边的四分之一。GUI 4 下接近正确，GUI 2 下整组水约向上错开111px。10-22 的独立诊断以 SDK 父矩形为固定范围，支持按实际整数 GUI 比例计算补偿；正常产品 Scene 随后完成 GUI 4／3／2 的26张原 PNG 对照。诊断 wrapper 和正常 Scene 的来源、结果分别保留，详见[采集记录](WATER_CAPTURE_R27.md)。

本次生产源码只增加三处行为：

- `Theme.configure` 缓存它原本已读取、取整的 GUI 比例，且在字体不变的提前返回之前更新。没有增加每组或每帧 SDK 查询。
- 显式 Product 水 profile 提供 `ui_offset_for_gui(size, gui)`，偏移为 `(0, min(size) / gui)`；未知、布尔、非正、非整数或非有限 GUI 值拒绝。原有 `ui_offset` 回调保留。
- Scene 的水分支使用这个可选接口；旧 profile 继续使用原回调。原 `+1.5 entityY` 旋转 pivot 保留，其他特殊内容分支未改。

实际实机候选 source contract 为 `45985a50b720b72cd9dd55a68cdeb7064fffa7201c79084b1ec8953ca11d5424`，正常 Scene owner 为 `water-r27-gui-scene-v4`。每档完成静态水源、向东流水和含水栅栏的 dry／wet 对照，另有两次原文档仍挂载时的真实 resize 接缝。72次原生几何读回符合原0.02 logical门；主代理已打开三档正面湿栅栏、GUI 2斜面栅栏／流水／resize接缝六张原图，水与石块和栅栏位置接合。它只支持所列静态场景和缩放行为，未授予动画或所有含水组合通过。

合入保留生产 CRLF 字节格式。三份合入文件与实际实机 LF 候选在换行归一化后逐字一致，AST也相同；原始与合入 SHA 分列记录在本地 `root-water-gui-merge-v1/before-and-candidate.json`。合入后文件 SHA256：

| 文件 | SHA256 |
| --- | --- |
| `widgets.py` | `519f68770391f3e959d2afc277225c44b24c86c727e1f90a743a0e3491a6b66d` |
| `liquid_product_deployment.py` | `5fa49e83b67841f008cf32fc9cbdff48dfd4335227d444e3e414b49af0caefd1` |
| `scene.py` | `5f150ea6b5c8b06cac44b2f076b70dccc143e6a65e5c1aeea4ce714984ba0d97` |

新增六项回归覆盖相同字体时 GUI 缓存刷新、比例输入边界、dynamic／frozen profile、真实水闭包的缓存读取与 legacy 回退、相同 ready request 下原生几何刷新，以及显式候选不能改变生产资格。连同 viewport、deployment、Product profile和公开卡 owner 合同共72项通过；第一次额外 ownership 模块因历史 sibling `test_tiles` 导入方式加载失败，测试 runner 加入 tests 目录后该模块6项通过，总计78项。故障注入测试预期会输出原生发布／恢复异常栈，不将这些预期栈记作测试失败。三份生产文件另经真实Python 2.7编译，按范围 review 没有新增端侧、监听或动态执行问题，既有大函数／多参数提示保留。

`liquid_product_owner_data.py` 与 qualification 原字节未改。旧 owner 的来源失配继续阻止默认准入，不能仅凭更新哈希把旧资格转给新实现。正式动画A仍有原593.9861ms source时间缺口，当前新源资格、完整公开场景及最终默认冷启D仍需分别完成。本次新增用户人工关闭0。
