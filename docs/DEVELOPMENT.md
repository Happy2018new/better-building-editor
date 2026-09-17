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


## 阶段 2：工作台与游戏桥接

- 新增 app-local Pyreact 工作台、高清文字资源、圆角控件、弹性反馈、逐层编辑、建筑库、透明投影和实际世界操作。
- `bridge.py` 隔离客户端 API；`world.py` 提供可测试的分批预检查、写入、回滚和撤销事务；服务端以 `__id__` 识别事件发送者。
- 调色板布局通过实际 SDK 的 `GetLocalPosListOfBlocks` 验证：`volume=(Z,X,Y)`，索引 `Y*sizeX*sizeZ + X*sizeZ + Z`。非对称 volume `(2,3,4)` 中 1→(0,0,1)、4→(2,0,0)、6→(0,1,0)。
- 游戏内字符串 API 按 UTF-8 边界处理；原生 Input 返回字节串必须先解码再截取名称。
- Session 每次 emit 增加 ui_revision，并显式传入依赖会话的组件，避免框架 props 复用导致内容不刷新。
- 三维控件在工作台内部持续保留；确认弹窗使用固定根上的 Modal。逐层画布分页控制在 144 个交互格子。
- UI 资源生成：`python tools/generate_assets.py --font .tools/fonts/NotoSansSC.ttf`；OFL 许可保留在资源目录。
- 单元测试：`python -m unittest discover -s tests -v`。
- 真实游戏回归：`python -X utf8 tools/verify_ui.py`（16 项交互检查）、`python -X utf8 tools/verify_world.py`（27 格可逆世界写入）、`python -X utf8 tools/verify_layout.py`（20:9 / 4:3 / 16:10 / 16:9）。
- 运行快照、日志、截图与 JSON 检查结果保存在 `.runtime/`，该目录不提交。

## 阶段 3：真实游戏回归与渲染修正

- 2026-09-17，网易 Windows 开发引擎 1.21.120：26 项单元测试、16 项 UI 交互、3 项真实按键/选区检查全部通过。
- `tools/verify_entry.py` 使用指定 Minecraft 窗口的 Win32 消息触发 P、F6、F7；确认重开工作台、标记第二角点并读取选区。它不向其他程序发送键盘输入。
- `tools/verify_world.py` 在预先确认的空中空气区域写入 27 格，再撤销并重新检查全部为空气；4 项断言通过。
- `tools/verify_layout.py` 的 20:9、4:3、16:10、16:9 共 16 项比例与列边界断言通过。
- 对 1307 格庭院模型逐材质核对原生调色板坐标，全部等于文档坐标。PaperDoll 的初始观察轴与世界实体不同；工作台将俯仰映射到 `-90-pitch`、水平转向映射到 `initRotZ`，修复了模型横置和从地板下方观察的问题。
- 新建客户端实体须延后到后续帧再挂方块几何体；同帧调用会返回 True 却不渲染。正式流程延后 0.2 秒挂载，生成完成后才替换旧投影；关闭、维度切换和重复更新会取消尚未挂载的实体。4 项生命周期单元测试覆盖这条链路。
- 在真实世界观察了 3×5×2 的半透明模型；投影不放置真实方块。最新工作台及投影截图位于 `.runtime/modern_projection_workspace_final.png`、`.runtime/projection_final_visible.png`。
- 后台 PrintWindow 在这台机器上有时输出全白，但交互树仍正常；最终视觉检查使用确认游戏为前台窗口后的客户区截图。仅输出截图路径不算视觉通过。
- MCDK review：业务目录 10 个 Python 文件全部可解析；仍有参数数量、函数长度及 `sys` 导入的静态提示。`sys` 仅用于 Python 2/3 字符串边界判断，已在实际引擎中验证。
- 本轮临时 SDK 探针与热重载入口已删除。字体贴图和全部资源 JSON 已验证可读。
