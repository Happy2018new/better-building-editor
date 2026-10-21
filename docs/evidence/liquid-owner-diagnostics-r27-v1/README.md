# R27 水 owner 合同的只读差异诊断

核对基线：`8150eab2eabc2a25bd8d1fc22d3aed70ff20edee`。

新增 `tools/check_liquid_product_owner_contract.py --check`，复用原生成器的 `generated()` 计算结果，输出逐文件 `added`、`removed`、`changed` 及预期／实际 SHA，并分别报告生成器和生成物的差异。新增、移除侧不存在的 SHA 用 JSON `null` 表示。比较继续只做 CRLF 到 LF 的原有规范化。

版本检查改用该只读入口。原生成器、`SOURCES`、合同 JSON、运行时 owner 常量及旧资格文件均未改动；生成函数调用前后的两份生成字节完全一致，没有运行写合同模式。真实旧合同下，旧入口与新入口均以 `1` 退出，仍保留相同四处来源漂移：

- `bridge.py`：SDK 配置字节解码，以及完整源海带 part 的输入。
- `geometry_palette.py`：两层海带代理准备；提取 helper 的函数体 AST 和水 suppression 语句保持一致。
- `render_context.py`：完整源海带 part／缓存，以及门和箱子副本的目标归属。
- `tiles.py`：海带 part 参与缓存失效。

这些是行为整合变化，不能通过更新 hash 搬用旧资格。22 个 `liquid_` 前缀实现文件保持一致，也不能据此推导混合场景的画面资格。

合同仍是显式文件表，并非传递依赖闭包。`native_layers.py`、`cell.py`、`transfer.py`、`kelp_render.py` 等 helper 不在当前列表；仅改未绑定 helper，诊断入口仍会通过，因此每份结果都明确说明该限制。这个工具没有授予运行时或 GPU 资格。

定点验证共通过 24 个测试：8 个诊断测试覆盖真实旧合同、临时源树、三类差异与 SHA、缺失文件、无效 JSON、生成器自身指纹、未绑定 helper、CLI 的 `0/1` 退出码和字节保留；另有 16 个版本检查测试。首次临时目录检查暴露的 Windows 8.3 别名差异已通过路径 resolve 修复，对应反例随后通过。

MCP 的 Mod Python 工具未识别宿主 `tools/tests` 范围，返回 `files=0`，未计为审查通过；本改动已做宿主源码／导入检查，并等待父代理独立审查。未启动游戏，人工关闭数和新增 GPU 资格均为 0。

`check-current.json` 保存真实失败诊断；`summary.json` 绑定四个改动工具／测试文件的 SHA、受保护文件的前后 SHA 和验证结果。原始旧入口 stderr 及静态四文件 diff 保留在本轮私有运行目录。
