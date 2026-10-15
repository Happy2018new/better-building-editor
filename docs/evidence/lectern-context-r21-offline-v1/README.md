# West Lectern Context-Clipping Investigation

This is an offline investigation of the retained R20 west-facing comparison.
It is not a product admission and does not change either enabled book/table
gate. The matched north-facing page qualification remains limited to that
reference view. No new game instance was started to produce this package.

Both original captures are reliable, use the same recorded camera/rotation/
screen/foot, and belong to a completed, restored, source-unchanged run with no
cleanup errors. Their SHA256 values and exact unscaled crop bounds are recorded
in `analysis.json`. `native.png`, `candidate.png` and `review.png` were inspected.

The actual world block, candidate Document and prepared palette all identify
`minecraft:lectern`, aux 1, west, powered false. The book pose selects direction
64. The candidate report records only a packed context body part, not an
independent body part. Thus the host state mapping did not revert to south.

The body difference is larger than the top-page displacement. At crop column
90, the first brown/beige silhouette pixel is y78 in the native image and y129
in the candidate, a 51-pixel gap. At page column 180 the corresponding top is
y56 versus y61, a 5-pixel gap. These column observations describe the existing
silhouette and are not page, pose or pixel-acceptance thresholds.

The inspected shared fragment explicitly discards packed-context fragments
outside the center cell range [0.9999, 2.0001]. The installed experimental
native lectern geometry contains a 22.5-degree rotated top board. Its corners
extend beyond a unit cell under both rotation-sign controls: the right-handed
calculation reaches Y 1.081528 and Z 1.153281; reversing the angle sign reaches
Y 1.153281. The raw cube fields, resulting bounds, source hash and both sign
controls are preserved in `analysis.json`.

The leading hypothesis is that center-cell clipping truncates the lectern top
board's overhang, exposing a book-cover edge that the complete body would hide.
This must be separated from any remaining book-pose difference before changing
hinge angles, thickness or translation.

There are two explicit evidence limits. The experimental native JSON is a
resource reference, not proof that the hardcoded world renderer uses the same
mesh. The original R20 report did not attest this shared fragment's hash. The
current main and retained book-r20 clone fragment bytes match at
`8c1c7a5f6bc17c9826085da7a0816aa64b910cb9068bdc0b34853f801c4f9077`.
A fresh source-bound runtime control is still required.

## Prepared Runtime Control

`probe_native_palette_body_r16.py` now accepts `--aux 1 --context-control`
with `--block minecraft:lectern`. The owner-bound diagnostic captures world,
empty, directly captured palette, serialized palette, project-prepared palette
and the unchanged public packed-context builder, each from four fixed views.
It records requested/actual aux, waits for that exact client state, hashes the
whole disposable project's behavior/resources/tools, and restores its world,
player, camera, environment and workspace. It assigns no book candidate and
patches no business module or qualification gate. A cyan-concrete run supplies
the independent placement/decoder positive control.

If world/live/roundtrip/prepared preserve the overhang and only packed context
truncates it, that distinguishes center-cell clipping from native tessellation
and serialization. If live already differs, investigate the native geometry
path before proposing an independent body. Only after the body comparison is
controlled should book-off/on and isolated book-direction/pose controls follow.
The new runtime options are compile-checked but have not yet been exercised in
the game.

`analyze_lectern_body_context_r21.py` is the prepared host-side reviewer for
that control. It requires all 24 source-bound captures, checks exact matching
cameras within each view, preserves unscaled crops and reports empty-frame
silhouette differences without alignment or recoloring. Its observations do
not decide admission. The analyzer is compile-checked; a completed runtime
matrix is still needed to exercise it.

## Offline Replay

```powershell
python -X utf8 tools/analyze_lectern_context_bounds_r21.py `
  --report .runtime/book-r20-final-reference-v1/report.json `
  --project .runtime/projects/book-r20 `
  --native-geometry D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data/resource_packs/experimental_vanilla_block_geometry/models/blocks/lectern.geo.json `
  --output .runtime/lectern-context-r21-review
```

The output directory must be fresh. This replay reads the retained raw captures
and installed native geometry and never opens or controls a game.
