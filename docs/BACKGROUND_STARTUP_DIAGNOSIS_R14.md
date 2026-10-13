# R14 shared startup diagnosis

All timestamps below are Asia/Shanghai on 2026-10-13. This checkpoint records
failed admission, not a successful editor, projection or material validation.

Three full-pack sessions crashed before world IPC, and no new engine log was
created for those launches. Windows Error Reporting identifies the same
Minecraft.Windows.exe 1.21.120.0 native access violation, c0000005, at offset
0000000000803a90:

| Lane | Owner | Game PID | WER time | WER report ID |
| --- | --- | --- | --- | --- |
| Water | water-product-r14-v1 | 12108 | 19:10:37 | 21802aad-035d-4f8e-b901-7467257262ae |
| Item | item-product-r14-v1 | 35464 | 19:12:28 | 0fe80270-141d-4226-ab3d-76d33a5d9146 |
| Snow | snow-centered-r14-product-v1 | 22992 | 19:15:37 | b7da330f-3213-41fd-bbfc-7fe54375dade |

All used the approved noactivation guard and patched MCDK, retained background
window protection, and were cleaned by exact process creation identity. A
launcher identity-change error reflects the real process exit; relaxing that
check would not repair startup. The archives contain WER text but no accessible
minidump or engine stack identifying the failing routine. Protected executable
bytes at the WER offset do not provide usable source-level attribution.

Water and item included the new sword resources. Snow HEAD c42f9ad2 was based
on 52189693 and did not include those resources, so the new sword resource
commit is not a necessary condition for the three failures. A full resource
bundle problem remains a hypothesis, not an established cause.

An earlier minimal-BP scaffold control reached a real world and WGC at
18:51-18:53. Its later shutdown WER was a separate ucrtbase.dll c0000409 fault;
it must not be merged with the three Minecraft startup access violations.

## First minimal contrast

The root authorized exactly one read-only minimal-BP contrast, owner
background-minimal-r14-preworld-v1, beginning at 19:25:03. It created game PID
16392 and fresh engine log Debug_Log2026-10-13_19-25-30.txt. The log reaches
OnAppStart/initMultiplayerRequestHandler. No Minecraft WER was found after
19:20 at the 19:29 check.

This is a changed observation, but not healthy-world admission: the observer's
manifest read raised PermissionError after roughly 34 seconds. It was stopped
at 45.1 seconds; game and MCDK identities then returned null, the private config
was removed only after its bytes matched, and background protection remained
valid. No reliable screenshot, palette result or world-ready result exists.

The failed supervisor scanned registry manifests using unguarded read_bytes
while instances.py publishes JSON by temporary-file replacement. Transient
file unreadability is observed; a replacement/sharing race is plausible, but
the original report did not preserve winerror and does not prove that cause.
Original ignored reports, logs, plan and supervisor remain unchanged locally.
They contain session secrets and unrelated foreground metadata, so they are
not committed verbatim.

## Changed-condition contrast

The root authorized one further serial minimal control in its reserved game
slot after fixing only the manifest-reader failure. Other game starts are held.
[managed_registry_snapshot.py](../tools/managed_registry_snapshot.py) permits
at most two seconds for an owner/project snapshot and retries only
PermissionError. Its callback preserves the read stage, attempt and OS error
codes and rechecks the already-bound process identity and background guard.
Permanent denial, invalid JSON, schema/path mismatch, duplicate owner sessions,
missing files and other I/O errors still fail. It never launches or replays SDK
calls and never returns a cached session as current.

[run_minimal_startup_control_r14.py](../tools/run_minimal_startup_control_r14.py)
is frozen before launch. It permits one startup, reserves cleanup time, and
retains all existing process and background checks. If real client admission
succeeds, it uses the exact frozen scaffold pure-read probe for loaded ground
and natural air, then attempts one WGC image and stops its exact owned game.
No blocks, actors, inventory or product render resources are modified.

Ten offline regression cases cover transient recovery, persistent denial,
callback guard failure, wrong bindings, ambiguity, malformed data and bounded
time. Their pass does not establish native startup or visual acceptance. The
second native control and actual image review will be recorded separately.

## Second minimal result

The changed-condition minimal run completed in 80.3 seconds. Client UiInit was
true, 83 render ticks were recorded, and loaded player feet were (0.5, -60.0,
0.5). The frozen server probe read real grass at (0, -61, 0) and natural air at
(4, -58, 4). For natural air, GetBlockStates returned None; the raw palette
independently contained air in common and its empty state dictionary, with
empty extra, extraStates and actor maps. Those observations remain distinct.

WGC returned a fresh native 1994 by 1105 frame. Actual image inspection shows
the flat grass world, sky, player hand and HUD, with no black frame or loading
popup. All recorded guards remained valid, the foreground stayed unchanged
through capture, and game/MCDK identities were null after exact cleanup.
[Sanitized result](evidence/background-startup-contrast-r14-v2/result.json),
the exact supervisor sources, plan and PNG are preserved separately. This is
startup and native palette evidence, not editor or projection acceptance.

No startup access violation occurred. A later shutdown WER at 19:37:14 reports
ucrtbase.dll c0000409 at 00000000000a527e, report
b822c2cd-a1eb-4754-84ec-72d756ee6c8c. This matches the earlier minimal control's
shutdown signature and is separate from the full-pack startup faults.

The root authorized one further serial baseline-52189693 full-pack contrast.
Its BP/RP tracked files must exactly match that commit; no diagnostic resource
pack is added. Client readiness reads existing UiInitFinished-created
session/hud fields, followed by the same frozen server pure-read probe, WGC
and exact cleanup. All other starts remain held. Healthy minimal startup does
not prove which resource, concurrency condition or shared startup state caused
the earlier failures.

## Serial baseline result

The exact baseline full-pack control failed in 37.0 seconds, before world IPC
or any fresh engine log. Tracked BP/RP bytes matched 52189693 and all 1,362
source pins were unchanged after cleanup. MCDK listed only the existing Mod
BP/RP, its debug BP and the owner-bound session probe. The game was PID 24552;
both its identity and the MCDK identity were null after cleanup.

The WER signature changed: Event 1000 at 19:44:04 names unknown as the fault
module, c0000005, address 000000014f932aa0. Event 1001 at 19:44:14 records BEX64,
StackHash_9a2a, PCH_3F_FROM_ntdll+0x0000000000161914 and exception data
0000000000000008, report fb21b237-6581-403e-9200-5a0199768286. The WER archive
again contains only text, with no accessible minidump. This is not a repeat of
the earlier Minecraft module offset. No screenshot or native product acceptance
is claimed. [Sanitized result and frozen inputs](evidence/background-baseline-startup-r14-v1/result.json)
preserve this failure separately.

The baseline failure shows that this round's added resources are not required
for failed admission and that serial execution alone is not sufficient. It
does not establish a particular RP or BP defect. The root authorized exactly
one next contrast: the previously healthy minimal diagnostic BP together with
an exact private copy of baseline 52189693 RP, omitting the original Mod BP.
That run retains the existing guarded process, registry, deadline and cleanup
contracts; both original and mounted resource bytes are checked for drift.
