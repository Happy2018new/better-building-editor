# 水 R29 v3：cdd源冻结准备，未启动MC

本包保存 `cdd0601537e2466dc336ddd46ad5ae6e6863fcad` 的独立水准备，**没有MC／RPC、没有新的owner或qualification生成，当前源资格仍false**。原v2宿主／来源／资格保留不变。来源4491、辅助1391、显式实现42；56宿主／55 external静态控制、root review、freeze、inspection及API兼容审计通过。

合同 `ea096af71f254c1ae5a40df4de3a39710e44293b55a3ea6652223de8e2463faa`，来源binding `f8c0ea2ad6bfbf6d5789b1bb96ceff9cedef1c038fd9752fd05be5055034c442`，host `9727e99673e04158101035761032473db217d03802ec037092fd79874f7c300a`。原119,618,244字节base ZIP只引用并核SHA；新小overlay145,953字节，未再复制大archive。准备不等于源已通过F／A／B／R／G／D。

启动门9.319GiB、运行门6GiB、实际MC总数／句柄和固定相机／ROI／qualifier均保持。实际资源控制覆盖先落采样后判门、阈值边界、坏JSON传播和admission；这些为离线负控，没有停止真实游戏。通用restore未保存projection_transform，当前链只适用fresh identity水会话，禁止复用投影变换会话。

80份原件去重为64个gzip对象，`index.json`含原始／压缩SHA，references保留工作区根相对路径。包不含游戏工程、base ZIP、完整source-overlay或全部external原件，因此不是独立可启动包；需原固定输入才能复建。后续产品源一旦改变，须保留此v3作为历史、重新冻结新版本，不能只换hash授旧资格。
