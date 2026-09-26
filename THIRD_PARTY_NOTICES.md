# 第三方来源与许可

本文件区分本项目原创内容与随仓库提供的第三方内容。原创内容适用根目录的 [学习用途许可](LICENSE)，第三方内容保留各自权利与原有许可，不能用本项目的“保留所有权利”声明替代。

## PyreactMC

本项目使用 PyreactMC 客户端 UI 框架

- **上游与作者：** [EnderWolf006 / PyreactMC](https://github.com/EnderWolf006/PyreactMC)。Copyright (c) 2026 EnderWolf006；各贡献者保留其依法享有的权利。
- **当前集成基准：** [`9580d0123584ae8b4b4b3a7b0357250e151c54cd`](https://github.com/EnderWolf006/PyreactMC/commit/9580d0123584ae8b4b4b3a7b0357250e151c54cd)。本仓库包含本地修改，不是未经修改的官方发行版。
- **许可：** PyreactMC 自定义许可 v1.1（2026-09-18）。完整 [LICENSE](behavior_pack/modern_projection/pyreact/LICENSE) 与 [NOTICE](behavior_pack/modern_projection/pyreact/NOTICE) 共同构成许可，均保留上游原文；不是标准 Apache-2.0、MIT 或无条件使用许可。
- **范围：** [`behavior_pack/modern_projection/pyreact/`](behavior_pack/modern_projection/pyreact/) 中的框架及修改版本；从上游引入的 [`resource_pack/ui/PyreactBase.json`](resource_pack/ui/PyreactBase.json) 模板内容；[UI 开发技能](.agents/skills/pyreact-ui-building/)、[调试技能](.agents/skills/pyreact-debugging/)中的上游代码与文档；[`tools/pyreact_legacy/`](tools/pyreact_legacy/)中的历史上游工具。第三方归属不因文件位于框架目录之外而改变。
- **修改说明：** [框架补丁记录](behavior_pack/modern_projection/pyreact/UPSTREAM.md)、[上游同步记录](docs/PYREACT_UPSTREAM.md)、[历史工具来源](tools/pyreact_legacy/README.md)。

**必须注意的上游条件：**

1. 在网易《我的世界》的相关开发者组件／服务器游戏作品详情介绍中，按 NOTICE 清晰保留“本项目使用 PyreactMC 客户端 UI 框架”原文。仅在 README 中写明或仅把文字放在图片里，不能替代该义务。
2. 按相关开发者账户统计，全部付费组件与全部网络游戏的累计获取量合计达到或超过 **1,000,000 次**时，未经上游原作者本人事先另行书面授权，禁止开始或继续使用。不能只统计使用本框架的作品，也不能改用收入或其他指标代替。
3. 免除或调整归属要求也需要上游原作者另行书面授权；门槛豁免与归属豁免互不替代。复制、修改和再分发时须保留完整许可、NOTICE 与必要的修改说明。

以上为提示，具体范围、统计口径、例外及义务均以上游完整文件为准。本项目作者的授权不能代替上游授权。

## three.js

- **项目：** [three.js](https://github.com/mrdoob/three.js)。
- **权利声明：** Copyright © 2010–2023 three.js authors。
- **本地文件：** [`docs/vendor/three.min.js`](docs/vendor/three.min.js)，供浏览器特效预览使用。
- **许可：** [MIT License 完整文本](docs/vendor/three.LICENSE.txt)。

three.js 本身的许可不因用于本项目特效预览而改变。本项目作者独立编写的特效、着色器和页面内容不会因此自动成为 MIT 许可作品。

## Noto Sans SC 与字体图集

- **来源：** [Noto CJK / Noto Sans SC](https://github.com/notofonts/noto-cjk)。
- **随附权利声明：** Copyright 2014–2021 Adobe，保留字体名 `Source`；以随附文件原文为准。
- **使用位置：** [`resource_pack/textures/modern_projection/type/`](resource_pack/textures/modern_projection/type/) 的字形和短语图集；生成方式见 [字体资源说明](docs/FONT_ATLASES.md)。
- **许可文件：** [OFL.txt](resource_pack/textures/modern_projection/OFL.txt) 与 [FONT_LICENSE.txt](resource_pack/textures/modern_projection/FONT_LICENSE.txt)，保留 SIL Open Font License 1.1 原文。

本项目不对第三方字体软件及字形主张原创著作权，其适用许可与原有声明继续保留。独立编写的生成脚本、排版、界面和其他原创表达适用本项目许可；使用该字体输出的整张宣传图或文档不会仅因此整体变为 OFL 许可作品。

## 游戏、SDK 与外部开发工具

Minecraft 及相关名称、原版方块／物品素材和游戏画面中的第三方内容，其权利属于 Mojang、Microsoft、网易或其他相应权利人。网易 ModSDK 及开发客户端的使用遵守各自适用条款；本仓库不授予这些内容的额外权利，也不表示得到上述公司的认可或担保。

MCDevTool、宿主 Python、Pillow、fontTools 等外部工具与依赖由各自权利人按其许可提供。通过项目脚本安装、调用或在本机缓存它们，不会使这些工具改用本项目的学习用途许可。若将第三方工具另外打包分发，应保留其适用许可及声明。

## 原创内容与混合文件

除上述第三方内容及其他明确标注来源的部分外，Happy2018new 独立创作并有权许可的业务代码、脚本、模型、纹理、着色器、文档和宣传资产适用根目录 [LICENSE](LICENSE)。`extras/` 与 `dist/` 中的独立特效代码及资源也不因可以单独加载而获得自由复用授权。

一个文件包含多方内容时，按实际来源分别保留相应权利。目录归类和本文索引不用于剥夺未列明的第三方权利，也不扩张本项目作者的授权范围。
