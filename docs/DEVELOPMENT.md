# 现代化投影开发记录

## 阶段 1：编辑内核与开发环境

- Pyreact-MC 保持项目已有实现，业务代码位于 `behavior_pack/HelloScript/projection`。
- 文档体积上限 32768 格、单轴 64 格，所有草稿编辑限定在文档长方体内。
- 64 个工具集中定义在 `catalog.py`，由 `Editor.run` 执行；界面、搜索和测试共用目录。
- 原子提交、最多 50 步 / 262144 个变更格的历史；失败的越界操作不会部分生效。
- 单元验证：`python -m unittest discover -s tests -v`，13 项通过。
- 方向性方块的旋转/镜像暂时明确拒绝，避免在未实现状态转换时损坏楼梯、门等朝向。

## 本地资料库

已下载 `https://github.com/GitHub-Zero123/mcdk-assistant`：

- 源码资料：`.tools/mcdk-assistant`，commit `481f461d589847b9dceed762a9d8557bcd278e81`。
- Windows LITE 二进制：`.tools/mcdk-runtime`，release `v0.2.6`。
- 项目 MCP 配置：`.codex/config.toml`。配置方法参考 <https://developers.openai.com/codex/mcp/>。
- 当前任务可直接使用 `python tools/mcdk.py list` 和 `python tools/mcdk.py minecraft_docs '{"command":"api CombineBlockPaletteToGeometry"}'`。
- `.tools` 为开发机器缓存，不随模组打包。

## 开发依赖

Python 3、Pillow、requests、psutil、pyperclip；游戏内代码兼容 ModSDK Python 2.7。
当前机器 `python3` 是 Windows Store 空别名，调试命令使用 PATH 中实际可用的 `python`。
所有命令均通过 PATH 查找解释器，不硬编码解释器安装路径。

字体方案参考用户指定的 AddOn 示例：OFL Noto Sans SC 高清离线栅格化，静态短句贴图复用，动态文本按字形拼接，未知字形回退原生平滑字体。
