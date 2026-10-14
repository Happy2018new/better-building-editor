# Round 16 Water Acceptance

Custom water remains disabled in production until every schema 2 gate passes.
These runs validate the declared `java_snapshot_water_v1` style, not exact
vanilla colors, simulation or future-engine parity.

## Retained Runs

| Run | Launch Contract | Result |
| --- | --- | --- |
| `visibility.json` | `e39338e09713c4da8faaa862973037594fc5b41e0e1f53e8b3e7c2ffff3b1a52` | Completed and restored; 18 section controls and 56 world cleanup records. |
| `near-visibility-v2.json` | `11a9b1c5a04b548b2f0b5115265903882f8f3a79f872c283c6dd69cdc08bff71` | Completed and restored; 114 rows and 180 captures. Editor custom water is visually absent; production acceptance fails. |
| `editor-reopen-v2.json` | Same v2 launch | Completed and restored; reopening the editor does not restore visible water. |
| `native-uniforms-v2-retry.json` | Same v2 live game | Actual native Uniform 1 through 4 agree with all eight visible control records. Reapplying their values leaves the editor failure unchanged. |
| `clean-editor-pool-v4.json` | `901e20cb4d0abe8c70fdb8ba639e37d29227aedae417692ad4449e252b747fe0` | Clean startup without an assertion, using unchanged water shaders. Editor water is visible, 96,000 independent water pixels disappear under the section control, and restoration has zero RGB error. |
| `acceptance-frozen-v4.json` | Same v4 launch | Incomplete: the next capture was blocked at 250,457 native handles by the predeclared 250,000 limit. Restoration completed. This report cannot qualify any gate. |
| `acceptance-editor-v5.json` | `03b39a97c6d3722a734060b3093b8d44c3f90a827759a57f418b4aceb03fd71e` | Rejected before SDK mutation: importing the legacy screenshot wrapper replaced shared ctypes `GetClientRect` argument types. |
| `acceptance-editor-v6.json` | `54035aec34fe6b2f5709d033b45fad277f0cc1f6d64e04b9900fee5d8bb04a7a` | Incomplete: the owned game/MCDK exited after 49 rows and 106 native-assertion checks. The last dispatch returned no value and cleanup could not run. No retry or qualification was performed. |
| `editor-core-v7.json` | `56d72d5f0c76c23433c13a7efcde751c9ad74d443dc623cfcf0efac6277d4b4d` | Completed and restored in 190 seconds. All ten applicable independent-water section controls and both opaque side-UV tests pass. Original overall geometry/alpha analysis fails because the falling fixture is cropped and alpha baseline native IDs predate section reconstruction. |
| `editor-neighbors-v7.json` | Same v7 launch | Completed and restored in 213 seconds. Both nested native methods stay at or below 1.01 ms. Slab/stair front-on alpha regions have no eligible water-covered body pixels; a new oblique-top control is required. |
| `editor-core-v9.json` | `b0e1e5e505430e9ed25f2890981131c796452f712c2f20d980b6277729e47662` | Completed and restored in 190 seconds. Editor geometry, ten independent section controls, fence transparency/alpha and both side-UV controls pass. Maximum owner call is 8 ms. |
| `editor-neighbors-v9.json` | Same v9 launch | Completed and restored in 254 seconds. All eight section controls and pane/slab/stair alpha controls pass; partial-solid depth geometry passes. Maximum owner call is 8 ms. |
| `full-core-v10.json`, `full-neighbors-v10.json` | Same v9 launch | Completed and restored; world visibility, geometry, alpha and side-UV fail. Camera is near the fixture but the actual player is 66 blocks below it. |
| `world-uniforms-v10-retry.json` | Same v9 launch | Actual world uniforms agree with cached values, and reapplying them does not restore visible water. Diagnostic only. |
| `world-near-player-v11.json` | Same v9 launch | Completed and restored. Moving only the unchanged pool projection/camera to the original player's vicinity restores clearly visible transparent top/south/east water. No shader or uniform changes. Diagnostic only. |
| `full-core-v12.json` | `b5db1e7e0769e6e42759648c29b9a0cb5c7bddbbc38b5019f953f691a0fd2b2f` | Aborted before its first capture at 271,180 native handles; original player foot and registered platform restore successfully. Failed evidence, not qualification. |
| `full-core-v14.json` | Same v12 launch | Completed/restored in 225.8 seconds. Core geometry/transparency/visibility pass; side UV and one cold CPU maximum fail. |
| `full-neighbors-v15.json` | Same v12 launch | Completed/restored in 246.2 seconds. All neighbor geometry, three body alpha controls and eight section controls pass; measured world owner maximum 87 ms. |
| `full-core-v16.json` | `f087480e241a7036ad0f4c07eb683c80ea2eb3b8258bc21a522d39952fda7cb7` | Completed/restored in 224.8 seconds. Core geometry/alpha/visibility pass. Pool-only camera scale 0.25 crops physical side samples outside the viewport; UV fails and is not reusable evidence. Maximum world advance is 103 ms, including 96 ms in one native model construction. |

`camera.json` and `camera-v2-wgc.json` independently calibrate the exact bound
session with three stone silhouettes. Both pass and restore, with effective
vertical FOV 66.5 despite the engine reporting 60. No activation or resizing was
performed. Capture receipts permit user initiated foreground observation while
prohibiting agent activation.

The v2 startup encountered the known vanilla `DisabledSkinScreenController`
assertion. `startup-assertion-v2.json` records the exact owned process identity,
dialog and owner-bound `WM_COMMAND IDIGNORE` recovery. This is a startup
limitation, separate from render acceptance. The first v2 calibration attempt
also selected a missing legacy capture helper; its failed report is preserved.
The later explicit WGC calibration is the valid measurement.

The next same-code startup (`water-product-r16-v3`, PID 36200) also encountered
that assertion and was stopped without acceptance. Its frozen inputs are
`launch-inputs-v3.json`; the complete archive is retained locally. The next
startup, `water-product-r16-v4`, PID 29988, uses those same frozen inputs and
has no startup assertion. The pool is visible again without changing its
shader alpha, depth or clipping. This establishes that the earlier failure is
not reproduced by the clean baseline, but does not prove the skin popup caused
it. Assertion-affected runs remain diagnostics, not qualification evidence.

## Metrics And Corrections

- `visibility-analysis.json` records an incomplete first replay. It is rejected.
- `visibility-analysis-v2.json` compared transparent side RGB directly across
  differing stone/sky backdrops. It is rejected.
- `visibility-analysis-v3.json` removes the paired dry backdrop at the already
  accepted alpha 0.45. Editor side repetition passes, but distant world side
  correlations fail the unchanged 0.85 threshold.
- `near-visibility-analysis-v2.json` accepts capture identity and source
  stability, but rejects side repetition and overall product acceptance. Its
  initial section metric could count disappearance of overlapping native
  bodies; the analyzer has subsequently been tightened to require wet/dry
  evidence of visible water before counting hidden pixels. The old result is
  retained rather than silently rewritten.
- CPU measurements in both completed matrix runs pass p95 5 ms, p99 16.7 ms
  and maximum 100 ms limits. They exclude IPC and screenshots and do not prove
  GPU frame rate. The maximum observed isolated model count is eight, not the
  configured capacity of 256.
- `near-visibility-analysis-v2-water-only.json` applies the corrected independent
  water eligibility rule. All eleven editor cases have zero independently
  visible water pixels and are rejected; native body disappearance cannot pass.
- `clean-editor-pool-analysis-v4.json` passes editor visibility and opaque side
  continuity: south correlation 0.964 / RMSE 2.59 and east 0.983 / RMSE 1.82.
  All mirrored, phase-shifted and constant negative controls fail. This narrow
  editor-only run is not full acceptance: world lifecycle samples are absent,
  and one measured `LiquidControls.update` call takes 128 ms, above the unchanged
  maximum 100 ms limit, although p95 and p99 are approximately 1 ms.

The side analyzer now supports an explicit alpha-one frozen control, isolating
UV repetition from background motion and layered transparency. Default alpha
and underwater-body visibility require their own controls. Mirrors, wrong
texture phase, constant images, missing timing samples and hidden native bodies
have rejection tests.

The v5 host preflight failure was corrected by making `check_native_dialogs`
use the skill's existing `_window` bindings instead of importing the legacy
capture wrapper. A Windows subprocess regression verifies that importing the
water probe preserves those bindings and actual window enumeration succeeds.
The v6 termination cause remains unknown; its MCP log records shutdown at
20:28:56 and complete exit at 20:29:05, rather than a completed test.

The long v4 run measured a maximum 180 ms `LiquidControls.update` call. The
100 ms limit remains unchanged. Later runs record nested `_render_pose` and
`_payload` timings and bounded outlier details to distinguish native cold
construction from steady updates. Short completed batches may be combined
only when their exact `(display route, public case)` coverage is complete and
nonduplicated; failed batches and partial rows are never reused.

The v7 captures exposed two host-control defects. The 460% falling view crops
its top at the ordinary Scene viewport boundary; its complete control now uses
300%. Alpha baselines must be sampled after section reconstruction and before
changing opacity, because reconstruction legitimately allocates new native IDs.
The probe now also restores the selected editor layer after its section control.
Neither change modifies production geometry, shaders or numerical limits.

The completed v9 batches exercise the corrected editor controls. The slab and
stair view exposes their wood top through water; each has 327 eligible body
pixels and 524 eligible rear pixels. Fence, pane, slab and stair opacity controls
use fixed geometry, reject invisible endpoints, and pass the unchanged bounds.

The v10/v11 world comparison exposes a distance/context boundary: native entity
projection remains visible while distant free-model water is invisible, and
moving the camera alone is insufficient. The cases use identical sources and
uniforms in separate clean instances. They support player-relative culling or
world-loading context as the cause, but do not establish an exact distance
threshold or a same-instance distance scan.
World acceptance now registers an initially empty stone platform, moves the
server player near the elevated fixture, waits for client position replication,
then restores the exact original foot before clearing the registered region.
The qualification collector requires both replication and original-foot
restoration. This corrects the near-field test fixture; it does not resolve the
observed production FreeModel/native-entity distance mismatch.
`run_water_batch_r16.py` runs launch, calibration, bounded capture and
reclamation without idle gaps; the 250,000 handle ceiling is unchanged.

| Distance Diagnostic | Player Foot | Camera | Camera Target | First Configured FreeModel Center | Foot-to-Center Distance |
| --- | --- | --- | --- | --- | --- |
| v10 invisible water, native stone visible | `(0.5,-60,0.5)` | `(9.5,9,10.5)` | `(6.5,6.5,6.5)` | `(5,5,5)` | approximately 65.31 blocks |
| v11 visible water and stone | `(0.5,-60,0.5)` | `(9.5,-55,10.5)` | `(6.5,-57.5,6.5)` | `(5,-59,5)` | approximately 6.44 blocks |

Both use dimension zero, configured scale `(16,16,16)`, and the pool's unchanged
four logical water cells. The first anchors are respectively `(3,3,3)` and
`(3,-61,3)`. Center values come from the successful configured pose and renderer
calculation; this engine exposes no documented FreeModel position getter. Later
v14/v15 acceptance instead moves the actual foot to `(2.5,6,2.5)` while retaining
the elevated fixture. Those near-field passes cannot qualify far-field parity.

The v14 full core completes/restores in 225.8 seconds: ten independent section
controls, geometry, fence opacity, and all 26 lifecycle samples pass. Both opaque
pool-side controls fail the unchanged 0.85 correlation bound (south 0.814, east
0.683), and one `drop_north` cold world advance reaches 157 ms against the 100 ms
maximum. The v15 full neighbor batch completes/restores in 246.2 seconds: all
eight section controls, pane/slab/stair opacity and geometry pass. World advance
maximum is 87 ms. Neither narrow batch is full product admission.

The v16 closer pool view is rejected because physical sample coordinates leave
the native viewport. The side analyzer now explicitly rejects offscreen or
nonfinite coordinates instead of allowing interpolation to clamp to the edge;
an eight-test pixel suite includes that regression. The original failed replay
and the stricter `full-core-acceptance-v16-crop-guard.json` remain separate. The
v16 cold source call spends 96 ms in `WorldLiquidRenderer._create`, while the
enclosing advance reaches 103 ms. Both product runtime and 100 ms bound are
unchanged, so its CPU gate still fails.

`editor-neighbors-depth-analysis-v7.json` adds a depth-aware oracle for the
fixed public neighbor controls. It projects the known opaque stone, bottom-slab
and upright east-stair surfaces independently and removes water pixels that
those surfaces are nearer to the camera than. Transparent glass remains in the
pixel test. With unchanged thresholds, slab/stair/stone IoU is respectively
approximately 0.97/0.95/0.96 with two-pixel boundary error. Opposite-angle world
controls remain necessary; this replay does not qualify those missing routes.

## Remaining Work

1. Preserve the clean v4 baseline and reject assertion-affected startup runs.
   Editor water is visible without shader changes; the root cause of the earlier
   editor-only disappearance has not been established.
2. Complete all three routes, world opaque side controls, missing-projection
   partial-solid neighbors and opposite-angle separated-water controls; keep
   all existing numerical thresholds. Editor and full-neighbor opacity pass,
   while the v14 world side and one cold-call budget remain failed evidence.
3. Open the complete public water gallery through the ordinary editor.
4. Qualify the source/resource closure, then cold-start the ordinary default
   Session and verify editor, full projection, missing projection, biome and
   occupancy behavior without assigning a candidate profile.
5. Characterize and resolve or explicitly bound the observed FreeModel/native
   entity far-field visibility mismatch. Near-field fixture correction does
   not prove equal render distances or restore distant custom water.

Full captures, receipts and source archives remain locally available. Compact
review artifacts will be selected only after the final result is known.
