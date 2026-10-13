# R14 evening runtime admission

The user corrected the current round numbering to R14 through 2026-10-13
23:30, followed by R15 through 2026-10-14 07:00. The root owns the hibernation
schedule at that final deadline. This support task does not modify that schedule.

At 2026-10-13 18:38 Asia/Shanghai, ordinary Windows CIM and Get-Process
enumeration returned no Minecraft.Windows.exe process and no game MCDK
launcher. The visible mcdk-asst-lite.exe processes are MCP documentation
helpers, not Minecraft instances. Historical session records still contain
ready states; those records are stale and are not reusable world identities.
This observation does not claim a complete NT handle census or explain why the
previous twenty-one residual process rows disappeared.

The root allocated one active instance each to liquid_product_r13e,
snow_product_r13e, item_product_r13e and scaffold_product_r13e, plus one root
reserve: at most five active games. Background support launches no game.
Each specialist must recheck current capacity before launching and stop its
owned processes when finished. No game activation, resize, desktop input or
foreground fallback is permitted. Failed, stale, black or otherwise unreliable
captures must be explicitly reported.

The following existing binaries were checked again with Get-FileHash on
2026-10-13 before providing the startup recipe:

| Input | Root-relative path | SHA-256 |
| --- | --- | --- |
| Patched MCDK | `.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe` | `b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9` |
| Focus guard | `docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll` | `04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93` |
| Single-WGC helper | `.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe` | `cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8` |

The shared root is
`D:/Happy2018newの个人文件/GitHub/better-building-editor`.
The successful [R13 cold-start result](BACKGROUND_FOCUS_STARTUP_RESULT_R13.md)
and its exact
[supervisor source](evidence/background-focus-r13-v1/sources/smoke-r13.py)
provide the reusable owner-bound recipe. That source is a frozen historical
artifact and must not be edited. A new specialist supervisor should use a
unique owner and output directory, its own project paths, the pins above and
an absolute deadline with cleanup time reserved. The proven smoke uses one
launch, 120 seconds readiness and 210 seconds overall; the independently
prepared scaffold lifecycle supervisor reserves 70 seconds of its 330-second
budget for restoration and process cleanup.

The guarded child command is:

```powershell
python -X utf8 .agents/skills/pyreact-debugging/scripts/instances.py start `
  --project '<owned project>' --owner '<unique owner>' --name '<unique name>' `
  --preset ui --wait 120 `
  --mcdk '<shared root>/.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe' `
  --noactivate-dll '<shared root>/docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll' `
  --noactivate-sha256 '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93' `
  --noactivate-mcdk-sha256 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9' `
  --game-exe 'D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/Minecraft.Windows.exe'
```

The enclosing supervisor must observe owned foreground/noactivation state
while launch is pending, validate the returned client/server session markers,
and terminate only exact owned process creation identities on a deadline or
contract failure. An ordinary unguarded launch is not an equivalent fallback.
The project config should mount its owned project or minimal diagnostic pack,
use world_type 2, seed 0 and creative mode 1, disable hot reload during a frozen
run, and omit window-size/position requests. WGC calls must pass the explicit
helper above because worktrees do not inherit the root's ignored runtime tree.

No new Minecraft was launched to prepare this admission record. No session,
production resources, global TODOs, protected probes or hibernation schedule
was modified.
