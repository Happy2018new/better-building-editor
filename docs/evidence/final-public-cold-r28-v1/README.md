# R28 最终源公共入口 v1 首失败

本包绑定 b70ce7bf13ad6a4472f2b089ac812c162b174861。该次真实冷启动只完成第一张单水格卡的一对公开 load/confirm；五卡测试没有完成，合格自然主帧为 0。两张原图分别是卡列表和加载后的编辑器，均已查看，原字节复制。编辑器图中可见水与石基座；这不代替尚未通过的自然帧完整门。

首失败为 host 的 `Complete typed water document changed`。现场原生 expected、public actual 与水 STATE 的原 wire 完全相等；host Py3 与原生 Py2 的 material 索引顺序不同，导致对应压缩 chunk 字串不同。后续只读证明分别由真实 Python2/3 使用原 Document.from_data 解码全部 800 个位置，对前景/aux、背景/aux、完整 actor 类型、headers/registry、所有材质和 palette 行及 chunk 坐标进行严格语义比较，统一摘要相同；两解释器的 12 个错源/未知字段负控均拒绝。原失败继续保留，不把离线证明记为原生成功。

原 finally 双原稿恢复通过，cleanup_errors 为空，源与 41 host 未改；原 ordinary stop、独立精确 PID/创建身份释放与 watcher 退休完成。游戏退出为 0xC0000409、MCDK 为 0，正常引擎退出资格为 false。没有修改该 owner 的门、重试或 force。人工关闭 0，runtime_pixels_qualified=false。旧书 v4 仍只绑定此前 source48；此失败不转授其资格。
