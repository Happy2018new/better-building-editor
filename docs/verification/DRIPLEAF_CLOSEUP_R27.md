# R27：大型垂滴叶编辑器四近景补证

此前 OB07 的 zoom2 图仅为全场概览，不足以检查叶片与孤立茎。本次沿用同一冻结产品 source、公开 OB07 测试卡及完整恢复流程，仅增加四个固定编辑器近景：叶头 `(3,2,3)` 与孤立茎 `(3,2,23)`，各取 yaw35／215，pitch25、zoom12。使用正常 focus 请求与 `Session.camera_view`；没有原生 Doll 坐标写入、深度平面改动、shader 改动、候选 profile 赋值或生产代码修改。

公开卡实际载入与实际确认回调后，四阶段保持同一 Document／editor identity，完整 typed Document 语义不变，`camera_depth` 与 `camera_depth_pose` 均保持 0。每阶段保留实际 Session pose／pivot／pan／depth、实际 native Scene 尺寸、完整 Document 导出、strict raw／certificate 与原 PNG。共 15 raw＋15 strict certificate；这些证书只证明所记录的数据与 owner／前台关系，不自动证明像素正确。

root 已实际打开四张原 PNG，并报告：yaw35／215 下叶头与孤立茎均可见，近景足够观察局部纹理与茎轮廓。该观察只覆盖上述两目标四视角，不扩展为全部 44 组、链长、全部倾斜组合、投影或整个 OB07 的外观通过。本次人工关闭仍为 **0**。

四张原图位于 `.runtime/round-20261022/ordinary-closeup-lifecycle-v1/check/`：`ob07_head_yaw35_zoom12.png`、`ob07_head_yaw215_zoom12.png`、`ob07_stem_yaw35_zoom12.png`、`ob07_stem_yaw215_zoom12.png`。其原始字节与 SHA 均保存在安全小包内。两张公开卡／编辑器基线 PNG 仍留原路径并记录 SHA，不使用基线概览代替近景。

产品 source commit 为 `2ab5a29a21f68bac607637b10d4afb42ac9caaa6`，owner 为 `r27-ordinary-closeup-v1`，source manifest SHA 为 `22d1056904273afe2942676b420614dfbb54e2dc55250f898f9ef9ddf5fe135e`。近景入口 SHA 为 `ab335d4622c292a94d37c09f611672556c73f5c27e8f26e52d55155d9b9cb32d`；原公共卡 base driver 未修改，其 SHA 为 `c7396a51cac5bd0da37380a1638a73e434521e8be3599272af0fa0fd120c8c8d`。

运行报告 `completed/restored/source_unchanged=True`。两次内部恢复审计通过，独立 `face-restore-after1.json` 的 `changed_keys=[]`。ordinary stop 后同句柄观察到 game exit `3221226505 / 0xC0000409`、MCDK exit 0；因此 `normal_shutdown_qualified=False`，不能描述为正常退出。没有强杀游戏。独立身份复核两者 `same_identity_live=False`，watcher 核对自身 identity 后回收，资源已释放。

独立安全包为 `docs/evidence/ordinary-closeup-r27-v1-small/`，index SHA `3d8ca522394f3a571b98e211b6f190e085b6e55609176797de6fc423d2815a35`。包内 100 logical records／16 files／3,193,027 B，最大单件 240,000 B；四近景 PNG 保留无损原字节。原件 SHA、脱敏派生件内容 SHA、归档容器及分片 SHA 分别记录。独立验证重建 100 条记录与 96 个归档成员通过；实际凭据、嵌套 JSON 字符串和普通文本中的 JSON 转义变体均检查，两个嵌套／opaque 凭据反例均被拒绝。原始 session／stop 等文件仍留本地，发布包递归脱敏；大型 UI tree 仅保留本地并索引路径／SHA／大小。没有改写上一轮安全包或历史失败原件。
