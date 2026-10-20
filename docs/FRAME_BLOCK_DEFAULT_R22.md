# R22 普通完整立方体的默认资源候选

本轮将展示框里的三个普通完整立方体收窄成独立、可以按物品逐项验收的候选：
`minecraft:stone:0`、`minecraft:quartz_block:0`、`minecraft:grass_block:0`。
生成资源使用测得的 `0.25` 方块尺寸和 `[0, 0, 0.4375]` 中心偏移，
采用默认物品光照和 glint 片元，不包含旧实验的 `0.93` 亮度乘数。
当前没有打开生产资格，默认产品行为尚未改变。

## 产品范围与接线

`tools/generate_frame_block_default_r22.py` 从原生安装生成三项资源，使用独立名称：

- 模型及 shader：`modern_projection_measured_frame_block`。
- 资源目录：`modern_projection/frame_block_measured/`。
- 配置：`behavior_pack/modern_projection/projection/frame_block_measured_data.py`。
- 注册清单：`tools/data/frame_block_measured_item_registrations_r22.json`。
- 来源目录：`tools/data/frame_block_measured_item_catalog_r22.json`。

旧的完整立方体目录、模型、材质和 shader 均保留。共享模型表只追加六项模型，
共享材质表只追加 opaque 编辑器、世界材质两项。不能将旧资源名称下的像素结论
视为这些新名称已经通过原生加载或外观验收。

`frame_block_measured_profile.candidate_items()` 校验安装版本、palette、精确 aux、
资源 key、opaque 材质、完整立方体家族和展示框范围。
`production_items()` 额外要求被接受的姿态、匹配当前资源的证据摘要及非空精确物品名单。
普通内容和人工附魔的资格名单彼此独立：已接受的普通物品可以先进入产品，
`sprite_item()` 对尚未取得人工附魔资格的同一物品继续返回不支持。
没有据此扩大到阶梯、薄片、其他 aux、透明材质或非展示框容器。

当前资源契约为：

```text
148b2d0958433814ec2d8e2c29a77e8f0aab964a20b0a61f9bd866b81acdf03c
```

`PRODUCTION_QUALIFIED=False`、`POSE.accepted=False`、`QUALIFIED_ITEMS=()`、
`QUALIFIED_ENCHANTMENTS=()`。生成器目前始终输出这些关闭值；正式启用时需要
增加与实际验收证据绑定的可复现生成步骤，不能只修改生成文件中的开关。

## 已冻结的冷启动输入

本轮有效项目是 `.runtime/projects/frame-block-default-r22-v2`，
控制目录是 `.runtime/frame-block-default-r22-control-v2`，owner 为 `item-r22`。
v1 在来源快照阶段未完成，不可用于本轮采集。v2 项目、配置、矩阵及 plan 已冻结，
禁止原地补丁、热更新或覆盖输入。项目共 3,914 条来源，摘要为：

```text
7d3aaa6e5e347d76db6c9c7c1eca70dab4ef757fda57b1dc0015ec9b9ac4c4ca
```

`tools/prepare_frame_block_default_r22.py` 对照 Root 的全部快照来源，
校验已安装三物品资源与生成字节相等，关闭四项自动热重载，使用新世界，
并另外固定 native WGC 源文件和外部退出观察器依赖。
本说明和后写的离线 reviewer 不属于 v2 来源清单，分别固定指纹，
不能把新的 Root 文件集合宣称为 v2 当时的冻结快照。

## 最短实机验收路线

每个阶段需要 Root 单独安排 MC/WGC 窗口。没有自动重试或扩大矩阵。
先检查石头正面的原图，再决定是否继续两个其他普通内容，之后才运行预声明斜角。

| 阶段 | 普通物品及角度 | 用例数 | 协作停止采集边界 | 目标总耗时 |
| --- | --- | ---: | ---: | ---: |
| `stone_front` | stone 0° | 1 | 150 秒 | 180 秒 |
| `quartz_grass_front` | quartz、grass 0° | 2 | 230 秒 | 260 秒 |
| `stone_oblique` | stone −75° / +75° | 2 | 230 秒 | 260 秒 |
| `quartz_block_oblique` | quartz −75° / +75° | 2 | 230 秒 | 260 秒 |
| `grass_block_oblique` | grass −75° / +75° | 2 | 230 秒 | 260 秒 |

所有阶段固定晴天、时间 6000、关闭天气和昼夜变化，且分别重新采集相机校准。
边界在受控操作间检查，随后恢复环境；它们不是能打断任意底层等待的硬超时。
预计冷启动另需 90–180 秒，启动前至少留 9 GiB 可提交内存，运行中至少留 6 GiB。
全机有效游戏数启动前须小于 5，同 owner 不得存在活实例。
零句柄、零线程且没有存活身份的残留记录保留原始 census，但不占有效游戏数量。

可随时离线核对冻结状态：

```powershell
python -B -X utf8 tools/run_frame_block_default_r22.py check
```

仅取得 Root 当前运行窗口后执行：

```powershell
python -B -X utf8 tools/run_frame_block_default_r22.py start --scheduled-by-root
python -B -X utf8 tools/run_frame_block_default_r22.py capture --phase stone_front --scheduled-by-root
```

Root 实际检查首组原图并安排下一阶段后：

```powershell
python -B -X utf8 tools/run_frame_block_default_r22.py capture --phase quartz_grass_front --scheduled-by-root --first-image-reviewed-by-root
```

禁止激活、resize、桌面输入、force 或重复普通关闭。
本轮已冻结的断言 watcher 覆盖到 `2026-10-16T13:30:00+08:00`；
若实际运行窗口更晚，需要新的明确修订和来源核验。

## 原图核对与离线复算

在首轮采集之前，将 `tools/review_frame_block_default_r22.py`、
`tools/verify_frame_block_item_shaders.py` 当前指纹与已完成 GLES 编译报告另存到
control 的 `offline-analysis-v1.json`。它不改写冻结 plan，也不增加运行授权。
reviewer 使用冻结项目里的分析依赖。

```powershell
python -B -X utf8 tools/review_frame_block_default_r22.py --phase stone_front --output .runtime/frame-block-default-r22-stone-front-review-v1
```

每阶段校验来源、资源、矩阵、恢复结果和回执新鲜度；每个单用例阶段应有
20 张原始 PNG，双用例阶段应有 32 张。分析分别保留填充轮廓和未填充像素掩码，
计算 native/full/missing 对应面的原始 RGB、亮度比、纹理相关和 P95 差值。
没有图像平移、缩放配准、曝光或颜色拟合。必须实际打开原始编辑器和
native/full/missing 图，以及对照拼图；统计通过本身不等于产品外观接受。

此前默认石头片元存在约 1.0704–1.0776 的相对原生亮度比，成因尚未关闭。
旧 clone 使用 `0.93` 后的草方块亮度接近原生，但狭窄斜侧面仍有明显残差。
因此，本轮首先采集无乘数默认资源的石头原图，保留可能的负结果。
普通钻石剑 glint 的既有结论不适用于立方体或石英方块人工附魔。

## 离线验证与退出

已完成的针对性单元验证：新增四个 measured 测试、19 个完整方块测试、
12 个静态展示框测试及 16 个 sprite planner 测试，共 51 个通过。
此结果验证名单、资格边界和资源接线，不能代替游戏像素。

冻结 measured shader 已使用原生头文件在 GLES2/3 环境编译：
十个编译与链接组合通过；逐面 glint UV 每版本 96 个顶点；
48 姿态的 position、normal 每版本各 4,608 个样本通过。
GLES2 不支持原生头文件中的对应 skinning/instance 能力，相关组合只覆盖 GLES3。
报告为 control 中的 `gles-compile-v1.json`。

一次普通关闭后等待精确保留句柄的观察器，不能因为 stop 超时重复发送关闭或 force：

```powershell
python -B -X utf8 tools/run_frame_block_default_r22.py stop --scheduled-by-root
python -B -X utf8 tools/run_frame_block_default_r22.py finalize --scheduled-by-root
```

第二条仅在观察器确认游戏和 MCDK 实际退出、两份身份均消失后执行元数据收尾。
启动或关闭错误需保留原始失败和身份信息，不能重放启动入口。
Shared index、commit、全局调度、轮次截止时间及电脑休眠由 Root 统一处理。
