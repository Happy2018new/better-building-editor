# R23 原生网格 NORMAL 输入资格

2026-10-19 的独立冷测未取得 NORMAL 输入资格。引擎在绘制时报告 `Mesh missing vertex field NORMAL required by shader. Skipping draw.`，六面采集为 0。不能据原生材质的 `vertexFields: Normal` 声明、GLSL 离线编译或链接通过，启用依赖该输入的面剔除。结构化回执见 [NORMAL_INPUT_R23.json](verification/NORMAL_INPUT_R23.json)。

## 候选范围

`normal-r23-input-v1` 仅从已冻结的 `firefly-r23-c-v1` 冷副本只读复制 behavior/resource packs 与 `.mcdev.json`，没有访问后者的 MC。共 3,672 个包文件，约 119 MB；没有复制运行目录与工具树。随后只在新副本应用两份 NORMAL shader 覆盖。主源未修改，terrain 仍为 SHA256 `b20079f22bb9272d036f1ca4c1c148ab2a0a9c05ad0cf894b644db93ebd5971b`。

v2 离线检查发现诊断输出受 `renderContext.w > 0.5` 限制，普通 stone 和 raw_loaded 没有该标记，因此未运行 v2。v3 只移除该诊断输出门控，在这份独立副本的两个覆盖 shader 中输出未经 normalize 的 `NORMAL.xyz * .5 + .5`；长度小于 0.5 或大于 1.5 输出洋红。没有新增 discard、面归属判定或开放边界处理。

v3 manifest 为 `.runtime/round-20261019/concrete-color/normal-input-v3/manifest.json`，SHA256 `d6f7f1cdbf4a1cdd4fe09db586dfb27d753e7c67b29ed36411bce1a6d0f1e1ad`。16 项独立编译中 12 项通过；ES100 fragment 的 4 项宏续行失败与原基线相同。GLSL300 的 plain、SEASONS、BLEND/FOG、BYPASS 四组 vertex/fragment 均离线链接通过。这些结果不证明实际 GPU 输入存在。

## 计划与实际结果

计划为 product 和 raw_loaded 两路的 air/stone 六向对照；共享支撑移到 `(0,0,0)`，目标仍为 `(1,1,1)`，六个直接邻格均为空。工具保留原空气噪声和石头正对照阈值，并记录相机/实体位置与实体旋转、实际挂载的 offset/rotation 调用、六面中心的 WorldToScreenPoint 读回。未以屏幕方向猜测法线符号。

该实例使用 ui 平坦预设。启动前建立精确 owner 的断言 watcher，启动过程另建立绑定游戏/MCDK 创建身份的 exact-exit observer；游戏正常达到 ready。随后在等待首个 product air 夹具（含共享石头支撑）的投影时，出现上述 NORMAL 断言：`ShaderBase::checkVertexFormat`，源码行 118。尚未取得空气、石头或 raw_loaded 的有效采集，也没有方向、长度或两路一致性的实测结论。

这次诊断覆盖同一 shader 的所有网格，因此原生断言只能证明其中至少一条实际绘制缺失 NORMAL，尚不能精确归因到某个 Combine 目标，更不能断言所有原生网格都缺失 NORMAL。用户问题关闭数为 0，产品默认支持和 `normal_input_qualified` 均为 false。

## 故障恢复记录

未知断言窗口没有 noactivate 标记，受保护的 execute_code guard 正确拒绝继续执行，finally 的恢复读回亦无法派发。没有忽略断言，没有绕过 guard，没有把未验证的内存恢复记为成功；原报告保持 `completed=false`、`restored=false`、`captures=[]`。

普通 WM_CLOSE 在 10 秒后仍未退出。保留该失败后，仅对本任务新建的独立实例逐一核对 game 36396 与 MCDK 46840 的创建身份，再执行受管 force 清理；两进程已退出、session 为 stopped。exact observer 记录游戏退出码 1、MCDK 退出码 0，该退出发生在授权强制清理之后，不能解释成未经干预的自然崩溃。独立断言 watcher 也经创建身份核对后停止。

原断言、0 张采集、恢复未验证、普通关闭超时和强制清理各有单独回执，均保留在 `.runtime/round-20261019/concrete-color/normal-v3-failure/` 与对应 launch 目录。未重试 shader，未操作其他测试实例。后续若继续研究，需先缩小实际绘制的材质/网格范围并证明输入合同；当前证据不足以采用依赖 NORMAL 的面剔除方案。
