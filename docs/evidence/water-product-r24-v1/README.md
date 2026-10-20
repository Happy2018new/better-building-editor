# R24 自定义水：正式准入精简审阅包

2026-10-20，主仓正式 qualifier 已完成，`stage=product`、16／16 门通过。精确目标为 NEMC `3.10.0.420447`，风格为 `java_snapshot_water_v1`。正常会话会自动选用产品水；原生水没有重新作为验收方案，岩浆仍走已接受的原生路线。

`qualification.json` 与生成门 `qualification_data.py` 是原字节副本，资格 SHA256 为 `a324df78aa8d714cb31a0f1093676fe574c5fce40b051ff6f53eec2840e28596`。manifest 绑定39个产品owner源、资源合同、分析器选择、各成功原报告及冷启动默认入口D-v2；全部运行时来源仍指向保留的 `.runtime/round-20261020`。源合同细节、各阶段计数和未覆盖范围见 [本轮记录](../../WATER_CORAL_R24.md)。

包内保留两张已实际查看的联系图：

- [三路径默认水与含水栅栏](default-wet.png)：editor、full、missing，包含 source、pool、wet_oak_fence。
- [缺失投影占用与恢复](default-occupancy.png)：只移除指定一格的自定义水，源文档保留，随后恢复四格。

两图均是联系图的未改字节副本，分别组合了原捕获的局部画面；不是完整原图集合。`default-reviewed.json` 保存30行、9个wet用例、59次捕获及审图回执。原报告明确没有给会话赋候选profile，默认路径自动取得正式style；动画9／9、独立可见性9／9，完整恢复且源不变。`focused-tests.json` 是正式门生成后5模块63项回归的运行回执。

`d1-startup-failure.json`、`condition-change.json` 和 `archive-parity.json` 保留失败与受控运行条件变化：D-v1在旧实例仍活跃时增长至原句柄上限而中止；D-v2先停止旧实例，保持相同4,463项源和完全相同归档字节，以唯一活跃游戏完成验证。这个对照不证明并发是唯一根因。`d2-stop.json` 和 `d2-exact-exit.json` 明记：验证恢复后正常关闭未退出，按创建身份force，game退出1、MCDK退出0，不能写作干净引擎退出。

完整冷源zip、631帧动画burst、PNG／sidecar和旧失败继续留在本地运行目录。本包用于审阅结论及检查来源，**不声称脱离本地raw数据能够独立重跑全部GPU验收**。所有结果均为开发侧检查，用户人工通过计数未增加。

仅核对包内文件及正式门绑定：

```powershell
python -I docs/evidence/water-product-r24-v1/verify.py
```

另核对当前工作区39个owner源、资源／owner合同、qualifier和门与本次资格完全一致：

```powershell
python -I docs/evidence/water-product-r24-v1/verify.py --project .
```

这两个命令只做字节完整性和准入绑定检查，不启动游戏、不写门，也不把哈希通过等同于重新取得像素证据。
