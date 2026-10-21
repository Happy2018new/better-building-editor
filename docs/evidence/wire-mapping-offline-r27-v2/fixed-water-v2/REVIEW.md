# R27 离线 mapping v2 候选与跨版本控制

这是供下一轮独审与重新冻结的离线工具候选，**没有接入本轮 trial，没有重跑 MC，没有修改冻结 v1 或原始报告，没有获得产品资格**。

`mapping-exact.diff` 给出完整差异。核心只把外层 transport 解开后仍保留的 `entry['value']` 再解一层，并严格要求原始账本条目只有 `sequence/value`、序号为正整数、内部值仍是独立包装的 tuple。原有实际 native 调用序列、活跃 handle、资源映射、参数和值检查保持。其余两处差异只是独立 v2 schema 名以及继续读取既有冻结三片元 manifest 的路径。

`export_exact_observer_py2.py` 使用真实桌面 Python 2 执行 **原始冻结观察器的精确源码**；native component 明确为 fake，不声称游戏能力。它真实通过观察器代理调用了 15 次模型／uniform 方法，导出 5 份 snapshot。样本包含成功值、false 返回、原异常对象再次抛出、隐藏可见性、成功删除后复用同一 handle 而资源不同、两次创建历史和零存活模型。观察器导出 JSON 后恢复原组件对象与原类属性，空 dry 也从真实同一观察器源码导出。

Python 3 的 `test_py2_to_host_v2.py` 直接读取这份 Python 2 文件，而不是由 Python 3 重新模拟 observer 格式。18 项控制全部通过：非空 wet 正向、空 dry 正向、空 wet 拒绝、冻结 v1 必须继续拒绝该合法非空样本、原 v7 864 次真实调用及 288 次 group 快照只读关联，以及逐项变异后的拒绝。变异包含 native sequence、账本 sequence、账本 value、active handle、资源名、group uniform、visibility、实际调用参数、错误少一层表示、opaque 表示、丢失调用、把 false 或异常伪造成成功。

`host-cross-controls-v1/report.json` SHA 为 `27b02571aa0c2d1429c84e325bc22c2f5a645cd3b5680a2776d46552bcde313c`。原湿场景 `completed=true/restored=false` 判定保留；v2 对已保存数据的成功关联不是一次新游戏验证，也不会覆盖原失败。后续必须由 root 独立复跑控制、审查完整差异，再决定是否给下一轮建立新 host 冻结。

复核方式是先用 `D:/Program/Python27/python.exe -B` 运行 exporter，传入 `fixed-water-v1/water_setter_observer.py` 的绝对路径和一个全新输出目录；再用 `D:/Program/Python/python.exe -B -X utf8` 运行 host 控制脚本，传入该导出目录和另一个全新输出目录。两脚本都会拒绝覆盖已有输出，均不导入游戏 API 或启动 MC。
