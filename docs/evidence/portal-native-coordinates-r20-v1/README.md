# Native gateway coordinate readback, R20 v8

The frozen v8 clone completed exactly two real WGC captures, candidate/front
and native/front, at the same camera. Both images were opened and inspected.
The source map is the unchanged v5 coordinate route, SHA
47aa6848257f1701e625e5dff1824a98134774311addf252f2909e965965919f.
The report confirms completed, restored, source_unchanged and
project_source_unchanged; cleanup_errors is empty. The two presence_failures
are intentional: the starfield visibility detector rejects coordinate stripes.
No agent activation, raise, resize or desktop input was used.

The 16-layer diagnostic control is observed. The two north-facing normal
outputs are both [127,127,0], and native depth bytes match the measured layout.
The uncorrected native/candidate UV.x exact and within-one ratios are zero for
every layer. These failed comparisons are retained without rewriting them.
Each layer's X difference spans only adjacent bytes, consistent with a
translation rather than a ray-slope disagreement.

The offline model uses the bound camera coordinates, measured byte depths and
the native rotation formula. With no fitted X parameters, subtracting the
rotated camera.xy contribution predicts all 16 layer offsets to at most
1.0183 texels. After fitting one common Y phase of 4.59998 texels, the maximum
Y residual is 1.1202 texels. Additional explicit CPU ray/neutral-byte models
are retained, including their rejected alternatives. This supports a minimal
clone-only removal of the candidate's final +VIEW_POS contribution. It does
not directly measure either pipeline's uniform value and does not establish
that the corrected shader works. No corrected candidate was run in v8.

The first normal stop timed out after its owned-window WM_CLOSE request.
The retained exact process handles then observed MC50000 exit 0xC0000409 and
MCDK55092 exit 0 at 2026-10-16 02:32:42 Asia/Shanghai. This is not a successful
normal exit and does not establish the cause of failure. After both exact
identities were independently absent and no owned windows remained, a second
normal stop only finalized metadata. No force stop was used. The observer
finished and all portal exec sessions ended before the runtime slot release.

Offline replay from this package directory:

```powershell
python -B host/analyze_portal_coordinates_r20.py --report observed/report.json --output decoded-replay.json
python -B host/analyze_portal_view_models_r20.py --report observed/report.json --output models-replay.json
```

The replay bytes were checked against the preserved decoded/model outputs.
The package includes actual shaders, full material/model registries and the
gateway mesh used by this diagnostic. It is a bounded evidence package, not
a complete runnable world/SDK closure. Raw session/start/stop responses remain
private because they can contain routing credentials. Native bytes are kept
unchanged under the nested -text attribute.

This coordinate probe has no appearance, density, brightness, animation,
UI, lifecycle, missing, opacity or production qualification. Per-layer or
common phase fitting is diagnostic only and cannot replace those checks.
