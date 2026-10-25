# R29：确认目标、首包维度与查询失败证据

本包逐项保留原 `archive-index.json` 的 37 件（400,660 B）和 V2 索引的 16 件（142,945 B），并保存两个原索引的精确字节；没有改写旧输入。另保存 dcf34132 下四个当前产品源、六个相关测试／fixture 源和本打包程序。当前源 raw SHA 与最终比较／main-hashes 相符，十个源码均与该提交内容 CRLF 归一后一致。工作区原始行尾保留。

`index.json` 的 references 以原路径定位，objects 以 raw SHA-256 去重。每个 `.gz` 的文件名是解压后 raw SHA；索引另列压缩字节 SHA、raw／stored 长度。gzip 文件名为空、mtime=0、level=9，独立再次压缩字节相同。原索引的历史 pending_main_change 字段原样保留，其状态不代表当前主源。

实测：66 份逻辑引用，61 个唯一对象，逻辑原文 865,253 B、去重原文 771,569 B、gzip 共 166,140 B。索引与说明另计；完整目录字节数见打包终端回执。`verification.json` 来自新进程解压回读，逐项核验 storage／raw SHA、所有引用和原 37+16 件仍未变化，并复扫选定输入、解压对象及本包文字／专项文档。

最终 focused 是 23 条（16 客户端／库 + 6 服务端 + 1 既有冻结确认），Py2.7.13／Py3.13.13 各 19 控制（14 正常 + 5 query 故障）。这次打包没有重新运行它们。完整结论与限制见 [WORLD_DIMENSION_R29.md](../../verification/WORLD_DIMENSION_R29.md)。

失败证据仍保留：客户端候选未防住首包换维度；pre-query-fix 的五处注入中四处 RuntimeError 逃逸；preliminary22 的五个重复测试不作为新增覆盖；Py2 驱动准备错误单独保留。旧 README 的定点叙述与 baseline-observations 实际 9 记录有差异，以原始 JSON 为准，不补造缺失记录。

没有 MC、RPC、GPU、窗口／键鼠、原生世界写入或人工验收。本包不给水或其他渲染授予资格，人工关闭 0；原权限和 F11 语义不变。
