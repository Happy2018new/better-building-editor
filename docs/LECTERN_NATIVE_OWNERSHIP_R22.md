# Native lectern ownership correction

The existing default book companion is already enabled for NEMC
`3.10.0.420447`. This change addresses a separate native lectern body defect:
packing the lectern into a neighboring-cell context clips the sloping top
board where it extends beyond its owner cell.

`projection/lectern_body.py` identifies native lectern materials. All three
context builders now put each selected lectern in its own local overlay,
outside the packed context decoder, and omit its body/actor from neighbor
tiles. Native material, aux and states are retained. Its renderer actor moves
with the body; complete logical book NBT stays in the document for the existing
BookPreview and BookProjection owners. The extra block layer retains its
context path. A hidden or occupied non-target lectern cannot be duplicated in
the geometry for an adjacent selected block.

The existing enchanting-table proxy keeps its previous actor suppression:
the new helper copies actors only for a lectern. There are no new resources,
shared shader changes, model registration changes or book qualification edits.
Powered is preserved as logical metadata and is not a new appearance variant.

The `c9463079` hidden-neighbor correction already reaches production full world
preparation, initial and dynamic missing preparation, and the spare shader
buffer through `ClientBridge.geometry`. Each builder snapshots view-visible
layers before incremental work; visible occupied neighbors remain available
for native adjacency. The complete document/NBT is not reduced to targets.
The prior five cyan world images qualify only that marker path.

Eight focused R22 tests cover native state identity, the three builders,
six neighbors and extra layers, renderer-coordinate rebasing, logical book
ownership, hidden/show restoration, public full/missing preparation and
initial occupancy. An explicit table regression preserves one independent
table body, zero native table actor and one logical book across all three
builders. Existing context/occupancy and book suites also pass. These tests
establish data flow; new lectern raster acceptance remains pending.

## Frozen small runtime package

`tools/prepare_lectern_product_r22.py` exported committed sources at
`2e960e69573a75abe49cb5da602fd08f36ee0e68`, copied only the two product files
for this correction, and added the previously successful native authored-book
loot fixture. Other worktree changes were excluded. The v1 preparation is
preserved; v2 narrows actor copying to lecterns. The v2 project has 3,153 files,
four automatic reload flags false, and source digest:

```
89fe6bb038d504d4722ad306997e759cb0add37ec9f81b0abb2a0304094f9af6
```

`tools/probe_lectern_product_r22.py` reuses the successful real north-facing
lectern inventory placement, native book use and attached camera. It checks
the complete client/server title, author and two authored pages before
building a single logical document. It requests the existing default book
profile without assigning a candidate profile or overriding ownership flags.

The planned twelve actual originals are native empty/authored, full, missing,
actual occupied/unoccupied, hidden/shown, actual editor Scene full/hidden/shown,
and full with upper/side logical neighbors. World captures retain the native
attached camera. UI captures use the actual workspace and its normal Scene
controls. Active native receipts must put exactly one selected lectern outside
packed context; receipts cannot replace pixel review. The native authored
reference must be visibly usable before book appearance is adjudicated.

No additional cardinal or powered matrix is included. Earlier body-only
cardinal observations remain evidence for their own source/camera bundle.
This package does not transfer their qualification to all book/Scene views.

Acquisition has a ten-minute host boundary, 20-second RPC timeout, canonical
commit at least 6 GiB and fewer than 200,000 owned handles. OPENBLAS is set to
one thread before imports. The launch adapter requires root scheduling,
total effective live MC below five, the live owner-bound assertion watcher
through 13:30, fixed noactivation binaries and both exact process handles
retained before capture. There is no desktop input, activation or resize.

Preparation and fifteen templates have passed offline verification. There has
been no R22 Book runtime launch yet. After root grants the slot:

```powershell
python -B -X utf8 tools/launch_lectern_product_r22.py launch --scheduled-by-root
python -B -X utf8 tools/probe_lectern_product_r22.py run --session ASSIGNED_SESSION --capture-exe .runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe --output .runtime/lectern-product-r22-v2/runtime
```

Expected window is approximately 8–12 minutes; reserve 20 minutes including
native review, full restoration, one ordinary close, actual exact exits and
metadata finalization. Ordinary close may time out. It has no guaranteed
finite process-exit bound and must not trigger force or a repeated experiment.
