# Fixed Water Alpha Controls, R21

Production water remains unqualified and disabled. This standalone offline
package preserves the single-launch, four-case `full` water alpha batch from
session `e3a78811b489447b92972a2ad37485e5`, owned by `water-r21-alpha-v1`.
The fence, glass pane, slab, and stairs have 24 base records, eight visibility
frames, and 24 alpha frames: 56 original WGC PNGs. Six original native stone
calibration PNGs from the same session are also included. No `missing` batch
was run in this session.

The batch completed in 188.24420040000405 seconds with `completed`, `restored`,
and `source_unchanged` true and no cleanup errors. All 56 batch receipts are
reliable, background-safe, foreground-unchanged, and guarded against agent
activation. No game or capture host was suspended; the agent did not activate,
move, resize, or reorder a window. The launch and phase receipts retain the
canonical 9 GiB launch and 6 GiB runtime commit checks, including their actual
observations. The 3093-file launch source digest is
`cb2b32de68b69f435d69b59cf296d8492d88984ddb96e10f020d7fdbd0aef806`.

Both the original analytic projection and the explicitly requested native
stone projection produce valid evidence and pass all four fixed alpha
controls. Each uses alpha 0, 0.25, 0.45, 0.75, 1, and default without changing
the recorded geometry context. Their original per-region eligible counts,
endpoint RGB RMSE, body/water pixel counts, and default RMSE are retained.
The largest endpoint RGB RMSE is 0.33723914994091886 for the original model
and 0.3329177545908885 for the native model. Default versus 0.45 has RMSE zero
in every measured region. The unchanged alpha pass limit is RGB RMSE 3.

The native camera model uses only 24 measured stone corners, never fitted
water pixels. It has effective vertical FOV 65.9053871768296 degrees and a
maximum fitted residual of 0.00008354775673069526 physical pixels. This batch
does not establish native shape, UV, alpha, or style parity. Its wet-only
cases do not form a standalone geometry gate, and its frozen phases do not
measure animation. All native admission fields and `production_qualified`
remain false. The passing fence body/rear contribution diagnostic is kept
separate from native appearance admission.

The first normal stop timed out. Exact retained process handles then observed
game PID 7220 (creation identity `134365646578707893`) exit with `0xC0000409`
and MCDK PID 42548 (identity `134365646576717602`) exit with zero. A second
normal stop finalized the registry as stopped. No force was used. The raw WER
records `BEX64 / ucrtbase.dll / c0000409`, ReportIdentifier
`708c5be0-5432-4b23-a21a-1c0abf287e7d`, and AppSessionGuid beginning
`00001c34`, which binds PID 7220. This is not a clean game exit and does not
establish a cause for the failure.

## Replay

Python 3.13 was used. `requirements.txt` records the NumPy, Pillow, and SciPy
versions used when freezing this package. From any working directory:

```text
python -I -B /path/to/water-alpha-r21-v1/verify_package.py
python -I -B /path/to/water-alpha-r21-v1/verify_package.py --pixels
```

The first command checks every packaged byte, original capture receipts,
source and host bindings, resource gates, restoration, stop failures, exact
exit codes, and WER. `--pixels` additionally reruns both frozen analyzers and
the stone camera fit and compares their original metrics. It creates only
temporary rebased report copies and a disk-backed decoded-image cache.
The six pure stone silhouette and convex-hull functions are compiled directly
from their original frozen AST definitions, with their original Pillow and
`deque` globals. Their live acquisition modules are not imported; no function
body is rewritten or replaced by a stub.
Both complete host helper files and their launch-source counterparts are kept.
The verifier checks that the six selected function definitions have identical
ASTs; the host camera module's additional finalization error handling is not
misrepresented as the launch entrypoint's complete file hash.
Original reports, original absolute paths, source maps, and hashes are never
rewritten. No game, MCDK, Windows capture API, registry, sibling evidence
package, or checkout is required for replay.

To keep this package small, it includes the exact Python dependency closure
needed for analysis and the original acquisition entrypoints and hull helper,
alongside the real 3093-file launch hash receipt. It does not include all launch resources or a
relaunchable game clone. `code-bindings.json` distinguishes files frozen by
the executed host plan from dependency and entrypoint bytes checked against
the recorded launch source map. The full source report SHA256 is
`c94361857f2cea8533ad12cc4b7cf8aa62bd31188d09195ea649d80b007e2387`.
