# 附魔台台身位置修复

2026-10-15，NEMC 3.10.0.420447。用户报告书本与台身、台身与支撑块相交；本报告只验收台身位置，书本有独立的 owner 与外观矩阵。

真实世界的附魔台与青色支撑块作为同机位参考。原生直接 palette 和序列化 roundtrip 两条路径均将台身下移约 0.125 格，屏幕上约 27 像素；内部 `preview_enchanting_body` 通过 `prepare_palette` 生成后恢复正确高度。其六面采用原生纹理，代理 ID 仅进入渲染 palette，不写入文档、分享数据、NBT、前景层或背景层。

| 观察方向 | prepared 与原生红色纹样原位 IoU | 最优位置偏移 | 支撑内部保留比例 |
| --- | ---: | --- | ---: |
| 南 | 0.96919 | 0, 0 | 1.0 |
| 北 | 0.96817 | 0, 0 | 1.0 |
| 东 | 0.97250 | 0, 0 | 1.0 |
| 西 | 0.95707 | 0, 0 | 1.0 |

精确值以 `body-analysis.json` 为准。旧直接／roundtrip 路径的支撑内部保留比例只有约 0.767–0.780，作为能发现相交问题的负控。分析不移动截图来获得通过；平移拟合只报告原错误的大小。`report.json` 保存完整回执、源文件指纹及恢复结果，`crops.json` 保存原图和裁切的 SHA256；这里的 PNG 为原图未缩放裁切。

生产边界：只替换当前版本无状态的 `minecraft:enchanting_table:0`，未知 aux 保留原生路径；生成数据绑定 dump 来源。`tests/test_static_table_render.py` 检查图层、NBT、missing 上下文和原始文档保持不变。编辑器／full／missing 的整书检查另见 `.runtime/book-owner-r18-v1`，不能由本报告单独授予书本生产资格。

复验入口：`tools/probe_native_palette_body_r16.py`（四向 body 对照）、`tools/analyze_enchanting_body_r17.py`（纹样／支撑）、`tools/pack_book_diagnostics_r17.py --mode body`（无增强裁切）。
