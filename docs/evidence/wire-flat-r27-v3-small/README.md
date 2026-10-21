# R27 红石线私有候选审查包

候选尚未晋升，生产代码未写入，人工关闭项为 0。新增 `_DRY_WIRE` 常量与三个 helper 的差异见 candidate/three-helpers.diff。

新 flat：12 阶段、72 条实际原生记录全部导出并恢复。主控已检查六张原始 PNG；本包保存这六张原图的原始字节分片，24 张完整原图的哈希在 root-review/report.json。

boundary：首次整阶段读取 RPC20 超时，阶段导出和截图均为 0，恢复未完成；其余扩展未测。boundary 下界分析由真实 Python 2 和部署 IPC 原函数执行，最少 21 条记录仅文档字段即使 IPC 下界达到 48,340,592 字节。此为源推导下界，实际完整记录数和响应包均未捕获。

同一实例 ordinary stop 返回 0，实际游戏退出 0xC0000409、MCDK 退出 0。专属 watcher 在精确身份核对后单独回收，退出 1。游戏异常退出没有被这份 IPC 容量证据归因。旧 v2 未恢复失败独立保留在 historical-v2。

CPU 私有业务回归：1024 正例、1288 反例、2 混合 cache 文档；不证明 GPU，也不纳入生产测试。所有证据都保留原始哈希，summary 与 diff 明确是派生内容。本包没有对原始证据做脱敏改写；凭据递归扫描为零发现，session/config 与完整项目源不打包。

manifest.json 描述每个对象、原始来源与原始 SHA256、存储编码与分片 SHA256。先按 parts 顺序拼接；encoding 为 gzip 时解压，所得字节必须等于 content_sha256/original_sha256。PNG 分片直接拼接，无重编码。每个存储文件小于 300,000 字节。verify_bundle.py 可独立在内存中核验全部分片与重建对象。
