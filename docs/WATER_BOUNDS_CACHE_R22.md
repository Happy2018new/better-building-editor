# R22 water: bounded delivery and remaining invisibility causes

The deliverable is the existing product-only world bounds correction and
stable UI distance-request cache, checked against a new cold-loaded product
owner. Product water remains unqualified and disabled. This round does not
claim that all invisible water has one cause or that the historical elapsed
time failures have been repaired.

## What the evidence actually establishes

| Observation | Supported cause or limit | Current implementation | Smallest useful verification |
| --- | --- | --- | --- |
| R18 world water at `(63,-61,3)` has 117,941 wet-minus-hidden pixels at default +/-4, zero at +/-2, and 117,941 after restoring +/-4 | FreeModel culling bounds are too small for this exact fixture | `ProductWorldLiquidRenderer.BOUNDING_BOX` is +/-4; shared owners retain +/-2 | Cold product owner, same native IDs and camera, default4 / live2 / restored4 wet/hidden pairs, six PNGs |
| Editor v6 has no water under `RenderSkeletonModel`, water under same-model/same-pose `RenderEntity`, and no water after S restoration | Reversible native API/state behavior in that instance; underlying state cause is unknown | No workaround has been enabled | Reproduce an actually invisible S baseline first, then same-doll S/E/S with matched hidden control; do not infer a fix from an already visible baseline |
| R21 S/SE/S/SE/S all have 96,436 wet-minus-hidden pixels; candidate versus baseline difference is zero | Baseline already has signal; experiment is inconclusive for invisible-state repair | `repair_accepted=False` | Do not repeat that baseline as a repair acceptance test |
| V7 first captures show a Minecraft loading screen despite SDK ready state | Capture/startup readiness was insufficient for visual acceptance | Loading-screen captures are preserved and rejected | Verify real scene pixels and stable camera before interpreting water absence |
| Mixed-copy `b.project()` list-assignment failure disappeared after complete Python closure synchronization | No full original traceback; synchronization success does not establish root cause | New runs freeze a complete closure | Verify frozen file hashes before launch and after restoration |
| Stable request A/B performs source validation 240 times versus zero; both sides submit zero native models | Cache avoids repeated source validation on stable frames only | R21 cache remains in `LiquidControls._displayed` | Cold-loaded cache source/readback and existing focused tests; no new stable-frame timing claim |

The native API documentation exposes `SetFreeModelBoundingBox`, with a boolean
success result and explicit view-frustum culling semantics. The repository
does not have a documented `GetFreeModelBoundingBox`. A class constant and
frozen `_create` source are not a native bounds getter. The new report must
distinguish those bindings from live setter calls and reversible pixels.

## Historical timing remains unresolved

| Original maximum | Owner and fixture | Recorded child/context evidence |
| ---: | --- | --- |
| 168.999910 ms | `LiquidProjection.advance`, flow west | Same report's `_create` maximum is 16.999960 ms; the long parent call is not localized |
| 230.000019 ms | `LiquidPreview.advance`, pool | Logical plan construction, not a native model submission timer |
| 434.999943 ms | `LiquidControls.update`, flow east | Four requested/registered groups; nested render-pose and payload maxima are about 1 ms |
| 370.000124 ms | `LiquidControls.update`, wet slab | Requested groups and registry entries are both zero |

These Windows embedded-Python clocks measure elapsed time, which may include
scheduling delays. Thread CPU measurements were unavailable. A lower model
submission count cannot be presented as the cause or fix of these samples.
The raw failures in `water-ui-state-r20-v1` and references in
`water-timing-r21-v1` remain authoritative historical failures.

## Optional cold-request pacing candidate

`LiquidControls` accepts `request_starts_per_frame=None`; the existing default
is unchanged. The water Scene constructor can read an explicit
`profile.ui_request_starts_per_frame`. No current product profile sets it.
With a positive opt-in budget, only the start of a new shape upload consumes
a token. Existing pending uploads still settle and old fronts still receive
pose and appearance updates. The traversal rotates after each admitted start
so a continuously superseded first group does not starve later groups.
Clipping, deletion, error latches, retries and teardown retain existing paths.

This is an offline candidate, not an enabled performance fix and not part of
the six-image bounds runtime. It does not limit live orbit submissions, all
native uniform/layout calls, or the duration of one synchronous native call.
The total number of cold submissions is unchanged; total time to the complete
water surface may increase. Any future experiment must report per-frame actual
submissions, cold first/complete-water latency and old-front retention together.

Eight new tests exercise nonzero real renderer starts over eight groups,
bounded completion, unchanged default behavior, old-front replacement,
starvation resistance, failure latching, clipping/deletion, live pose updates
and invalid budgets. The targeted owner/renderer/item adapter suite has 106
passing tests. Structural review found no renderer issue; viewport advisory
findings are the existing long update function and six-argument `group_view`.

## Planned six-image runtime

One fresh cold session uses a complete frozen project and all four automatic
reload flags false. Verify the product projection and renderer types, original
source/cache binding, eight unique model IDs, zero staging/retired models,
fixed origin and camera, and actual native uniforms. Capture wet and hidden
controls for default4, bounds2, restored4, changing only live model bounds.
Keep the native 1994x1105 dimensions and prior R18 ROI `(700,430,1300,1000)`;
reject viewport/camera/source drift instead of silently rescaling.

There are no fixed-alpha repeats, player travel, entity-distance changes,
NBT reads, production admission or new cold-budget experiments in this run.
Runtime and WGC require an explicit scheduling grant. The launch gate is
9 GiB available commit, runtime gate 6 GiB, at most five live games, bound
13:30 assertion-watcher coverage, no agent activation, one normal close and
an exact-process exit observer. A nonzero exit remains a failure even when
metadata finalization succeeds. Expected window: approximately 6–10 minutes,
including startup, six captures, restoration and observed closure; normal
closure cannot be guaranteed to finish within a fixed timeout.
