# 两库候选：补齐历史输入后的原失败定点回归

原7021私有候选中，按冻结清单物理补入369文件／51,260,211字节，只重跑原28个未解决失败selector展开的54个顶层方法，**54／54通过，0错误／失败／跳过**。原fixture必需的21项anchor子进程测试也通过。测试113.134秒，驱动114.233秒。没有第二遍全量，也没有重跑额外9项归档skip。

原唯一全量3547项／33ERROR／10skip及失败分类均保持原SHA，不能把本次定点写成“重新全量全绿”。6608项既有候选／fixture输入、369项补入来源和测试后输入均逐SHA相同；runtime、tools和fixture没有为了通过而修改。原book fixture补齐和extras30项的既有身份保留，首次prepared-inputs不是最终fixture基线，原件有明确记录。

11个实际callee从私有工程导入且与原固定vendor候选相同，state/layout函数对象仍来自vendor。旧三metadata字节不变，63来源checker仍按原原因返回1。Windows长路径准备故障、140项部分复制及标准扩展路径修正记录均保留，没有junction／subst或源码补丁。

`index.json`映射23份原件至19个gzip对象，保存原始／压缩SHA。输入依赖方案另见[原始计划](../library-integration-input-plan-r29-v1/README.md)，原失败见[唯一全量](../library-integration-r29-v1/README.md)。本包不包含约49MiB补入原件全集或262MiB工程；索引不替代缺失源文件。候选固定7021，不包括主仓后续cdd修复，无MC／RPC／GPU／新资格。
