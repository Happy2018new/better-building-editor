# R29 两库接入：最终 dcf 源的私有 CPU 验证

绑定 `dcf34132ce8e33284066efe66b9693ff89dc675a` 和 CPU-v8 的 6333 项输入。原 93 条加客户端／库 16 条、服务端 6 条，合计 **115 条通过，0 error/fail/skip**。全部 219 个实际产品／测试导入来自新的 732 文件私有工程；固定的 7 caller、2 adapter、20 vendor 与 3 工具保留原字节。

实际 vendor transform 1104 次、transform_states 1124 次；layout 函数调用为 0，只核对了其私有导入与对象身份。旧 66,249 次布局对等没有重跑。63-source owner checker 仍拒绝旧合同，book／portal 的当前来源读取成功、旧 snapshot 被拒绝，metadata 没有刷新。全部原／新工程、主仓输入及两库保护 SHA 匹配。

[index.json](index.json)将原15份材料及原archive-index共16个逻辑文件映射到16个按内容去重的确定性gzip对象，原文共1526353字节，存储共409106字节。每项保存raw SHA、长度及storage SHA、长度，已逐项重压确定性检查、解压回读并核对原字节；原件保持不变。未复制732文件工程或旧8MB工程。解压对应objects文件后，按references.path恢复原名并核raw SHA。

范围与下一轮缺口见[生产切换前检查](../../verification/LIBRARY_CUTOVER_R29.md)。当前已执行CPU范围无接入阻塞；原7021唯一全量的33 ERROR与后续54项补输入定点分别保留，115条不能拼成最终候选全量全绿。生产依赖未切换，没有MC／GPU／新源或人工资格。局部凭据扫描结果见[credential-scan.json](credential-scan.json)。
