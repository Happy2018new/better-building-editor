# Native Snow Startup V6 Result

The single V6 attempt satisfied the launcher-ready and visible-world-frame
startup prerequisite. It did not validate plant alpha, snow coverage, native
offsets, the position registry, resource health, or production acceptance.
No fixture, camera mutation, movement, health SDK probe, matrix or relaunch
was performed. The final launcher exit code is zero and `ready=true`; the 96
retained historical SDK errors are not the final launcher result.

## Frozen Inputs And Archive

- Executed plan SHA256:
  `0c1fde7a4d32b0b090736fbd98f7a9131b5e267c04692bd4da21c30ef52bc19b`.
- Supervisor SHA256:
  `944371ef0f471c1a4e7303b6e8a2d4747f2752c5c0aebf84992cb3212dc52554`.
- Actual CRLF readiness launcher SHA256:
  `e485a7b24e8d5d3c645d1d39ffcfd3cefa6ba5a7f96c1f5c65034e696a43cfba`;
  its reviewed e757ef5 Git LF bytes have SHA256
  `094188df49b1f733def68cc5dd1ceeaa3d4856bc3f426c96c3aada0366337712`.
- Final supervisor receipt SHA256:
  `b86063aede969c68fd8a6e4a06fec07a070ff2c4113bff77be51d6b383b53968`.
- Archive: `tools/data/snow-passive-startup-r12-v6`, 110 original file copies,
  plus generated post-cleanup verification and hash inventory. Originals in
  `.runtime` and the managed session directory remain intact.
- Archive index SHA256:
  `20242b53ece872809929a9dded38ea3a2edaedb6a7551dd900bdfd8f64ae0734`.
- Post-cleanup verification SHA256:
  `801dd08b632955a31ca2eae2cd2b3df43f7581161694b57541ec53bb0afaa153`.

The archive includes all seven original PNGs and capture receipts, launcher
stdout/stderr, supervisor receipt, backups and marker journal, all four
passive handle snapshots, exact V6/V5-final and handle-observer freezes,
executed input copies, historical final session manifest, instance config,
logs, and world pack references. Frozen file hashes were verified before
copying; source and destination hashes were compared after each copy.

## First Capture Results

Session `038844c8f42a436aa1474086ce66f8bb`, owner `snow-r12-passive`, ran
approximately 2026-10-13 02:32:04 through 02:34:05 Asia/Shanghai. The game was
PID 62696, creation identity `134363035328996422`; MCDK was PID 44228,
creation identity `134363035326797077`.

The first scheduled target was locked to 1 second before capture. PID
publication was late, so its actual game age was 17.566 seconds. The native
1994x1105 image was black and failed the nonblank check. Targets 15, 30, 45
and 60 were also black. That first failure remains in the archive and was
never replaced. Target 75 passed nonblank capture but visibly showed a
loading screen; its before/after manifest state was still `starting`.

The first post-ready target was locked to 90 before capture. At actual game
age 90.128 seconds it passed before/after owned identity, ready manifest,
IPv4 owned TCP pair, physical DPI-space dimensions, fresh native WGC and
nonblank checks. The opened PNG visibly shows the flat grass world, chest,
torches, player hand and HUD, without a loading overlay, on version 1.21.120.

- Selected image: `run/startup-090.png`, SHA256
  `d1a7f464984e7d429517902e7f076b391b55d2310fbbdf1958a12958645b74f5`.
- Selected receipt: `run/startup-090.startup.json`, SHA256
  `be4cabbab49ecc8eaa20227286fa75d9bbee0a1d8119f7d5b3467753d5f740b8`.
- First image: `run/startup-001.png`, SHA256
  `2813e22852cc4cf13c233d49b92af9b7034f931c02824211f5e84690af65d18d`.

Target 105 was not attempted. The launcher's final `error` is null; the last
historic SDK error says the player may not be in game or the target may be
unavailable. Both required client/server session probes ultimately passed.
Foreground ChatGPT remained unchanged.

## Deadlines And Cleanup

The frozen parent limits were 150 seconds total, observation through 110,
40 reserved for cleanup, and launcher wait 90. Preparation took 2.487
seconds; launcher start was at parent 4.136, final launcher result at 90.755,
and observation ended at 110.000 seconds. The whole run finished at 121.053
seconds with `deadline_exceeded=false` and no cleanup errors. These measured
limits are not an independent operating-system hard watchdog: synchronous
WinAPI and filesystem operations remain outside that guarantee.

Normal owned close returned "Game has not closed". The supervisor then
rechecked the exact owned creation/executable identities and terminated only
those two processes using the same verified handles. Both bounded native
waits returned zero; final owned alive/mismatch lists were empty. The final
passive snapshot independently recorded both as dead.

At 02:48:07, a further host-only identity check again found both owned PIDs
absent. Protected session 773c's game PID 44536 and MCDK PID 42372 still
matched their original creation identities. No protected SDK, WGC or process
mutation was performed. The archived manifest retains historical `ready`
state; it is not evidence of current liveness.

Both runtime scripts and `.mcdev.json` match their original backup hashes;
the own marker's original absence and the native flower texture hash were
restored. The pre-marker inventory matches all 1432 BP/RP files, with zero
added, missing or changed files.

## Passive Resource Observations

The separately frozen host observer did not change V6. Its prospective stop
rule required two consecutive intervals, each increasing by at least 5000
handles at at least 200 handles/second. This rule did not trigger.

| Local Time | Game Handles | MCDK Handles | Observation |
| --- | ---: | ---: | --- |
| 02:32:54.010 | 35345 | 229 | First available sample |
| 02:33:27.727 | 64847 | 229 | +29502 in 33.718 s, 874.969/s |
| 02:33:44.064 | 66566 | 233 | +1719 in 16.337 s, 105.222/s |
| 02:34:06.681 | unavailable | unavailable | Both exact owned processes dead |

The first sample was late, around parent T50/game age 41; no creation-time
baseline exists. The first follow-up was 33.718 rather than 15 seconds later,
and there was no live sample immediately before cleanup. Four samples are
within the maximum six. 66566 is the maximum observed count, not a lifetime
peak or proof of continuous stability. Counts are substantial; resource
health remains unaccepted and no cause is attributed.

The existing 29 positive states, 232 height observations and eight actual
negative lower-half states are unchanged. Position-registry acceptance and
native-offset recovery remain false. The separately documented h0 four-state
proposal requires a new finite executable plan and coordination; this result
does not authorize another launch.
