# Single Door Pair Diagnostic R11

Status: prepared offline for root review. No new native attempt has run. This is
one supported wooden door pair and its stone support, with 17 dry-air reserve
cells. It is a data replication diagnostic, not a physical orientation oracle.
The original v10 report and executed probe remain immutable.

## Documented Reason To Change The Read

The MCP documentation read on October 12, 2026 is
`ModAPI/接口/世界/方块组合.md`, `GetBlockPaletteBetweenPos`, client interface.
It explicitly says a door palette adds only the lower half and ignores the
upper half. It also requires the selected area's blocks to finish loading.
The client signature is `(startPos, endPos, eliminateAir=True)`; the prepared
probe calls it with `False`. An all-air selection with `False` returns an air
palette, whereas creation failure returns `None`. The same lower-only rule
also appears in the server and position-list versions.

`ModAPI/接口/方块/方块调色板.md`, `SerializeBlockPalette`, documents serialization
to a dictionary and shows multi-cell client selections. The local
`world_capture.restore_omitted_palette_cells` and its omitted-door-half test
already follow this rule by reading the actual omitted front from the world.
`ModAPI/接口/世界/方块管理.md`, `GetBlock`, documents the client's actual name/aux
tuple and the loaded-terrain prerequisite. `GetBlockNew` and `GetBlockStates`
are server-only. The probe does not invent a client equivalent or derive upper
typed states from the lower state or legacy aux.

The v10 upper-only `None` is therefore compatible with the documented omission.
It did not record `GetBlock` for that upper cell or the delayed server result,
so those original bytes cannot exclude incomplete client replication/loading.
The next attempt changes the observation method to distinguish those cases.

## Prepared Observation

Keep the documented v10 support/lower/upper/state writes unchanged. Before any
write, verify the reserve as dry air. Save all immediate setter returns and both
native server half states. For each of the two delayed stages, persist the server
read before issuing the client request. Any transport error is recorded with its
stage and side; it cannot erase the opposite side's successful observation.

Each bounded client request reads actual `GetBlock` values for lower, upper and
support, then calls `GetBlockPaletteBetweenPos` for the whole pair, lower alone,
upper alone and support alone. It reads the same actual fronts again afterward.
Each palette retains its availability, exact bounds and a typed frozen original
serialized tree, including the omitted upper record. No omitted record is filled
in. The existing client's chunk-event tracking is observed without new listeners
or imports of the client system. Missing tracking means unavailable corroboration,
not a declaration that the chunk is unloaded.

For the whole pair the serialized volume must be `(1,1,2)` in the repository's
native `(z,x,y)` order. Lower/upper linear indices are 0/1. Duplicate or outside
indices, changed bounds, malformed records and typed lower-state mismatch fail
verification. Actual client fronts are compared against the two observed SDK
legacy aux values recorded during setup, not against inferred new/legacy aux
equivalence. The support must remain actual stone in both client reads.

## Decision Path

| Observation | Diagnosis | Allowed conclusion |
| --- | --- | --- |
| Server halves change | `server_pair_changed` | Placement or server stability unresolved |
| Actual client front unavailable/unknown | `client_front_unavailable_loading_unresolved` | Client loading/replication unresolved |
| Client air/other front or before/after disagreement | `client_front_not_replicated` | Pair not replicated at this observation; cause unresolved |
| Exact fronts, whole pair unavailable | `pair_palette_unavailable` | Export failure unresolved despite readable fronts |
| Pair malformed or lower typed state missing/different | `pair_palette_invalid` or lower mismatch | No replication verification |
| Server typed pair exact, both actual fronts/support exact and stable, pair contains exact lower only, upper alone unavailable | `documented_upper_omission_observed` | Data replication measured with explicit partial client typed coverage |
| Pair also contains exact upper typed record | `complete_pair_palette` | Complete typed coverage measured for this observed pair |

`server_exact_native_pair` is independent of client palette coverage.
`data_replication_verified` requires both delayed decisions plus the immediate
and delayed exact server pair. `client_typed_pair_verified` and the old strict
`exact_native_pair` stay false when the upper typed record is omitted. All paths
keep `physical_orientation_accepted=false`. A zero CLI status means the bounded
data replication diagnostic verified its data and restored its reserve; it does not
mean full client typed coverage or orientation acceptance.

## Native Run Boundary

Root must review the prepared source/plan and explicitly assign one protected
owner-bound instance before a native attempt. Use one fresh output, the approved
MCDK/guard hashes, a flat creative config with all hotreload flags false, and an
external supervisor with a 150-second total bound that retains identity-bound
stop/restoration handling if the process is interrupted. The probe permits only
two delayed observations and a ten-second client cleanup check; it begins cleanup
if the observation phase exceeds 90 seconds. No blind repeat, full state matrix,
desktop input, activation, resizing, player/camera/settings changes, UI navigation,
resource reload, or healthy instance mutation occurs during preparation.

Clear all 17 cells through the same documented update-disabled server setter,
verify dry server air and actual client air, and confirm player feet unchanged.
Owner-bound stop and independent process absence remain mandatory after a cold
launch. A failed diagnostic preserves its raw observations and stops further
native expansion. A successful diagnostic only prepares the later separately
reviewed complete door-state pixel/ray orientation matrix; it cannot validate
hinge/open/direction transforms, materials or editor preview pixels by itself.
