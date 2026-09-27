# 手机着色器精度修复

2026-09-26。已检查主资源包的全部 11 个 GLSL 着色器，以及独立星穹特效包的 2 个着色器。本次修复精度声明及其顺序，使手机端使用与 PC 高精度路径一致的计算；星点密度、速度、颜色和几何参数不变。

## 两处主要问题

**法杖流动逐渐卡顿：时间 uniform 在高精度声明前已经被声明。**

`modern_projection_staff.fragment` 原来先引入 `uniformPerFrameConstants.h`，之后才写 `precision highp float;`。本地引擎 3.9.0.401155 的该头文件声明的是 `UNIFORM float TIME;`，没有独立的精度限定。因此，在默认使用 `mediump` 的片元环境中，`TIME` 会继承此前的中精度；后面的高精度局部变量不能恢复 uniform 已丢失的小数位。

引擎头文件注明 `TIME` 在 0–210 秒之间循环。对于用 FP16 实现 `mediump` 的 GPU，时间越接近周期后段，可表示时间值的间隔越大。例如 128–210 秒区间的间隔约为 0.125 秒，多个渲染帧读到相同时间，星空便呈现停顿与跳动。这是时钟量化造成的动画问题，不能据此推断整个游戏的帧率下降。

**环绕晶体几乎没有星点：随机函数计算缺少高精度。**

`modern_projection_aura.fragment` 原来仅将插值输入标为 `highp`，没有为 `hash()` 的参数、局部计算与返回值指定高精度。星点种子使用 `fract(sin(dot(...)) * 43758.5453)`；中间乘积很大，FP16 会丢失小数位，`fract()` 往往变为 0，无法通过星点阈值。仅给输入加 `highp` 不能保护整条计算链。

## 修复文件

所有受影响文件均在 `// __multiversion__` 注释之后、任何头文件和声明之前设置 `precision highp float;`。法杖片元是移动已有声明，其他文件是补充声明。顶点与片元阶段同时处理，以保持共享 uniform 和 varying 的精度一致。以下除两处主要缺陷外，也包括同类风险的预防修复，并不表示每个特效都已经在手机上观察到故障。

| 文件 | 处理目的 |
| --- | --- |
| [modern_projection_staff.fragment](../resource_pack/shaders/glsl/modern_projection_staff.fragment) | 高精度声明提前到引擎头文件之前，保护 `TIME`；覆盖法杖晶体、握柄、紫色变体与金色光点。 |
| [modern_projection_staff.vertex](../resource_pack/shaders/glsl/modern_projection_staff.vertex) | 明确顶点计算与引擎 uniform 精度，与片元阶段一致。 |
| [modern_projection_aura.fragment](../resource_pack/shaders/glsl/modern_projection_aura.fragment) | 保护 `hash()`、`skyStars()` 的参数、局部变量、返回值和星云计算。 |
| [modern_projection_aura.vertex](../resource_pack/shaders/glsl/modern_projection_aura.vertex) | 明确随机种子、轨道、动画时钟和输出计算的精度。 |
| [modern_projection_survey_stars.fragment](../resource_pack/shaders/glsl/modern_projection_survey_stars.fragment) | 保护测绘晶体的时间、窄高光、闪烁与颜色变化计算。 |
| [modern_projection_survey_stars.vertex](../resource_pack/shaders/glsl/modern_projection_survey_stars.vertex) | 明确轨迹、随机种子、动画相位和共享 uniform 的精度。 |
| [modern_projection_luminous_outline.fragment](../resource_pack/shaders/glsl/modern_projection_luminous_outline.fragment) | 保护金色线框的时间和流动光丝相位，避免时间量化。 |
| [modern_projection_outline.fragment](../resource_pack/shaders/glsl/modern_projection_outline.fragment) | 保护炫彩线框插值之后的色相小数计算。 |
| [modern_projection_outline.vertex](../resource_pack/shaders/glsl/modern_projection_outline.vertex) | 明确两种线框共用顶点阶段的精度，与两个片元程序分别匹配。 |
| [modern_projection_biome_blocks.fragment](../resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment) | 对预览／世界投影分支、中间数值及细小染色误差比较统一高精度默认值。 |
| [modern_projection_biome_blocks.vertex](../resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex) | 明确预览深度编码、投影计算和与片元共享的接口精度。 |
| [astral_survey_survey_stars.fragment](../extras/astral_survey_v1/resource_pack/shaders/glsl/astral_survey_survey_stars.fragment) | 同步修复独立星穹包的时间与高光计算。 |
| [astral_survey_survey_stars.vertex](../extras/astral_survey_v1/resource_pack/shaders/glsl/astral_survey_survey_stars.vertex) | 同步独立包顶点阶段的精度与接口。 |

`docs/effects_lab.html` 的着色器已经在开头使用 `highp`，并显式声明 `uniform highp float TIME;`，不需要调整。引擎自带头文件无需修改；独立包使用前请执行 `python tools/package_astral_effects.py`，将修复后的源码重新打包为 `dist/astral_survey_v1.zip`。

## 验证结果

- **112 组编译／链接全部通过。** 展开本地游戏的真实引擎头文件，在 ANGLE / SwiftShader 上验证 GLSL ES 100、300 的适用变体，覆盖法杖、环绕效果、两种线框、两套测绘特效、生物群系，以及骨骼、透明、季节、雾和抗锯齿分支。编译环境刻意先设置 `mediump`，检查着色器自身能覆盖默认精度。
- **36 组图像对比全部一致。** 对法杖普通／紫色、握柄普通／紫色、金色光点、环绕晶体这 6 个片元变体，使用合成表面，在 0、32、64、128、200、209.9 秒渲染。修复后使用中精度宿主默认值的结果，与修复前强制高精度的基准逐像素一致。此对比使用软件 GLES，不是 PC 游戏或手机截图对比。
- **周期后段动画验证通过。** 同样的 6 个变体在 200 秒附近按 60 FPS 渲染连续 60 帧，每个相邻帧的输出都有变化。
- **35 项相关单元测试通过。** 包含新增的 `tests/test_shader_precision.py`，以及已有法杖、测绘、生物群系、独立归档测试。新增检查防止高精度声明再次被放到头文件之后，或在后面被降回中精度。

数值模拟额外说明了问题机制：200 秒附近的 60 个时间样本，FP32 保留 60 个不同值，FP16 仅剩 9 个；对 16,641 个星点格子的哈希乘积只做最后一步 FP16 量化，约 98.87% 的 `fract` 结果就变为 0。阈值为 0.30 时，合格种子比例由约 69.83% 降为约 0.93%。这只是 IEEE 浮点数值模拟，未模拟某台手机完整的 GPU 运算，不能当作手机实测星点数量。

本地诊断脚本和详细结果位于忽略目录 `.runtime/shader_precision/` 及 `.runtime/check_shader*_precision.py`，不随模组发布。

## 真机验收边界

本轮检查时 `adb devices -l` 没有已连接设备，因此尚未做手机画面对比或性能测量。高精度修复消除了已确认的精度缺口，但各 GPU 的三角函数实现仍可能产生个别星点位置差异，不能承诺跨设备逐像素一致。

使用更新后的资源包完整重启客户端后，应在固定视角下同时观察法杖与环绕晶体，连续运行至少 4 分钟，覆盖一次 210 秒时间回绕：周期后段的流动应持续平滑，晶体星点不应再因随机种子量化而消失。还应检查金色光点、金色／炫彩范围框、测绘晶体与生物群系投影，确认这些共享精度规则的效果正常。
