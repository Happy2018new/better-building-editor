# 控件与页面性能记录

2026-09-18，Windows / RTX 4050 Laptop，1920 × 1080 游戏客户区，游戏内 Tracy 10 秒采样。使用 `tools/profile_controls.py` 连续进行原生鼠标操作，采样期间不发送剪贴板调试请求。帧率为采样总帧数 / 10 秒，包含操作间隔，不代表最低帧率或所有机器上的保证。

| 负载 | 修改前 | 第一轮 | 压缩控件后 |
| --- | ---: | ---: | ---: |
| 连续拖动厚度滑条 | 14.3 FPS | 51.5 FPS | 57.5 FPS |
| 选取 / 浏览切换 | 39.3 FPS | 34.4 FPS | 51.1 FPS |
| 建筑库 / 工作台切换 | 29.9 FPS | 42.5 FPS | 51.4 FPS |

原始采样 ID：

- baseline: `cap-20260918-112817-189364`, `cap-20260918-112948-b426c1`, `cap-20260918-113030-165d4c`
- compact: `cap-20260918-115853-562386`, `cap-20260918-115918-e846ee`, `cap-20260918-115940-6b7c82`

改动：滑条本地更新读数和原生轨道，业务值即时写入、页面发布合并；页面移动容器并淡出单个覆盖层；纯视觉提交无需整屏刷新；相同 Element 的干净子树跳过递归更新；九宫圆角压缩成一个布局节点，粒子采用一张序列图片；工具参数保留稳定槽位，减少选项切换时重建。第一次粒子实现增加了布局节点并使选项切换回退，因此已被替换。

阶段验证：42 个 Python 单元测试、19 项游戏内编辑/滑条/拾取回归通过。后续外观和动画修正需重新运行相同负载。

复现：

```powershell
python -X utf8 tools/profile_controls.py slider label
python -X utf8 tools/profile_controls.py segments label
python -X utf8 tools/profile_controls.py pages label
```
