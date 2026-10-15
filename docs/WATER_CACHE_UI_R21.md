# Water cache and native UI experiment, R21

The stable liquid distance cache experiment passed its narrow request-reuse
contract. The settled-pool S+E experiment is inconclusive for invisible-state
repair because its original S baseline already contains visible water.
Neither experiment qualifies cold construction, the historical 169/230/370/435 ms
stalls, complete clipping/occlusion behavior, or production native parity.

## Offline Replay

This bounded package contains original bytes, 11 native 1994x1105 PNGs and raw
WGC receipts, failed and successful reports, executed wrappers and amendments,
three selected frozen source files, and the complete source fingerprint list.
It excludes the full 3,093-file project and live session credentials. Original
absolute paths in receipts are provenance only; replay reads package files only.
The verifier uses Python's standard library without a game, Windows APIs,
Pillow, NumPy, or external project dependencies.
The package's `.gitattributes` disables text conversion for every payload so
Git preserves the original CRLF/LF bytes on both staging and checkout.

```powershell
python -I -B -X utf8 docs/evidence/water-cache-ui-r21-v1/replay.py --package docs/evidence/water-cache-ui-r21-v1
```

Every payload file is covered by `manifest.json`; the verifier checks the exact
file set, byte lengths and SHA-256 hashes before semantic and pixel replay.
`origins.json` maps byte-exact copies to their original repository paths.

## Cache A/B

Both steady phases have 60 rows after five warmups. Baseline performs 240 source
validations; candidate performs zero. Both have zero native submissions. View
and pose callbacks, renderer validations, publication restoration and snapshots
match. Depth, clip, unclip, invalid request and retry controls completed.
The sampled runtime resource boundaries retain the 6 GiB available commit gate.

The original zero-phase failure is preserved: the embedded Python has no
`hashlib.sha256`, and probing `hashlib.new('sha256', ...)` was unsupported too.
The successful retry returns the exact compiled baseline string and verifies
it byte for byte, hashing on the host only. No game-side SHA success is claimed.
Original frozen host and minimal outer retry remain distinct files.

## S+E And Native Review

Five phases ran in order: S baseline, SE, S restore, SE repeat, final S. Each
has wet and hidden native images; one additional image shows an ordinary
depth step and return. Eight actual front IDs remained stable and unique.
The report records four native uniforms per group, tag 134, and initial/final
logical and native pool equality. The candidate uses `minecraft:cow` only as
the entity API identifier, with unchanged model, scale, rotation and depth -50.

Fixed ROI `(470,354,1540,848)`, maximum channel difference at least 8:

| Phase | Wet minus hidden pixels |
| --- | ---: |
| S baseline | 96,436 |
| SE | 96,436 |
| S restore | 96,436 |
| SE repeat | 96,436 |
| Final S | 96,436 |

Candidate versus baseline, candidate repeat, skeleton restore and final
skeleton wet differences are zero.
Native image review sees coherent water top/sides over stone and no visible cow
geometry. The depth-step label changes by one cell but the water fixture is not
visibly cut, so this image does not qualify comprehensive depth clipping.
`repair_accepted`, `production_qualified`, `initial_construction_qualified` and
`shared_depth_qualified` remain false. The original zero-capture assertion-helper
signature failure and the minimal v2 compatibility amendment are both retained.

Key images in this package: `ui/result/skeleton_baseline_wet.png`,
`ui/result/candidate_wet.png`, `ui/result/candidate_depth_step.png`, and all
paired hidden/restored captures. Raw reports retain their original assessment;
the later `analysis.json` supplies the baseline-visible inconclusive assessment.

## Lifecycle And Limits

Session `d88c93b78e304410b24e1c2feabc6010`, owner
`water-r20-depth-cache-ab-v1`, game PID 8756 creation identity
`134365801198650139`, MCDK PID 48772 identity `134365801196531006`.
One `force=False` normal-close request timed out; no force or repeated close
was used. The retained exact observer then saw game exit `0xC0000409` and MCDK
exit 0 at 07:38:24 Asia/Shanghai on 2026-10-16. Metadata finalized stopped and
not ready. This is **not a clean shutdown**. The raw timeout and nonzero game
exit remain part of the evidence.

All package preparation and replay are offline. No product default was enabled
by this experiment, and source, resource and broader native parity acceptance
remain unqualified. This evidence must not be widened to unrelated fixtures.
