# R29：特殊物品来源的有限候选普查

本包保存既有只读调查的 23 份顶层原件，包括 delivery-index、final-review、生成／check／单测试回执、资源读取 provenance、版本调查和前后守卫。此次只封装字节，不重新生成 census、不重跑测试或 check、不读取引擎资源本体或 exe，也不复制 fixture-root、运行工程或 326MB 私有工程。默认 tools/data census 仍缺失，原全量／skip 记录保持原结论。

这份候选范围是 **40 个 ID**，受现有来源分类器与 catalog 限定，不能当作全部特殊物品的穷举或生产支持。9 类计数为：弩 1、空地图 1、填充地图 1、挽具 16、不确定手持模型 3、旗帜物品 1、图案盾牌 1、头颅方块物品 8、特殊武器模型 8。catalog 的 1907 个已加载 ID 中，427 个 ID／6098 个 aux 组合是平面候选，仍非生产资格；1532 个有拒绝记录的 ID 中有 52 个同时存在平面候选组合，不能把至少一个被拒探针扩张成整个 ID 不支持。

原工具只查 vanilla／vanilla_base／vanilla_netease **3 个包**。私有进程将包范围临时扩展到安装目录中全部 **21 个包**后恢复模块常量；原始输出没有替换。实际读取 provenance 为 **462 文件／2,984,554B** 和 **467 文件／2,995,984B**。这两个数是本调查实读资源引用数，既不是 40 个 ID 的数量，也不是全部安装资源的总数；较宽 report 中 121 条关联资产记录另有自身口径。

较宽定义扫描多出 chemistry 的 3 份 JSON（4,015B），对这 40 个 ID 没有找到新的几何或纹理。按两边已序列化 JSON 对比，39 个 ID 行完全一致，只有 shield 的 additional_source_assets 真正新增 chemistry/materials/entity.material 和 vanilla_login/materials/entity.material 两条引用；未找到新的图案材质定义。多包同相对材质路径存在不同 SHA，没有推断引擎实际包优先级。早期 pack-scope-comparison.json 的 9 个表面变化来自内存 tuple 与 JSON list 的类型差异，pack-scope-comparison-v2.json 明确纠正并保留旧报告，不把假差异当新增适配工作。

安装路径名为 3.10.0.420447；21 份 pack manifest、exe 版本记录及 SHA 只作为来源材料。Minecraft.Windows.exe 的 FileVersion／ProductVersion 为 1.21.130.0，其与网易发行版 3.10.0.420447 的映射 **未独立证实**。目录名与 manifest 不能提升为该映射的独立证明，也没有据此判定安装错误。

既有工具曾用明确私有输出成功生成完整 JSON，随后原 CLI --check exit0。既有真实 InstalledSourceTests.test_checked_in_census_preserves_known_overlap_and_scope 仅执行 **1 条、通过 1 条**：测试模块 ROOT 在内存中指向完整未修改的私有 fixture，原测试源码没有改。私有 fixture 与顶层生成 JSON 的 SHA 相同；本封装只归档顶层等价字节，在 index 的 declared_fixture_aliases 引用原 delivery 绑定，不读取或复制 fixture-root 树。这证明工具和该条断言在这些私有输入下可工作，不能替代默认路径的缺失、将旧全量 census skip 改成通过或推定整个 suite／精确版本来源／原生渲染都已合格。未发现默认文件过去已生成的跟踪记录，也没有编造其历史缺失原因。

旗帜在 3 包与 21 包下均未找到 attachable 来源；**不能由无 attachable 推断旗帜不能接入**，也没有把立地旗帜方块姿态直接当作旗帜物品／展示框姿态。盾牌有 1 个 attachable、atlas.shield 动态图集引用和 44 个图案 PNG 来源；这些存在性证据不证明编辑器可直接使用。盾牌图案着色合成、动态 atlas 绑定、真实 item userdata、物品展示框模型与 pose、编辑器／世界渲染、包优先级及新原生资格都仍待验证。没有因找到资源就宣告旗帜或图案盾牌支持完成，production_qualified=false，人工关闭 0。

[index.json](index.json) 将 23 个逻辑原件按 raw SHA 去重为 22 个确定性 gzip 对象，逻辑原文 1,547,077B、去重原文 1,543,439B、存储 124,116B，最大对象 26,704B。filename 为空、mtime=0、level=9；每条 reference 记录原名／raw SHA／长度，objects 记录 storage SHA／长度。解压后按 references.path 恢复原名并核 raw SHA。delivery-index 中未复制的 fixture 别名独立列出，不冒充本封装重新读取了 fixture 或引擎资源。

[verification.json](verification.json)由独立新进程逐项核 raw／storage SHA、长度、确定性重压、解压回读、原件不变与相对链接；局部凭据扫描覆盖原文、JSON 解码字符串与本目录元数据，未扫描整个历史 runtime 或其他会话。pack.py／verify.py 只封装与检查材料，不导入产品、不运行已有测试。完整私有组合全量及历史补验的边界见[独立证据](../library-full-current-r29-v1/README.md)；本包不会改写它们。
