# R23 压力板静态信号专项

2026-10-19 的小型内置蓝图已在真实编辑器、完整投影和缺失投影中完成一次静态状态检查。四种材质均能看到信号 0 略高，信号 1 与 15 共用压下外形。该结果提供了可复查的状态差异证据，尚未证明与原版世界的绝对厚度一致；**本专项关闭 0 项问题，压力板问题仍开放**。

## 内置蓝图与范围

入口为 `test.blocks.pressure_signals`，显示名为“压力板 · 信号 0／1／15”。源文件为 `behavior_pack/modern_projection/projection/debug_pressure_blueprints.py`，尺寸 16×5×20，包含 12 个压力板和 12 个石英支撑块。

| 行 | 材质 | 三列状态 |
| --- | --- | --- |
| 1 | 石质压力板 | `redstone_signal=0 / 1 / 15` |
| 2 | 木质压力板 | `redstone_signal=0 / 1 / 15` |
| 3 | 轻质测重压力板 | `redstone_signal=0 / 1 / 15` |
| 4 | 重质测重压力板 | `redstone_signal=0 / 1 / 15` |

四行的位置分别为 `(3 + 列号×4, 2, 3 + 行号×4)`。这是明确保存状态的静态外形比较，不模拟红石、玩家踩踏或重物数量。信号 1 与 15 应共用压下外形，不应把二者缺乏差别判为故障。

## 实测证据与修正

可跟踪摘要为 `docs/evidence/pressure-fixture-r23/preflight-v1.json`。它保留原始报告、显示／隐藏原图、原生捕获回执、36 个有效单板裁图、联系图及源文件 SHA256，而不把截图全部复制进仓库。

| 路径 | 有效报告 | 有效样本 |
| --- | --- | --- |
| 完整投影 | `.runtime/round-20261019/pressure-fixture-proxy-v2-run-v1.json` 的 `full` | 4 材质×3 信号 |
| 缺失投影 | 同一报告的 `missing` | 4 材质×3 信号 |
| 真实编辑器 PaperDoll | `.runtime/round-20261019/pressure-fixture-proxy-v2-editor-v2.json` | 4 材质×3 信号 |

三份联系图均已查看：

- `.runtime/round-20261019/pressure-fixture-proxy-v2-run-v1_full_contact.png`
- `.runtime/round-20261019/pressure-fixture-proxy-v2-run-v1_missing_contact.png`
- `.runtime/round-20261019/pressure-fixture-proxy-v2-editor-v2_editor_contact.png`

第一轮 `run-v1` 的编辑器采集**不纳入结果**。工具直接写入 `camera_pivot`，没有驱动已经挂载的 Scene 消费定位请求；四行实际仍处于同一构图，部分裁图落到其他材质。原图已暴露此问题，不能因差分非零而使用。修正后通过 `locate_selected()` 发出请求，等待请求消费且实际 pivot 与目标一致，再设置缩放、姿态并清空焦点。`editor-v2` 已重新逐行捕获并目视核对，旧报告及原图仍保留。

有效编辑器构图为 yaw 0°、pitch 10°、zoom 5，约 88.38 原始物理像素／方块；世界构图偏移 `(0, 1.5, -9)`，约 98.54 像素／方块。工具拒绝屏外、被视口截断及低于 64 像素／方块的目标。编辑器使用实际 doll 控件的显示／隐藏控制，世界使用实际投影 actor 的显示／隐藏控制；裁图按实际投影坐标生成。

两份报告均完成并恢复，文档、grid、选项、导航与游戏相机读回一致，无残留 active／preparing 投影，`cleanup_errors=[]`。被测快照资源哈希未变。有效结果为 12 组“材质×路径”、36 个压力板；它们不是 36 项独立问题。

## 工具验证与剩余工作

维护工具为 `tools/verify_pressure_fixture_r23.py`。`--plan-only` 可先输出计划；实测必须明确绑定 session、owner、project 和原生单帧捕获程序 SHA256。离线检查验证了全部 12 个状态、24 个方块、逐行构图，以及屏外／截断／过小目标的拒绝；修正后的 30 段游戏注入已使用实际 Python 2.7.13 编译通过，记录为 `.runtime/pressure-fixture-r23/py2-compile-focus-v2.json`。

仍需对照原版世界的绝对厚度和贴图，检查其余 12 种压力板材质，以及真实世界占用下的缺失消隐和必要组合。部分编辑器裁图经过蓝色选中边缘，世界中间列经过准星，不能把这些图直接当作干净的原版厚度基准。红石实时模拟不在本蓝图范围。摘要中的 `shape_accepted=false` 保持不变。

实例 `alpha-r23-proxy-v2` 已于 2026-10-19 22:24 释放给主代理；该专项之后只整理离线证据，没有继续访问 MC。
