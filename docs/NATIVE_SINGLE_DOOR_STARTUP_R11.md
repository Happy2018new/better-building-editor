# Single Door Startup Failure R11

The one authorized whole-pair launch on October 13, 2026 failed before the door
probe ran. Session `9d11924b3f56457a83b760fc46c15dce`, owner
`transforms-r11-door-pair-v11`, used the approved MCDK and noactivation DLL,
90-second readiness window, 110-second work budget and 150-second total bound.
The supervisor finished in 109.367 seconds. Door data replication, typed client
coverage and physical orientation remain untested. There was no fixture write
or screenshot, so neither fixture restoration nor capture reliability is claimed.

Exact launch stdout, supervisor receipt, MCDK log, used launch sources/config,
unexecuted prepared probe and the later host fix are frozen under
`tools/data/native_single_door_startup_r11_v11/`. The manifest pins their raw
hashes. The successful frame log was copied read-only; no SDK request or input
was sent to that session.

## Startup Evidence

Times are Asia/Shanghai. Successful frame session
`773c643b5cf344918e04d8b4eef2657a` is a comparison, not new door evidence.

| Stage | Successful frame | Door attempt |
| --- | --- | --- |
| MCP / IPC listener started | 22:52:11, ports 53100 / 53101 | 01:04:12, ports 62363 / 62368 |
| Server Mod initialized | Before 22:53:07 | Before 01:05:36 |
| World generation started | 22:53:07.105 | 01:05:38.253 |
| Client Mod / IPC socket connected | Around 22:53:10.753 | Around 01:05:41.331 |
| Runtime binding | 22:53:12, three tool calls; ready manifest | Last attempt 01:05:40, before IPC connect; no verified return |
| World generation completed | 22:53:14.608 | No recorded completion |
| In-game screen / HUD | 22:53:18 | No recorded in-game screen or HUD |

The door MCP endpoint handled eight initialization/list/tool-call rounds with
HTTP 200 from 01:04:37 through 01:05:40. Listener discovery and MCP transport were
already working. The final discovery attempt 11 received only 1.507 seconds of
remaining readiness time, took 1.643 seconds and raised `TimeoutExpired`. It
ran after the final attempted SDK read and while the client's IPC connection
was arriving. It replaced `last_error`; the old launcher did not preserve the
previous SDK result or its full error. A successful HTTP tool call is not a
successful game RPC.

The C++ code executor in `tools/mcdk/src/game_process.cpp` rejects execution
when `getClientCount()==0`, before sending JSON IPC. The Python IPC connect log
marks a socket connection, not a successful native SDK return. Both Mod sides
initialized on this attempt, but completed world loading and client/server RPC
readiness cannot be inferred. The `get_world_record` / `user_mgr` errors also
occur in the successful frame log, so they do not explain this failure alone.
Only the door log has the shown logging rollover `WindowsError 32`; no measured
causal connection to loading time is available.

## Cleanup

Normal owner-bound stop returned 1 with "Game has not closed". The supervisor
then inspected the exact own creation identities and its force stop returned 0.
Game PID 45640 / creation `134362982526790886` and MCDK PID 24804 / creation
`134362982524244758` were independently absent after shutdown and again at
01:22:58. Frame PID 44536 retained creation `134362903316974407`. Foreground
remained ChatGPT and the owned window retained noactivation.

Both temporary wrappers restored their original hashes, and the originally
absent worktree `.mcdev.json` was removed. The later authorized edit to the own
launcher is a code fix, not a failed restoration; `cleanup-audit.json` separates
these observations. No cleanup error occurred.

## Narrow Host Fix

Prepared commit `ca82cc9` reuses the first unique child and owned listener
discovery. Later retries verify both exact process creation identities and use
the existing passive `GetExtendedTcpTable` approach with `AF_INET` and
`TCP_TABLE_OWNER_PID_LISTENER`. Only the requested IPv4 loopback or wildcard
listener is accepted. No later full CIM scan can consume the final budget.
Identity changes and another listener owner stop readiness without dispatching
another SDK request or terminating an unrelated process.

Each initialization, notification, tools-list, SDK POST and session DELETE uses
the remaining deadline. Requests are refused after the deadline, and responses
arriving after it cannot establish readiness. SDK phase, complete error text
and raw JSON-RPC errors are retained separately from discovery failures. The
90/110/150 limits are unchanged. Thirteen fault tests cover late IPC, PID reuse,
listener takeover/disappearance, initial discovery timeout, automatic network
calls, deadline handling and IPv4 listener decoding; eight existing guard tests
also pass. The source is frozen as `instances-fix-prepared.py` and has not been
used in a new native launch.

The next decision is review of this host fix and any separately assigned finite
startup test. The door replication gate is still closed; no full door-state or
physical orientation matrix follows from this attempt.
