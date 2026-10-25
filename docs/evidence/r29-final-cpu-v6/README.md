# R29 生命周期补修后的完整 CPU 回归

产品来源为 `af9c628c40b688a2ffa9091f1e6b5abc9e6aa70f`。实际工作区完整回归为 **3,591 项、跳过 1 项、OK、exit 0**；unittest 本体 517.341 秒，宿主总耗时 532.208170 秒。

测试前后各自重新枚举 behavior_pack、resource_pack、tests、tools，得到相同的 6,331 项输入、259,526,838 字节，`changed_selected_inputs=[]`。范围包含历史 untracked 测试和工具，不能称为 clean HEAD 专属回归。日志中的故意异常和拒绝由相应控制用例断言；最终 unittest 结果为通过。

本轮实际变更的 13 个产品模块由 CPython 2.7.13 和 3.13.13 编译通过，未执行游戏 import、未生成 pyc；两个编译报告的源码 SHA 与同次回归输入逐项匹配。没有无故重复运行同源全量。

[index.json](index.json) 记录 8 份原件和 7 个去重 gzip 对象。对象解压后的 SHA、字节数及存储 SHA 已独立复核；before 和 after 相同而共用对象。包约 288KB，原始日志和完整清单仍可恢复。

这是 CPU、源码稳定性和语法兼容证据，没有运行 MC、ModSDK 网络或原生像素检查，不新增人工关闭，也不转授当前水、书或末地的实机资格。
