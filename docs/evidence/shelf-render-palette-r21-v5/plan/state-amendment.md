# Explicit-State Boundary Amendment

This file does not alter frozen v5 source, clone, host hashes or reports.

The pure v5 helper assumed the selected `(minecraft:oak_shelf, 0)` key always
implied its canonical south/unpowered states. `prepare_palette` actually keeps
caller-supplied state dictionaries, even when they conflict with that aux.
Therefore the original helper is only suitable for its constrained fixture;
it must not be adopted as a general prepared-palette transform unchanged.

The single uncommitted `tools/shelf_render_palette_candidate_r21.py` helper
now includes the state guard. Its original frozen bytes were preserved at
`.runtime/shelf-render-palette-r21-v5-state-guard/original_shelf_render_palette_candidate_r21.py`.
It accepts absent/empty states, or exactly:

```json
{"minecraft:cardinal_direction":"south","powered_bit":false,"powered_shelf_type":0}
```

The bool and int fields retain their native types. Partial, unknown, north,
powered and conflicting records pass through unchanged, including actors and
item payloads. The guard handles each nested context palette independently.
It imports no product registry at runtime and does not change original data.

`tests/test_shelf_render_palette_guard_r21.py` establishes the real boundary
through `prepare_palette` with aux0 and explicitly north-facing state, then
checks that the amendment preserves this body and its actor. Additional
focused checks cover power, unknown state, native scalar types, canonical
acceptance and mixed context batches. There is no expanded runtime matrix.

The original frozen v5 manifest and clone remain unchanged. Its original
manifest no longer verifies the current root helper, as expected. Root uses
the explicitly bound sibling control
`.runtime/shelf-render-palette-r21-v5-state-guard/run.py` for the guarded
acquisition. This runner is a byte-exact copy of the original; it reads a
separate `frozen.json` that updates only the helper host hash and records the
original manifest and old helper provenance. The clone, resources, owner,
three images and lifecycle plan are identical. No second tools API remains.
