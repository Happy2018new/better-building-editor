# Single-line native gateway coordinate correction, R20 v9

The v9 clone changes only the candidate world vertex line from
parallaxPositionInWorld=t*viewRay+VIEW_POS to t*viewRay. The viewRay expression
and all other BP/RP/tool source-map entries are identical to measured v8.
v9 source SHA is 436d6fbb806dce614a82fee812d85122ded52079125fbb45abc0cc335567de8d.
The complete before resources, mesh and registries are preserved by commit
ab541a0a in portal-native-coordinates-r20-v1. This package adds the actual
corrected shader, the exact one-line diff and fresh live results.

Exactly two WGC images were captured and manually opened: candidate/front
and native/front at the same camera. Both are fresh, resolved coordinate
stripes. completed, restored, source_unchanged and project_source_unchanged
are true, and cleanup_errors is empty. The starfield detector's two intentional
presence_failures remain recorded because coordinate stripes are not stars.

The 16-layer control is observed. UV.x is within one texel for every sample in
every layer; exact ratios range from 0.8798 to 1.0. Every layer's UV.y fitted
phase is the same value, 5 texels, with all residuals within one. This verifies
the bounded north/front coordinate correction. It does not verify absolute
native star density, brightness, animation speed/direction or other faces.

The initial preflight incorrectly read physical free RAM as the commit gate.
No game had been launched at that point. The correction receipt retains that
mistake. The actual authorized gate is CommitLimit minus CommitTotal, obtained
by the unchanged canonical commit_at_boundary function. Prestart available
commit was 12180901888 bytes; six runtime boundaries all passed 6 GiB, with a
minimum of 8317026304 bytes. Physical RAM is recorded but is not a second gate.

The first normal stop timed out. The exact retained process handles then
recorded MC29416 exit 0xC0000409 and MCDK21756 exit 0 at 2026-10-16 03:00:15
Asia/Shanghai. This is not an accepted normal exit; its cause is not established.
After exact identities were absent, normal stop only finalized metadata.
No force stop was used. Every portal exec ended before releasing MC/WGC.

Offline replay from this package directory:

```powershell
python -B host/analyze_portal_coordinates_r20.py --report observed/report.json --output decoded-replay.json
```

Replay output bytes were compared with observed/decoded.json. The launch map
also binds unchanged sources; this is bounded evidence, not a complete runnable
world/SDK closure. Raw session/start/stop responses remain private. Native
source bytes are preserved without text conversion.

No production profile or product renderer was changed. Appearance, other
faces/views, UI, lifecycle, missing, opacity and animation qualification remain
open. No appearance clone was started after this coordinate run.
