# R29 投影 v7：截止前未满足启动条件

最终冻结产品源为 `dcf34132ce8e33284066efe66b9693ff89dc675a`。主仓 CPU-v8
已通过，3613 项测试、跳过 1 项，exit 0，6333 个输入前后未变化。
独立物理副本、source/host/observer 绑定及 frozen guard 已准备完成。

本目录只记录最终 v7 的未启动结果。更早 v1 的 ready 资源门失败和退出证据
保留在原目录，不能被此处的未启动表述覆盖。

北京时间 05:00:35 至 06:29:35，每 60 秒读取一次 OS 资源，共 90 个真实样本。
06:30 到达最晚启动线，采样器自动完成，实际 exit 0。90 个样本全部未满足
10,005,745,664 B（9.3186 GiB）的启动前余量门槛；运行门槛仍为 6 GiB。

| 指标 | 结果 |
| --- | --- |
| 最低提交余量 | 5,848,875,008 B（5.447189 GiB） |
| 最高提交余量 | 7,956,713,472 B（7.410267 GiB） |
| 最后提交余量 | 7,929,839,616 B（7.385239 GiB） |
| 最后样本时间 | 2026-10-25 22:29:35 UTC / 北京次日 06:29:35 |
| 最后全机实例分类 | live 1、零资源墓碑 8、unknown 0 |
| 最后距启动门槛 | 仍少 2,075,906,048 B |
| v7 自有 MC / watcher | 均未启动 |

普通冷 Session observer、功能 smoke、截图、世界写入、玩家或相机修改均未执行。
没有调整 profile/资格 metadata，没有调用自有 stop 或 watcher retirement。
外部独立对话的 MC 没有被连接、输入、检查游戏状态、热载、关闭或重启。
本次没有获得投影实图验收，也没有授予当前源水、书或末地资格。

22:31:23 UTC 的只读 OS 审计没有找到命令行明确匹配 v7 owner/project/host 的
进程（0 个），且 v7 的 launch report、watcher start receipt、feature smoke 和
stop 目录均不存在。命令行归属不能单独识别没有标记的继承进程，因此这个
0 只与已记录的“启动链从未调用”共同支持本 owner 未启动；它不代表全机没有 MC。
审计未读取外部会话配置，也未输出外部命令行。

`index.json` 是原始 90 样本简明索引；`samples/` 只选首样本、最低、最高和
最后样本，内容与原件逐字节一致。全部 90 份原始 OS 快照继续保留在
`.runtime/round-20261026/validation-v7/conditional-capacity/`。
`no-launch-receipt.json` 保存精确范围、绑定和 CPU 结果 SHA、选样来源/hash。
`conditional-launch-grant-v7.json`、`prepare-report.json` 和
`owned-process-audit.json` 分别保留授权范围、离线准备与 OS 归属审计。
