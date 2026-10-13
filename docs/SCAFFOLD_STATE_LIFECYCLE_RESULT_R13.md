# 第十三轮脚手架原生状态诊断

本记录属于统一待办 `IMPLEMENTATION_GAPS.md` 的 F04-M11 接续证据，不另建待办清单。生产支撑表仍限定原 14 个状态样本，其余 15,844 个状态不由本轮推断。

## 原生启动 v1

2026-10-13 13:37:49 冻结后，仅尝试一次后台冷启动。计划使用新的防焦点 DLL `04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93` 和已有 MCDK `b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9`。源工具 `probe_scaffold_state_lifecycle.py` 的字节 SHA-256 为 `e2f1e5614f7d8c07703823c7ccbc18ed74443b2f9f4c76e48d86d9664c3f5633`，未改写旧采集段的方法。

计划为 17 个顺序短例：石头、原木、按钮、门、栅栏门、墙、雕纹书架和置物架各一组直接 legacy aux／转换并设置语义状态，再加独立石头正控。逐例复用同一 17 格干燥空气保留区，记录支撑写入后、脚手架写入后、延迟 0.35 秒后的真实 `GetBlockStates`；每例和最终恢复均清空两层。它不尝试完整 15,858 状态扫描，也不产生编辑器或投影像素验收。

启动在客户端进程环境／Debug IPC 可用性校验前失败，返回 `Code execution failed. The player may not be in the game or the target is unavailable.`。MCDK 的 MCP 端点可达，原始日志没有原生 Debug IPC 客户端连接成功记录。77 次被动观察都确认游戏保持后台与 `WS_EX_NOACTIVATE`。因此本轮失败不能归因为已复现的前台激活，也不能由这些观察推出玩家已入世界。

没有到达实际世界／夹具校验，未运行方块写入和生命周期读回，也没有获得 WGC 世界原图。后台画面资格没有取得；这一边界已显式报告给根代理。启动总耗时 145.125 秒。owner `scaffold-r13-lifecycle-v1`，session `79bd38fe236d4e4ca1840002c4a6ee41`；游戏 PID 47640、创建身份 `134363434817926467`，MCDK PID 63092、创建身份 `134363434814592743`。普通停止后独立核对两者身份均为空，清理错误为空。私有 `.mcdev.json` 已移除，全部固定源指纹及 BP／RP 清单字节保持不变。

原件和 token 摘要化记录见 [归档索引](evidence/scaffold-lifecycle-r13-v1/index.json)：13 个文件、756,780 字节、0 张图片、0 个原生状态观察。只有索引明确标识的 session token 字段做了 SHA-256 替换，其余原字节保留。原始计划、失败和预期均不覆盖；不按同一条件盲重启。

## 已完成的来源保护

支撑能力生成器原先把 Python 的 `False == 0` 当作有效整数状态：`stability=False` 可能通过距离 0 的判断，普通字典相等也会把 byte 的 `stability_check=True` 和 int 的 `1` 视为相等。本轮将 requested aux、实际 support aux、实际 scaffold aux 和 stability 限定为真正的整数，再按类型和值核对原生 scaffold states。缺失或无效测量保留为 unknown，类型不符的状态不进入能力表。

这项修复不扩大生产样本，已有生成表字节不变。新增负向测试覆盖 bool aux／stability 以及 int 代替原生 byte。`python -X utf8 -m unittest discover -s tests -p 'test_scaffold*.py'` 的 46 项通过，`generate_scaffold_support.py --check` 通过，仍为 14 个已观察状态和 15,844 个未观察状态。它是宿主生成器保护，不冒充 ModSDK 原生测量。

新增 `analyze_scaffold_state_lifecycle.py` 只接受已完整恢复、源指纹一致的 17 例诊断。它按实际采样时机区分“写脚手架前支撑已经变化”“脚手架邻接写入改变支撑”“延迟阶段改变支撑”和“上半格在脚手架写入前已经存在”，同时比较直接与语义路线。它验证写入前的上半格和紧邻采样一致，保留 bool／int 区别，并始终把能力及三个画面范围标记为未分类／pending。四个宿主回归通过；本轮尚无完整原生输入可供分析。

## 接续边界

旧 21 段 `[0,5376)` 的次序、指纹和 unknown 分类保持。它们的 scaffold states 来自 registry 推导，不能与本轮真实 `GetBlockStates` 方法混合，也不能把 3,167 个支撑变化径直归因于 legacy/new aux 数值差异。

已准备有变化的 v2：独立最小诊断 BP 只包含逐字复制的当前 registry 模块与独立诊断入口，不加载完整编辑器／渲染资源。它仍要求原生会话身份、实际玩家脚坐标和后台新鲜世界图通过，随后才运行同一个 17 例工具。该方案只减少原生状态诊断的无关启动依赖，不替代产品渲染验收；截至本记录未启动，等待团队后台启动资源问题的判断及串行启动槽位。

## v2 的入世界门槛错误与 v3 接续

v2 随后在 14:19:29 使用独立最小包进行一次有变化的冷启动，原生 SDK 和 session 绑定已经可用，WGC 能取得新鲜非空图。但宿主仅检查玩家 ID、非空脚坐标和版本，错误地接受 `[0.5,32769.62109375,0.5]` 这一加载期坐标。实际 PNG 仍是“正在加载”画面。已明确承认这是准备门槛错误；新鲜 WGC、原生 SDK 可达和非空坐标都不能证明实际世界已初始化。

方块工具的原生干燥保留区检查拒绝 `Non-dry reserve`，发生在建立 probe marker、方块写入、掉落规则和液体流动 setter 之前。没有完成任何一个生命周期样本。`cleanup.missing_probe=true, restored=false` 保持原返回，不篡改为恢复成功；该次没有进入写入阶段。全部固定输入保持不变，私有配置移除，游戏 64976／MCDK 39468 的精确创建身份独立核对为空，总耗时 105.831 秒，宿主清理错误为空。

[v2 原件索引](evidence/scaffold-lifecycle-r13-v2/index.json) 包含 21 个文件、1,987,186 字节和一张加载期原图。索引明确标记 `world_qualified=false`、`native_cases_observed=0`，不将它计入实际世界、17 状态或任何渲染通过。源指纹和旧失败均不覆盖。

v3 已准备但尚未执行。`scaffold_diagnostic_world.py` 建立独立诊断客户端，真实监听 `UiInitFinished`，随后累计至少两次实际 `GameRenderTickEvent`；两种监听均在 Destroy 配对注销。宿主还要求相同玩家、版本和维度、三次同步稳定且位于正常高度范围内的客户端／服务端脚坐标、服务端非空气地面正控，以及真实原生状态确认的 17 格干燥保留区。通过这些检查后才取得实际世界图、运行仍为 `e2f1e561...` 的旧 17 例工具。

新增四项宿主测试拒绝加载高度哨兵、UiInit 未发生、渲染 tick 不足、未加载地面、两端坐标／身份／版本不符、含液体或缺失真实状态，并验证监听配对、原 registry 字节副本和 Python 2 编译。全部 50 项脚手架定点测试通过。对生成诊断包执行定点 imports，命中六个模块；MOD review 实际解析客户端一文件、无发现。宿主测试仍不代替 native UiInit 或世界像素。

准备的监督器 [固定源](evidence/scaffold-world-admission-r13-v3-prepared/host.py) 的 SHA-256 为 `22178717963b518d019a37ef50c349814cb9262bb533fa3b5a4d3e208cb3aeca`，标记 [prepared_not_executed](evidence/scaffold-world-admission-r13-v3-prepared/prepared.json)。它保留 330 秒绝对预算、70 秒清理余量、原生写入期间 0.5 秒被动后台／身份检查以及异常 SDK 恢复和精确停止。新的防焦点 DLL 从根仓库已提交归档读取，续接不依赖已退休的另一工作树。此准备记录不是原生结果，实际执行必须另存新计划、回执和图像。
