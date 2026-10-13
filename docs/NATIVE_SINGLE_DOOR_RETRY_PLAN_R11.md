# Single Door Pair V12 Plan

Status: prepared for root scheduling review. No v12 native launch has occurred.
The original v11 startup-only failure remains frozen and unaccepted. This plan
uses the reviewed finite supervisor with the one corrected host-launcher pin.
It does not change the door fixture or observation method.

## Sources And Budget

The launcher SHA256 is
`e485a7b24e8d5d3c645d1d39ffcfd3cefa6ba5a7f96c1f5c65034e696a43cfba`,
from commit `ca82cc9`; the root copy was verified equal after integration.
The prepared probe remains SHA256
`6fe41694606a33f6ede15cbccf72f4c4a951dcf424017ce524af1ae0281517a8`.
MCDK, guard DLL, client wrapper and flat creative config retain the approved v11
hashes. The immutable prepared manifest pins the v12 supervisor bytes.

Readiness stays 90 seconds, combined launch/probe work stays 110 seconds and
total supervision stays 150 seconds. Before launch, recheck the actual live
game count through creation identities and `GetExitCodeProcess==259`; permit
one additional game only if the resulting count stays at most five. Recheck all
fixed input hashes and use the fresh owner/name `transforms-r11-door-pair-v12`.
The worktree config currently does not exist and must return to absence.

The launcher discovers the unique MCDK game child and owned listener once.
Later retries verify exact creation identities plus passive IPv4 loopback or
wildcard listener ownership. They preserve SDK errors and use the remaining
deadline per actual network call. This removes repeated discovery cost; it
does not prove world generation will complete within the unchanged deadline.
No longer wait, activation, input, resizing, settings change or resource reload
is introduced.

## One Finite Attempt

After root source review and scheduling release, run only:

```powershell
python -X utf8 tools/run_native_single_door.py .runtime/door-pair-supervised-v12 --shared-root 'D:/Happy2018newの个人文件/GitHub/better-building-editor' --owner transforms-r11-door-pair-v12 --name transforms-r11-door-pair-v12
```

The unchanged probe writes one supported door pair in 17 dry-air reserve cells,
independently records two delayed server/client reads, uses the whole-pair
palette and actual client fronts, and clears all reserve cells. It confirms
player feet unchanged. No strict typed upper state is synthesized, and no
physical orientation acceptance is possible from this diagnostic.

Any readiness or diagnostic failure retains original stdout/stderr and partial
receipts. The supervisor attempts normal owner-bound stop, then inspects exact
creation identities before any force stop. Unpublished game discovery is for
cleanup only and must preserve the original manifest. External input edits
are retained with a restoration refusal. Independently verify both owned
processes absent and input hashes/config restoration afterward.

No automatic repeat follows failure. Data replication success permits only a
report and a separately reviewed next decision; it does not authorize the
complete door-state orientation matrix. The protected frame and other owners'
sessions are not used by the diagnostic.
