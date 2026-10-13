# 传送门实机审计记录（R15）

本目录记录 2026-10-14 对 NEMC 3.10 `portal`、`end_portal`、`end_gateway` 和 `end_portal_frame` 的一次受管实例启动尝试，以及该尝试未取得像素证据的原因。

## 结论

本次没有任何可接受的运行时像素验收结果。不能据此宣布四个方块在编辑器、完整投影或缺失方块投影中通过，也不能据此宣布 Combine 的实际跳过行为已被实机确认。实例在启动期间进入了前台，且 MCDK 的客户端执行通道持续返回“玩家不在游戏或目标不可用”；实例随后由同一 owner 回收。

静态资源只用于确定后续测试的候选路径：`portal` 有原版 flipbook 与 `portal.material`；`end_portal` 和 `end_gateway` 有独立 texture set 和末地材质 shader 资源；`end_portal_frame` 是带 `end_portal_eye_bit` 状态的普通框架方块。资源存在不能替代像素验收。

## 启动与回收

| 字段 | 值 |
| --- | --- |
| engine | `3.10.0.420447` |
| Minecraft | `1.21.130.0` |
| attempted owner | `portal-runtime-audit-r15` |
| attempted session | `dd637e34605847f5a4c9589a551ae7d6` |
| project | `D:/bbe-r14-nemc310/.runtime/nemc-clean-310` |
| MCP port | `53543` |
| result | `failed` then `stopped --force` by the same owner |
| game process observed | PID `41336` during failed attempt |
| readiness | `startup_endpoint_discovered=true`, client execution unavailable |
| foreground | startup ended with the game window foreground; this was not accepted as a visual result |
| screenshots | none; no PNG or capture receipt is claimed |
| production changes | none |

启动器日志中的重复错误是：`Code execution failed. The player may not be in the game or the target is unavailable.` 回收后该实例的游戏进程不再运行。下次必须显式提供已批准的 noactivation DLL、MCDK SHA256 及窗口合同，不能复用本次启动命令。

## 离线资源核对

以下文件来自本机 NEMC 3.10 安装目录，SHA256 作为版本化来源记录。它们只证明资源和状态定义存在，不证明 Combine、材质深度、切面占用恢复或动画帧在项目路径中工作。

| 方块 | 资源／状态来源 | SHA256 |
| --- | --- | --- |
| `portal` | `data/resource_packs/vanilla/blocks.json` | `cb3aad2d0d012bfb63a462ec9a5d8af54128c8afc26d74ac6f4ae074c9d50faa` |
| `portal` | `textures/flipbook_textures.json`（`portal` entry） | `54fef45e43eabb065a703f829d70320430c746744289775e57af582cb240fd7a` |
| `portal` | `textures/blocks/portal.png` | `eb13fff62c7cae77f178e87be57656ed53bb796c9d81dfd2f83f26f47f632be5` |
| `portal` | `materials/portal.material` | 未复制；安装源待下一次实机收集 |
| `end_portal` | `textures/blocks/end_portal.png` | `11add57000c9d5dc8ba3980155abd115d419c28355eb5d8afa4f92f39e055729` |
| `end_gateway` | `textures/blocks/end_gateway.png` | `5e033bbe390138059e3e9b46863b08c3ae93c0ca48c1978bef87bbadf835e3be` |
| `end_portal_frame` | `textures/blocks/endframe_top.png` | `97e5083d492a71aabb1af44f01beefbb2b05892be5dbd41e379d07dda7359ac19` |
| `end_portal_frame` | `textures/blocks/endframe_eye.png` | `c47605275fa93cf4c3c29691b1263d7c8d08e3e882846de55f94250a36dce1fb` |

仓库方块注册表中，`portal` 的状态映射是 `portal_axis=unknown|x|z`；`end_portal` 与 `end_gateway` 各只有空状态；`end_portal_frame` 的状态映射包含四个基数方向和 `end_portal_eye_bit=0|1`。这些映射可用于下一次测试矩阵，不可替代实机状态读回。

## 待补实机矩阵

- `portal`：`portal_axis=x` 与 `z`，连续帧，两侧透明深度，切面后占用恢复。
- `end_portal`：顶面与底面，材质是否被 `CombineBlockPaletteToGeometry` 跳过，透明合成和切面恢复。
- `end_gateway`：顶面与侧面，材质／光束是否有快照可依据，Combine 跳过与切面恢复；不测试传送行为或粒子。
- `end_portal_frame`：四方向、无眼／有眼，静态框架与眼睛面是否在同一调色板中正确显示。

下一次取得空闲受管 3.10 实例后，必须分别保存结构化 `Combine` 返回值、固定视角的后台截图及截图可靠性报告；若后台捕获不能取得可靠画面，应明确报告而不能把结构化成功当作像素通过。
