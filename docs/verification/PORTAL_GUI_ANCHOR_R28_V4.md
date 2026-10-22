# R28 末地表面 GUI 锚点 V4：原图、原生坐标与恢复证据

V4 单次实测完成了末地折跃门和末地传送门各自 GUI2／3／4 的 A → B → A-return 对照。**本次证据支持旧版编辑器末地表面的 GUI 锚点诊断；产品代码、资格常量和外观验收状态均未修改，人工关闭数为 0。** 原生候选模型没有被选用，星点亮度、密度、动画方向和速度未据此验收。

所有 18 张原始 WGC PNG、各自捕获收据、完整原始报告和源清单都已保存在 [V4 证据包](../evidence/portal-gui-anchor-r28-v4/index.json)，不依赖运行目录中的图片副本。PNG 没有重编码或用拼图替换。两份源清单和完整报告采用确定性的 gzip；解压后恢复原始字节，索引逐项记录原始路径、长度、SHA-256、包内路径及压缩后 SHA-256。

## 固定实验与实际运行

owner 为 `portal-r28-gui-anchor-v4`，运行及全部 36 项历史辅助文件固定在提交 `b70ce7bf13ad6a4472f2b089ac812c162b174861`。冻结运行源共 3,712 项。游戏和调试器均只启动一次，没有业务重试、补拍、额外 case 或额外取景。

A 使用继承的 `PortalProfile.ui_offset(size) = (0, min(size)/4)`；B 仅在本次 Session 的同一个 profile 实例上临时覆盖为 `(0, min(size)/actualGUI)`；A-return 删除实例覆盖，恢复原继承方法。没有切换模型、材质、profile、蓝图、相机或文档。GUI4 是事先固定的零位移对照。

| 原生 GUI | 固定物理客户区 | 每个 family 的阶段 | 预期 B−A 逻辑 Y 位移 |
| --- | --- | --- | --- |
| 2 | 1280 × 720 | A／B／A-return | `min(size) × (1/2 − 1/4)` |
| 3 | 1600 × 900 | A／B／A-return | `min(size) × (1/3 − 1/4)` |
| 4 | 1994 × 1105 | A／B／A-return | 0 |

实际授权见 [root grant](../evidence/portal-gui-anchor-r28-v4/provenance/root-launch-grant-v4.json)：实验截止 `2026-10-22 22:15 UTC`，watcher 截止 `22:20 UTC`，分别为次日 `06:15／06:20 +08:00`。sealed host 声明的更晚硬上限没有替代该次授权。实际 watcher 调用及完整初始状态检查分别保存在 `provenance/assert-watch-start.json` 和 `provenance/complete-initial-status-v1.json`；启动没有改写 sealed `start_watch.py`。

runner 于 `2026-10-22 21:42:50.661124 UTC` 返回 0，`completed/restored/source_unchanged=true`，`cleanup_errors=[]`。完整报告原始长度为 5,574,267 字节，SHA-256 为：

`51c566cf095528f24c1a2878db9cac26fa48ac9262f31a9e6e40ccd6081d1513`

## 原生读回与缓存矩形分别核对

原报告 `triplets[].deltas[].actual_logical_dy` 来自 `portal_geometry[].geometry` 的 Python 缓存矩形，不能把其约 `1e-14` 的公式误差说成原生 UI 坐标误差。包内 [native-triplets.json](../evidence/portal-gui-anchor-r28-v4/analysis/native-triplets.json) 另从实际 active slot 的 `position` 计算 `B.y − A.y`，保留全部 21 组 A／B／A-return 的原生局部／全局位置、尺寸、可见性、模型 ID、双槽状态和四组自定义 uniform。

| family | GUI | groups | 缓存位移对公式最大误差 | 原生 slot 位移对公式最大误差 |
| --- | --- | ---: | ---: | ---: |
| end_gateway | 2 | 3 | 0 | 0.00000175041244 |
| end_gateway | 3 | 3 | 1.0658e-14 | 0.00000203926972 |
| end_gateway | 4 | 3 | 0 | 0 |
| end_portal | 2 | 4 | 0 | 0.00000175041244 |
| end_portal | 3 | 4 | 3.5527e-15 | 0.00000203926972 |
| end_portal | 4 | 4 | 0 | 0 |

单位均为逻辑 UI 像素。21 组中，原生 `position` 对对应缓存位置的最大差为 `0.00000528861881`，小于原协议固定的 `<0.001` 门限。两种 family 的 GUI4 原生位移均为 0；每组 A-return 的完整 `slots` 读回与 A 值完全相等，包括原生位置、尺寸、可见性和模型 ID。

原协议还检查了以下不变量，离线复核直接重放已冻结的 `protocol.py` 和 `camera_gate.py`，没有重新定义门限：

- 18 次捕获前后均为同一个 editor／document，完整 typed document、groups、profile identity 和 models 相同；世界投影关闭且 world actor 数为 0。
- 实际 mounted Scene 相机与 Session 一致，目标和姿态均为 `(35, 35, 2)`，速度为 0、未拖拽，并且捕获前后 Scene fiber、相机对象与 target 一致。
- 每个 portal group 只有一个 active native front，模型 ID 有效并与缓存绑定一致；四组自定义 uniform 的原生／缓存值相等，捕获前后及同一 A/B/A 三联内绑定值一致。
- 实际 surface 的所有原生祖先均存在并可见，surface、doll、renderer 可见；原生 slot 的位置和尺寸与已发布矩形在原门限内一致，条目未裁切且 ready request 存在。
- WGC 从实际客户区取图，原始尺寸与预定客户区一致，capture helper 返回 0；帧时间不早于请求，前台窗口没有被捕获过程改变。

以上“四组自定义 uniform”不包括引擎自然推进的 `TIME`。本次允许 TIME 变化；不同帧的星点不要求逐像素相等，也不以坐标正确证明表面全部外观已验收。

## 18 张原图及独立开图范围

每个链接均指向对应原始 PNG；18 张共 3,668,791 字节。每张图的原路径、长度及完整 SHA-256，以及原始 `.host.json` 的对应关系，均列在 [index.json](../evidence/portal-gui-anchor-r28-v4/index.json)。

| family／GUI | 原始 A | 原始 B | 原始 A-return |
| --- | --- | --- | --- |
| gateway／2 | [A](../evidence/portal-gui-anchor-r28-v4/captures/end_gateway_gui2_a.png) | [B](../evidence/portal-gui-anchor-r28-v4/captures/end_gateway_gui2_b.png) | [A-return](../evidence/portal-gui-anchor-r28-v4/captures/end_gateway_gui2_a_return.png) |
| gateway／3 | [A](../evidence/portal-gui-anchor-r28-v4/captures/end_gateway_gui3_a.png) | [B](../evidence/portal-gui-anchor-r28-v4/captures/end_gateway_gui3_b.png) | [A-return](../evidence/portal-gui-anchor-r28-v4/captures/end_gateway_gui3_a_return.png) |
| gateway／4 | [A](../evidence/portal-gui-anchor-r28-v4/captures/end_gateway_gui4_a.png) | [B](../evidence/portal-gui-anchor-r28-v4/captures/end_gateway_gui4_b.png) | [A-return](../evidence/portal-gui-anchor-r28-v4/captures/end_gateway_gui4_a_return.png) |
| portal／2 | [A](../evidence/portal-gui-anchor-r28-v4/captures/end_portal_gui2_a.png) | [B](../evidence/portal-gui-anchor-r28-v4/captures/end_portal_gui2_b.png) | [A-return](../evidence/portal-gui-anchor-r28-v4/captures/end_portal_gui2_a_return.png) |
| portal／3 | [A](../evidence/portal-gui-anchor-r28-v4/captures/end_portal_gui3_a.png) | [B](../evidence/portal-gui-anchor-r28-v4/captures/end_portal_gui3_b.png) | [A-return](../evidence/portal-gui-anchor-r28-v4/captures/end_portal_gui3_a_return.png) |
| portal／4 | [A](../evidence/portal-gui-anchor-r28-v4/captures/end_portal_gui4_a.png) | [B](../evidence/portal-gui-anchor-r28-v4/captures/end_portal_gui4_b.png) | [A-return](../evidence/portal-gui-anchor-r28-v4/captures/end_portal_gui4_a_return.png) |

截至本次封包，root 已亲自打开其中 10 张：gateway GUI2 的 A/B/A-return、GUI3 的 A/B、GUI4 的 A/B，以及 portal GUI2 的 A/B/A-return。root 直接观察到 GUI2 的 A 表面浮于石基座上方、B 向下贴合、A-return 再浮起，GUI3 位移较小，GUI4 A/B 位置一致。其余 8 张原图已保留，但本记录不将其列入 root 开图数。该范围记录在 [root-visual-review-scope.json](../evidence/portal-gui-anchor-r28-v4/analysis/root-visual-review-scope.json)，与启动前的 `root-review-v4.json` 源审计是不同记录。

## 恢复、普通 stop 与异常退出

捕获后恢复了原始继承方法、Session／文档／选择／撤销重做／资料库／profile 和导航状态，并进行了两次独立业务恢复审计；两次均 `restored/preview_ready=true`。物理客户区恢复到原始 1280 × 720。临时实例覆盖和测试标记已移除。原始报告保留这些审计的完整字段。

普通 stop 返回 **1**，原 stderr 为 `Game has not closed; inspect it or explicitly use stop --force`。随后完整保留 45 秒 grace 策略；游戏和 MCDK 在 grace 内退出，**force 未执行**，registry finalize 返回 0 且最终状态为 `stopped`。不能把普通 stop 返回 1 描述为正常返回 0。

| 进程 | PID | creation identity | 实际退出 |
| --- | ---: | --- | --- |
| Game | 9084 | `134371787916027946` | **`0xC0000409`，异常退出** |
| MCDK | 70352 | `134371787913835733` | 0 |
| Launcher | 25640 | `134371787868296636` | 0 |
| Observer | 57792 | `134371788002882820` | 0 |
| Assertion watcher | 2232 | `134371787824614197` | 精确匹配身份后终止，退出 0 |

helper retirement 没有再触碰 Game／MCDK。closeout 按 PID 与 creation identity 逐一确认这些本次持有的进程身份已不存在；root 又独立确认后释放 MC 槽。游戏异常退出保留为事实，不被 runner 成功或恢复成功覆盖，也未据此宣称异常退出原因已经定位。

安全的 [native-closeout-v1.json](../evidence/portal-gui-anchor-r28-v4/provenance/closeout-v1/native-closeout-v1.json) SHA-256 为：

`4076ab2d09a38c7326dacc5979ea62f61596f8d9cf4cf6a09169a20543c04dc4`

可能含本地会话凭据的原始 stop、launcher record 和 launcher stdout 没有进入包；其原路径、长度和 SHA 保存在 `provenance/excluded-sensitive-inputs.json`，上述生命周期结论来自已脱敏 closeout。封包的 JSON、源文本和 gzip 解包文本检查未发现凭据形态值；捕获收据中也没有复制会话配置内容。

## 源边界与下一步

| 冻结 owner | source manifest SHA-256 | host binding SHA-256 |
| --- | --- | --- |
| V3 | `85930b432fa751cc5557e1bba1002950e5613f88673466f9270f6189b5bec2ec` | `0f308d26da9fbb1194b8dfaabbdef5712734b7b6549155270ac319395837dc62` |
| V4 | `1eeb82b058137dc3dc0863875180463ec3d56b255c6052403bbd5b5fe4c35371` | `7dcecd2a72499295139d09341b298499d943325a29b158a2fdf348649f644f9e` |

实测关闭前核对两套冻结源及 binding：各自 3,712 运行文件、36 历史辅助文件和全部绑定 host／控制字节未变。包保存两份清单的全部原字节、V4 全部 25 bound host 对象及 4 控制收据、关键原源文件和外部工具 hash。离线 verifier 重核这些包内字节和原始 guard 收据；它不声称重新启动游戏进行了新的源资格验收。

若继续修产品，最小范围可以是在 `projection/scene.py` 的 `portal_view` 增加与已有液体／书本路径一致的可选 `ui_offset_for_gui(size, Theme.native_gui_scale)` 调用，再由 portal profile 提供 GUI-aware offset 并保留原 fallback。这只是下一步建议，本次未实现。**`projection/scene.py` 位于当前水产品 39 项显式生产源合同中，修改该文件会改变合同；必须重新生成并核验对应源合同、完成必要回归和重新资格处理，不能直接沿用旧 water39 资格。**

现有末地原生候选／原生世界候选资格及相关失败记录均未改写；原先的 V2 启动失败、V3/V4 离线控制和本次实际异常退出仍分别保留。此锚点证据不替代原生世界表面、完整外观或玩家人工验收。

## 离线复核

在仓库根运行：

```powershell
python -B -X utf8 docs/evidence/portal-gui-anchor-r28-v4/verify_package.py
```

复核只使用 Python 标准库和已封存的纯离线 gate，逐项检查 92 份原始输入的存储／解压 SHA、18 图的尺寸及捕获收据、36 次 before/after 状态 gate、18 次 capture stability、6 组 A/B/A、21 组原生坐标、两次恢复审计及退出事实，不启动 MC 或 watcher，不修改产品资格。

首次成功收据见 [verification-receipt.json](../evidence/portal-gui-anchor-r28-v4/verification-receipt.json)。封包工具的首次本地复核曾假设 V3 有 `helper_source_commit` 字段而报 `KeyError`；V3 原清单实际没有该字段。最终复核改为比较 V3/V4 的完整历史 helper hash 集，并检查 V4 显式提交；这项离线复核器修正没有改变任何原始运行证据。
