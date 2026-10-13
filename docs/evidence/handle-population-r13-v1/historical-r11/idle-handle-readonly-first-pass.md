# R11 idle process handle review

Scope: read-only diagnosis of root-owned smoke session
`bd48f2f809fb4f0daf3ce560d5751adc`, owner `native-r11-retry-smoke`.
Game PID17276, creation identity134362834338766836; MCDK PID29104.
No fixture was created by this reviewer. No game code, hooks, injection, window
operations, mutable MCP or game launch/stop was used. Other sessions were only
listed as public metadata. Root independently stopped the smoke process.

## Evidence and bounded conclusion

The creation-bound census in `smoke-handle-types-2121-v1.json` records168927 game
handles, confirmed by both GetProcessHandleCount and the sampled extended system
handle table. Captured-at UNIX time is1791811565.3180668; the filename is merely a
label and is not its capture timestamp.

Of the168927 handles,168180 are File type, of which168124 have the exact granted
access mask0x0016019f. Event171, Thread77, Semaphore62, Section22 and all other
resolved types are much smaller. Object index56 has228 entries; duplicating its
first representative returned Windows error50 and the type remains unresolved.
Do not silently classify these228 objects.

The separate public process reads observed168927,168929,168927 and168925 handles
in the reviewed window. Root also reported the21:17 and21:21 values as nearly
stable. There is no evidence of sustained growth in this smoke instance over that
window. Earlier reports of growth in other owned games do not establish growth or
a shared root cause in this newer smoke instance.

Windows sockets and device handles are File objects too. Without their object
names, the168124 common-mask handles cannot be called disk-file handles, sockets
or render resources. The first bounded name-sampling attempt found zero owned
entries after root stopped PID17276. It did not reopen or restart the process.

## Source observations

- `tools/native_focus_guard/guard.cpp` installs user32 window creation/show/style
  and activation hooks. Its callbacks do not directly create kernel handles.
  MinHook initialization is one-time. This does not prove the guard or an engine
  reacting to its rejected activation calls cannot contribute indirectly.
- `.../tools/mcdk/include/mcdk/focus_guard.hpp` creates two remote initialization
  threads during startup and closes each thread handle. The module snapshot is
  also closed. A library is intentionally left loaded for the child's lifetime;
  this is not an explanation for a continually rising handle count.
- `.../tools/mcdk/src/game_process.cpp` owns launcher pipe/NUL handles with
  UniqueHandle and starts the child with handle inheritance enabled. Inheritance
  occurs at launch, and the MCDK parent observed243 handles, so this path does not
  account for168124 later retained game File objects by itself.
- `.../src/reload.cpp` creates a directory handle and one overlapped Event for each
  watched directory, plus a stop Event per watcher thread. These are MCDK-host
  objects, and normal cleanup explicitly closes them. They must not be attributed
  to the game solely because both processes participate in hot reload.
- Generated debug pack `DEBUG_ENV_SCRIPT/IPCSystem.py` creates one listener thread
  at line103 and one TCP socket at116, then uses a50ms recv timeout at119. Normal
  receive-loop exit sets self.sock=None at156 without an explicit close/finally;
  connect failure at118 also lacks an explicit cleanup block. Python socket
  destruction can release the local socket, so absence of an explicit close is
  not proof of a leak. A single retained socket or listener cannot explain the
  measured scale without additional evidence of repeated construction.
- Generated `CALL_ON_CLIENT_THREAD`/`CALL_ON_SERVER_THREAD` allocate threading.Event
  per request, not continuously during idle. The game has only171 Event objects
  in the census, so Event accumulation is not the dominant observed class.
- The loaded-module list showed the existing native_focus_guard.dll under the
  archived r7 directory, plus NVIDIA OpenGL/overlay, Nahimic audio and native game
  DLLs. Loading a module is not causation; no module has been blamed. The guard
  DLL hash matches the root session manifest c22fa0cd0bdbfb7d9218d59573b61619111f9bd180562c9bd51c69276c11c178.

## Read-only tools and next discriminating evidence

`audit_handle_types_readonly.py` verifies PID creation identity and running state,
samples SystemExtendedHandleInformation, and duplicates only one representative
per type index into its own host process for NtQueryObject(TypeInformation).
All duplicates and the process handle are closed. The successful census took
1.182s. The tool now additionally reports distinct objects and multiplicity
distributions; that enhancement has not been retroactively added to old evidence.

`audit_handle_name_readonly.py` resolves one owned handle's name. Its caller must
run it with a short host subprocess timeout because NtQueryObject(NameInformation)
may block for some handle types. A timed-out helper should be stopped locally,
never by terminating or modifying the game. This helper has not yet returned an
owned live handle name.

The next useful evidence, during an independently authorized short owned run, is
two type/multiplicity snapshots plus three names from the dominant mask. Repeated
handles to the same object distinguish duplicate-handle retention from repeated
new object allocation. Names distinguish AFD sockets, named pipes, filesystem
resources and device handles. Keep any future registration, rendering, IPC or
guard control separate from the present source review and from visual acceptance.

## New authorized scaffold-startup sample

Root authorized the same read-only inspection of session2699507492214c3a8d16abb888cb5198,
owner native-r11-scaffold-4096, PID59984, creation134362854334328488. Its session
metadata moved from starting to ready by this census. The reviewer called no game
code. Root planned an SDK/scaffold test separately; exact test timing belongs to
root, so these counts establish no cause from the SDK scan.

`scaffold-startup-handle-types-v1.json` recorded78840 total handles and78077 File
objects. Of these,78023 have0x0016019f. The subsequent fresh table/name sample used
the first, middle and last common-mask entries:164,159256 and316632. Every sampled
name was `\Device\Afd` with NtQueryObject status0. Raw output is preserved in
`scaffold-startup-handle-name-samples-v1.json`. This points to network socket
objects rather than shader/GPU resources; it does not establish which code creates
them and cannot prove every same-mask entry has the same name.

Important limitation: this host's system table returned zero for every kernel
object pointer. The v1 `object_multiplicities` fields therefore misleadingly count
all zero values as a single object and are UNUSABLE. They cannot establish duplicate
handles or distinct allocations. The reviewer immediately fixed the diagnostic
tool to exclude zero pointers and report their count, leaving the v1 raw file
unchanged. Future counts must state when multiplicity is unavailable.

The second creation-bound census `scaffold-ready-handle-types-v2.json` recorded
78842 total handles and exactly the same78077 File /78023 dominant-mask counts.
The revised tool explicitly records all object pointers as zero and supplies no
false multiplicity result. Get-NetTCPConnection returned7 rows including three
listeners, two bound rows, one established loopback connection and one HTTPS
CloseWait row; Get-NetUDPEndpoint returned3 rows. Raw public endpoint metadata is
in `scaffold-ready-network-endpoints-v1.json`. Large AFD object count is therefore
not evidence of tens of thousands of active TCP/UDP endpoints.

Three further successful ObjectBasicInformation samples are recorded in
`scaffold-ready-handle-object-samples-v1.json`. Each same sampled handle has
handle_count2 including the local diagnostic duplicate, hence only one remaining
actual handle for each sampled object at query time. These three samples do not
support a theory that all counts are repeated duplicates of the same socket.
The returned pointer_count65531/65531/58263 is retained as opaque raw evidence and
is not interpreted. Current evidence narrows the affected class toward many
retained AFD socket objects, but does not identify their creation code, age,
connection state or root cause. There is no justified render or SDK-scan blame.
