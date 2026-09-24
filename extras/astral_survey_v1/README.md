# 可迁移的星穹测绘特效 v1

此目录冻结了金色改版前的游戏特效，来源为 `eb99934` 的游戏资源（星穹实现来自 `09a5521`）。它包含星空线框、环绕晶体、常驻星芒、点选划过，以及可选的原 HUD 动态按钮素材。HTML 预览不属于此运行包。

所有标识改为独立的 `astral_survey` 命名空间，Python 包为 `AstralSurvey`，可以和现代化投影的金色特效同时加载。没有 Pyreact、编辑器、建筑库或服务端模块依赖。

## 接入其他网易 ModSDK 模组

1. 将 `behavior_pack/AstralSurvey` 和 `behavior_pack/entities` 合并到目标行为包。
2. 合并 `resource_pack` 的 entity、models、shaders、render_controllers、textures 目录。把 `materials/entity.material` 的四个材质定义合并到目标同名文件的 `materials` 对象，**不要覆盖目标已有材质**。
3. 使用目标包原有 manifest；本目录提供的 manifest 仅用于独立加载资源包时使用，无需复制到目标模组。
4. 在目标的客户端系统创建对象，接入每帧更新、切换维度清理与退出销毁。完整重启游戏加载新材质和几何。

```python
from AstralSurvey.api import AstralSurvey

# 客户端系统 __init__ 中
self.survey_vfx = AstralSurvey(self)
self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(),
                    'OnScriptTickClient', self, self.on_survey_frame)

def on_survey_frame(self, args):
    self.survey_vfx.update()

# 两个坐标都是包含在选区内的方块坐标
self.survey_vfx.select((10, 64, 20), (13, 68, 23))
self.survey_vfx.strike((10, 64, 20))

# 清除选区、切换维度时
self.survey_vfx.clear()

# 客户端系统 Destroy 中；同时解除自己注册的事件
self.survey_vfx.destroy()
```

若目标已有渲染帧事件，可在该事件中调用 `update()`。请每帧只调用一次。`show_box(origin, size)` 接受最小角和正数尺寸；`select(a,b)` 接受两个包含端点的方块坐标。调用 `clear()` 后可重新创建，`destroy()` 后应新建对象。`modMain.py` 仅让独立行为包的 Python 路径被引擎识别，不会自动创建任何系统或特效；合并进已有行为包后可省略此文件。

## 可选 HUD 素材

`optional_hud` 保存原始三态按钮图集与 JsonUI 模板。复制其中 textures 到资源包，把 `astral_tools.json` 放入 ui 并添加到 `_ui_defs.json`。模板命名空间是 `AstralSurveyTools`。自行注册 ScreenNode 并绑定 `open_button`、`clear_button` 的回调和文案；本包不附带编辑器导入、清除业务逻辑。3D 效果无需这些可选文件。

## 运行特征

- 仅 `CreateClientEntityByTypeStr`；不创建服务器实体或方块，没有碰撞、重力和阴影。
- 三个常驻演员，最多三个点选效果，点选效果 1.8 秒后回收。
- GPU 计算运动、颜色和晶体反光。Python 仅更新相机锚点和少量计时。
- 世界方块会遮挡主特效；单独的细淡定位线可穿墙，保证选区可见。
- 不包含场景颜色采样，因此晶体折射为解析近似。
- 在 1 格及 64×128×64 范围使用过；移植后仍需在目标游戏版本与手机上验证。

详细旧效果说明见 [REFERENCE_EFFECTS.md](REFERENCE_EFFECTS.md)。生成归档：在主项目执行 `python tools/package_astral_effects.py`。归档使用固定文件时间并附 SHA-256 清单，来源是此冻结目录，不会意外打包未来的金色资源。
