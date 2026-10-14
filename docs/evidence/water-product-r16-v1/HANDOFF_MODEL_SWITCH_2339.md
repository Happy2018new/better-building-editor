# Water Model-Switch Handoff, 2026-10-14 23:39

Work stopped at the user's model-switch request. No commit or staging performed.

## Preserved Round 16 Result

`checkpoint-r16.json` preserves the five completed/restored batches covering
57/57 public case/route pairs under runtime closure
`62bc9ac06e810f5a9ac9cbf7dc663b82944083435ff7b3cdf4ad61b5224e51e7`.
Geometry, 12/12 fixed-body opacity controls, 54/54 independent section controls
and 108/108 world lifecycle samples pass. Production remains disabled.

World side UV, cold construction, distant visibility, animation across three
routes, biome, exact occupancy, reverse neighbors, public gallery and ordinary
cold-start default admission remain open.

## Unintegrated Water Construction Policy

New independent modules:

- `liquid_product_render.py`: subclass limits native creates to one per frame.
- `liquid_product_projection.py`: injects that renderer into existing
  `LiquidProjection`, preserving explicit renderer overrides.
- `liquid_product_profile.py`: declares `renderer_factory` and
  `projection_factory` hooks.
- `generate_liquid_product_owner_contract.py`: adds both modules to source list.
- `tests/test_liquid_product_render.py`: four focused ownership/policy tests.

Ten focused render/profile tests pass. A single native creation previously took
96 ms; this count limit cannot guarantee one native call is below 100 ms.

`liquid_projection.py` is byte-equivalent to its pre-change implementation.
`liquid_render.py` and its shared default of eight creates per frame are unchanged.
No `world_projection.py` integration was made. It currently instantiates the
shared owner directly, so the new profile hook is not yet used by ordinary world
projection. The proposed integration selects
`getattr(profile, 'projection_factory', LiquidProjection)` at that one entry.

Qualification impact: cauldron's implementation closure includes
`liquid_projection.py`; portal's recorded closure also includes
`world_projection.py`. The subclass avoids changing cauldron's shared owner.
Changing the world entry still requires portal re-verification. No qualified
hash was rebound. Water owner data has NOT been regenerated after these edits;
new water runtime evidence must bind a fresh closure rather than inherit old
35-file qualification.

## Distance Diagnostics

v18 was reclaimed after its idle handle count reached 549,234, over the unchanged
250,000 ceiling. No later v18 qualification capture was used.

v19 identity:

- Project `D:/bbe-r16-water-production`, owner `water-product-r16`.
- Game PID 48680, MCDK PID 35076, port 19354.
- Session `C:/Users/Happy2018new/.pyreact-debug/instances/9966378c03354934b8e607e3b6245e94/session.json`.
- Installed frozen inputs remain `launch-inputs-v16.json`, contract
  `f087480e241a7036ad0f4c07eb683c80ea2eb3b8258bc21a522d39952fda7cb7`.

Both same-instance diagnostics completed and restored state; screenshots were
actually viewed:

- `world-distance-v19-x3.json`, origin `(3,-61,3)`: water and stone visible.
- `world-distance-v19-x63.json`, origin `(63,-61,3)`: stone visible, water absent.

The player's foot was not moved and fixture height is identical. At the distant
camera, terrain is visibly outside loaded chunks. Thus these observations rule
out an exclusively vertical-height cause but still do not separate player-range
culling from chunk/world-loading context. They are diagnostics only.

`diagnose_water_world_r16.py` now supports independent x/y/z anchors.
The v19 ordinary batch did not start: a relative launch-input path resolved
against the isolated project rather than main repo. That failure was retained
in `horizontal-context-v19.log`. The host runner now resolves the path before
launching its child. This does not alter installed runtime or qualify the run.

## Side UV Follow-Up

`diagnose_water_texel_centers_r17.py` samples fixed texel-center physical points,
derived from the declared point-filter shader, without fitting texture phase.
Editor both sides and world south repeat exactly; world east remains failed
(v18 approximately -0.02 correlation). This is diagnostic only. Before changing
admission sampling, add an independent synthetic perspective texture oracle and
negative controls; no acceptance threshold has been relaxed.

## Shutdown

v19 probe finalizers restored profile, camera and projection. Normal owned
instance stop was requested after the last diagnostic. Both PID 48680 and
MCDK PID 35076 were confirmed absent at shutdown. Earlier owned games, including v18
PID 37732, were already absent. Do not target the user's protected 3.9 PID 40452.
