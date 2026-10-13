# New-IPC owned handle review

Scope: root-authorized creation-bound, read-only type counts and at most three
name samples per live owned game. No game code, mutable MCP, network-content
reads, source-handle close, hooks, game launch/stop, reload or binary replacement.
All target process handles and local duplicates opened by the helpers are closed.
Only the independently launched, explicitly supplied processes below were read.

## Samples

Times are Asia/Shanghai on 2026-10-12, derived from each raw captured_at_unix.
The new MCDK binary recorded by the two agent sessions is
`b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9`.
The revised generated IPC source raw SHA was independently reported by root and
owners as `aa37dc422b869936d34380c23f81a8fb1b0ca3b8cd12aed781efa929c9c91e8c`.
This reviewer did not recapture those generated modules from the games.

| Owned Game | Creation Identity | Time | Total | File | 0x0016019f |
| --- | --- | --- | --- | --- | --- |
| Root smoke PID57476 | 134362880770762084 | 22:26:27.690 | 830 | 69 | 12 |
| Root smoke PID57476 | 134362880770762084 | 22:29:04.168 | 827 | 70 | 12 |
| Frame-family PID28912 | 134362886915447443 | 22:29:56.524 | 57225 | 56461 | 56407 |
| Entities retry PID4412 | 134362890549409242 | 22:31:54.421 | 52074 | 51441 | 51395 |

Root smoke identity was supplied by root. The frame session was
`4ddf0c3d571d4eb5af8ce126effc1918`, owner `frame-r11-background`; its owner
authorized the sample while independently requesting stop. The entities session
was `ba42e62369a441f189f5f8091a9f737f`, owner
`entities-r11-shelf-slot5-retry1`; its owner supplied identity during its already
authorized bounded startup. Neither agent launched for this review.

The root type snapshots took 0.317s and 0.177s; frame took 0.226s and entities
0.351s. There was no per-handle name dump. The root first/middle/last candidate
handles 560/2352/3740 all resolved to `\Device\Afd`, status0. Their basic
handle_count values including the local diagnostic duplicate were 3/2/2.
The entities first/middle/last candidate handles 572/105816/209224 also all
resolved to `\Device\Afd`, status0, with basic handle_count3/2/2. Name batches
took 0.665s and 0.777s. They were individually bounded by a four-second local
helper timeout. These names establish the sampled objects, not every same-mask
entry. The large entities population is consistent with many AFD objects; no
creation code, allocation stack, connection state or active-endpoint count was
captured here.

The frame name batch and second census refused before target-object queries
because its owned process was no longer running. No name file was produced, and
there is no within-session growth difference for frame or entities. Their owners
independently stopped them; this reviewer did not stop or relaunch them. The
earlier entities PID27208 was independently confirmed absent and never read.

Every returned kernel object pointer was zero. Object multiplicity is therefore
unavailable; zero-pointer exclusion in the helper prevents misleading counts.
Object type index56 remained unresolved: DuplicateHandle returned error50.
It accounts for228 entries in root/frame and206 in the entities startup. Its
entries have not been silently classified.

## Startup Timing

Entities census/name capture was 22:31:54.421 / 22:31:55.785. Its retained
`mcdk.log` subsequently shows ModernProjection Server Init adjacent to
22:32:03.831 and Client Init between the timestamped22:32:07.760 and22:32:08.928
lines. There is no `[IPCSystem] connected` line in that retained log. Thus the
observed high population predates those business client initialization logs.
Logging is not an allocation trace, and absent connection logging alone does not
prove the debug module was never imported or that no attempt occurred.

The frame retained log has exactly one IPC connected line, to port56716. It has
separate host HTTP MCP session create/terminate pairs during readiness polling.
Its owner reported stale WGC game time and an owner-binding read timeout before
fixture mutation. These observations establish neither socket provenance nor a
render/material root cause.

## Source Lifecycle Review

The exact patched template LF SHA is
`07116d149b80f7b7176806fcb27608e8d421a1ac62b3770e1abccdc20b127520`.
Searching all included debug-pack Python finds only one socket constructor:
IPCSystem.py:120. ON_CLIENT_INIT at518-521 calls start; client loader destroy
calls ON_CLIENT_EXIT/close. The receiver creates a socket once per listener and
does not reconstruct it on receive timeout, JSON dispatch or reload packet
dispatch. Its finally block closes it on listener exit/connect failure.
The existing start method still has a scheduling race: multiple calls before a
worker stores self.sock can schedule multiple workers. There is no live evidence
of repeated start calls at the scale of these populations.

Game.py reload operations call xupdate, refresh_addons, restart_local_game and
shader reload. They do not directly create Python sockets. External SDK/engine
internals reached by these calls were not inspected or attributed. Config.py
defaults log protocol0 (stdio); modMain wraps the inherited output stream when
that protocol is selected. The SDK's own Safaia log names do not establish that
MCDK selected its optional Safaia host receiver.

Host src/reload.cpp creates directory File and Event handles in MCDK, one set per
watched directory, with cleanup. They are not game AFD objects by ownership.
tools/mcdk/src/host_bridge.cpp creates host-side connections on retry, closes a
failed connect immediately, and shutdown/closes each completed connection before
retrying. src/debug.cpp accepts game IPC on MCDK and closes it in eraseClient or
stop. These host objects are distinct from the target game handle census.

The actual local mcdk.py Client performs each HTTP POST in `with
self.opener.open(...) as response`, reads the response there, and terminates MCP
session by DELETE in close. Readiness polls can create multiple short host TCP
connections, but the client lives in a host Python process. Binding checks use
execute_code routed over the already connected game IPC. No source path found
creates a new game socket per HTTP readiness poll. This is a source observation,
not verification of cpp-mcp, embedded sockets or native engine internals.

## Reproducible Host Experiment

`probe_ipc_socket_lifecycle_host.py` pins the actual patched class and uses the
existing test AST loader/FakeSocket, without game imports or real connections.
`ipc-socket-lifecycle-host-v1.json` records:

| Case | Socket Constructions | Closed Instances | Retained Instances |
| --- | --- | --- | --- |
| 10000 idle timeouts in one listener | 1 | 1 | 0 |
| 10000 type100 packet dispatches in one listener | 1 | 1 | 0 |
| 100 sequential EOF listener lifecycles | 100 | 100 | 0 |
| 100 sequential connect-failure lifecycles | 100 | 100 | 0 |
| 8 starts before worker entry | 8 | 8 | 0 |

The request case counts actual listener dispatch but replaces the JSON handler
with a payload counter. It does not exercise API calls or response writes.
The deferred start case confirms the already known source race, then executes
workers sequentially; it does not simulate simultaneous connected workers.
All assertions passed. These counters are not Windows handle measurements and
do not verify the game Python2 socket implementation or engine networking.

Run from repository root:

```powershell
python -X utf8 .runtime/frame-material-review-r11/probe_ipc_socket_lifecycle_host.py --output <fresh-host-json-path>
```

## Bounded Conclusion

The revised binary can coexist with low stable ready-game counts and with large
startup File/AFD populations in separate owned sessions. The IPC framing repair
does not establish a solution or cause for the handle phenomenon. High AFD
population occurred in an entities startup without the frame family's temporary
marker experiment, so that marker is not a necessary observed condition.
Hot-reload directory watchers are host-owned; their possible indirect relation
still requires a controlled comparison. Root owns any next launch/control choice.
The discriminating next evidence is phase-bound small type/name snapshots during
an otherwise fixed startup, or an explicitly authorized allocation trace. This
review supplies no guessed shader, SDK, guard, network or IPC root cause.
