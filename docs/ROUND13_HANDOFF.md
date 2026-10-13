# 第十三轮恢复交接（2026-10-13）

本轮截止今日 15:50，不休眠。全部后续任务继续集中维护在 [IMPLEMENTATION_GAPS.md](IMPLEMENTATION_GAPS.md)；本文件仅保存准确恢复入口和已验证边界。先读统一清单顶部最新检查点，不从 ROUND12 的空白原生参照或 UI 物品缺图重新开始。

## 仓库和现场

根仓库 `D:/Happy2018newの个人文件/GitHub/better-building-editor` 的 `dev` 已整合全部专项代码和证据，源码及专项证据截止 `8c321e4`，后续收尾提交仅保存根验证和交接。不推送、不改 main／render-dragon。五个用户暂存 `tools/p0_palette_*probe.py` 保持原字节和暂存状态，排除在全部提交之外；依据 `.runtime/r13-protected.json` 校验，main 为 `160e551667f45af3d540d185f8e1e5efda07c14b`，render-dragon 为 `0b20a29c42cbd2f0b0ba2a47e4a4369f017d0fa1`。

本轮所有自有 MC／MCDK 按准确 PID／创建身份核对停止，配置、资源和注册恢复。旧 ready session 不可复用；21 个低资源 NT 残留仍可枚举，不能称完全销毁。新游戏仍需准确身份、最多五个活动 MC、后台 WGC；禁止激活、resize、桌面输入或前台回退。根归档中的被动进程枚举不代替活动状态分类。

专项工作树 `D:/bbe-r13-background`、`D:/bbe-r13-liquid`、`D:/bbe-r13-snow`、`D:/bbe-r13-item`、`D:/bbe-r13-scaffold` 均干净，无未集成源码。不要再 merge 整条旧代理分支或其同步基线。本轮均以精确所属 blob 整合。

## 可恢复入口和结果限制

| 范围 | 入口和可靠结果 | 保留的限制 |
| --- | --- | --- |
| 水 | [V4b](NATIVE_LIQUID_WRITE_RESULT_R13_V4B.md)；`probe_liquid_original_sides.py --fixture-height-above-foot 2`，新会话仍需石块三视角标定。H／L palette／direct／full 六组均可见，14 原 PNG 可靠。 | H 3px 边界仍 FAIL；投影亮度／纹理不同，UV／alpha／animation／production false。+24 空图根因未唯一证明，无需为后续矩阵重复定位。 |
| 水高度 | [输入与数学审计](LIQUID_NEAR_HEIGHT_BASIS_R13.md)：16 完整邻域，H `44/63→178`、L `5/36→35` 与发布载荷一致。 | 回读只验证规则输入，不验证 native mesh 公式；H 量化最多 .339px，原波浪 shader 活动性未知，不能据此拟合水高度／FOV。 |
| 植物 | [居中罂粟](CENTERED_PLANT_RESULT_R13.md)、[四坐标](NATIVE_PLANT_COORDINATES_RESULT_R13.md)、[可信来源边界及 holdout](PLANT_COORDINATE_SOURCES_FOLLOWUP_R13.md)：原生和候选有可见花，原生相邻及负坐标位置确实不同。 | 干花 recall .598／precision .685 未过 .75。未找到可信 NEMC 坐标哈希，选择盒不是 mesh pivot，禁止拟合现有图；`POSITION_PLANT_PROXIES={}`。 |
| 物品 | [原生诊断](ITEM_RENDER_DIAGNOSTIC_R13.md)、[接入／版本合同](ITEM_RENDER_INTEGRATION_R13.md)：UI 比例 `1/16` 完整剑 1908、glint 1819、时间变化 990、普通／恢复 0。 | World 同 UI 比例太小，默认 1 可见但本体 72<80／恢复 1124 失败；UI/world 单位独立。BoundItems 尚无 Scene／projection 调用，服务端路线私有显示未验证。 |
| 脚手架 | [状态生命周期](SCAFFOLD_STATE_LIFECYCLE_RESULT_R13.md)：+2／+18 天然空气 states=None，草为 {}。单格准备 server SHA `cb3f8d2bcbfe353634cd0fa8c50e9ce15e9f556da3b89cbfee33d7423efa2259`。 | 单格未运行、未绑 owner；需新冻结身份／来源和无冲突保留区，正常15秒／绝对45秒／清理15秒。表仍14实测／15844未知，不补 None 为 {}。 |

植物首次启动图为空，reliable=false 已明确报告且原件保留；随后12张矩阵和2张就绪图可靠。Editor 用内置蓝图验收，full／missing 投影须独立测试；原生能力阳性不能替代共享深度、透明贡献、切面、已建格隐藏或生命周期。

## 诊断隔离与冷重放

`9c7c741`、`ebba7cf` 修复 runtime／owner 共用模块串扰。`isolated_diagnostic_module.load` 只加载相邻宿主源码，为每个实例登记独立模块，失败移除登记，完整来源仍可扫描。串行导入回归检查原函数、candidate、owner 及实际 contract 返回值稳定。`22e74e0` 纠正 standalone server owner 创建诊断 actor 却声明无世界修改的矛盾，旧冻结证据原样保留。

[冷重放说明](LIQUID_NATIVE_ARCHIVE_REPLAY_R13.md)：V2 只含 helper 与三归档的冷目录复算原 FAIL，所有数值一致；缺模块不回退当前源码，CRLF／PNG 单字节篡改拒绝。V4b 有193条混合记录／117源码，在一次性冷副本按原索引与 frozen_project 派生别名后精确复算 OBSERVED，实际导入46源码。默认 CLI 直接消费混合 index 仍拒绝，派生方法和原拒绝已归档。此兼容入口归 M07，不可通过放宽 SHA 解决。

## 根验证

[根验证归档](evidence/round13-integrated-verification/archive-index.json) 同时保存原失败、最终结果和准确整合／被动枚举：

- V1：2345项／8 errors，诊断串扰，原 passed=false 保留。
- V2：runtime隔离后2374项／183.457秒，97来源与全部生成检查通过。
- V3：owner隔离后2375项／180.134秒，同来源／生成检查通过。
- 最后仅改 owner 元数据及契约断言，根物品22项／6.987秒通过，未把此前全量称为覆盖最后这两处增量。
- Runtime导入审计172文件、违规零；projection结构扫描144文件成功，48个既有advisory不是功能验收，新BoundItems无新增finding。
- 最后719个所属Git blob、663个索引原件／62045241字节精确核验，用户暂存和两分支保护通过。源码格式检查通过，原件CRLF保持。

总体继续粗估75%（70%–80%）。本轮缩小了关键故障范围并验证实际附魔能力，三项主要渲染仍没有完整产品关闭，测试和提交数不能换算为产品完成率。
