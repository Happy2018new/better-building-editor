# Terrain and Liquid Occupancy Publication

## Contract

A missing-only occupancy refresh keeps the previous terrain bank and liquid
models published until both candidates are ready for the same detached
occupancy snapshot. Liquid planning uses the complete immutable logical
document, including neighbors and extra layers. The target occupancy snapshot
is copied independently from subsequent client reads.

The existing `LiquidProjection`, `WorldLiquidRenderer`, `ProjectionOccupancy`,
and `OccupancyShader` owners perform four stages:

1. Prepare hidden models within the existing planning and creation budgets.
2. Wait for native model settling and the terrain resource warmup.
3. Attempt terrain overlay/selector and liquid incoming/old visibility writes.
4. Finalize both published descriptors and caches, then retire obsolete models.

Deferred liquid readiness does not call independent promotion or release the
old active models. A revision identifies the liquid candidate; a superseded
revision cannot publish its associated terrain snapshot. The paired occupancy
refresh retains `pending_model`, its snapshot, and in-flight `after_build`
changes while waiting. Changes observed during preparation transfer to the
next refresh after publication.

## Failure and Lifecycle

Every attempted publication write is journaled before the native call. This
includes a setter that changes native state before returning `False` or
raising, and a new native overlay attachment that partially succeeds. Cache
updates do not serve as a rollback journal: recovery forces the previous
payload or visibility even when the success cache already contains that value.

A failed switch restores both surfaces. Failed recovery entries remain with
their existing owners, and stationary follow, another occupancy switch, manual
rebuild, and opacity publication wait for recovery. After successful recovery,
the failed automatic refresh remains latched for explicit update. Closing
transfers actors to the existing terrain retirement owner and active/staging
free models to the existing liquid cleanup owner. Failed native destruction
continues to count toward ownership and allocation limits.

Standalone liquid opacity writes use the same retained recovery journal, even
when no occupancy pair is pending. Follow, opacity, biome updates, manual
preparation, and independent liquid advance wait for that recovery; stationary
frame updates retry it. An idle terrain publication journal preserves existing
overlay restoration so this guard does not bypass legacy follow recovery.

Initial/manual world preparation binds the new terrain actor hidden and waits
for liquid readiness before publishing. Initially empty missing-only
projections register a later actor before delayed binding; that actor remains
unpublished while liquid preparation is pending. Stop, dimension change, and
manual replacement invalidate stale tracker work and close its liquid owner.

The default production liquid profile remains absent. No native acceptance
gate, texture/UV mapping, shader asset, or profile activation changed.

## Host Validation

Focused suites run from `codex/r12-paired-projection`, based on integrated
retirement/follow commit `87fb442`:

| Suite | Passing Tests |
| --- | ---: |
| `test_projection_pair.py` | 20 |
| `test_liquid_projection.py` | 18 |
| `test_liquid_render.py` | 35 |
| `test_bridge.py` | 53 |
| `test_occupancy_review.py` | 26 |
| `test_projection_follow_transaction.py` | 13 |
| `test_projection_retirement.py` | 7 |
| `test_occupancy_neighbor_context.py` | 8 |
| `test_render_context.py` | 14 |
| `test_occupancy_initial.py` | 4 |
| `test_liquid_profile.py` | 8 |
| `test_liquid_viewport.py` | 19 |

The pair suite includes synchronous provider rejection; asynchronous provider,
model-map, create, bounds, scale, rotation, position and uniform failure;
first/middle/last overlay and liquid show/hide failures; selector failure;
both false and exception results after native mutation; rollback failure and
retry; hidden new overlays and partial attachment; retirement budget rejection;
reused/empty liquid groups; successful publication cache observers; changes
during settling; superseded candidates; initial empty projections; live opacity;
planning cancellation; place/remove cancellation; and shutdown during recovery.
The late actor timer also carries a local cancellation token so an older
callback cannot revive a discarded snapshot during manual replacement.
Manual replacement tests verify that a new liquid visibility write can mutate
and throw while the old pair remains owned, and that retirement SDK callbacks
observe the complete new generation after successful finalization.
Standalone opacity tests cover missing-only and ordinary projection, mutation
before false or exception, failed rollback, blocked public controls, and
stationary frame recovery without a pending occupancy pair.

Publication observers compare copied descriptors, terrain uniform/visibility
caches, liquid model IDs/group payloads/visibility caches, occupancy snapshots,
and commit counters during native calls. They verify that the public state
remains the old pair until all publication writes succeed.

The liquid owner retains `2 * max_groups` accounting including retired models,
eight creations per advance, masked staging, and its settling requirements.
The terrain owner retains the two-pool retirement containment documented in
`PROJECTION_RETIREMENT_R12.md`. No world-writing API or native game operation
was invoked for this change.

Scoped MOD review parsed nine matching files without a parse failure. The
advisories are existing long receive/capture/initial-occupancy functions,
geometry arguments, existing broad follow/publication exception handling, and
the follow function crossing the length threshold after the recovery guard.
`git diff --check` passed.

Independent scoped source review found no remaining blocker. It checked forced
rollback and retained failures, standalone opacity recovery containment, idle
overlay restoration compatibility, Python-only finalization between pair cache
and descriptor publication, and preservation of follow and retirement owners.

Host adapters prove call order, ownership, cache publication, cancellation,
and retry behavior. They do not prove that native render threads display both
surfaces in the same frame, that hidden staging has no visual transient, or
that the currently gated liquid material/UV profile is visually correct.
Those remain separate native acceptance requirements.
