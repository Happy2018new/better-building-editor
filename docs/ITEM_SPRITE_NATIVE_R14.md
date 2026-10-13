# Item Sprite Native Acceptance, Round 14

Current status: **pending**. No item pixels have been accepted and the
production profile remains disabled. A successful model allocation or an
offline resource check is not treated as visible acceptance.

## First Background Launch

- Source: `cb04f900`, including private item integration `71d0b7c7` and bounded
  high precision glint phase `70586411`.
- Owner: `item-product-r14-v1`; session
  `835b8b01575148c384a47cd385208848`.
- Approved noactivation DLL SHA-256:
  `04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93`.
- MCDK SHA-256:
  `b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9`.
- The game exited before gameplay IPC binding. Managed discovery reported
  `Owned game creation identity changed; refusing to bind`.
- Windows Application Error at 2026-10-13 19:12:28 Asia/Shanghai associates the
  owned PID 35464 with `Minecraft.Windows.exe`, exception `0xc0000005`, offset
  `0x803a90`. Another startup at 19:10:37 reported the same offset; that is a
  clue for shared startup diagnosis, not proof of the root cause.
- No assertion dialog remained after cleanup. The observed foreground stayed
  on the user's application. There was no activation or foreground fallback.
- Exact owned game and MCDK identities were both absent after cleanup. The
  temporary worktree config was removed only after its fingerprint matched.
- Elapsed time: 34.51 seconds. No reliable editor/world pixels were obtained.

Raw evidence is preserved locally under `.runtime/item-product-r14-v1/` and the
managed session directory. The original manifest contains a temporary session
token; do not publish it verbatim. Runner `1ef222af` removes tokens and window
titles from future JSON exports. No automatic identical retry was attempted.

## Remaining Matrix

The public `test.entities.item_contents` blueprint supplies observed native
ordinary, enchanted and empty frame/glow-frame data. The prepared runner checks
actual Scene controls, three temporal compositor frames, editor removal and
undo. A follow-up must separately accept world full/missing filtering, depth,
cutaway, opacity and cleanup. Shelf filled-slot NBT remains unobserved.

Offline integration verification: **184 tests pass**, including 15 item
plan/resource/lifecycle tests and seven joint publication tests. Native failure
does not promote those tests into editor or world rendering acceptance.

## Prospective Pixel Scoring

The prepared item runner now freezes behavior/resource files, host tools,
versioned item source specifications and SDK scripts immediately before launch,
then verifies they remain identical afterward. Editor captures record actual
native PaperDoll global positions, sizes, applied poses and model IDs before
and after each image. World captures retain expected and observed camera
position, rotation, viewport and FOV. Changed source, camera, layout or capture
identity cannot qualify a pixel measurement.

The ordinary public `test.entities.item_contents` blueprint supplies the exact
source association. Three temporal frames are paired with an item-only hidden
control: editor surfaces and world free-model item uniforms are muted and
restored without changing the document, block geometry or source NBT. Empty
frame controls are retained. No inventory or item RPC is added.

`tools/analyze_item_sprite_product.py` projects the opaque versioned bitmap at
the declared support plane through actual editor controls. It scores ordinary
and enchanted silhouettes independently, ordinary/empty temporal stability and
animated enchanted pixels confined to the same silhouette. World scoring also
requires an independent camera calibration matching the captured viewport and
reported FOV; using a reported FOV as an assumed vertical FOV is not accepted.
The calibration file must retain three passed native stone views, their fixed
silhouette metrics and strict owner-bound captures, and its bytes must match
the recorded hash. A scalar FOV without that independent evidence is rejected.
Thresholds are fixed in the analyzer before native capture. Eight offline tests
exercise correct synthetic controls and reject absent/displaced bodies, extra
nearby geometry, frozen glint, ordinary animation, escaped highlight and layout
drift. Synthetic fixtures are not native evidence.

Prepared commands, to be run only after shared startup clearance:

```powershell
python -X utf8 tools/run_item_sprite_product.py --run-id fresh --world
python -X utf8 tools/analyze_item_sprite_product.py .runtime/item-product-r14-fresh/report.json .runtime/item-product-r14-fresh/pixels.json
```

The analyzer exits nonzero when a requested route is unscored or its measured
body/highlight controls fail. Its `production_qualified` and
`native_glint_accepted` fields stay false. All orientations, depth, opacity,
item replacement, shelf slot schemas and other item families remain separate
pending acceptance. Cutaway, erase/undo and genuine missing-world occupancy
captures are retained by the runner but are not promoted into scored gates by
these initial silhouette/highlight measurements.

World runs now obtain the independent stone calibration in the same owned
session before opening the item blueprint. The three views use guarded native
captures and the existing stone-hull fit. Failed calibration is retained and
reported as unscored world pixels while editor controls still run. Calibration
cleanup failure aborts the run. The item fixture identity stays a string; its
separate blueprint result is retained as `fixture_state`.

Fresh owned `item-product-r14-v2` passed all three stone views at effective
vertical FOV **66.6 degrees**, 1994x1105 physical pixels and 499x277 engine units.
It then stopped before item pixels because the runner wrongly required item
controls on the testing page, which has no item Scene. That harness gate is now
limited to actual preview phases. The game and supervisor were exactly cleaned;
no item body or glint acceptance is inferred from the camera-only result.

Fresh `item-product-r14-v3` completed all planned capture phases with unchanged
sources, valid guarded receipts, same-session calibration and exact cleanup.
Both editor and world body/highlight gates failed: all four expected content
silhouettes had zero observed item pixels. Empty controls remained stable.
Actual game `mcdk.log` reported `C1503: undefined variable PROJ` when compiling
the item fragment shader; the MCP latest-error endpoint returned no errors.
The generator now includes the installed `uniformWorldConstants.h`, which
declares `PROJ`, and owned-run reports explicitly collect this native compiler
failure family. No item plane, source bitmap or pixel threshold changed.

Fresh `item-product-r14-v4` completed and restored without native item shader
errors. The swords were visibly present. Editor and world moving-highlight
gates passed for both ordinary frame families: 37--110 moving enchanted pixels,
zero ordinary-item motion and stable empty controls. Body silhouette gates
remained failed. Original inclusive-polygon replay and a corrected independent
pixel-center/nearest-texel replay are both retained; no threshold was lowered.
The replay reports separate launch-analyzer and current-analyzer hashes, while
all runtime/resource inputs must still equal the frozen launch snapshot.

The user-requested closeup run derives ordinary, enchanted and empty frame cells
plus their supports from the public blueprint, using `cell.rebase` for the
temporary document. It does not edit public source resources or payloads.
Each route obtains twenty fresh native frames separated by at least 0.4s,
plus an item-only hidden control, editor cutaway/restore and genuine world
occupancy/restore. The prospective editor pose and independent world near
camera are declared before capture; actual poses, QPC and host times remain
in each row. Minimum intended body extent is 48 physical pixels. Near-scene
animation qualification remains separate from failed remote body geometry.

User-authorized foreground observation is recorded explicitly; the runner does
not activate or resize a game. Shared capture schema 3 must retain owner identity,
guarded noactivation and fresh native frame checks even when the user switches
to the game. An unreliable capture is reported as a failure, with no activation
fallback. Native launches are still on hold pending the shared full-pack startup
diagnosis; no new item pixels were obtained while preparing these tools.

## Enlarged Animation V5

Frozen `item-product-r14-v5`, source `d5015c38`, completed all ordinary captures
and 46 closeup captures with exact owned-game cleanup and no native item shader
errors. Actual near swords measure 56x56 physical pixels in the editor and
53--55 by 53 pixels in world projection. Native QPC spans are 29.847 seconds
and 35.048 seconds. Ordinary swords and empty-frame controls have zero temporal
motion. Every independently observed enchanted sword pixel changes over the
sequence; movement stays inside the observed silhouette. Editor near body
positions pass; world near ordinary sword still fails the fixed body gate.
The original distant editor/world body gates also still fail. These results
do not qualify production or establish vanilla glint parity.

`analyze_item_sprite_closeup.py` writes fixed-crop GIFs from the original native
frames at native QPC intervals rounded to GIF's 10ms granularity. It never
resizes, enhances, synthesizes or paints on those frames. Raw PNGs and receipts
remain separate. World crosshair occludes part of the center sword and remains
visible; it is not erased. Cutaway can release model IDs and restoration can
allocate new IDs, so transition controls validate unchanged camera while
positive/hidden/temporal controls require exact native model layout equality.

Only the two explicitly named offline analyzer files may differ at replay;
launch and replay hashes are retained. Every runtime, shader, texture, pose,
capture helper and bootstrap input still requires its original frozen hash.

## Prospective Native Glint Comparison

The next private test will place actual `minecraft:frame` blocks and their stone
supports at previously confirmed-air coordinates. SDK server
`CreateBlockEntity(level).SetFrameItem(pos, dimension, itemDict)` supports
`enchantData`; `GetFrameItem` reads it back, and `SetFrameRotation` sets the
original rotation in degrees. `CreateBlockInfo(level).GetBlockEntityData`
supplies independently read typed native `Item` NBT. A diagnostic actor bound
to a free model is never called an actual frame block. The selected public
ordinary/enchanted pair is diamond sword already; any variant must explicitly
record its public source, desired identity and actual typed readback.

Before collecting that run, comparison uses these fixed rules: each route
retains ordinary, enchanted and empty controls for at least seven seconds;
the sword's physical bounding sides must both be at least 48 pixels. Use the
same world camera, coordinates, frame face, item rotation, fixed environment,
and opaque full/missing projection. A content-only hidden control establishes
the observed sword mask independently of modeled geometry. For each body,
report native frame intervals, maximum RGB temporal range, luma temporal range,
the fraction whose temporal RGB range exceeds 2 and 8, per-step highlight
centroid travel divided by body width and real elapsed seconds, and ordinary
and empty negative motion. The enchanted control must satisfy the existing
moving-highlight gate (at least four moving pixels, at least 4% of body pixels,
at most 5% movement outside its silhouette); ordinary and empty controls allow
at most three moving pixels. Compare those measurements descriptively against
the actual frame. A stronger visual match is not claimed merely because a
temporal gate passes. Different native lighting, projected material response,
screen perspective or crosshair occlusion must be stated; no fitted offsets,
postcapture brightness normalization or adjusted acceptance thresholds.

Every changed native block is tracked before mutation and restored to its
confirmed original air state. The test uses the existing private debugger
entry and adds no production RPC or authorization surface.
