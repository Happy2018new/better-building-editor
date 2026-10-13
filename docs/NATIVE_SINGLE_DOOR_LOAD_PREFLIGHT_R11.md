# Prospective Single-Door World/Player Load Preflight

Status: prepared host helper and offline tests only. No native attempt has run
this code. The existing V12 probe, runner source pin, budgets, and frozen prepared
V12 family remain unchanged. Root review is required before live integration and
one specifically scheduled native attempt. The V12 failure does not support any
door state transform conclusion.

## Evidence And Documented Calls

V12's launch phase ran from supervisor elapsed 1.822419 to 87.072630 seconds,
or 85.250211 seconds. Probe started at 87.086960 with 22.913048 seconds left under
the 110-second work limit. The immediately observed foot Y was 32768; the derived
support Y32779 setter returned false/air. No door setter ran. Full supervisor
cleanup finished at 102.389227 seconds. Initial child/listener discovery had
succeeded at 7.821 seconds; most startup time was waiting for SDK routing.

Authoritative MCDK `minecraft_docs` searches used for this proposal:

- `api GetEntityDimensionId`: server component returns dimension 0 for overworld,
  1 for nether, 2 for end, or a custom dimension ID.
- `api GetFootPos` and `api 脚底`: server `CreatePos(entityId).GetFootPos()` reads
  foot position; the foot-specific entry was returned by the latter search.
- `api CheckChunkState`: server `CreateChunkSource(levelId).CheckChunkState(
  dimension, pos)` returns bool, whether that position's chunk finished loading.
- `api SetBlockNew`: only loaded terrain can be set; false means no block change,
  and does not identify the reason by itself.
- `netease 区块` and `netease 320`: chunk extent is 16 x 384 x 16, with lower
  Y -64 and upper boundary 320. Fixture cell Y uses the conservative half-open
  interval `[-64,320)`, giving the documented 384 layers.

No documented runtime dimension-height query was found using
`GetDimensionLocalHeight`, `GetMinHeight`, `GetMaxHeight`, `GetDimensionHeight`,
`GetDimensionMinMaxHeight`, or `GetDimensionInfo`. This proposal therefore limits
the diagnostic to the known private flat overworld/runtime, rather than guessing
a height API. Horizontal `[-128,128)` is an explicit local fixture scope around
this private flat world's spawn; it is not claimed to be an engine world border.

## Gate Behavior

`tools/native_single_door_load_preflight.py` reads only server runtime, level ID,
player list, dimension, foot position, fixture marker presence, and chunk state.
It stores every raw reading without clamping, substituting, normalizing, or
moving the player. The original fixture offset remains floor(feet) + `(4,12,4)`.

The gate waits at most 30 seconds for one player, finite non-boolean numeric
feet, runtime `1.21.120.0`, dimension exactly 0, and all 17 reserve cells inside
the fixed Y/horizontal scope. Invalid feet are retained but never used for
chunk queries or fixture construction. If feet are valid but the full reserve
would cross a boundary, the wait remains read-only. An unresolved prior fixture,
unsupported runtime/dimension, multiple players, replaced player, or changed
world binding aborts immediately.

For each valid candidate, the helper re-reads the same world/player/dimension/
foot before checking one representative position per target reserve chunk. All
checks must return the boolean true. It reads feet again after chunk checks and
rejects movement. Two consecutive loaded candidates, separated by a 250 ms
host wait, must have the same derived origin and feet within 0.01 on all axes.
Movement or a not-loaded chunk resets that stability requirement. A reply at
or after the deadline cannot pass. Receipt progress is persisted after each
anchor/chunk result and at completion. SDK/transport failures are recorded with
their original text and raw RPC dictionary, then re-raised without replay.

Load timeout classification is `world_player_not_loaded`; last raw/status entries
explain whether feet, full fixture bounds, or chunks blocked readiness. This
occurs before `mutation_attempted` or a fixture marker is set, so cleanup is
explicitly no-fixture-mutation. A later support setter refusal remains a separate
setup failure with its original returned value and actual block/state reads.

## Integration To Review

1. Replace only the single-door probe's current one-shot `shapes.PREFLIGHT` call
   with this helper; keep the full stair/trapdoor probe unchanged.
2. Use a deadline-aware owner-bound `Client` subclass for load reads. Each actual
   network operation, including `_verify_binding`, tools/call, initialization,
   tools/list retry, and close, must use the current remaining deadline, with a
   per-operation maximum of two seconds. Setting one timeout before a composite
   `call()` is insufficient because binding and execution each open a request.
3. Recheck the accepted world/player/dimension/feet, full reserve bounds and
   loaded target chunks inside the SETUP RPC immediately before reserve checks,
   marker creation, and the first setter. Recheck feet after those read-only
   checks too. This closes the host-to-SETUP gap; any failed check returns a load
   classification and does not create a marker or call a setter.
4. Persist a mutation-intent receipt before issuing SETUP. The server response
   must explicitly say whether the guard passed and a marker/write was attempted.
   On uncertain transport failure, keep mutation intent true and perform exact
   owner-bound cleanup; never replay SETUP.
5. Keep all actual support and half-state reads, whole-pair palette/front checks,
   delayed observations and cleanup semantics from V12. No screenshot attempt or
   physical orientation acceptance is introduced by this preflight.
6. Freeze a new prospective probe/helper/runner/plan family, set new source pins,
   adapt existing offline probe and supervisor tests, and send exact hashes for
   root review before any scheduled game. V10/V11/prepared V12 raw bytes stay fixed.

## Concrete Finite Budget

Proposed new limits are readiness 120 seconds, load gate 30 seconds, fixture and
observations 20 seconds, probe fixture cleanup 20 seconds, supervisor work 200
seconds, and cleanup-inclusive total 240 seconds. The work/total difference
retains 40 seconds for emergency fixture cleanup, owned stop, exact process
verification, input restoration, and receipt persistence. This is a prospective
budget change, not permission for a native attempt.

At V12's observed +87-second SDK readiness, the load gate would have its full
30 seconds and the following fixture work would retain 20 seconds. At the
proposed cold-start ceiling, 120 + 30 + 20 + 20 = 190 seconds leaves about 10
seconds inside work200 for launcher/preflight overhead and 40 more for supervisor
cleanup. The supervisor must establish the latest safe fixture-start time before
launching the probe; if its actual remaining work cannot fit the read-only gate
plus fixture/cleanup reserves, it fails without starting fixture mutation. Late
results are retained as evidence but cannot extend any deadline. No repeated
launch or automatic retry is part of the proposal.

## Offline Verification

Eleven focused tests cover V12 Y32768 retention with no chunk/fixture calls,
natural settling, two consecutive stable loaded readings, NaN/Inf/malformed
feet, full reserve/horizontal bounds, unsupported dimension/runtime, unresolved
fixture, absent/replaced player, changed world binding, unloaded/ambiguous chunks,
all reserve chunks across negative coordinate boundaries,
movement during chunk reads, deadline replies, original native errors, and actual
execution of the prepared server read snippets against SDK stubs without setters.
These are prospective host fault tests, not native load evidence.
