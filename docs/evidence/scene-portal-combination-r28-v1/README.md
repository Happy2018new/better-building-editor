# 五类 Scene owner 与 portal 锚点：私有组合可行性

结论：两份原封补丁可以在 exact `b70ce7bf13ad6a4472f2b089ac812c162b174861` Git 原字节上顺序应用。组合只在本目录生成，主仓产品与两个原封候选保持不变。这里确认离线组合可行性，不代表合入、原生运行或人工验收完成，不增加下一窗口约 4 小时实施预算。

## 实际补丁应用

`inputs/five-owner.patch` 与 `inputs/portal-anchor.patch` 都是原候选补丁的逐字节副本。先在独立 `combined/` Git 根执行默认 `git apply --check`、`git apply` 应用 owner，再按相同方式应用 portal，四次调用均退出 0。实际命令、cwd、stdout、stderr、returncode 全部保留于 `git-application-invocations.json`；没有 relaxed、force 或忽略上下文的标志。

`combined.patch` 是这两个变更的三文件组合补丁。另在 `replay/` 的 exact b70 原字节上实际执行默认 check/apply，均退出 0，三个输出文件与 `combined/` 实际输出逐字节相等。

完整 Scene AST 检查先确认五个 owner 的候选 AST 等于 sealed owner 候选、`portal_view` AST 等于 sealed portal 候选，再仅恢复这六处 body、移除唯一 `.scene_owner import own_preview`，结果与 b70 整个 Scene AST 完全相同。构造点、原 effect 顺序、依赖数组以及水专用预算参数等都没有额外变化。详见 `ast-and-apply.json`。

## 必须保留的换行差异

当前 Git 的真实 `core.autocrlf=true` 来自 `D:/Program/Git/etc/gitconfig`。默认 git apply 使新写入的 `portal_profile.py` 和 `scene_owner.py` 使用 CRLF，两个 sealed 候选中对应文件为 LF。实际输出被原样保留；LF 规范化内容和整个 AST 均一致。`eol-observation.json` 给出两边原始 SHA 和 CRLF 计数。Scene 本身仍保留原有 CRLF。

初始生成器曾以 portal profile 的 raw-byte 相等为过严断言，在两补丁均真实应用成功后退出 1。`preparation-history.json` 保留这一事实；随后只修正检查解释，并未改补丁或强行改变生成源。组合 patch 只在 profile/helper 的 diff 表达时规范化换行，避免把 Git 的自动 EOL 转换表现成整文件代码修改；上面的独立 replay 已证明其在真实当前默认配置下逐字节复现实际输出。

## 新的真实解释器回执

下面检查全部读取 `combined/behavior_pack/modern_projection/projection/` 的实际组合文件。没有把任何旧候选回执直接当成组合证据。

- `verify_combined_owner_controls.py`，真实 CPython 2.7.13 和 3.13.13：各 8 项真实 Scene 前缀构造／hook 控制、50 项真实 owner effect closure 差分控制全部通过。新回执为 `owner-controls-py2.json` 和 `owner-controls-py3.json`。
- `verify_combined_portal_controls_v2.py`，相同两解释器：编译四份实际 baseline／combined profile 和 Scene，执行真实 pure cell/profile，并提取实际组合 Scene `portal_view` 调用；各 8 组公式、9 组 hook／fallback 分派、12 项非法 GUI 拒绝、同一 callback 的 GUI2→3→4→2、21 组历史 V4 尺寸公式全部通过。新回执为 `portal-controls-py2-v2.json` 和 `portal-controls-py3-v2.json`。
- `validation-invocations-v1.json` 与 `validation-invocations-v2.json` 保留所有实际工具调用和退出码。第一版 portal driver 的 Py3 已通过，Py2 因 `compile` 的 Unicode 绝对文件标签触发 ASCII 编码失败；第二版仅把编译标签改为实际 ASCII 相对源码名，两解释器重新运行均退出 0。第一版 driver 和回执被保留。`portal-driver-preparation-history.json` 给出精确的一处胶水修改，没有改源码或控制期望。
- `driver-adaptations.json` 记录从两份原驱动到组合驱动的逐项入口／路径／AST 允许区域调整。owner 生命周期期望、portal 公式与分派期望均未改变。

实际 owner 控制的模拟边界仍为 hook scheduler、native factory 与资源 close；portal 控制仍使用显式 group_view、camera/session closure 和 Theme GUI 值。完整 Scene、SDK、真实 Pyreact scheduler、native slot、GPU、MC 均未执行。21 项历史公式只是历史尺寸的离线公式复算，不是组合候选的原生验证。

## 结构 review 与来源保护

首次带 scope 的 review 实扫 0，原样保留为 `review-first-zero-scan.json`，不记作通过。随后不带 scope 的真实 review：baseline 实扫 2 文件、combined 实扫 3 文件，均为 Scene／Scene.tick 两项旧函数长度 warning 与 Scene 参数数一项旧 hint；helper 无新增 finding。回执在 `review-baseline-v2.json`、`review-combined-v2.json`。

`sealed-source-guards.json` 逐项复核原 owner 索引绑定的 12 文件、原 portal 索引绑定的 22 文件；同时复核 portal 原有 45 项生产源／合同／metadata 的当前 SHA。`index.json` 绑定本组合包文件。只读 Git 操作与私有 Git 根不涉及主仓 stage、commit 或 push。

## 交给 root 的边界

这是下一窗口的可审查组合准备。两项变更合并后 Scene 的源合同已经变化，不能转授旧 water39、portal、书本或其他原生资格。若之后决定合入，应由 root 按 portal 的 `NEXT_ROUND.md`、owner 的原 README 和新源合同执行必要的 16 个水 gate、12 个 portal gate 及 owner 原生生命周期验证。本包不启动 MC、不关闭人工问题、不追加实施工时；人工关闭数为 0。
