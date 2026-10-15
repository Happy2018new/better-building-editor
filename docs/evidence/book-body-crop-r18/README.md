# Neighbor-face component control

This cold-started control restores the original zero-inset table geometry
and removes only `netease:no_crop_face_block` from its behavior definition in
the disposable clone. `minecraft:block_light_absorption=0` and render layer
`alpha` stay unchanged. The root production files and book gate are unchanged.

The component's documented purpose is to retain one of two adjacent faces,
like adjacent leaf blocks, instead of culling both. This establishes a basis
for a component-only control; it does not promise that removing it will fix
custom model tessellation. Source consulted through MCP `minecraft_docs`:

`NeteaseGuide/mcguide/20-玩法开发/15-自定义游戏内容/2-自定义方块/1-JSON组件.md`

Section anchor: `no_crop_face_block`. Retrieval: `netease 相邻面 --top 4`,
then `read <above path> --start 550 --end 700` on 2026-10-15. The component
has no parameters and the source also describes its lighting and render-layer
requirements. No back-face-culling semantics are inferred from its name.

The bottom-only 12-frame control completed and restored, sources were
unchanged, and cleanup errors are empty. Both `review-00.png` and
`review-01.png` were actually inspected. The occupied high view still has a
complete obsidian-textured bottom plane over the support. The same-camera
interior comparison has maximum difference 126 and 5,878 pixels above 8 in
the high view. Thus removing this component does not fix the bottom defect.
Low-view zero difference is insufficient to rule out a horizontal plane.

The four-horizontal-neighbor control is recorded in
`../book-body-crop-r18-sides`. Its high occupied image also retains textured
table walls. Its low occupied book visibility remains a separate unresolved
settling/capture issue and is not accepted as disappearance evidence.
No production qualification may be granted from this control.

Managed instance: `0e439fed620640c1b07890504a041a6d`, owner `book-owner-r18`.
The archived `geometry.json` and `behavior.json` are the exact tested files.
Full native PNGs and capture receipts remain at SHA-bound report paths.
