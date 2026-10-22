# 下周期 Scene 五 owner 最小机械抽取：私有候选

这是可执行的离线准备，**本轮不合入、不修改主仓产品、不启动 MC、不转授真实资格**。候选基于 `b70ce7bf13ad6a4472f2b089ac812c162b174861` 的精确 Git `scene.py`；原 SHA256 为 `e1a2c18c65f37d29dbaeb35d7b4b512252539871f112ed9552d4e68d955a69a9`。`scene.original.py` 保留 Git 原字节，`scene.candidate.py` 保留原 CRLF。机械差异在 `candidate.patch`，新 helper 仅 24 行。

`scene_owner.py::own_preview` 只接管登记和关闭闭包。五个 `own_*` 函数和其 `use_effect` 调用位置仍留在 Scene；各原 effect 的依赖数组不改。恢复五个原函数体并去掉唯一 helper import 后，**整个候选 Scene AST 与原 Scene 完全相等**，包括剩余构造、相机、输入、tick、native view、布局、其他 hooks 和渲染代码。候选不引入 SDK、Pyreact 或服务端 import。

## 明确保留的构造和 hook 差异

owner 顺序仍为 `subscribe → attach_frame_pump → own_liquid → own_items → own_cauldrons → own_portals → own_books`；其间原 `use_ref`、`use_memo` 次序及依赖逐项保留。每家族 profile 为 None 时，仍登记对应 effect hook，但不创建 preview/controls 或 native model。

| 家族 | 原 preview 构造，保持原表达式 | 原 controls 构造，保持原表达式 |
| --- | --- | --- |
| 水 | profile 的 `preview_factory`，缺失时 `LiquidPreview`；参数仍为 Session、provider_factory、models、max_groups | `LiquidControls`；独有 `request_starts_per_frame=getattr(profile,'ui_request_starts_per_frame',None)`，预算不改 |
| 物品 | `ItemPreview(session,item_profile)` | 独立 `ItemControls` |
| 坩埚 | `CauldronPreview(session,cauldron_profile)` | `LiquidControls`，不新增水预算参数 |
| 末地门 | `PortalPreview(session,portal_profile)` | `LiquidControls`，不新增水预算参数 |
| 书 | `BookPreview(session,book_profile)` | `LiquidControls`，不新增水预算参数 |

每个非 None 家族仍在原位置独立调用 `session.bridge.factory.CreateModel(None)`。helper 在 owner effect 真正执行时才登记字段；没有把构造或登记提前到 render／import 阶段。

## 登记、关闭与异常语义

登记仍按 `preview字段 → controls字段` 顺序写 Session，不清空已有 error。清理的顺序严格为 **`controls.close() → preview.close() → 读取当前 Session preview 身份 → 仅身份 is 原 preview 时依次清 preview、controls、error=''`**。这不是异常行为改进批。

| 情况 | 原行为与候选行为 |
| --- | --- |
| preview 为 None | 返回 None；不登记、不清字段、不关闭 controls。判定仍为 `is None`，falsey 但非 None 的对象照常拥有资源 |
| 正常卸载 | 两次 close 依次完成后才检查身份，匹配才清三个字段 |
| 旧 owner 迟到清理，新 owner 已替换 preview | 仍先关闭旧 controls、旧 preview；不清新 owner 的字段或 error |
| controls.close 内同步替换 Session owner | 仍随后关闭旧 preview，再检查替换后的身份，保留新 owner |
| preview 仍相同但 controls 已替换 | 仍只检查 preview 身份，按原行为清掉当前 controls 字段；不新增 controls 身份条件 |
| controls.close 抛异常 | 原异常对象直接传播；不调用 preview.close，不检查身份，不清字段 |
| preview.close 抛异常 | controls 已关闭；原异常对象直接传播，不检查身份、不清字段 |
| controls 为 None | 登记仍完成；cleanup 在访问 None.close 时抛 AttributeError，preview 不关闭 |
| 当前 Session preview 字段缺失 | 水／物品保留 `getattr(...,None)`：两次 close 后不抛错、不清其他字段；坩埚／门／书保留无默认值读取：两次 close 后抛 AttributeError |
| 重复调用 cleanup | 仍重复调用两次 close；不加幂等标志、重试、finally、吞错或额外恢复 |

字段名只是现有五个固定 family 的机械映射；字符串仍遵循原 `unicode_literals`。没有更换公共类、profile、算法或 Session 接口。结构性调用方扫描确认 `panels`、`ui` 直接引用 Scene，间接有 `client_system`、`debug_blueprint_ui`、`material_browser`；Scene 接口和导入位置不变，这些调用方本批无需同步修改。新增 helper 属主仓客户端生命周期边界，不迁往 renderer／states 库。

## 实际离线控制与复跑

`verify_actual_owner_controls.py` 读取原始／候选 Scene AST，执行 **原 Scene 的真实 owner 构造／hook 前缀及五个真实 effect 闭包**，与候选逐事件、逐状态、异常对象身份对照；不是手抄一份 cleanup 充当基准。只有 hook scheduler、native factory、资源对象及其 close 是显式假边界；不执行 SDK import、Scene UI、真实 Pyreact 调度或渲染。

真 Python 2.7.13 与 Python 3.13.13 各通过 **8 组构造／hook 控制 + 50 组 owner 生命周期控制**。构造覆盖全 None、全启用、原生水 fallback、预算缺失与每个家族单启用；每个家族分别覆盖上表十种生命周期。完整模块和 helper 也在两解释器编译。主仓 scene.py 在控制前后原字节一致。

原回执为 `controls-py2.json`、`controls-py3-final.json`；两解释器的 58 项 case 逐项相同。脚本支持 fresh 输出路径，禁止覆盖历史文件：

```powershell
python -B -X utf8 D:/Happy2018newの个人文件/GitHub/better-building-editor/.runtime/round-20261023/scene-owner-minimal-v2/verify_actual_owner_controls.py <新的输出文件.json>
& D:/Program/Python27/python.exe -B D:/Happy2018newの个人文件/GitHub/better-building-editor/.runtime/round-20261023/scene-owner-minimal-v2/verify_actual_owner_controls.py <另一个新的输出文件.json>
```

MCDK 对私有 `.runtime` 路径最初返回 files=0，这些结果不当作审查通过。另以相同 helper SHA 的独立临时 behavior_pack 快照完成真实结构审查：2文件解析成功、0 finding，原回执在 `helper-structural-review.json`。这只审查 helper，不授 Scene／引擎资格。

准备期间的 CRLF 精确 needle 失败、Python2 Windows 路径编码失败及 Unicode 源携带 encoding 声明的 AST 输入失败均在 `preparation-history.json` 说明；只修私有生成器／控制加载方式，没有改候选生命周期来迎合测试。

## 下一窗口接入边界

本轮只交付候选，不将“58例离线相同”计为已完成 Scene 重构。下一窗口仍使用既定剩余约4小时实施容量，不新增／重复记账。落地主仓前先核 Scene 原 SHA；若期间产品有变更，先按新源重新生成 diff 与回执，不盲目套补丁。

若正式应用，只改主仓 Scene 的五 owner 函数体／helper import，并新增 scene_owner.py；随后按最终实现重新生成／绑定资格来源及完整依赖。**Scene 仍留在水合同，新增 helper 也必须纳入实际依赖，不能移出39项显式合同或用本候选转授旧39资格。** 下一窗口需要真实冷启动、五家族挂载／卸载／取消／重载与相关编辑器／投影显示验证，并按受影响水合同复验；本轮未运行这些。异常语义若需改善，单独作为后续行为修复，不混入机械抽取。
