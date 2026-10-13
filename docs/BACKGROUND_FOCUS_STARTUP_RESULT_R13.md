# R13 owned background startup repair

The revised test guard reached an actual Minecraft world and initialized the
editor workspace in one bounded cold start, then returned a fresh nonblank
1994x1105 background WGC frame. The exact owned game and MCDK processes were
closed successfully. This enables the separate liquid, snow and item experiments;
it does not qualify their rendering behavior.

The earlier R12 V12 game was actually foreground even though its window had
`WS_EX_NOACTIVATE`. The old guard covered public foreground/active/show/position
entry points but omitted `SetFocus`. Microsoft's
[SetFocus remarks](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setfocus)
explicitly say that it also activates the target window or its parent. That
activation can occur inside user32 and need not pass through the hooked public
`SetActiveWindow` entry point. The revised owned-process guard denies non-null
focus requests, including child controls, with null and `ERROR_ACCESS_DENIED`,
while a null target retains the real focus-release path. This test process runs
without OS keyboard focus; SDK and UI initialization still completed in the
actual smoke. Legacy x64 `SetWindowLongW/A` calls now preserve the noactivation
style as well. The old pointer variants remain guarded.

The launcher injection already occurs while the primary game thread is
suspended, before that thread resumes. That ordering and the launcher acceptance
checks remain unchanged. The host's MCDK style processor already uses
`SWP_NOACTIVATE`, and the smoke configuration does not ask it to move or resize
the game. No foreground restoration, real input or activation fallback was used.

Both native probe threads exercised top-level and child `SetFocus`, explicit
foreground/active/bring requests, window creation, legacy and pointer style
replacement, show and position APIs. The probe verified rejection results and
actual background/focus state. Its module-snapshot retry regression also passed.
The existing 29 launcher tests passed: eight noactivation contracts, eight
background-startup checks and thirteen readiness checks.

The frozen real smoke had one allowed launch, a 120-second readiness budget and
210-second outer limit. Capacity was zero active games plus twenty unchanged
zero-thread/handle/memory/CPU residual NT process rows. It owned session
`67abdfc2f8334ad2857d22455c5b7119`, owner `background-r13-v1`, game PID 48556 with
creation identity `134363429806698631`. All 66 passive observations kept the game
in the background and its visible window nonactivating. Client/server markers,
the initialized `ModernProjectionClientSystem.session`, and player foot
`[0.5, -60.0, 0.5]` passed. The actual image contains the flat world, sky, HUD and
player hand, and was visually inspected. Capture freshness, variance and encoding
checks passed; ShellHost PID 46908 / HWND 34802164 remained foreground. Total
elapsed time was 108.367515 seconds, including ordinary stop and final identity
verification. Both owned process identities were absent, all source/binary pins
remained unchanged, and cleanup errors were empty.

The exact binary pins are:

| Input | SHA-256 |
| --- | --- |
| New guard DLL | `04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93` |
| Existing isolated MCDK | `b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9` |
| Single-WGC helper | `cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8` |
| World PNG | `7beb36b2bd25df15d7627d8de24a3384633c38c2d0a46159292a37c666e6ec40` |

The fresh DLL resides at
`D:/bbe-r13-background/.runtime/native_focus_guard-r13-v1/native_focus_guard.dll`.
It builds from `tools/native_focus_guard/build.ps1` with pinned MinHook v1.3.4 and
the unchanged isolated MCDK path recorded in `plan.json`. The evidence archive
preserves exact smoke source, guard/probe/launcher sources, plan, original image,
capture receipt and observations. Session routing tokens are replaced only in
the explicitly sanitized report and launch receipt; originals remain in the
owned local runtime directory. The index distinguishes sanitized artifacts from
unaltered evidence bytes.

The successful candidate run supports using this guard for the next bounded
experiments. V12 has no native call trace, so it does not prove that `SetFocus`
alone caused that failure. Actual foreground, ownership, readiness and WGC
freshness checks remain necessary for every later run; hidden or style-only
success cannot replace them.
