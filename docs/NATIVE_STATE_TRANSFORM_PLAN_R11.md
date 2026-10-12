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

Client construction and session-binding failures also persist their error and
explicit `mutation_attempted=false` cleanup status. Before the first native
fixture write, the report persists `mutation_attempted=true`; an uncertain write
still enters cleanup. A no-mutation connection failure is never physical evidence,
even when its cleanup status is restored.

New captures use schema 2. They retain the owned game and MCDK PIDs and creation
identities, session path, launch noactivation metadata, and explicit paths/SHA256
records for the probe, MCP wrapper and session loader. Before connecting, the
probe requires the verified background/noactivation launch flags and rehashes the
MCDK executable and guard DLL against that launch's recorded hashes. The replay
accepts unchanged schema 1 captures and requires complete provenance for schema 2.
Frozen schema 1 bytes and their hashes remain unchanged.

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
and covered offline. A subsequent fresh schema 2 capture using the protected
IPC-framing MCDK binary (SHA256
`b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9`)
connected and executed successfully, but the atomic fixture also failed at its
first upper wooden door half, aux 8 at `(4,-47,4)`. All sixteen complete pair
palette calls and stone supports returned success before the exact-cell guard
ran; the first lower half matched. The first upper half did not match exactly,
and its following single-cell `WorldAdapter.write` returned false. This report
does not contain the upper half's actual native states, so it cannot distinguish
native normalization from removal and does not establish a mapping error.

That failed capture is frozen as
`tools/data/native_state_transform_shapes_r11.door-atomic-failed.json` (SHA256
`c4a5ec8d05bba9bde13a5f87710a269c4cbf37a76525e63001898e1e278df813`), with its
exact source in `native_state_transform_shapes_r11.door-atomic-failed.probe.py`
(SHA256 `2a14bb6647afc93eb23208adaa20329c0a3bbe92dd9be5a454879e1eb345f98b`).
The runtime was `1.21.120.0`, with player feet at `(0.5,-60,0.5)`, fixture lower
Y `-48` and an explicitly written stone support at Y `-49`. The reserve was
empty/dry before setup. Cleanup verified all 286 reserved cells as dry air on
the server and air on the client, with unchanged player position. The owned
game PID 65180 (creation identity `134362885819781255`) and MCDK PID 55068
(`134362885816427693`) were independently absent after shutdown. This result
remains excluded from physical acceptance.

## Single-Pair Diagnosis

`tools/probe_native_single_door.py` prepares only one supported lower/upper door
pair and 17 empty/dry reserve cells. It obtains traditional aux values through
the documented `GetBlockAuxValueFromStates`, uses `SetBlockNew` with
`isLegacy=True` and `updateNeighbors=False`, then applies `SetBlockStates`.
Every setter's return and both halves' actual new aux and typed states are
recorded immediately, with server/client readbacks after 0.2 seconds and later.
No palette writes or inventory/rotation/player/camera/settings changes occur.
It clears the entire reserve through the same documented update-disabled native
setter and verifies server dry air, client air and unchanged player position.
The result is a placement diagnosis and never claims transform acceptance.

Its first protected cold launch failed in the launcher's combined CIM/listener
discovery query at
the ten-second query limit, before readiness or any probe/native fixture writes.
The session and failure reason were retained, its owned PIDs were independently
confirmed absent after identity-bound shutdown, and the slot was released.
This startup failure is separate from the actual atomic-door fixture failure.

A subsequent protected single-pair retry connected using the same approved
IPC-framing binary and runtime `1.21.120.0`. The original report is frozen as
`tools/data/native_state_transform_shapes_r11.door-single-diagnostic.json`
(SHA256 `a2e48d95e2a064b01bc8d2725c8e6889757b7f27bf5308fe4e462a3fb95bede9`), with
the exact executed probe in the matching `.probe.py` (SHA256
`6887bd5bf129483fe8406d289102b581fd4fa1486ddd9f51e512b99ed82f9764`). The explicit
support at `(4,-49,4)` was stone. Writing the lower half at `(4,-48,4)` with
legacy aux 0 returned true and automatically created the requested upper aux 8
at `(4,-47,4)`. The following unchanged upper write returned false, while both
halves already matched exactly. Both `SetBlockStates` calls returned true, and
all four immediate setter snapshots plus setup readback retained exact new aux
and typed states: south, closed, hinge false, with opposite upper-block bits.

The delayed client read failed because `GetBlockPaletteBetweenPos` returned
`None` for the upper cell. The report has `completed=false`, `restored=true`
and no delayed stage or `exact_native_pair` result. Although the host executed
the delayed server call first, its original combined dictionary assignment was
discarded on the client exception, so no delayed server observation is available
in the frozen report. These bytes have not been retroactively amended. They
establish immediate native setter behavior for one pair only, with no delayed
stability, physical shape or transform acceptance. The current recorder saves
each side independently and retains explicit stage/side errors; any missing
observation keeps completion and exact-pair flags false.

Cleanup verified all 17 reserve cells as dry air on the server and air on the
client, with unchanged feet `(0.5,-60,0.5)`. The owned game PID 53132 (creation
identity `134362910271095253`) and MCDK PID 42928
(`134362910269034694`) were independently confirmed absent after normal shutdown.
The private flat creative config, exact launch wrappers and original probe/report
remain archived under the worktree's `.runtime/single-door-v10-sources/`; the
temporary wrappers were restored and the newly created worktree config removed.

## Offline Verification

Twenty-one shape tests verify complete fixture coverage, symmetric ray-plan closure,
slab reflection, malformed/stale/native-time evidence rejection, and a synthetic
stair-box counterexample. The synthetic case verifies that wrong X and Y targets
are caught by distinguishing ray hits even when all enclosing AABBs are cubes.
It is a parser test, not native evidence. Separate frozen-native tests verify
the original raw/probe byte hashes, replay all 144 current target comparisons,
and reject deliberately wrong stair X/Y mirror targets against actual game
observations. Noise tests ensure numerical tolerance cannot turn enclosing cubes
into discriminating shapes. The connection-failure test exercises both client
construction and context entry failures, verifies no native execution is attempted,
and checks that the failed report persists and remains excluded from acceptance.
Schema 2 tests reject missing or inconsistent process/source provenance, unprotected
launches and changed binary hashes before any connection or native execution.
Two single-door tests execute the actual generated setup/cleanup against a native
API test double: an auto-created upper half's unchanged `SetBlockNew` false return
must remain a recorded observation, and a setter exception must preserve both
actual half states and still clear all 17 reserved cells. Two host failure tests
verify independent persistence of delayed server/client observations when the
opposite side fails, continued diagnosis and complete cleanup. A frozen-native
test verifies the raw/probe hashes, exact immediate snapshots, unchanged false
upper setter return and the absence of delayed stability/acceptance evidence.
The host tests do not add native observations.
No production mapping has changed.
