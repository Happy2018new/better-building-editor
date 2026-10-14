# Shelf Body Round 17 Checkpoint

Paused on 2026-10-14 at the user's model-switch request. No shelf runtime,
mesh, shader, production registration, or qualification was added.

## Preserved Work

- `tools/generate_shelf_resources_r17.py` currently inspects the twelve native
  3.10 shelf atlases, records their SHA256 values, and creates an isolated
  project copy. Despite its planned filename, it does not yet generate meshes.
- `.runtime/shelf-atlas-r17-v1/atlas-review.png` was visually reviewed. All
  twelve native `*_shelf.png` files have 32-by-32 atlases. Their source hashes
  are in `atlas-sources.json` next to that review.
- `tools/probe_shelf_native_shape_r17.py` is a prepared observation host. It
  has not run in game. It intends to record collision/clip boxes for the
  twelve woods and 32 existing registry states, followed by controlled native
  screenshots with a one-block cyan support as a scale reference. Both new
  tools pass `py_compile`; this is not a runtime validation result.
- Existing registry states were read, never changed: four
  `minecraft:cardinal_direction` values, `powered_bit` false/true, and
  `powered_shelf_type` 0 through 3.

## Native Evidence And Next Step

`docs/evidence/shelf-native-r16/v2` still establishes only oak aux 0: the
actual-world body is visible in four views while live, roundtrip and prepared
Combine palettes omit it. Actor data is empty and roundtrip data is exact.
This establishes a native body gap, not the geometry for all woods or states.

The native resource search found shelf textures but no readable shelf model.
Do not invent actor renderer fields or assume that connection/power states
share one geometry. First record native clip/collision responses and actual
world images, derive plank depth/thickness and atlas mapping against the cyan
block scale, then generate an independent versioned candidate. Reuse existing
LiquidPreview/LiquidProjection owners as the other companions do; keep the
production gate false until editor/full/missing image qualification passes.

## Paused Instance

The isolated project is `D:/bbe-r17-shelf-body`, owner `shelf-body-r17`.
Its session is
`C:/Users/Happy2018new/.pyreact-debug/instances/4c41d4cf0634408589edd389667c8b03/session.json`.
Launch spawned MC PID 54368 and MCDK PID 50728, but the 120-second readiness
wait failed in `client_process_environment`. The observation host never ran,
so no shelf fixture, camera movement or inventory edit needs restoration.
The first owner-bound normal stop timed out while the processes were exiting.
A subsequent independent process query found both PIDs gone, and a second
normal stop completed with session state `stopped`. No force stop was needed.
Inspect current process identities before any future reuse; stale PID numbers
are not authorization to touch other games. The unmanaged user 3.9 PID 40452
was not operated.

There are no staged files or commits for this subtask. The five user palette
probes and all shared scene/session/bridge/material/registration files remain
outside this task's edits.
