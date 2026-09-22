# 附加值角标调整

常用列表的一至两位数角标从 18×18 改为 13×13 设计像素，白色数字从 10 改为 8。图标向左下留位，与角标分开；三至五位数按位数扩展正方形，并为图标预留位置。方块目录移除所有角标，底部的附加值编辑器保留。

2026-09-22 从当前游戏已完成加载的完整 `session.block_catalogue` 读取，共 1,020 项，附加值非零的有 7 项（0.686%），其余 1,013 项为零：

| 名称 | 标识符 | 附加值 |
| --- | --- | ---: |
| 平滑石英块 | minecraft:quartz_block | 3 |
| 海晶石砖 | minecraft:prismarine | 2 |
| 石英柱 | minecraft:quartz_block | 2 |
| 青色染色玻璃 | minecraft:stained_glass | 9 |
| 黑色混凝土 | minecraft:concrete | 15 |
| 湿海绵 | minecraft:sponge | 1 |
| 云杉木板 | minecraft:planks | 1 |

此统计是当前目录去重后的实际展示项，并非所有方块支持的全部状态。现代标识符可用不同 ID 区分颜色/品种而附加值为零，目录合并同名新旧 ID 时也会优先保留常用列表中的形式。

验证：编译与 `git diff --check` 通过；游戏重新加载后的目录本页 36 个格子无 AuxBadge，正式 MaterialPicker 在临时卡片中的 18 个格子角标与图标均不重叠。读取并检查前台截图 `.runtime/stage57_catalogue.png`、`stage57_palette.png`。统计存于 `stage57_catalogue_aux.json`，布局记录存于 `stage57_badge_layout.json`。测试没有改变建筑或保存偏好，并检查草稿 JSON 一致。
