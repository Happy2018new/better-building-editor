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

User-authorized foreground observation is recorded explicitly; the runner does
not activate or resize a game. Shared capture schema 3 must retain owner identity,
guarded noactivation and fresh native frame checks even when the user switches
to the game. An unreliable capture is reported as a failure, with no activation
fallback. Native launches are still on hold pending the shared full-pack startup
diagnosis; no new item pixels were obtained while preparing these tools.
