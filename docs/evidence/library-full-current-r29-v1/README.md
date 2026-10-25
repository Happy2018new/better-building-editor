# R29：当前两库完整组合的全量与档案定点补验

当前dcf34132下的完整私有两库组合已经完成一次全量CPU：**3613 tests／skip10／OK**，unittest454.072秒，总473.296630秒。6989项输入、326,464,656B前后逐SHA相同；完成时实际404个产品模块均来自私有`.runtime/lib-full-dcf-v1/p`，其路径／SHA已再次独立核验。此包只保存日志、清单、provenance和driver，不复制该326MB工程。

随后只执行一次10条定点：原全量中因档案未复制到p而声明跳过的9条历史回放，加原census基线1条。子进程env `BBE_LIQUID_REPLAY_EVIDENCE_ROOT` 只指向主仓docs/evidence提供字节，不改系统环境、测试、工具或p源码。结果**9通过／skip1／失败0／错误0**，unittest29.505秒，总36.778753秒。完整原全量仍记skip10；不能把两次相加称3623个独立测试，不能改写为一次全量skip1。

唯一剩余skip的实际ID为`test_special_item_capabilities.InstalledSourceTests.test_checked_in_census_preserves_known_overlap_and_scope`，原因`Generated exact-version source census has not been created`；p中对应精确版本census缺失。没有生成输入求绿。

9条回放中2条正常历史回放保留原结论：V2为FAIL，V4b为OBSERVED；两者production_qualified仍false，各46个实际导入历史源码的相对路径／SHA已独立匹配到主仓档案的精确字节，共92项绑定。其余7条预期拒绝分别核对捕获篡改、源换行篡改、缺失模块拒绝checkout回退、几何计划即使重索引仍不能替换原绑定。worker的7次exit1是这些通过测试所要求的拒绝，完整stderr保留，不当作测试失败或隐藏错误。

每个worker使用原loader的`-I`独立子进程，清除PYTHONPATH，执行源码只从校验后的档案闭包临时物化。原回执提供实际导入的项目相对路径和SHA；原loader没有另行输出绝对临时物化根，不能声称本包额外采集了该绝对路径。测试模块与loader的实际绝对路径、worker命令、setup复制来源、完整回执及逐档案匹配见trace／child-result／review-provenance。主仓证据目录没有加入导入路径。

guard前后确认私有p6989文件326,464,656B、原full目录及顶层9记录、主仓4档案379文件34,590,927B、另4个相关主仓测试／工具输入全部不变。测试原有TemporaryDirectory会为篡改控制创建临时档案副本并清理，没有向p或持久包复制大型档案。四个原索引精确字节保存在包内；捕获PNG和源码档案正文仍在原主仓证据路径，通过索引／SHA引用。

本包30逻辑引用、28个确定性gzip对象，逻辑原文8,595,916B、去重原文6,189,460B、gzip共1,188,455B；index／README／verification另计。对象名为raw SHA，index列出raw与storage SHA／长度，filename为空、mtime=0、level=9。新进程verification逐项解压回读、重复压缩并核原输入未变，局部凭据扫描覆盖原文、JSON解码字符串及元数据。没有扫描或归档全部历史runtime。

这属于私有库组合CPU回归和**历史原图／历史判定回放**，不是当前实现的新MC、GPU、默认路径、真原生显示、资格或人工验收；人工关闭0。没有主仓产品改动、metadata刷新、MC／RPC或全量重跑。复跑driver保留原仓库布局及私有p／原档案路径依赖，必须选择新输出目录，不能覆盖旧原件。
