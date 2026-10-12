# Native State Transform Cross-Check

This experiment checks current NEMC physical direction semantics independently
of `state_transform.py`. It does not change any production mapping on the basis
of older external conversion labels. The checked-in palette has 15,858 native
records, 1,340 names and 113 state keys; its full six-operation audit establishes
legal targets and coherent transform laws, not native appearance acceptance.

## Independent Evidence

The current installed vanilla `blocks.json` provides texture bindings for doors,
stairs and rails, but no directional shape decoder for these engine-built meshes.
The neighboring `neomega-blocks` repository uses PyMCTranslate universal
conversions (`data/build_unis/uni_from_official.py`); its README records Bedrock
mapping inaccuracies. It is useful for identifying version/state differences,
but is not an independent physical oracle for those same conversion mappings.

The MCP ModAPI reference `ModAPI/接口/世界/方块管理.md` documents
`GetBlockClip` and `GetBlockCollision` as current native AABBs, affected by the
neighborhood. `GetBlockCollision(getAll=True)` instead returns custom
`netease:aabb` component data. An empty `collision` list is not evidence of an
empty vanilla shape, nor does that path promise a native stair box union.

`ModAPI/接口/世界/实体管理.md` documents
`getEntitiesOrBlockFromRay` on both sides, with arbitrary world position, unit
direction, distance, and `RayFilterType.OnlyBlocks`. It returns native block
position and precise `hitPos`, or `None` when no target is hit. Rays use clip
geometry, so their ability to distinguish stair occupancy must itself be checked
against complete state sets and stone/air controls.

## Fixed First Batch

`tools/capture_native_state_transform_shapes.py` captures every state of:

- `minecraft:oak_stairs`: 8 states.
- `minecraft:wooden_door`: 32 half-states, placed as 16 matching supported pairs.
- `minecraft:trapdoor`: 16 states.
- Unit stone and empty air: 2 controls.

The 58 observations are separated by four cells and have isolated stone floor
supports where needed. All source, support and adjacent reserve cells must be
empty and dry before writing. The capture records 16 symmetric horizontal rays
per observed cell, at quarter-cell heights and cross-axis positions, plus native
typed states and clip/collision bounds. It reads server/client first snapshots
and server/client snapshots after one second. It never calls the transformer.

The tool requires an explicit owner-bound session and matching project. It does
not start a game, use desktop input, activate a window, move a player/camera,
change settings/resources, or persist a draft. Cleanup removes the complete
reserved fixture, checks native residue and verifies the player's position is
unchanged. A prior live marker is refused; failed observations remain in the raw
report. Run only after the root agent assigns a game slot.

```powershell
python -X utf8 tools/capture_native_state_transform_shapes.py .runtime/state-shapes-fresh.json --session <owned-session.json> --owner <owner> --name minecraft:oak_stairs --name minecraft:trapdoor
python -X utf8 tools/analyze_native_state_transform_shapes.py .runtime/state-shapes-fresh.json .runtime/state-shapes-replay-fresh.json
```

## Falsifiable Replay

`tools/analyze_native_state_transform_shapes.py` first rejects stale palette
provenance, partial state sets, duplicate records, type changes, external ray
hits, unstable side/time observations, or incomplete cleanup. It normalizes
native coordinates relative to their own source cells, applies six explicit
coordinate matrices to every AABB corner and ray hit, then compares the result
with the captured native shape of the production candidate target.

Door closed/open side-offset slabs make a quarter-turn interpretation error
falsifiable under X/Z reflection even if rotations and group closure pass.
Lower/upper door halves are compared in each cell's local coordinates, because
the editor also reflects the cell position and swaps the half state.

Identical enclosing cubes cannot establish stair occupancy. The analyzer requires
at least eight distinct native stair signatures, four door slab signatures, and
six trapdoor signatures before accepting physical direction evidence. Door hinge
and half symmetries can share slab bounds; exact six-operation comparisons still
check every captured state. A failed discrimination check stays unresolved even
when every candidate shape comparison passes.

Rails have symmetric enclosing boxes that do not establish their textured
endpoints or slope direction. They need a separate native geometry or visual
endpoint oracle. This first batch does not claim rail appearance acceptance,
stair neighbor-corner correctness, textures, editor/projection pixels, or all
materials. New palette versions need a fresh version-bound capture; aux IDs are
resolved from typed native states rather than inferred by arithmetic.

## Current Native Result

On October 12, 2026, the bounded SDK-only capture completed for all eight oak
stair states and all sixteen wooden trapdoor states, with stone/air controls.
The native runtime reported `1.21.120.0`; the installed package's `data/manifest`
reported both `version` and `engineVersion` as `3.9.0.401155`.

The immutable observations are
`tools/data/native_state_transform_shapes_r11.raw.json` (SHA256
`1625d5598300f74c9f83530628a9cecf69b663da6edbbe563946f33220e8e970`).
`native_state_transform_shapes_r11.probe.py` preserves the exact capture source
(SHA256 `198b76c0733e28e9333812058418d9912de24134588c654696ed1e7d893855da`).
The separate `native_state_transform_shapes_r11.replay.json` records the
candidate transformer hash, analyzer hash, comparison tolerance and all results.
These files have Git text conversion disabled to preserve their byte hashes.

All 144 native coordinate comparisons pass: 48 for stairs and 96 for trapdoors.
Native ray hits distinguish all eight stair occupancy shapes, while trapdoors
have six distinct shapes (two closed horizontal slabs and four open vertical
slabs). Closed direction symmetries and open upper/lower symmetries do not
artificially increase discrimination. This supports the current direction/half
targets for these two sampled materials. It does not verify textures, other
materials, stair corner topology, rail endpoints or preview/projection pixels.

Coordinates retain six decimal places after local normalization. Comparison uses
an explicit absolute tolerance of `0.00001` block, including shape discrimination;
`None` versus a ray hit remains an exact difference. Float32 world coordinates
at different fixture positions produced a `0.000001` difference for otherwise
matching trapdoor bounds and hits. All four native snapshots were otherwise
stable; typed state comparison never relaxes booleans to integers. Native air
states are `None` on the server and `{}` in the client palette, so only those
empty state representations are treated as equivalent.

Cleanup verified all 302 reserved cells as dry air on the server and air on the
client, with unchanged player position and no remaining fixture marker. The
owned game PID 57600 (creation identity `134362836481169893`) and MCDK PID 39512
(`134362836478168669`) were independently confirmed absent after owner-bound
shutdown; its allocated slot was released. No desktop input, window activation,
player/camera/environment settings, archives, drafts or production mappings
were changed.

The full default batch remains unresolved for doors. Lower-first single-cell
palette writes reported failure for the first upper door half, including after
an exact-existing-cell guard was added. The frozen failed report
`native_state_transform_shapes_r11.door-failed.json` has `completed=false`,
`restored=true`, and verified client cleanup for all 574 reserved cells. It is
excluded from physical acceptance. An isolated retry observed both door cells
as air; an atomic supported pair or a documented native placement path needs
its own fresh capture. Older conversion labels are not a reason to alter the
production door mapping.

The current capture tool prepares each door pair with a complete supported
`volume=(1,1,2)` palette. Its two records retain separate native name/aux keys
and typed states; the lower and upper indices are 0 and 1. This follows the
repository's existing supported tall-plant/bed probes and the documented
`SetBlockByBlockPalette` operation. Both cells must then pass exact native
readback and side/time replication. This replacement fixture path is prepared
and covered offline, but has not yet passed a fresh native door capture.

## Offline Verification

Seventeen targeted tests verify complete fixture coverage, symmetric ray-plan closure,
slab reflection, malformed/stale/native-time evidence rejection, and a synthetic
stair-box counterexample. The synthetic case verifies that wrong X and Y targets
are caught by distinguishing ray hits even when all enclosing AABBs are cubes.
It is a parser test, not native evidence. Separate frozen-native tests verify
the original raw/probe byte hashes, replay all 144 current target comparisons,
and reject deliberately wrong stair X/Y mirror targets against actual game
observations. Noise tests ensure numerical tolerance cannot turn enclosing cubes
into discriminating shapes. No production mapping has changed.
