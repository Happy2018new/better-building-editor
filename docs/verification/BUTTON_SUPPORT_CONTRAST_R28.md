# R28 T02 支撑材质对照诊断：V2 失败与 V3 实际结果

root已独立核对归档原始来源、四模型typed输入、六阶段提交、恢复和精确退出，并逐张打开八张对照原图。该诊断关闭视觉问题0项，未修改产品渲染实现。证据见[归档索引](../evidence/button-support-contrast-r28-v3/root-index.json)。

V2 实际在 `freeze()` 调用 `guard()` 时触发 `KeyError: u'combined'`，原因是四模型方案已将键改为 `combined_stone`，guard 仍使用旧键。V2 完成 0/6 阶段、创建 0 个私有模型，没有白支撑结果。此前离线验证未运行真实 Diagnostic 实例的 freeze/guard/prepare 路径，这一验证缺口保留在失败记录中。V2 的局部／全局恢复、60 格 undo、两次独立审计及 release 均完成；游戏退出码是 `0xC0000409`，不能记录为正常退出。

V3 是新的独立 owner，只修正一个客户端模型键。它复用精确 `b70ce7bf13ad6a4472f2b089ac812c162b174861` 的 3,712 个 runtime 文件和 778 个冻结 helper；没有改生产源码、restore、六阶段／四模型方案、等待门控或五处 V7 状态读取。根代理独立检查后另行授予一次 MC 窗口，V3 在该新授权下完成全部六阶段，未重试 V2。

四个唯一私有模型的实际 Deserialize 输入与 Serialize 结果一致。石／白 combined 模型都包含 `stone_button aux0`，native index827，状态为未按下、facing0；对应 support-only 模型仅移除这个按钮及其状态。A/B 唯一输入变化是 index1083 的支撑从 `stone aux0` 改为 `white_concrete aux0`。native volume、其余状态与布尔值、pose、slot0、可见性、布局及 source tint setter 值保持一致。实际 RenderBlockGeometryModel 名称、返回值、门控状态与原图 SHA256 已逐阶段绑定；A2 复用 A 的原模型名称和参数。

沿用 V2 预先声明的原图 ROI `[577,242,714,452]`，结果如下：

| 对照 | 改变像素数 | 原图差异包围框 |
|---|---:|---|
| A 石支撑 combined − support-only | 263 | `[626,365,665,403]` |
| B 白支撑 combined − support-only | 760 | `[626,365,665,403]` |
| A2 石支撑 combined − support-only | 263 | `[626,365,665,403]` |
| A → A2 combined | 0 | 无 |
| A → A2 support-only | 0 | 无 |
| 原完整场景对象ROI → 原源恢复 | 0 | 无 |
| 原完整场景对象ROI → 私有 A combined | 0 | 无 |

白支撑 combined 的原图显示灰白支撑上的局部石纹矩形；support-only 原图没有该矩形。这里的石纹属于按钮输入增加后带来的局部净画面差异，不能写成整块支撑仍在显示石材。石支撑上的 matched 差异较弱，白支撑提供了更清楚的对照。A/B support-only 改变 9,122 像素，combined 改变 8,362 像素；三组按钮对照的 bbox 相同。以上支持“在这个固定视角，按钮确实产生了可重复的局部画面贡献”，无需用颜色倒推原生渲染路径。

证据边界：没有读取 native mesh 顶点、面材质 ID、UV 或 GPU tint uniform；模型输入和 Render 调用成功不等于 native GPU 几何回读。不能据此关闭按钮厚度、贴面位置、全朝向、旋转／镜像、所有材质或原生外观验收。未将石纹像素自动认定为原生 mesh／shader 的证明。

V3 实际局部恢复返回 errors空、callback 所有权正确，恢复了两个原生提交；原两格源重新核验并截图，随后 undo 恢复全部60格。全局 restore 的两份字段／相机／工厂／profile 审计通过，独立 after1 和 after2 的 `changed_keys` 均为空，source/host hash 不变。8 个 sequence 步骤全部返回 0，普通 stop、watch close 与独立 release 完成。game73044／identity134371808691939165 的 retained-handle 退出码为 `0xC0000409`，MCDK69964 退出0，watcher1732 退出0；registry stopped，三身份 current均为空，未 force。槽位已显式释放。

最小归档位于 `docs/evidence/button-support-contrast-r28-v3/`，包含不可变 V2 失败原件／脱敏结果、V3 十张原图、四模型六阶段实际记录、来源与恢复证书、实际 host资产、独立审核／授权、双审计与异常退出记录。原图不改写；JSON 对凭据字段脱敏并使用无损 xz 存储，原始 SHA256、脱敏内容 SHA256、存储 SHA256 分别列明，typed native wire 数据已验证保持不变。较大的 source manifest 使用连续字节分片，各片单独无损压缩，按 chunk_index 重组后解析，完整内容哈希一并保留；所有单文件小于240,000字节。

root使用独立PIL差分重算10组原图对象ROI，并分别解码实际Deserialize／Serialize数据。A/B支撑材料变更同时替换common中的材料key与对应的空states材料key，其余输入保持；不将空状态字典的材料重命名误记为按钮状态改变。首轮独审的V2索引schema／路径假设和漏换空states材料key已在root回执明确更正，未改原证据。对象ROI重复不代表整张截图包含实时调试文字的RGB相同。

原包104文件及嵌套V2的15份原始来源均已重hash；root复核全部字段仅发生已声明脱敏，typed wire保持原值。代理原索引和root补充索引分别保留。归档脚本保留原私有路径假设，不能从本目录直接作为产品入口运行。
