# Offline Startup Comparison R11

The alpha startup failed because the inspected MCDK code observed zero debug
IPC clients at its failed readiness read. The cause of those zero connections
is still unknown. This offline task did not launch a game, invoke the observer,
connect to MCP/private IPC, or inspect a live game window or process. Healthy
session `773c643b5cf344918e04d8b4eef2657a` was accessed through saved files only;
its live runtime remains owned by frame.

The generated healthy debug pack, generated failed debug pack and installed
debug source have the same 17 files and SHA-256 hashes. The debug UUID/version,
project manifests and corresponding world links agree. Both manifests contain
the same dependency UUID `48199e63-9544-494a-90ab-2864e8f37f39`, absent from both
observed world pack lists; that shared metadata cannot establish a
failure-specific dependency cause. Session-probe UUIDs, module names, tokens,
paths and world names differ as expected for isolated sessions. File existence
and matching hashes do not prove that the failed engine loaded those files.

The effective configs differ in session paths, world identity and MCP port.
Healthy config explicitly disables daylight/weather cycles; failed config omits
both fields. Flat world, creative mode and disabled hot reload settings match.
After failure cleanup the resource trees match all 709 files. Current behavior
trees have seven differing projection files and one additional
`plant_position.py`: the destination-origin adapter and related rendering
paths. These are post-cleanup observations. They do not prove controlled
prelaunch source equality or rule out application import/init failure.

## Connection And Logging Chain

The portable source anchors in `analysis.json` bind these observations:

1. `game_process.cpp:204` returns the exact failure when client count is zero.
   Startup used direct return, so the failed read did not reach request framing.
2. The failed log records MCP port `52112` and debug listener port `52115`.
   The debug port must come from its listener log, not `MCP + 1`.
3. Inspected MCDK source starts the listener, inserts its port into
   `MCDEV_DEBUG_IPC_PORT`, builds a UTF-16 child environment and passes that block
   to `CreateProcessW`. The environment builder filters inherited `MCDEV_`
   entries and applies explicit overrides. This weakens a stale inherited-port
   explanation, but the actual failed child's environment was not recorded.
4. The generated client loader invokes its before hooks from the first
   `LoaderSystem.Update`, then `ON_CLIENT_INIT` creates the client component and
   starts the socket thread. Server initialization alone does not connect.
   Missing/invalid port makes `start()` return silently. The client makes one
   IPv4 `localhost` connection attempt and has no automatic reconnect.
5. MCDK filters pipe output to lines containing `[Python]` when debug mod
   inclusion is enabled. The failed log has zero such lines. That cannot prove
   that the native engine produced no loading/error output before Python's
   output wrapper was installed.

Healthy resource-pack completion is recorded 55.40356 seconds after game
creation, and world-generation completion at 62.91056 seconds. Its IPC
connected print appears among nearby 22:53:10 lines but has no timestamp of its
own. This makes startup delay around a 60-second gate plausible without proving
the failed engine's actual state. No failed-startup pixels were captured.
Remaining candidates include slow/stalled native loading, missing client
initialization, loader/import/environment failure, one failed socket connect,
or a disconnect before the observed reads. No texture or geometry cause was
established.

## Prepared Passive Observer

`tools/observe_owned_startup.py` takes one host-only snapshot. It separately
permits `starting`, `failed` and `ready` manifests while verifying explicit
owner/project/manifest bindings, both live PID creation identities, actual
executable paths and the current visible background nonactivating window.
It leaves the standard ready-only loader and standard capture client unchanged.

The observer reads the IPv4 TCP ownership table, retains only the two owned
processes' endpoints at the logged debug port, and records an observed listener
or matching established pair. It never connects to the private IPC port or
calls SDK/MCP. An established OS pair is not an SDK-ready result, and passive
sampling can miss a transient connection or disconnect.

The only capture program permitted is the archived single-WGC executable at
`.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe`,
SHA-256 `cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8`.
The observer checks ownership and guards before and after capture. It rejects
foreground, minimized, undersized, rebound or resized windows, dead/reused
processes, stale frames, blank pixels and timeouts. Failed receipts and any
produced pixels remain available. It does not activate, restore, resize, send
input, launch/stop a game, replay a mutation or choose a fallback backend.

For a future reviewed run, invoke one snapshot with an explicit owned session:

```powershell
python tools/observe_owned_startup.py --session <owned-session-file> --owner <owner> --project <owned-project> --output <fresh-startup-frame.png>
```

The prepared `passive-startup-plan.json` proposes one launch, a 150-second total
external supervisor budget, startup observation through 120 seconds and 30
seconds reserved for identity-bound cleanup. A 90-second launcher gate and
nonoverlapping samples near 1/15/30/45/60/75/90/105 seconds would preserve screen
and connection evidence even when readiness fails. The supervisor must hold
effective config, source trees, manifests, texture condition and binary hashes
fixed. It must reserve remaining cleanup time and stop only its verified owned
processes. This plan is prepared for root review and was not executed.

## Portable Evidence

`tools/data/plant-ipc-offline-r11-v1/index.json` binds 76 payloads, including the
unchanged original comparison, saved healthy/failed logs and configs, full debug
source, inspected MCDK source, observed manifest files, differing current
projection files, observer source/tests and the future passive plan. Its index
SHA-256 is `f4686f31985c5f4adc1a23f0265a5422bb71deba3a90640a2788e357b694952b`.
The comparison SHA-256 remains
`aec5c563c7cab0b65be51d779610e22783951b36d1e57103c67ff89c98f18d28`.
Archived source comparisons are historical file receipts, not live runtime
recertification. Archive integrity and inference limits are checked offline by
`tests/test_plant_ipc_offline_evidence_r11.py`. The observer's host-mocked tests
do not certify actual Windows capture or TCP-table calls; that verification is
reserved for the next reviewed owned run.

Accepted production scope remains 29 positive states / 232 height observations
and eight observed negative lower-half states. Seed-name false rows remain
unobserved. The original native unit-cell ROI, 0.75 recall/precision and 3-pixel
tolerance are unchanged. No native mesh pivot/hash/offset formula, marker
pixels, holdout acceptance or production position registry was recovered.
