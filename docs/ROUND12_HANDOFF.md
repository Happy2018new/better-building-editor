# 第十二轮恢复交接（2026-10-13 上午）

本轮形式截止为今日 12:00，不休眠。03:10 后中断，08:46 恢复；暂停时段不计工时。10:35 查询 API 订阅可用约 40.75 美元，充值余额未知，已接近 40 美元保留目标；提前收束。最后一次水诊断、恢复、必要回归和所属结果提交已完成，不再追加候选或 Astra 咨询。

唯一待办仍为 [IMPLEMENTATION_GAPS.md](IMPLEMENTATION_GAPS.md)，本文件仅保存恢复入口。进度口径继续为本轮粗估贡献 2–4 个百分点、总体约 75%（70%–80%）。主要水／含雪植物／物品附件／glint 缺口尚无完整关闭，不能用测试数或运行完成标志提高功能进度。

根仓库在 `dev`，不推送，不改变 `main`／`render-dragon`。五个 `tools/p0_palette_*probe.py` 用户文件保持原暂存状态，禁止混入提交。所有整合都使用准确 owned 路径；新归档中 ignored 配置仅准确路径 force-add；无需 stash 用户修改。

## 已集成

- `6b1dfef`：流水顶面 opt-in 候选，默认 profile 不变。独立顶面 mesh／UV／256 角度、方向源码和资源来源精确哈希；GLES 56 组／28,512 检查通过。原生方向与 UV 未接受、production false。
- `98596a3`：含雪实际业务 UiInit 门控和 V1C 高处天空失败，147 owned Git blobs exact。
- `cf085fb`：含雪近处夹具、实际 forward 检查与跨 render 相机恢复，V1E 原生植物可见、首投影无植物；正式 follow owner 改变物理 anchor 后 whole tuple 断言失败，证据保留。
- `52cdfbe`：R15 有限深度执行器和实际牛 Molang overlay 遮角标失败，0 次剑绑定，247 owned Git blobs exact。
- `95bf203`／`f7c9f3d`：真实水 world-ready 等待、保留区与清理、live 相机 mask 精确绑定复用，独立真实六图 cache/recompute 完整结果和衍生像素一致。根 17 readiness 和 26 camera tests 通过。
- `02f9e56`：统一待办和进度边界。
- `b9198f6`：含雪 V1F 八状态实际植物缺图与恢复结果，117 非共享属性 Git blobs exact；根 28 项定点回归通过。
- `506cf5b`：物品 R16 真实玩家正控／普通剑深度负观察、file identity 工具及冷检出便携修复；根 22 项物品诊断和 3 项文件身份测试通过。原始 helper 按哈希私有加载，保留根当前工具版本。
- `125262f`：水 V11 不完整矩阵、三张水尝试原图及成功恢复，32 所属 Git blobs exact。

完整根闸门 `.runtime/version-bundle-r12-0940-v1.json`／`.log` 在流水顶部+V1C 整合后通过 2,204 tests／398.501 秒、97 来源和全部生成检查。它早于后续深度与含雪 F 整合，不能替代其定点回归。

## 最终实机观察

物品 R16 的 14 原图完整，四角标记有效，真实玩家首尾约 547,335／546,155 稳定像素；同 anchor 普通剑 depth -15/-50/-15 全部 0，恢复空场差分 0。Runtime/health completed、restored true，cleanup 无错误。深度没有解决普通 UI 附件，glint 未进入有效测试。停止超时原件保留，随后两个原创建身份均 absent，saved ready 仍 stale。下一候选可用明确可见真实网易骨骼主体 + 对应 BindItemToSkeletonModel 检验模型家族；不得把 PaperDoll modelId 当 entityId。官方资料研究来自 UI控件 RenderEntity/RenderSkeletonModel/GetModelId、物品 BindItemToMinecraftModel/BindItemToSkeletonModel、模型 SetModel；没有保证全部 client 实体 world 附件会进入 UI。

含雪 V1F 完成原纹理八状态／13 原图：native plant 12,370、projection plant 0；native snow 25,956、projection snow 25,846；covered-minus-snow 原版 10,344、投影 0。雪轮廓在冻结容差内；粗 covered 面积匹配不能盖过植物正控失败。实际 actor foot+1、每 part offset 原生 bool、logical origin/parts/unit scale稳定，正式跟随保持开启；跨 render 相机恢复、factory／探针／监听移除和 owned stop 全通过。Alpha 未运行。下一轮从真实植物缺图修复，不再纠缠已通过的加载/方向/位置门控。

水 V9c 是 transport-ready 加载坐标 32768、无图无夹具；V9d 实际 world-ready 后取得 7 原图，但重复石块信号计算吃掉 normal60，相机／environment 恢复未证明。V10 完整校准 FOV66.6及全部恢复通过，首水图前因相机 setter 即时 getter 返回上一帧旋转而失败，无水／alpha。最终 V11 在预声明和每捕获前等待至少两个实际 render、连续稳定实际相机读回、forward dot>.99，保持原 strict camera 门槛，并在断言前保留 raw state。V11 共取得 10 张原生 PNG（首世界图 1、石块校准 6、水尝试 3），full_h_vnw 可见半透明蓝水与下方石块，但 native_h_vnw/native_l_vnw 只有草地／HUD，无水和支撑块；SDK 块读回不能证明可见原版正控。第二个 full case 因 projection_liquid 为 None，在状态读取时报 NoneType.renderer，未完成矩阵，alpha 为 0。侧面 UV／动画／透明度／流水顶面／production 均未接受。句柄峰值 848，非句柄或期限失败。全部 216 格读回空气，flow／camera／visual／Scene/profile／environment／render observer 恢复通过，cleanup／persistence errors 为空；actual-ready 到停止 114.159 秒、创建到停止 187.338 秒。没有 V12 重试。

## 整合入口与边界

物品工作树 `.runtime/r11-frame`：`db07045` R16 最小正控变化、`c0aad44` 74 原件约 2.08MB、`4ee5d9b` 正常 file identity 依赖与 git-common-dir定位、`6bd42d9` 按精确哈希加载已提交不可变 R14 helper 和 R15 deadline 源。根已合入 `506cf5b`，早期 `.runtime/item-depth-root-tests-r12-v2.log` 的 sibling import 失败保留，最后根全部 22 项 depth 回归和 3 项 file identity 测试通过。冷检出测试复制必要已跟踪文件，不依赖 sibling／`.runtime`。

含雪树 `.runtime/r11-snow`：`7a6a6b4` F settle/透明 offset 提交探针和 `8097720` 59 结果原件。根已合入 `b9198f6`，receipt `.runtime/integrated-snow-v1f-r12.json`；归档 index `5f9234781b4e0fb28e6a90756524a4c7bd6427f3f32a4cb0a40443a833e179f3`。根 F 28 定点回归和独立增量 QA 通过。

水树 `.runtime/r12-liquid-production`：最后 plan `.runtime/liquid-priority-r12-v11/plan.json` SHA `7bccac448271093c6cdda2a0efc6e7ed521c1eb16dc317cc576818d792c27585`。Owner `liquid-r12-priority-v11`，session `c717a150a6964991956bda8de03f4151`，game1556 creation134363326438374356、MCDK52556 creation134363326436169860，两精确身份均 absent、session stopped、WGC 已释放。来源 `095e410` 的 32 份最小结果已逐字合入根 `125262f`，约 9.05 MB，没有复制整套 world／冻结包；归档入口 `docs/evidence/liquid-priority-r12-v11/archive-index.json`。根 `f7c9f3d` 的 probe_liquid_workspace.py 与 `1b56e22` final 来源相同；三个 side oracle 文件与 `483c09a` 相同，三个原生启动工具／测试与 `8459ce7` 相同，无额外工具依赖待迁移。仅隔离水树有原有 capture_native_burst.py 修改，本轮未暂存／提交它。

最多 5 活跃 MC，后台 WGC 截图，禁止前台激活／resize／桌面输入回退。旧20个 NT残留零thread/handle/VirtualSize/CPU对象，仅不占活跃容量，不能称已完整销毁；新增或变化条目保守计 active/unknown。后台截图无可靠取得必须明确向用户报告。
