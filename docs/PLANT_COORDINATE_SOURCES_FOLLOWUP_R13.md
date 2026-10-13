# Plant coordinate source follow-up R13

This bounded offline follow-up did not recover a verifiable NEMC vanilla
plant random-offset algorithm or seed rule. There was no game launch,
production-profile change, screenshot fitting, AABB-centroid fitting or
new offset implementation. The exact documentation replies and source
fingerprints are retained in `tools/data/plant-coordinate-sources-r13.json`.

The Bedrock Wiki `minecraft:random_offset` component documentation says
custom-block offsets are based on world position and affect geometry,
selection and collision. Its axis configuration documents ranges and
steps. It does not give the integer coordinate hash, overflow/sign behavior,
world-seed dependency, vanilla poppy defaults or a promise that NEMC's
hardcoded vanilla flower path shares that implementation. This is a useful
source for a separately declared custom-block control, not authority to
copy a guessed Java algorithm into the NEMC renderer. Earlier R9 results
also found that the documented Netease custom-model random offset changed
visible placement without changing its unit-cube selection box; the
international custom-block component contract cannot override that actual
version-specific observation.

The installed NEMC 3.9 `blocks.json` was re-read and retains SHA256
`cb3aad2d0d012bfb63a462ec9a5d8af54128c8afc26d74ac6f4ae074c9d50faa`.
Its poppy entry contains only `textures: poppy` and `sound: grass`; fern
also lists its carried texture. The native atlas retains SHA256
`9ce3e389999a7aff19968a60fd21dad1811cf63ec3edd6afac0af0df649e212c`.
The installed vanilla RP models directory contains only `entity`, and the
vanilla BP blocks directory is absent. These assets do not declare the
hardcoded vanilla cross or its coordinate-seed algorithm. The earlier
definition/renderer investigation remains applicable: matching feature
files concern world generation, which is a different coordinate process.

A targeted text search in the provided `neomega-blocks` repository found
no matches for random-offset/position-random/coordinate-hash/getseed or
several common coordinate-hash constants. Its inspected `rt_hash/init.go`
loads block identity/state conversion indexes, and `convert.go` defines
block-to-ID conversion interfaces. Its runtime hash is not evidence of a
world-position rendering hash. This is a bounded search result, not a claim
that no useful algorithm can exist anywhere else.

The new four-coordinate control makes only these finite statements:
adjacent X/Z cells visibly differ, sampled positive/negative diagonal
coordinates look similar, and corresponding client/server clips reproduce
R9 relative values. Sign handling, dependence on world seed or biome,
the coordinate bit width, Y participation and mesh-pivot semantics remain
unproven. In particular, the similar two diagonal samples cannot establish
an absolute-value rule.

## Proposed independent holdout after a source contract exists

Before acquiring new images, freeze the exact source-derived candidate,
native cross geometry/UV authority, seed/sign/overflow semantics and output
predictions. Prefer an engine-supported random-offset component if it is
shown to share the required native behavior; otherwise a versioned native
implementation source is needed. Keep the production registry empty while
that authority is missing. API-derived exact-position diagnostic data must
stay diagnostic rather than becoming a universal production table.

Predeclare fresh target coordinates such as `(15,-48,3)`, `(16,-48,3)`,
`(-1,-48,3)`, `(0,-48,3)`, `(6,-48,-7)` and `(-7,-48,6)`. These separate
chunk-boundary, zero/sign and mixed-sign effects, and are disjoint from the
R13 native image coordinates. A future one-player private world must first
verify each target/support pair is loaded air in both layers; unavailable
terrain ends the control rather than changing the coordinate after seeing
results. The existing fixed relative camera, full stone-footprint coverage,
first-image retention, actual render/forward checks, before/after raw SDK
boxes and cleanup contract remain the control framework.

Only after freezing the candidate should its native/projection dry-plant
comparison run on these holdouts, using the unchanged .75/.75 precision/
recall and three-pixel tolerance. Failure must not trigger per-position
translation fitting. Two declared private worlds with seeds 0 and 1 can
separately test whether the proposed seed rule survives world changes;
state and camera controls stay equal. Seed/biome invariance must be tested
if the claimed source contract relies on it. Editor/full/missing-mode and
snow-height qualification remain later separate controls. This plan was
not executed and does not increase accepted production scope.
