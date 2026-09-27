# RenderDragon 着色器迁移工具

此目录包含全部项目着色器的离线 HLSL 转换器，以及早期 Windows ModPC 像素阶段试验。**它还不是已完成的普通 Addon 适配。** 全量转换结果与未解决条件见 `docs/RENDERDRAGON_MIGRATION.md`；早期实机证据见 `docs/RENDERDRAGON_PILOT.md`。

## 全量转换

`translate_all.py` 以正式 GLSL 为唯一算法来源，经 glslang / SPIRV-Cross 生成 HLSL，再用 DXC 编译 `vs/ps_6_3` 和 `vs/ps_6_5`。不维护另一套手写近似算法，也不改动正式 OpenGL 文件。

- `material_inventory.py`：按本机 `vanilla_base → vanilla → vanilla_netease → 项目` 叠加材质，读取继承、宏、渲染状态及变体；同时包含基础材质覆盖所影响的原版派生材质。
- `spirv_interface.py`：显式对齐顶点输出与片元输入的 Location，保留纹理编号；不改 SPIR-V 算术指令。
- `translate_all.py`：覆盖主资源包及 `extras/astral_survey_v1` 的所有顶点/片元源码，编译选定的骨骼与画质组合，输出反射信息和 SHA-256。
- `verify_translation.py`：验证源码/引擎依赖未变化、全覆盖、产物哈希及阶段接口；拒绝把 `--only` 子集算作全量结果。
- `bootstrap_translation.py` / `toolchain_sources.json`：下载并核验固定版本工具源码、构建 SPIRV-Cross。

构建环境：宿主 Python 3.10+、Visual Studio C++ 工具链、CMake、Ninja；它们属于开发工具，不运行于游戏内的 Python 2。在 Developer PowerShell 中执行：

```powershell
py -X utf8 tools/renderdragon/bootstrap_translation.py
py -X utf8 tools/renderdragon/translate_all.py `
  --game '<本机游戏目录>' `
  --glslang '.runtime/renderdragon/translation_tools/glslang/bin/glslang.exe' `
  --spirv-cross '.runtime/renderdragon/translation_tools/cross_build/spirv-cross.exe' `
  --dxc '<匹配客户端编译器的 dxc.exe>' `
  --validator '<dxv.exe>'
py -X utf8 tools/renderdragon/verify_translation.py `
  .runtime/renderdragon/translated/report.json
```

`bootstrap_translation.py` 可通过 `--cmake` / `--ninja` 指定工具路径。它在短 ASCII 临时目录编译 SPIRV-Cross，完成后清理临时目录并将可执行文件放回 `.runtime`，避免 Windows Ninja 在中文工作区下重跑失败；必要时用 `--build-root` 指定临时父目录。不要替换游戏中的 DLL。DXC 使用当前客户端匹配的本地副本；本轮匹配 `dxcompiler.dll 1.6.2106.3`，显式指定 validator 1.6。完整工具哈希记录在本机构建报告中。

输出在 `.runtime/renderdragon/translated/pNNNN/`：每组含 `vert/frag.hlsl`、SPIR-V、反射 JSON 和两个 Shader Model 的 DXIL。`report.json` 将每组对应回具体材料、变体、原始文件及宏。产物会展开开发者本机的游戏头文件，必须保持本机使用，不作为项目自有源码提交。

当前全量结果为 13 个源文件、35 个材质、175 个继承后的材质变体、552 组程序；对应 1,104 份 HLSL 和 2,208 份 DXIL，均通过本机编译与校验。这里的组合范围为现有材质声明加 static/single/large/netease 骨骼及 basic/fancy/fancy_aa 画质组合，不代表引擎所有隐藏宏、VR、实例化和移动后端均已覆盖。

**离线程序尚未对接 RenderDragon 的原生输入布局、常量上传、PBR 输出和普通资源包加载入口。** 默认 `LegacyUniforms` 位于 b0/space1，需要后续引擎适配；坐标保持原 OpenGL 约定，没有猜测矩阵而盲目翻转 Y 或修改 Z。编译成功不能代表可直接放入 `renderer/materials` 生效，更不能代表实机视觉一致性。

## 早期像素阶段试验

## 文件

- `starfield.hlsli`：从本项目法杖 GLSL 移植的星点、星云、视角高光、握柄稀疏星点和金色矿物算法。使用 HLSL `float2/3/4`、`frac`、`lerp`、`atan2`，保持 32 位浮点运算。
- `staff_probe.hlsl`：当前客户端 `Actor`、`ActorForwardPBR`、`ActorPrepass` 的诊断接口。保留完整输入语义顺序，并为 PBR 预通道输出三个颜色目标。
- `build_probe.py`：仅生成本地试验文件，不修改游戏安装目录，不安装资源包。

## 构建

本次环境为网易 ModPC `3.9.0.401155`。宿主 Python 3 环境需要 `lazurite==0.11.0`，编译器使用与客户端配套的 `dxcompiler.dll 1.6.2106.3` 及 `dxil.dll`。本地 `dxc.exe` 必须能加载这些配套 DLL；不要替换游戏内的 DLL。

```powershell
py -X utf8 tools/renderdragon/build_probe.py `
  --templates '<游戏目录>/data/renderer/materials' `
  --dxc '<本地编译器目录>/dxc.exe' `
  --output '.runtime/renderdragon/build'
```

添加 `--solid` 可构建纯洋红色诊断程序；若加载成功，覆盖到的物体会明显改变颜色。添加 `--validator <dxv.exe路径>` 可额外验证每个编译产物。

当前客户端的 `Direct3D_SM60` 槽位实际存储 `ps_6_3`，`Direct3D_SM65` 存储 `ps_6_5`。脚本按实测槽位编译，保留原来的顶点程序、深度通道、完整输入签名和已有常量偏移；仅替换相关像素程序，并在缺少 `Time` 的片元常量块末尾追加该试验变量。共覆盖 Actor 432、ActorForwardPBR 216、ActorPrepass 144 个变体条目，重复字节码按平台和常量寄存器复用。

生成的 `.material.bin` 以开发者本机客户端材质为模板，包含客户端原有内容，**不能提交或随模组分发**。输出应一直保留在 Git 忽略的 `.runtime/` 中。工具源码没有包含这些二进制。

## 试验接口与限制

当前适配层通过贴图尺寸 `48 × 8` 和蓝色色块选择本项目的法杖表面。这只是本地实验的识别方式，不是引擎公开的自定义材质注册接口，也不保证与其他资源包隔离。非命中的物体仅返回基础贴图；预通道的原版光照也被简化，因此不能全局安装后用于正常游戏。

星空使用 `Time.x` 作为候选时钟，折回 210 秒范围，并对非有限值回退到零。新增 uniform 元数据不等于引擎会每帧写入它：**本轮确认星云/星点程序显示，尚未确认这个时钟持续更新，不能声称动画迁移完成。** 此前用渲染控制器 `color` / `overlay_color` 传时间的诊断未成功，当前版本不依赖它们。

适配层暂用 UV 局部坐标及固定法线/视线方向构造输入，以隔离原生顶点数据。最初直接使用原生世界坐标与屏幕导数时出现黑块；换成这套输入后恢复正常。公共 HLSL 算法还对 Fresnel 的幂运算底数做 `saturate`，避免舍入使其变为负数。不能仅凭这次组合修正认定黑块只有一个原因。

法杖晶体尖端变形、真实本地法线、视角视差、运动向量、完整 PBR 光照、紫色法杖/金色光点的材质路由以及环绕晶体尚未迁移。预通道使用全自发光和简化材质参数；当前只验证星空像素算法进入原生管线，不是最终视觉效果。

本机临时替换客户端编译材质已确认 HLSL 执行（洋红色对照及星空程序均可见），但它与普通模组资源包的加载入口是两个不同的条件。实际清理状态和相同字节码的资源包对照结果见试验报告。当前不得把这些实验文件加入正式资源包并宣称自动适配完成。
