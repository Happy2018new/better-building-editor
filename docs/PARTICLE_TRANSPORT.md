# 星点动态参数与回归验证

法杖环绕、移动拖尾、测绘器端点和线框星点共用原生粒子载体。轨迹与颜色仍由原有 GPU 特效计算；载体的 UV 和 RGBA 用于传递有界参数，不是最终显示颜色。

## 本次修复

原生粒子会在上一帧与当前帧的顶点属性间插值。旧协议将连续变化的速度、形成进度与粒子编号、种子交错打包；跨字段进位时，中间值会解码成其他编号或种子。结果是移动拖尾与点击形成动画出现随机重排、跳变或四角退化。

- UV 只保存静态编号、尺寸、方向和布局元数据。每个地址占 4 个编码值；虚拟纹理尺寸为 65535，四角偏移为 0.5 / 3，兼容 UNORM16 量化、截断和至多半像素的图集内缩。
- 测绘特效使用独立通道传递亮度、环绕速度、形成进度；密度仅在固定编号区间内变化。
- 玩家环绕特效的三个速度分量分别使用 RGB 的低位区间；高位出生进度在同一载体生命周期内固定。A 通道单独传递形成／切换阶段。
- 静态元数据改变时重建载体。普通移动和端点重复点击复用载体，避免每帧创建粒子。
- 新载体先写全参数，再延迟 0.10 秒开放显示；代数、载体 ID 和激活序号共同阻止过期回调激活已清理或替换的载体。
- 隐藏只清零 alpha，保留 RGB 元数据，确保用于大范围剔除边界的隐藏粒子始终能被正确识别。

金色框、星空框和玩家环绕的最终颜色仍来自各自 fragment shader 的原有配色。本次不修改颜色或混合材质。

## 可重复验证

宿主 Python 的定向测试：

```powershell
python -m unittest discover -s tests -p test_native_glow.py
python -m unittest discover -s tests -p test_astral_staffs.py
python -m unittest discover -s tests -p test_survey_effects.py
python -m unittest discover -s tests -p test_biome_shader.py
```

`tools/verify_native_transport.py` 使用真实 GLSL 解码器进行 WebGL2 transform feedback，检查全部编号、隐藏边界粒子、四角、量化方式、图集内缩与连续参数插值。需要宿主安装 Playwright，并提供 Chromium 和游戏 GLSL 头文件路径；不往游戏 Python 加载这些依赖。

```powershell
python tools/verify_native_transport.py --headers '<游戏目录>/data/shaders/glsl' --browser '<Chromium 路径>' --report '<结果 JSON 路径>'
```

实机回归使用普通世界并开启美丽的天空，包含仰视天空、冰、树叶、水、真实石墙遮挡、第一／第三人称前进与转向停止、两端点形成和重复点击。移动由服务端 `SetFootPos` 驱动，点击序列调用实际 `draw_bounds` / `pulse_point` 业务入口；这些录像不代表物理键鼠输入回放。

## 透明投影与后期星点的合成

**本分支的后续合成方案未通过最终验收，透明投影遮挡仍未完成修复。** 以下实现只在天空背景等隔离场景中通过；普通世界远岛和水面会覆盖投影。失败证据、测试盲区及能力边界见 [PROJECTION_COMPOSITING.md](PROJECTION_COMPOSITING.md)。前一提交的动态参数稳定性修复仍然独立有效。

原生星点在较晚阶段绘制，会被前面的透明投影深度挡住。动态参数修复与这个遮挡问题相互独立。

已确认直接关闭投影深度写入会使纯天空背景下的投影被后续天空覆盖；同时保留早期实体发光和后期粒子的 alpha 补偿方案，在当前网易 3.9.0.401155 的 OpenGL 后端触发 `Unknown blend target: 7`（`DestAlpha`）。不能仅凭资料列出该混合参数就认定当前后端支持它。

现在将投影颜色与天空保护深度拆开：颜色模型保留连续透明混合与深度测试，但不写深度；另一个客户端实体复用相同的 native geometry，只写入接近天空的远深度，输出零颜色。专用天空 shader 将背景天空深度归一到最远端，因而不会覆盖保护范围内的投影，而近处星点仍可通过深度测试。真实不透明地形的深度不被保护层替换，仍能挡住后方星点。

保护层沿用方块纹理的 alpha test，并恢复原始近／远裁剪范围。为避免多重采样下 alpha=0 导致保护层完全失去覆盖，BlockGeometry 的三类 cutout 基材质移除 AlphaToCoverage；UI 复用这些材质，因此也要回归草叶的镂空与网格深度。太阳、月亮与原版星空材质保持原样。

主模型与保护层成对准备、提交和销毁，自动隐藏已占用方块时同步两个几何缓冲区。零透明度隐藏保护层；更新失败恢复之前的可见性和位置。详情与验证方式见 [PROJECTION_COMPOSITING.md](PROJECTION_COMPOSITING.md)。

这不是顺序无关透明：晚绘制的加法星点不按投影透明度或叠加层数衰减；相交的多层透明面、水冰等仍受引擎提交顺序影响。验收必须同时确认投影表面、后方星点、真实墙体遮挡，不能仅凭星点出现判为成功。
