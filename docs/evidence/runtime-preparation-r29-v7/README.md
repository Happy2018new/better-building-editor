# R29 最终来源：投影 v7 与水 v5 准备

两份独立物理验证工程绑定最终产品提交 `dcf34132ce8e33284066efe66b9693ff89dc675a`。本包保存来源和宿主准备记录，**不代表 MC 已启动、实机验证通过或新增人工接受**。另一个独立 Codex 对话的不同模组 MC 没有连接或操作；全机计数只读 OS 进程和资源。

投影 owner 为 `r29-transform-cold-v7`。3716 runtime 文件、119,020,141 字节，785 host 文件，4502 份物理副本均无 hardlink。相比 v6 仅 bridge 与 projection_target runtime 变化；14 个本地 host 的 owner／project 替换、原工具字节、observer 绑定、显式 42／20／20 源清单及 frozen_guard 均已核验。未变化的 21 个宿主控制沿用已执行的 v6 回执，未机械重跑。root 另核三份关键绑定 SHA 并实际运行最终 frozen_guard。

root 在 CPU-v8 实际通过后，仅给投影一次有条件的冷启动：fresh 可用 commit 至少 10,005,745,664 B、unknown 0、全机实际活 MC 少于 5；运行门为 6 GiB。顺序为普通冷 Session observer、原冻结 smoke（含本项目自有独立空世界的允许写入）、完整恢复与读回、普通所属 stop、实际退出观察、所属 watcher 退场。不得修改 profile／metadata、bootstrap 或自动重试。06:30 后不新启、07:00 止实验、07:30 前恢复。grant 记录不是执行回执；后续是否准入及实际结果须单独保存。

水 owner 为 `water-r29-v5`，使用独立新身份，不复用投影会话。root 独立核了 56 host、55 external、95 份 v4 原件、三份旧 metadata、四文件增量 ZIP、base／overlay 引用及源审查，随后实际 freeze／inspect／API audit 通过。4491 source、1391 auxiliary；相对 v4 的 runtime 变化为 bridge、projection_target、session、server_system 四项，42 项规范化显式水合同中真实变化是前三项。原 generator 及三 metadata 保持，不把旧资格授给新来源。

水 source 合同为 `312d504f63f9cfa4f6e5ecc1ba672f8beb6211e9bfb6d3e33ba0950ec99e1b9e`。约 119 MB base ZIP 只保留原路径与 SHA 引用，新 overlay 为 146,657 B；不复制大包入本归档。水在此记录时**没有启动授权**，FABRG／冷 D 尚未执行。原 host 的通用恢复没有保存 projection_transform，因此未来仍须 fresh identity 水会话。

[index.json](index.json)保存 35 份引用和 35 个确定性 gzip 对象，压缩内容 805,085 B，记录 raw／storage SHA 与长度并已逐项解压核验。包含投影绑定、必要宿主、water 源审查／冻结／inspection／API audit 及 root 实际审核记录；未复制两个游戏项目。本包依赖保留的旧来源及宿主记录，不宣称可以脱离那些输入独立重建或涵盖完整运行时／GPU依赖闭包。

当前水、书、末地新源原生资格仍为 false。CPU-v8、私有两库验证、静态宿主检查及这些准备都不增加人工关闭数；旧失败与旧版本资格按原来源保留。
