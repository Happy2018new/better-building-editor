# R28 最终源五张公共卡冷启动 v4 smoke

本包绑定 b70ce7bf13ad6a4472f2b089ac812c162b174861，独立精确 Git 冻结 3,712 runtime + 36 helpers，没有旧诊断 overlay，也没有修改生产渲染器。实际正常 Session 自然取得默认水、书 profile；没有 bootstrap、profile 赋值、GUI setter 或材质/相机校准。

真实公共入口完成单水格、四格水池、含水栅栏三卡各一次，以及附魔台/讲台两卡各加载与公开重载，共七对 load/confirm、九张主帧、23 次唯一 capture。主帧原图及元数据逐字节复制；历史图为零。完整 typed 文档（保留原 wire 并严格比较全部位置/声明表/来源字段的语义）、聚焦、真实 native ID/uniform/可见祖先和严格缓存来源关联见 summary/public-cards/cache-proofs。完整 source/halo/cache/首次 create 保留在原 report，以确定性摘要关联，包内不复制重复大数组。累计 tile_builds 按现场原值记录，不冒充增量。

这是 GUI2 单档公共路径 smoke，不重跑或重授水 FA 矩阵，不关闭 GUI4 偶发空白、GUI 全矩阵、逐像素或人工验收。人工关闭 0，runtime_pixels_qualified=false。双原稿恢复、精确 ordinary stop/独立释放和 watcher 退休另有原始回执；实际 0xC0000409 等退出码仍属异常，不能称正常引擎退出。
