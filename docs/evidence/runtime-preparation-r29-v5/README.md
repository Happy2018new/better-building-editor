# R29 当前产品源的投影 v5／水 v4 静态准备

冻结产品源为 `af9c628c40b688a2ffa9091f1e6b5abc9e6aa70f`。这里只保存静态准备和授权原件；条件授权不等于启动或执行，以下结果不授实机或人工资格。

投影 v5 的独立物理副本含 3,716 项 runtime、119,017,299 字节及 785 项 host；4,502 文件无 hardlink。21 项离线控制、14 个 host AST、observer 完整性和 frozen_guard 通过。source manifest、host、observer SHA 分别为 `a2ca77a663b4c6bf596b4c2359cb20cce3000e7c2e1dbc5c2ad42ca8ce59fc96`、`a5bd2908bc65523ab66d6d4a8e83a348907be95912672e808ef0b01c942c9c7a`、`51ed1fcede8b9df6f5862a56c435e27d3e20cd6ca7f61246eda3b2a26d74b068`。v1—v4 的历史结果与未启动状态不覆盖。

水 v4 的 root 来源复核确认相对有效 v3 唯一生产差异为 server_system.py 的生命周期补修；42 项显式水实现合同不变。4,491 项源、1,391 项辅助、56 项 host／55 项外部依赖已核对；旧 v3 的 94 项文件逐 SHA 保留。原 119,618,244 字节 base ZIP 仅按 SHA 引用，增量 ZIP 为 146,044 字节。metadata 保持原件，没有刷新当前资格。

水 source inventory contract 为 `06e6a907149372f76959485b41c7eaf054fac930149285d499693fc3e8012855`；binding 为 `5b1c21449c3b7406432fcc9724a7fbe3d4f1f4ba33c7e1218033117bc4c4c8de`，host 为 `6b7c3edb83ec0da26f366541d09121a50af7f43b85ecaddd8fd02f997abe394c`。freeze 后独立 inspection 和 projection API audit 通过；通用恢复没有保存 projection_transform，因此只适用于 fresh identity 水会话，不能借用投影变换测试会话。

[index.json](index.json) 保存 100 份准备原件、84 个去重 gzip 对象，约 1.55MB，最大对象约 518KB。没有嵌入大型 base ZIP、世界或游戏。不能凭准备成功沿用旧源的水／书／末地资格。
