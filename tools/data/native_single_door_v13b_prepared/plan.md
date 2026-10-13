# Corrected Single-Door V13b Prepared Family

Status: integrated host sources, offline fault review and immutable source freeze.
Native execution has not occurred. Root must review exact hashes and schedule
one owner-bound protected attempt before this family is launched. This revision corrects V13 runner cleanup and child wait accounting. Original
V13 remains frozen at manifest `c69f755f7aaf055e1bb56f847ea562833ae695dd27cd2941254365f8437e4876`.
The load-gated probe and SDK paths are byte-identical to V13.

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

After launch, the supervisor reserves two seconds for process startup and three
seconds for child kill/reap, then requires at least 72 seconds for the complete
probe before issuing it. Launch at elapsed 130 would leave 65 seconds and fail
without issuing a probe. At V12's observed
elapsed 87, it would retain the full gate and cleanup reserves. Once loading
passes, the probe also checks that a full 20-second fixture interval and cleanup
reserve still fit; insufficient time fails before SETUP. Late data and verdicts
cannot extend deadlines. No automatic launch retry or full direction matrix runs.

Each subprocess phase reserves three seconds for kill/reap inside its supplied
absolute deadline. Initial communicate waits use the remaining phase time minus
that reserve; after kill, communicate is reclamped to the remaining deadline.
No child starts with three seconds or less available. Process creation time is
charged to the same deadline. This removes the former additive three-second wait
per timeout. The offline all-timeout cleanup schedule reaches elapsed 232 seconds,
then fails with owned absence unverified. The reported total also includes file
I/O and process identity checks; it is a measured limit, not an independent
watchdog guarantee against an OS or disk stall.

## Owned Launch Inputs And Registry

Before copying any staged launch input onto its target, the runner verifies the
staged bytes against the fixed approved source SHA and persists installation
intent. A finally block observes and journals the exact target SHA or absence,
even if copying truncates or partially writes the target and then raises. The
original copy error is retained along with any target observation error.

Restoration is allowed only while the target still matches that observed owned
snapshot and any original backup still matches its original SHA. Unobservable
installation targets or subsequent external drift fail closed and retain the
current bytes. Partial writes restore exact original bytes for existing targets
and exact absence for previously absent targets. An input never attempted is
recorded as unchanged. Approval receipts use the fixed expected hashes, never
reaccept a shared source that changed during staging.

Before input installation, the runner freezes existing registry paths and IDs.
An owner/name/project collision fails without launching, issuing SDK calls or
stopping that prior session. Lost launch replies can trigger recovery only after
an actual launch phase was attempted. Recovery excludes every prior registry
path and prior session ID, including an old ID copied to a new path, and refuses
multiple new matching candidates. Recovery errors are recorded without skipping
launch-input restoration.

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
`tools/data/native_single_door_v13b_prepared/`. The family records no native
acceptance. Offline tests cover load faults, final SETUP guards, support refusal,
lost setup acknowledgement and cleanup intent, per-request deadlines including
binding reads, late raw response/error preservation, insufficient work reserve,
owned stop, partial input-copy restoration, unobservable and externally changed
input refusal, staged-source drift, zero-launch owner/name collision, exclusion
of prior registry paths/IDs and child kill/reap deadline accounting. New-family checks verify source
pins and frozen bytes; earlier frozen checks still verify their own independent
snapshots. Host utility review is by scoped diff inspection and these tests;
the Mod Python reviewer selects zero host utility files and is not counted as
a successful structural review.
