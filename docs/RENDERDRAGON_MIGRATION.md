# RenderDragon 全量源码转换与接入状态

日期：2026-09-27。工作分支：`dev`，从 `main` 的 `f0b8bdf` 创建，保留此前像素阶段试验。

**已完成全部项目顶点/片元源文件的离线 HLSL/DXIL 转换与编译校验；未完成可分发的 RenderDragon 模组接入，也没有通过游戏内一比一视觉验收。** 不应将此分支描述为已经完成双后端适配。

## 覆盖范围

| 原始着色器（名称省略包路径） | 文件数 | 编译程序组 | 保留的效果来源 |
| --- | ---: | ---: | --- |
| `modern_projection_staff.vertex / .fragment` | 2 | 60 | 晶体尖端、蓝/紫星空、握柄、金色光点、原有星点密度及时间算法 |
| `modern_projection_aura.vertex / .fragment` | 2 | 60 | 环绕晶体、星点、拖尾、切换过渡、第一人称相关标记及发光变体 |
| `modern_projection_outline.vertex / .fragment` 与 `modern_projection_luminous_outline.fragment` | 3 | 60 | 普通线框、炫彩框、发光轮廓、线宽与位置计算 |
| `modern_projection_survey_stars.vertex / .fragment` | 2 | 150 | 测绘晶体、引导/打击/发光分支及原有世界尺寸逻辑 |
| `modern_projection_biome_blocks.vertex / .fragment` | 2 | 102 | UI 深度、生物群系草侧颜色、投影标记、季节/透明/雾/抗锯齿 |
| `extras/astral_survey_v1` 的 `astral_survey_survey_stars.vertex / .fragment` | 2 | 120 | 旧版线框、引导、星点及打击变体 |
| **合计** | **13** | **552** | 所有项目着色器源文件 |

主包 GLSL 路径为 `resource_pack/shaders/glsl/`，旧版路径为 `extras/astral_survey_v1/resource_pack/shaders/glsl/`。

读取本机原版材质继承后，共得到 **35 个受影响材质、175 个材质变体**。这包括项目对原版基础材质的覆盖所影响的派生材质，不只统计项目材料文件里的显式名称。每组是一个完整顶点/片元程序对；所选组合为声明的材质变体及 static/single/large/netease 骨骼、basic/fancy/fancy_aa 画质。未验证引擎隐藏宏、实例化与 VR 等额外组合。

## 转换方法

1. 保留原 GLSL 文件作为算法来源，不修改星点密度、速度、颜色参数或当前移动端高精度修复。
2. 用开发者本机客户端的 GLSL 头文件解析真实 uniform、骨骼及纹理声明；头文件没有复制进 Git。
3. glslang 编译 GLSL 为 SPIR-V，SPIRV-Cross 转为 HLSL。由编译器处理矩阵、向量、`mod` 等语义，不使用关键词替换模拟迁移。
4. 修正顶点/片元的接口位置：原版顶点头文件额外声明 `uv`、`overlayColor` 等变量，两阶段分别自动编号时会错位。按名称统一 SPIR-V 的 Location，再比较类型、数组及位置。此操作不改算术指令。
5. 保留 `TEXTURE_n` 的槽位 n；记录继承后的深度、剔除、混合、采样器等状态，供后续原生材质适配使用。记录不等于已经应用到 RenderDragon。
6. 不启用半精度 HLSL 输出，拒绝 `half` / `min16float` / `float16_t`；DXC 使用 `-Gis` 和 validator 1.6，分别生成 SM 6.3 / 6.5 程序。
7. 输出源码、引擎依赖、每份构建产物的 SHA-256，并复核所有文件覆盖和构建完整性。

## 实际验证结果

- 552 / 552 组离线编译成功，0 组失败。
- 1,104 份生成 HLSL；2,208 份 DXIL 经独立 DXV 校验通过。
- 全部顶点/片元数据接口的位置和类型检查通过。
- 全部 13 个正式源文件的 SHA-256 在构建前后相同。
- `verify_translation.py` 复核全量输入、材质继承、产物数量/哈希和阶段接口通过；子集构建会被拒绝当作全量成果。
- 迁移工具的回归测试覆盖材质继承、采样器状态、骨骼/画质宏，以及头文件多余 varying 导致的数据错位。
- 8 项迁移工具测试和原有的 3 项着色器精度/群系回归均通过。工具链安装脚本也已实际重跑，修复了中文路径下 Windows Ninja 的增量构建失败。
- MCDK 定点审查解析了 6 个宿主 Python 文件。`subprocess` 告警对应本机编译器调用，不进入行为包；另有 2 项长函数建议已人工复核，不能将审查结果描述成零告警。

以上是源码转换与离线验证，不是实机视觉验收。本轮没有把未接入的程序装到正式资源包，也没有把以前的诊断截图当作本轮全量效果。

本机明细（不提交）：

```text
.runtime/renderdragon/translated/report.json
.runtime/renderdragon/translated/pNNNN/vert.hlsl
.runtime/renderdragon/translated/pNNNN/frag.hlsl
.runtime/renderdragon/translated/pNNNN/vert.reflection.json
.runtime/renderdragon/translated/pNNNN/frag.reflection.json
.runtime/renderdragon/translated/pNNNN/vert_6_3.dxil
.runtime/renderdragon/translated/pNNNN/frag_6_3.dxil
.runtime/renderdragon/translated/pNNNN/vert_6_5.dxil
.runtime/renderdragon/translated/pNNNN/frag_6_5.dxil
.runtime/renderdragon/translation_verified.json
```

报告的 `jobs` 字段对应具体源文件、材质、宏及变体；`results` 字段包含产物哈希。复现步骤见 `tools/renderdragon/README.md`。产物使用本机游戏头文件，不作为项目自有代码分发。

## 完整迁移尚未完成的原因

### 1. 普通模组资源包未加载编译材质

此前的严格对照证明：相同的已知可运行 HLSL/DXIL，临时替换本机客户端原生 Actor/PBR 材质时会执行，只放进普通 Addon 的 `renderer/materials` 则没有应用。详见 `RENDERDRAGON_PILOT.md`。这限定于网易 `3.9.0.401155` 和已测试路径，不能推广成所有 RenderDragon 版本均不支持。

本轮查询的资料没有给出这个客户端可用的 Addon 原生编译材质注册入口。`ReloadAllShaders` 等旧着色器接口的存在不能证明其支持加载 RenderDragon 的自定义程序。

### 2. 原生渲染接口需要真正对接

当前生成的 `LegacyUniforms` 是中间布局，位于 b0/space1。引擎不会因为变量名为 `TIME`、`WORLDVIEWPROJ` 或 `EXTRA_ACTOR_UNIFORM1` 就自动向这个新布局写入数据。还需要解决：

- 原生顶点布局、TEXCOORD/SV_Position 语义与 root signature。
- 每帧时间、相机/模型矩阵、骨骼和 EXTRA_ACTOR_UNIFORM 参数的真实上传。
- ActorForwardPBR / ActorPrepass 的渲染目标、法线、材质参数和运动向量。
- 深度、透明混合、剔除及采样器状态的实际应用。
- OpenGL 与 D3D 的裁剪空间差异，以及引擎矩阵是否已完成转换。当前没有盲目翻转 Y 或 Z，避免重复转换。

此前原生试验仍使用诊断 UV、固定法线/视线及简化 PBR，只验证了星空像素算法可执行，不能拿来证明以上条件已经满足。

### 3. 一比一效果需要游戏内对照

即使源码算法和常数相同，仍须验证真实坐标、时钟、纹理、透明度与渲染通道。计划验收包含同场景/视角/时间的静止、奔跑拖尾、切换两法杖、第一/第三人称、轮廓、UI/世界草侧、时间回绕与长时间运行。跨 GPU 的正弦等浮点运算也不能仅凭编译成功保证逐像素比特相同。

目前 `runtime_verified` 和 `visual_parity_verified` 都明确为 `false`。下一步首先需要确认当前网易客户端支持的自定义编译材质加载及绑定途径，再完成原生接口和上述验收。直接替换安装目录的诊断方法不是可发布模组方案。

## 分支与现有版本

本轮在 `dev` 工作，没有提交或推送。正式 OpenGL 着色器和材质没有改变，客户端原生文件也没有新增修改。全量转换工具不会操作游戏安装目录或启动设置。
