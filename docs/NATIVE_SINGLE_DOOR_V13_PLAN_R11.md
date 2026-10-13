# Corrected Single-Door V13 Prepared Family

Status: integrated host sources, offline fault review and immutable source freeze.
Native execution has not occurred. Root must review exact hashes and schedule
one owner-bound protected attempt before this family is launched. This is a new
load-gated experiment, not a replay of V12 or an orientation matrix.

## Scope And Evidence

The first target is one supported wooden-door pair, unchanged native south/closed
lower and upper states, with server actual typed states and delayed client whole-
pair palettes plus real `GetBlock` fronts. Upper client typed state is never
synthesized. Actual lower typed direction and pair replication may be established;
physical orientation, screenshot reliability, and production mapping acceptance
remain false. No screenshot or camera/player movement is part of this experiment.

V12 reached SDK readiness after an 85.250-second launch phase and then read feet
at Y32768. Support Y32779 returned false and remained air; neither door setter ran.
With work110, only 22.913 seconds remained when the probe began. Its raw failure
and cleanup are fixed in `native_single_door_load_failure_r11_v12/`, not changed
by this prepared family. V10, V11 and prepared V12 bytes stay fixed as well.

The authoritative searches and fixed-world reasoning remain in
`docs/NATIVE_SINGLE_DOOR_LOAD_PREFLIGHT_R11.md`. Documented server APIs are
`GetPlayerList`, `GetEntityDimensionId`, `GetFootPos`, and
`CreateChunkSource(levelId).CheckChunkState(dimension,pos)`. SetBlockNew supports
loaded terrain and false alone does not identify why no change occurred. The
known private flat world/runtime is restricted to dimension 0 and Y `[-64,320)`;
horizontal `[-128,128)` is a local fixture scope, not a claimed engine border.

## Integrated Gate And Journals

The load gate includes its client handshake and waits at most 30 seconds. It
records raw feet without clamping, substituting, or normalization. Non-finite,
malformed, boolean, or out-of-scope coordinates never reach a chunk query or
fixture construction. Full reserve bounds must pass, every reserve chunk must
return boolean true, and two consecutive loaded readings separated by 250 ms
must share the world/player/dimension/origin and feet within 0.01 on each axis.
Changing bindings, unsupported runtime/dimension, multiple players or an existing
fixture aborts; loading timeout occurs before any setup RPC.

`DeadlineClient` reclamps each actual RPC, including initialization, the initialized
notification, every tools/list retry, session-marker binding reads, tool calls,
and DELETE, to two seconds or the current remaining phase deadline. Its opener
rechecks remaining time immediately at each network open. Raw successful/error
responses and native RPC error dictionaries are journaled. A response at or after
the phase deadline cannot establish readiness or a verdict. The outer supervisor
also bounds the child process, independently of socket timeouts.

Before SETUP, the host persists mutation intent and leaves it active until a
valid server acknowledgement says mutation was or was not attempted. SETUP repeats
the accepted anchor and loaded-chunk check in its own server call, reads all
reserve cells, rechecks target chunks, world/player/dimension/runtime and feet,
and checks the marker immediately before creating one. Failed guards return an
explicit classification with `mutation_attempted=false` and call no setter.

Once the guard passes, the server marker journals each setter intent before it
runs. Actual support return/block/state, each actual half and setter return, and
the immediate final pair are retained. A genuine support refusal is classified
separately from load failure. A lost or malformed reply is never replayed; the
host still attempts exact owned cleanup. CLEAR returns recovered server write
intents and observed setup data, journals every clear step, confirms all reserve
cells air/no liquid and unchanged player, and verifies client air replication.
Recovered data from an uncertain reply does not automatically accept the pair.

## Finite Work Budget

Readiness is 120 seconds. Load/handshake is 30 seconds, fixture and delayed
observations 20 seconds, probe fixture cleanup 20 seconds, and final client close
at most two seconds. Supervisor work is 200 seconds and total, including owned
stop, emergency cleanup, exact process checks and input restoration, is 240.

After launch, the supervisor reserves two seconds for process startup and requires
at least 72 seconds for the complete probe before issuing it. Launch at elapsed
130 would leave 68 seconds and fail without issuing a probe. At V12's observed
elapsed 87, it would retain the full gate and cleanup reserves. Once loading
passes, the probe also checks that a full 20-second fixture interval and cleanup
reserve still fit; insufficient time fails before SETUP. Late data and verdicts
cannot extend deadlines. No automatic launch retry or full direction matrix runs.

## Ownership And Delivery

The runner requires this isolated `.runtime/r11-transforms` worktree, fresh output,
fresh owner/name and pinned source/binary hashes. Only the approved MCDK
`b8eb8959...` and guard `c22fa0cd...` are used. It independently counts actually
live game identities and refuses a sixth game. Only its exact owned identities
may be stopped. The protected frame session `773c643b5cf344918e04d8b4eef2657a`
is not sent SDK/input calls. Foreground/background protection and exact launch
input restoration remain required. No input, activation, resize, player/camera,
settings, UI/reload fallback or production transform change is introduced.

Frozen sources and exact byte inventory are in
`tools/data/native_single_door_v13_prepared/`. The family records no native
acceptance. Offline tests cover load faults, final SETUP guards, support refusal,
lost setup acknowledgement and cleanup intent, per-request deadlines including
binding reads, late raw response/error preservation, insufficient work reserve,
owned stop and external edit restoration refusal. New-family checks verify source
pins and frozen bytes; earlier frozen checks still verify their own independent
snapshots. Host utility review is by scoped diff inspection and these tests;
the Mod Python reviewer selects zero host utility files and is not counted as
a successful structural review.
