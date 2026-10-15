# Runtime Amendment V2: Host Threads And Effective Census

Prepared offline. No game, capture, stop, stage or commit was performed.
Use this entry for later root-scheduled actions:

`.runtime/frame_block_grass_r21_run_v2.py`

The original README, plan, launcher, reviewer, capture host and frozen
dependencies retain their original bytes. The new wrapper binds them through
`runtime-amendment-v2.json`, SHA256
`0d18af9f2354c66f741ead2713d33391fe68f049a80beda111652e85a990885a`.
The wrapper's SHA256 is
`c668de7398e23af0c79b00d06a95d794e3fe68d6e1f05b88998bc20c967c588c`.

The wrapper sets `OPENBLAS_NUM_THREADS=1` inside its own process before it
imports the original launcher or its census/NumPy dependency. Original start,
capture host and exact observer subprocesses inherit that environment. The
wrapper's `review` action gives the frozen reviewer the same inheritance.
No global environment or frozen source is changed.

An isolated import beginning with `OPENBLAS_NUM_THREADS=24` was verified to
produce `1`; `threadpoolctl` confirmed OpenBLAS 0.3.30, pthreads, one thread.
A fresh ordinary Python child also read `1`. This is host configuration
verification, not new game or image acceptance.

The amended read-only census retains every raw CIM row and excludes a row
only when HandleCount and ThreadCount are both exactly zero and no live
process identity exists. Any positive count, unknown count or live identity
is conservatively counted. Five offline cases verified these distinctions.
The imported launcher's preflight function is replaced only in the wrapper
process; the original launcher file remains unchanged.

Read-only preflight at `2026-10-15T21:34:11.717577+00:00` observed 16 raw rows,
15 exited zero-handle/zero-thread shells and one effective live game,
PID 39520, identity `134365734724755907`, 850 handles and 73 threads.
There was no same-owner live game. Available system commit was 8335699968
bytes, below the unchanged 9 GiB launch requirement, so preflight returned
`passed: false`. No capacity was freed by process mutation. This observation
is stale before any later launch; root must run preflight again when assigned.

```powershell
python -B -X utf8 .runtime/frame_block_grass_r21_run_v2.py check
python -B -X utf8 .runtime/frame_block_grass_r21_run_v2.py preflight
```

Only after root assigns the runtime window and live preflight passes:

```powershell
python -B -X utf8 .runtime/frame_block_grass_r21_run_v2.py start --scheduled-by-root
python -B -X utf8 .runtime/frame_block_grass_r21_run_v2.py capture --phase front --scheduled-by-root
python -B -X utf8 .runtime/frame_block_grass_r21_run_v2.py review --phase front --output .runtime/frame-block-grass-overlay-r21-front-review-v1
```

Every start or capture records a separate runtime amendment invocation receipt
before delegating to the original guarded operation. Existing operation
evidence is retained, and retries or phase chaining are not automatic.

Open the fresh native/full/missing shown PNGs and montage. The original
front completion/restoration and bound review requirements remain in force.
Only root may then explicitly schedule each oblique phase:

```powershell
python -B -X utf8 .runtime/frame_block_grass_r21_run_v2.py capture --phase left75 --scheduled-by-root --first-image-reviewed-by-root --front-review .runtime/frame-block-grass-overlay-r21-front-review-v1/review.json
python -B -X utf8 .runtime/frame_block_grass_r21_run_v2.py review --phase left75 --output .runtime/frame-block-grass-overlay-r21-left75-review-v1
python -B -X utf8 .runtime/frame_block_grass_r21_run_v2.py capture --phase right75 --scheduled-by-root --first-image-reviewed-by-root --front-review .runtime/frame-block-grass-overlay-r21-front-review-v1/review.json
python -B -X utf8 .runtime/frame_block_grass_r21_run_v2.py review --phase right75 --output .runtime/frame-block-grass-overlay-r21-right75-review-v1
```

All 9 GiB launch, 6 GiB runtime, handle, admission-time, normal-stop and exact
exit observation requirements in the original README remain unchanged.
No phase has run and appearance/production acceptance remains false.
