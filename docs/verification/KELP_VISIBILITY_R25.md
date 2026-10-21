# R25：海带双面可见性与源邻格部位

海带正式接入已保存为本地 `a76cd73a`，专门的公开蓝图随后保存为 `7c7c32f0`。原生海带在部分观察方向缺画；新的双面交叉代理直接使用安装版 `kelp_a`／`kelp_top` atlas。部位按完整原始Document的上邻格决定，修复同age柱、缺失投影和跨区块编辑中只按局部目标选择顶部的问题。**本页记录开发侧窄验证，用户人工关闭数仍为0。**

## 渲染与文档边界

原生方块身份、age、类型化NBT、保存、分享和真实放置数据保持原样；替换只发生在渲染副本。上方仍有源海带时本格为茎，否则为顶部。隐藏上层、只渲染下格、真实世界占据上格均不改变源部位。原生age不作为顶部判据。

`SurfacePalette`在内存携带完整源Document和逻辑原点，不写入palette数据。Bridge、增量ContextBuilder及tile mesh身份都纳入部位；上邻格变化后即使本格原生palette不变，也会重建相应模型。原有上下halo、脏区传播及公开geometry签名保持。旧同步参考API继续要求覆盖完整逻辑体积，不能向它传入局部目标冒充源。

两个隐藏代理、模型和blocks条目由 `tools/generate_kelp_proxies.py` 管理；profile固定安装版atlas、flipbook、两条TGA及模板来源。没有复制TGA、修改terrain／flipbook／shader，也不向公开方块表加入代理身份。此模型不声明等同原生tessellator网格或随机相位。

## 候选冷源的实机结果

该阶段使用基准 `3eeaadb5684d8470d5f438d7f3772384a6962752` 加正式候选，不是直接摆私有诊断alias。3708 runtime文件manifest为 `ccadb5e1f8ee0c517ec4876dedb378642286443471a248e6fe16320f9064df92`，候选patch为 `1cbcb88c657af42a7287160c634890075e738eed1ba7133ccb4a2a89ef21d1bc`，候选manifest为 `c35b59fb15ea2e0fd33a6bbb18864cf4ef424fed2d35dcfc948533fb331f0e01`。原冻结hash和失败记录不因后续集成改写。

| 检查 | 实际结果与边界 |
| --- | --- |
| 原生源提交 | 蓝图中只放原生kelp，实际渲染提交为正式stem／top代理，同age柱正确区分两部位，孤立age25为顶部 |
| 编辑器正反面 | 两个相反轨道视角均能看到整柱及孤立顶部，不再反向整面消失 |
| 完整／缺失投影 | 原生源柱、孤立顶部和stone对照均显示 |
| 真实占据 | 实际占据柱上格后仅下方茎保留；继续占据下格后整柱消隐，孤立顶部与stone保持；清空占据后整柱恢复，源部位不变 |
| 跨Y15／16 | 初始茎／顶正确；只删除上格一次，下格改为顶部；原生Editor撤销后恢复茎／顶 |
| 原始失败 | 删除阶段即时to_data含已删空的Y1 chunk，稳定预览自动移除它，原字节等值门失败保留；另立recovery不重放删除，逐格校验180格、非chunk元数据及唯一消失空chunk解码 `00 00` 后取图 |

主代理独立实际打开上述10张关键原PNG，结果与报告相符。此阶段只提供静态生产路径证据，没有将静态图写成动画速度验证。较早atlas可行性采样在编辑器／完整投影各8.6秒看到叶片形变、stone固定像素保持；195／103有效帧并不等于识别出原生全部20源帧，原生完整周期与随机相位仍未授资格。

两次独立恢复核验通过原Session、editor、Document完整data、profiles、factory、原世界格及0 actor／无任务。相机exact相等为False，roll残差 `-1.3660377589985728e-05°`，另记0.0001°内语义恢复。普通stop与registry finalize完成、无force；同handle游戏退出为 `0xC0000409`，MCDK为0，不能称正常引擎退出。

## 离线验证与集成

13项业务覆盖26个age、上邻格、非对称索引、非零原点、跨16、隐藏层、uniform缓存、前后台顺序、typed NBT和撤销／重做；5项资源测试覆盖权威生成物及13类profile篡改、TGA／atlas负控。root在主仓Python3运行18项、真Python2运行13项，generator `--check`均通过；最终箱修复叠加后69项context／door／kelp／chest相关回归、公开卡组合41项通过。六个生产模块的MCP定点review均实际扫描1文件，新kelp模块无发现，其余保留既有长函数／参数提示。

候选归档把4个受Git `-text`保护的CRLF模块转为LF；集成时仅恢复原CRLF字节风格，文本语义不变，另留newline receipt。随后箱归属仅以小diff叠加到render_context。旧候选hash保持；最终生产字节与公开入口必须以新冷源重新冻结检查，不能搬候选来源资格。

## 公开入口与仍待项目

“测试蓝图 → 方块表 → 海带 · 茎顶／孤立／跨区块”，ID为 `test.blocks.kelp_visibility`，尺寸16×18×8。按X从小到大为同age低柱、孤立age25顶部、跨Y15／16的同age柱，共5格原生海带与3格stone支撑。公开卡离线已验实际页面函数可达，旧卡顺序及R09／R10／R14文档保持。最终共同源码冷入口结果另附，不提前把离线可达当成实机点击。

周末重点看正反面均可见、茎顶纹理不互换、切换缺失投影后正确消隐恢复，以及删除／撤销上格后的部位。含水／含雪组合、精确原生网格和完整动画周期继续单独待验。原报告、失败与恢复／退出回执在本地 `.runtime/round-20261021/kelp-production-live-v1/`；[小型证据索引](../evidence/kelp-render-r25-v1/evidence-index.json)绑定原始文件，缩略图只作导航。

## 正式整合源码的公开冷入口续验

10-21恢复窗口另冻结 `7c7c32f05fbc6d4eb0e7e9895f060f1f39b8860c`，与箱归属修复共用3708个runtime文件，manifest为 `7872491a970fd54d3331f2bdaf89dd04f87224ec184d612123749e74e82a65fa`。实际测试页卡片和确认回调载入8格公开Document，未投递Windows鼠标。提交读回为3格stone、2格stem、3格top，活动region owner均严格ready、签名／cache／native提交匹配；仅确认无内容的备用PreviewTile不计入活动提交。

原宿主先将空备用tile的 `name=None` 误作活动提交而失败；第二次宿主取palette时遍历到tuple也失败，均原样保留。第三次完成语义与恢复，但两个编辑器近景为空，不能算视觉通过。原因定位到宿主直接写 `session.camera_pivot` 未同步已挂载的OrbitCamera；第四次通过实际 `camera_focus_request` 再缩放补拍，没有修改生产渲染代码。

主代理实际打开第四次的4张原PNG：编辑器低柱／孤立顶部、编辑器跨Y15／16柱、对应两张missing近景均可见，茎顶连续，stone对照在画内。默认卡片编辑器原图亦能看到三组。报告 `completed`、`restored`、`source_unchanged` 均为true，两次独立恢复相机exact相等。本续验未写世界、未赋候选profile，也没有重做旧源的真实占据及删除／撤销实验。

原失败、第三次空近景、第四次有效原图及恢复回执已绑定[共同冷源索引](../evidence/final-kelp-chest-r25-v1/index.json)。游戏普通stop后真实退出 `0xC0000409`、MCDK为0；registry finalize及watcher精确回收完成，无force，不称正常引擎退出。该公开入口可进入周末R15人工候选；用户人工关闭数、动画资格及其余植物家族状态不变。
