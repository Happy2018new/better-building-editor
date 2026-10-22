# R28 水 provisional → D：仅静态计划

静态主机位于 `.runtime/round-20261023/water-default-preflight-v1`。该目录只准备主机文本、diff 和离线分派检查；没有创建 MC 项目，没有生成 owner contract，没有授予临时候选或正式资格。必须先完成并由 root 审核当前源 B/R/G，才能执行后续操作。当前 F/A 的限定结果已经 root 审核，不能代替 B/R/G 或 D。

## 必要输入与源边界

- F 三份：`.runtime/round-20261023/water-final-matrix-v1` 内的 `product-v2-f-editor-v1.json`、`product-v2-f-full-v2.json`、`product-v2-f-missing-v2.json`。
- A：`.runtime/round-20261023/water-final-matrix-v1/product-v2-a-v1.json`。
- 待采 B/R/G：`.runtime/round-20261023/water-final-brg-v3` 内的 `product-v2-b-v1.json`、`product-v2-r-v1.json`、`product-v2-g-v1.json`。
- 每份 world 报告各自的同会话 camera 原始报告、PNG、12 项 single-stone 读回；不能把 F/A 相机移作新 B/R/G 或 D 会话的相机。
- 已审单像素 AA seam extractor、3 正／9 负控、固定 startup-v2 validator 与二进制 SHA；分析必须显式启用，不能默认回退到旧 extractor。
- 当前共享的 39 项 `generate_liquid_product_owner_contract.SOURCES`、resource_data、模型／材质注册与艺术资源必须继续通过 `source_closure`。各报告允许不同 owner/session；其原始 source contract 不重标。
- 已审 F/A 源 contract 为 `4e4eb7fff2b3dd8d6519ce70c7290c911f6c54ff2c9dbd0e7d3cf160a6b54749`，基准共享提交 `d6b4626cfc4397b23374e3cffdb479ae95bb8129`。

## 审核通过后的操作顺序

1. 从当前同源 base ZIP + overlay 重构独立项目 `D:/Happy2018newの个人文件/GitHub/better-building-editor/.runtime/projects/water-r28-default-v1`，逐字校验；不用硬链接，不修改 F/A 或 BRG 冻结项目。此步骤尚未执行。
2. 只在该 disposable 项目执行其 `tools/generate_liquid_product_owner_contract.py`，再执行同命令加 `--check`。它生成 `tools/data/liquid_product_owner_contract_v1.json` 与 `behavior_pack/modern_projection/projection/liquid_product_owner_data.py`，不手工填写 SHA。
3. 用新审核 host 显式激活已审 extractor/startup validator，校验 F/A 与 BRG 各自 camera，再导入**共享仓库的** `tools/qualify_water_product_r16.py`。必须断言 qualifier 的 `ROOT`、`__file__` 与 generator 的 `ROOT` 指向共享仓库；不能误导入冻结项目的 qualifier，使最终 `set_gate(ROOT, ...)` 写到旧私有项目。
4. 使用下列正式参数 provisional qualify。`--accept-reviewed` 只在 root 审核 B/R/G 原图与原门之后使用；`--admit-candidate` 使 gate 只写入 disposable 项目。新 host 尚未生成或执行，下面是 argv 模板。

```text
python -B -X utf8 <REVIEWED_QUALIFICATION_HOST>
  --project <D_PROJECT>
  --frozen-report <F_EDITOR> --frozen-report <F_FULL> --frozen-report <F_MISSING>
  --animated-report <A> --biome-report <B> --reverse-report <R> --gallery-report <G>
  --output <FRESH_PROVISIONAL_DIRECTORY>
  --admit-candidate --accept-reviewed --native-world-geometry --native-editor-gui
```

5. qualifier 原逻辑会把 disposable gate 标记为 `isolated_candidate`，manifest 的 `default_path` 仍为 false；候选 gate 为冷默认路径测试临时开放原要求的全 gate。此行为来自既有 `set_gate`，不是本轮手工设 gate，不能拷回共享仓库。按实际生成字节重新冻结 D source inventory／contract；与 F/A 相比只允许上面的两份生成物及 `liquid_product_qualification_data.py` 三个元数据文件变化，39 项生产实现和资源不能改变。
6. 将静态主机目录的已审 host 原字节复制到 fresh 正式 D host 目录，准备 source provenance、launch inputs、plan、全 host/external SHA binding。root 审核后另给新 D owner grant，才可运行 group。当前静态主机没有上述启动输入，不能启动。

```text
python -B -X utf8 <FINAL_D_HOST_DIRECTORY>/run_group.py --root-grant <NEW_D_ROOT_GRANT>
```

7. group 只执行正常冷启动 → 普通 Session 初始化 → GUI2/1280×720 → 世界只读基线 → 本会话 camera → 独立恢复 → D → 最终独立恢复与精确退出。D 使用普通默认 profile，`--production-default --extras --controls all`，三个 route `editor/full/missing`，三个 case `source/pool/wet_oak_fence`；不 freeze、不赋 candidate profile。原 `default_path` 仍要求可见动画、三 route 原图和 missing pool 精确占位／恢复，不降低门。
8. D 原图、GUI、camera、profile 无赋值证据、动画、占位、恢复和固定资源门均通过并经 root 复核后，才在共享仓库执行 `tools/generate_liquid_product_owner_contract.py` 与 `--check`，确认和 disposable 生成值相同。然后经同一已审 qualification host 使用原参数，加 `--default-report <D>`，输出 fresh final directory，**移除 `--admit-candidate`**。这一次正式 qualifier 才写共享 gate；不复制 disposable gate，也不手改任何资格常量。

```text
python -B -X utf8 <ROOT>/tools/generate_liquid_product_owner_contract.py
python -B -X utf8 <ROOT>/tools/generate_liquid_product_owner_contract.py --check
python -B -X utf8 <REVIEWED_QUALIFICATION_HOST>
  --project <D_PROJECT>
  --frozen-report <F_EDITOR> --frozen-report <F_FULL> --frozen-report <F_MISSING>
  --animated-report <A> --biome-report <B> --reverse-report <R> --gallery-report <G>
  --default-report <D> --output <FRESH_FINAL_DIRECTORY>
  --accept-reviewed --native-world-geometry --native-editor-gui
```

## D host 最小修正与离线独审

`run_default.py` 复制已审 BRG `run_camera.py` 并单列新版本，旧 host 保持原字节。原 host 虽留有 D 分支，入口只允许 camera；其 WGC wrapper 又无条件执行 single-stone 断言，因此不能直接开放 D。

- camera 仍在每次 WGC 前后检查 single-stone，保留既有 12 项读回和同会话 camera 验证。
- D 的每次 WGC 前后转入 Scene 读回。editor label 使用已有 `describe_scene(value, 2, active)`，附实际 canvas／clip 等 native control；world label保留其原相机／near-player 协议，不套单方块 Scene 断言。
- D 的实际 `probe.SCENE_STATE` 读回追加 `scene_game.EXTRA_STATE`，使 GUI2／cached GUI 的一致性能够走正式 `--native-editor-gui` 分析；camera 读回保持原路径。
- group 中只出现 camera 与 D，没有 F/A/B/R/G 重拍。

`offline-preflight-v1.json` 运行实际 AST wrapper，使用仅记录调用的 stub：camera 正确调用两次 stone／零次 Scene，D 调用零次 stone／两次 Scene，原 capture 各调用一次，原返回值透传；实际 `tracked_run` 仅 D 的 SCENE_STATE 追加 GUI读回。执行实际 argv 分支，确认 D 三 route／三 case、production-default/extras/all、没有 frozen。没有发 RPC 或启动 MC。

固定门继续为可用 commit ≥6 GiB、单进程 handles <250000、相邻增长 <10000；不降低门、不挂起绕过。07:25 停采，07:40 前恢复；root 负责总实例调度与最终休眠。若 B/R/G 或 D 某项失败，保留原报告并停止资格流程，不把本计划当作已经通过。
