# Water Timing Diagnostics R21 V1

This package preserves additional timing observations from the unchanged
`water-r20-v7` owner session. It does not qualify production water or replace
the failed formal samples in `../water-ui-state-r20-v1/`.

Run the standalone verifier from the repository root:

```powershell
python -X utf8 docs/evidence/water-timing-r21-v1/verify_package.py
```

## Measurements

`paired-clock.json` records 36 wet/dry transitions across pool, flow west,
fence, pane, slab, and stairs. Each timed invocation reads `time.time()` and
Windows CPython 2.7 `time.clock()`. Both measure elapsed wall time. They are
not CPU measurements. `LiquidControls.update` has 10,338 calls and maxima
10.999918 ms / 11.863700 ms for the two clocks; `LiquidPreview.advance` has
10,338 calls and maxima 6.000042 ms / 5.661100 ms. Thread CPU measurements
were unavailable because the embedded interpreter could not import ctypes.
Unsupported `maximum_thread_cpu_ms: 0` fields are not measured zero CPU use.

`profiler.json` records two real owner-bound `mc_profiler` jobs using Yappi,
target `client`, duration 30 seconds, disk storage. CPU and wall clocks use
separate windows, each with six wet/dry transitions over pool, flow west,
and slab. Both jobs completed. Exact water-filtered hotspot and call pages
are retained in `liquid-query.json`; exported server reports are retained as
`profiler-cpu.md` and `profiler-wall.md`.

| Method | CPU Calls | CPU Total Seconds | Wall Calls | Wall Total Seconds |
| --- | ---: | ---: | ---: | ---: |
| LiquidControls.update | 3747 | 0.265625 | 5775 | 0.5607786 |
| LiquidPreview.advance | 3747 | 0.09375 | 5775 | 0.1117812 |

These are aggregate times across different samples, not per-call maxima.
The CPU report has coarse 1/64-second timing increments. Different call
counts, startup work, profiler overhead, and competing game processes prevent
a direct CPU/wall subtraction or an optimization claim. No product change
was made between these jobs.

## Limits and Provenance

The previous elapsed-time failures remain approximately 169, 230, 435, and
370 ms. Their exact report hashes, methods, and raw maxima are recorded in
`references.json`. New short samples do not supersede those failures. No
root cause has been established; scheduling delays, clock behavior, and
normal algorithm work have not been separated for the original long calls.

All diagnostics restored their wrappers and workspace and verified the
same 3093-file source closure:
`cb2b32de68b69f435d69b59cf296d8492d88984ddb96e10f020d7fdbd0aef806`.
Its reconstructable archives remain in the referenced UI evidence package.
Exact diagnostic hosts and the package builder are included and hash-bound.
There were no screenshots, desktop input, activation, window movement, or
window resizing in these timing observations. No launch/session credentials
are included. Product source, shaders, models, textures, admission flags,
thresholds, metrics, and pass/fail rules were unchanged.
