# Wet Actor Offline Diagnosis R6

The preserved `wet-actor-ancestry-cold-r5.json` remains failed and unchanged.
This host-only diagnosis and actor-mask correction do not constitute visual
acceptance. No production code, camera, pixel position, threshold or capture
was changed.

## Confirmed Actor-Check Defect

The actor RGB heuristic previously searched the union of the fixed keep and
occupied regions. Brown native fence pixels in the keep region supplied a
false actor positive control. In `pot_fence_context`, 2917 of 2925 actor-color
pixels are in the keep region; in `sign_fence_context`, 2880 of 2888 are there.
Both occupied regions contain only eight actor-color pixels. Isolated pot
and sign cases have zero observable native actor-color pixels.

`component_checks()` now intersects only the actor mask with the existing
occupied region. Water masks and all existing limits retain their behavior.
The six focused offline tests include a fence-only negative control, water
positive control, occupied-region actor positive control, missing-component
checks and invalid native-baseline rejection.

## Remaining Rendering Failure

Each adjacent-water case has 41768 native water pixels in its fixed keep
region, with zero projection contribution there in context, dynamic and
initial stages. At original pot pixel `(1161,574)`, native RGB is
`(101,140,175)` while empty, context shown and context hidden are all
`(171,210,255)`. The water is absent from this projection signal, rather than
merely recolored, and the fixed region includes the native water correctly.

Frozen pure-Python context preparation retains water in geometry-input
batches: adjacent cases contain four common water entries, fence cases two
common and two extra entries, and isolated cases one common entry. These
preserved images cannot establish whether native tessellation omits liquid
geometry or the render/shader path hides it. No production fix is proven.

The next live investigation needs a valid native dry actor positive control
and minimal plain-water geometry/render isolation. It must preserve the
original failures and use new evidence for any acceptance decision.

## Preserved Evidence

Instance artifacts are under
`C:/Users/Happy2018new/.pyreact-debug/instances/54a2b4d9ebe34eabad28b6e9cd90b30d/artifacts/`.
The separate `wet-actor-offline-r6` directory contains `diagnostic.json`,
`fixed-roi-review-sheet.png`, `diagnose_wet_actor_r5.py` and `frozen-source/`.
The diagnosis records 50 protected input fingerprints before and after and
asserts that all remain unchanged; `accepted_visual_evidence` is false.

- Original report SHA-256: `12d045d82242b6576b656a87f92e310693d47e7e6b6c11384e67a00b33cbd509`.
- Diagnostic JSON SHA-256: `b3dadf24332e67ac6f7627ec98641432a6936488a7f68f5236efc9732b746778`.
- Review sheet SHA-256: `5d83d90431fb391edada0a53d134b89951bb467ba778372492410a0e7712d783`.

Relevant integration production sources match the frozen source archive in
normalized UTF-8/LF content. The checker differs in raw line endings only
before this correction. Integration was inspected read-only.
