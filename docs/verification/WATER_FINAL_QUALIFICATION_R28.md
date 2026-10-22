# R28 当前水产品最终资格：BRG、冷启动 D 与共享正式门

2026-10-23 凌晨，在当前合源 F/A 已通过的基础上，完成独立同会话 B/R/G、disposable provisional admission、普通冷启动 D，以及 root 亲自执行的官方共享最终资格。最终 manifest 的 `stage=product`，原有 16 个产品门全部为 true，正式 owner 与资格常量由官方工具生成。**本轮人工关闭数增加 0；未宣称与原生水的几何、RGB、动画速度完全一致。**

本文是 [当前 F/A 记录](WATER_CURRENT_FA_MATRIX_R28.md) 的后续专项记录。F/A 记录中的“当时 B 尚未采样”、旧 host 路径拒绝和旧分析器拒绝仍为历史事实，不覆盖旧结论，不把早期失败改成通过。

## 最终结论与证据范围

| 阶段 | 本次使用的原要求与结果 | 不扩展的结论 |
| --- | --- | --- |
| F | 既有当前合源三路径 × 19 case，精确几何、独立 alpha／透明度、UV、可见性、生命周期和预算通过 | 保留各单路径原汇总值；整体预算来自原合并工具 |
| A | 既有三路径 × 东／南／西／北／下落的 15 cells，可见动画和物理方向通过 | 不据此声称原生速度幅值一致 |
| B | 三路径群系控制及 missing 占位恢复，原门通过 | 占位要求为准确移除一个已发布 cell，恢复全部四个 |
| R | 三路径 × 五个反向邻接／透明重叠 case，source cells 和 shapes 与 F 一致，独立可见性通过 | 未接受反向视角逐 case 精确几何；五条编辑器泛用几何失败保留 |
| G | 编辑器完整加载 81-cell 公共全览，scene size 为 40 × 8 × 50，聚合水像素可见 | 未以缩略全览证明每个 case 精确几何；一条泛用几何失败保留 |
| D | 正常冷初始化、不指定候选 profile；三路径 source／pool／wet fence 可见，动画和精确占位恢复通过 | D 的三个动态透明度诊断仍为 false；不替代 F 的同相位独立透明度门 |

最终 16 个原门为 animation、biome、budgets、default_path、editor、geometry、lifecycle、neighbors、occupancy、projection_full、projection_missing、public_gallery、side_uv、transparency、transparent_overlap、visibility。最终通过来自原 qualifier 的既定职责分配，没有改门限、ROI 或算法，也没有把所有阶段的全部泛用诊断都重标为通过。

## BRG 实测与保留的失败

独立 owner 为 `water-r28-final-brg-v3`，只安排同会话 camera → B → R → G；已通过 F/A 没有重复启动重拍。group 完成，用时 473.5204 秒。

| 阶段 | 原始行数 | 原始静态 PNG | 结果 |
| --- | --- | --- | --- |
| B | 6 rows、13 extras | 23 | 群系与精确占位恢复通过 |
| R | 30 rows | 30 | 15 个湿态可见性 cell；30 行 source cells／shapes 与 F 一致 |
| G | 2 rows | 2 | 完整 81-cell 全览与 461 个聚合可见水像素 |

R 的 15 个可见性 cell 为 5,769～21,082 个贡献像素。原始 R 编辑器 `neighbor_oak_slab`、`neighbor_oak_stairs`、`neighbor_glass_pane`、`neighbor_stone` 和 `transparent_overlap` 的泛用几何诊断仍失败。保留的离线几何诊断讨论了反向视角与 Scene 裁切的关系；BRG 当时没有逐次捕获实际 canvas／clip 的读回，不能用另一次 D 的读回补写成 R 的实测证据。

G 的泛用几何 IoU 约 0.59715，仍为失败。全览中的 19 个平移后 shape 集与 F 相同，支持全览加载和源几何一致性；小尺寸整幅全览的聚合可见性不被用作每个 case 的精确几何验收。

root 显式审核并接受的是表中 R/G 的原门范围。五条 R 失败、一条 G 失败及原诊断全部保留；未重新选择 mask、ROI 或阈值，未重新拍摄并覆盖这些旧记录。

## 源闭包与两套冻结 metadata

F/A/BRG 冻结 source contract 为：

`4e4eb7fff2b3dd8d6519ce70c7290c911f6c54ff2c9dbd0e7d3cf160a6b54749`

D 冻结 source contract 为：

`18d36ac18162771addcd9e23ac3692ab3e86e94c9f0944de3a75f413f64f016f`

每套均核对 4,483 项源文件和 1,391 项辅助文件。D 与 F/A/BRG 的生产实现 39 项、资源与注册字节相同，只有以下三个 metadata 字节不同：

1. `tools/data/liquid_product_owner_contract_v1.json`；
2. `behavior_pack/modern_projection/projection/liquid_product_owner_data.py`；
3. `behavior_pack/modern_projection/projection/liquid_product_qualification_data.py`。

前两项由共享官方 generator 独立计算并核对；第三项是官方 qualifier 对 disposable project 生成的 `isolated_candidate` gate，用于冷启 D，不能直接复制成正式资格。provisional manifest 的 `default_path=false` 保持原值。

disposable 项目由既有基 ZIP 与精确小 overlay 重构，没有硬链接或新的大源码 ZIP。首次准备脚本因 release 字段误写为 `restored` 而失败，发生在创建项目之前；失败记录与原脚本保留，v2 只改读实际字段 `independent_restored`。原 source contract 没有被重命名或改写成后续最终共享快照。

## 普通冷启动 D

root 独立审查 D 的 24 个 bound host、49 个外部依赖、全部源与辅助文件，并单独授予唯一 MC 槽。实际单次 group 为 camera → D，总用时 475.6358 秒；相机 54.3414 秒，D host 268.7316 秒。没有 bootstrap、没有在运行时指定候选 profile，没有热重载替换生产实现。

冷观察先看到系统存在而普通 Session 尚未初始化，随后自然得到 Session/HUD 与 `ProductLiquidProfile`。末态 `profile_callback_is_source_function=true`，`explicit_bootstrap_performed=false`、`profile_assignment_performed=false`，引擎为 `3.10.0.420447`。

相机有 12 项真实单石观测；相机后独立恢复通过。D 完成 30 rows、22 extras、59 张原始静态 PNG，`completed/restored/source_unchanged=true`，无 cleanup errors。D editor WGC 前后另有 38 次 native bank 与实际 Scene canvas／clip 读回，直接记录 SDK integer GUI、cache 和 native 布局；没有借用旧 F 的 canvas 代替本次读回。

原 default-path 要求全部通过：

- source、pool、wet oak fence 在 editor／full／missing 中均可见，九个可见性 cell 贡献像素为 3,450～49,992；
- 九个动画 cell 均有可见变化，未冻结动画；
- missing pool 占位时准确删除一个已发布 cell，撤销后恢复原四个，source cells 保持一致；
- D 分析 `evidence_valid=true`，没有几何／alpha 失败。

D 的三个动态 wet-fence 透明度诊断仍为 `passed=false`、`phase_controlled=false`。各自 body／rear 的可见贡献区域通过，整体同相位条件没有满足；原结果完整保留，没有把区域通过写成整体透明度通过。最终独立透明度门仍使用 F 的同相位控制，不用 D 的动态图重评级。

## 官方最终共享生成与资格

root 打开并审核九张 D 基础原图及两张占位／恢复原图，独立核对全部 59 captures、源闭包、host 与精确释放，再生成正式 root review receipt。final wrapper 先完成只读 inspection；最终执行由 root 亲自完成，顺序为：

1. 显式激活并核对 FA、BRG、D 各自同会话相机、原 startup validator 与已审 seam extractor；
2. 验证八份原始报告的 source closure、39 个共享生产源以及全部输入 SHA；
3. 执行共享官方 generator，再执行其 `--check`；
4. 调用共享原 qualifier，含 `--default-report`、`--native-world-geometry` 和 `--native-editor-gui`，`admit_candidate=false`；
5. 由 qualifier 的正式 `set_gate(ROOT, …)` 写入共享产品资格，不复制 disposable gate。

共享恰好变更前述三个 metadata；disposable D 的全部原字节保留。F/A/BRG 和 D 仍分别使用自己的捕获源 contract，不声称正式 gate 写入后的共享完整快照就是 D 当时捕获的 source contract。

| 原件 | SHA-256 |
| --- | --- |
| 最终 product manifest | `2f827d28f74ee5f70f5301e556e170003314baa1b0927ef46f4f152dd9947625` |
| root 最终审查 receipt | `15b9c67e58d9a1d6db9bbca343d71fdf6ef617174bb2ef8cfc935fef2a2b4707` |
| final wrapper | `02bc7ca0055ab283c7117d69d18b68860a13b5f681735e51df58814ce6b763fc` |
| final 只读 inspection | `0dbfdb21dd2a25a3debded4ece8bbe88c933636d936a4fdb0e3c7e91f7df6502` |
| D 原始报告 | `826bdc8446b63a1cc69792c5abec8b0d0ed7b947dc3535f9f910d3225463b8a4` |
| D 原 default-path 分析摘要 | `afde0a2381418e9bfe6576eed39d01e2187a57be02985d48f8221079ec67ad27` |
| D 冷观察 | `2e7d6d19a87e3781488e15fbbfde62f35e0a43881048ad36f50c61a37135874a` |
| 共享生成 owner contract | `f54d64cdab7292832ee1fc9c870905fdd45ec030739b61836812db527bfcc684` |
| 共享生成 owner module | `12eb260ab36dcb1d64ccd06f4912319bf6925e624194b57ec90a15c3de3f4ef1` |
| 共享正式 gate module | `f27e2351c83fb35fa7bade5879375ed388eb328cd78ac5591d7bdd48764bbc0d` |

## 恢复、精确释放与小文件证据

BRG 与 D 各阶段后均独立恢复 Scene、世界和相机，最终源保持不变。普通 stop 首次返回游戏尚未关闭；既定等待内，同句柄观察记录游戏 `0xC0000409`、MCDK `0x00000000`，registry finalize 成功。没有 force、进程挂起、调整资源门或无条件重试。

BRG、D 各自的 game／MCDK／observer／launcher／continuous guard／assert watcher 六个精确 PID 加 creation identity 全部 absent。没有把 identity 消失写成游戏 code 0 正常退出。BRG 精确 release SHA 为 `e7317f93920dd19ff6dd50aafc46b95f91a0fa5a58338189ef35b192a28c7676`；D 为 `ec66cca915a5c135712402e123a0a304a115d6214570b6de4d2df601ae9bfa71`。原 group 的观察快照保留，最终同句柄 exit 在独立 release 中补证。

D 启动前可用 commit 约 14.9 GiB；固定最低 6 GiB 门没有降低。D 150 个资源采样中 game handles 最大 849、MCDK 最大 234，原 250,000 上限与相邻增长 10,000 门保持不变。没有修改用户自己的进程。

[最终精简证据索引](../evidence/water-final-qualification-r28-v1/index.json) SHA 为 `db473930f58b652e38ff0bfc6ed352ebcfcf333d6149410b23e85aed88c09202`。185 个对象、209 个存储文件，共 11,136,077B；最大单文件 239,000B，15 张精选原 PNG 保持原字节。大对象确定性 gzip 后分块；原始 SHA、派生 SHA、脱敏字段及重构方式分别记录。

126 张本次静态原图（含两次相机）及其 capture receipt 全部按原路径、字节数和 SHA 列入 runtime 索引；未选择的原 PNG、源码基 ZIP／overlay 与既有 A burst 保留 runtime，没有复制大源码 ZIP 或整套 burst。此前 F/A 包仍按其原索引单独引用，不重复拷贝。原 R/G 几何失败、D 动态透明度诊断、准备失败、provisional `default_path=false`、恢复与非零游戏退出观察全部保留在包中。

独立重构已逐字比对 183 个未脱敏原对象，重新计算并比对 2 个脱敏对象，核对 421 个精确 runtime 引用；185 个对象及 209 个存储文件全部通过，凭据发现数为 0。该检查重新确认三个 D 动态透明度诊断仍失败、R/G 精确几何未被重评级，未启动 MC 或修改任何 owner／资格。
