# Empty Lectern Packed-Context Control

This is a diagnostic, not a product admission. The existing book and table
gates are unchanged. In particular, this control does not widen the qualified
north-frontal book-page view or establish a corrected west-facing book pose.

On NEMC `3.10.0.420447`, an empty `minecraft:lectern`, aux 1, west,
powered false, was placed above cyan concrete in an owner-bound disposable
world. Six paths were captured from the same four fixed cameras: world,
empty, live palette, serialized palette, project-prepared palette and the
unchanged public packed-context builder. All 24 captures are reliable and
have matching before/after cameras. The completed run restored its world,
player, environment and workspace with no cleanup errors.

The 3092 project source hashes in `inputs/prelaunch.json` were recorded before
the cold session was created and exactly match `report.json`. Sources also
remained unchanged through the run. This includes the shared context fragment
and vertex shader, unlike the earlier retained R20 comparison. Hot reload was
disabled. Host tool/dependency bytes are retained under `inputs/` and match
the hashes recorded by the runtime report. The single-frame capture helper
was `cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8`.

## Observed Body Difference

The 24-tile review and the unscaled crops were visually inspected. Native,
live, roundtrip and prepared meshes retain the full sloping top board. Only
packed context truncates its upper portion in all four views. Fixed-column
brown-outline observations provide compact examples, in original crop pixels:

| Camera | Crop X | World Y | Prepared Y | Context Y | Context Minus Prepared |
| --- | ---: | ---: | ---: | ---: | ---: |
| South | 240 | 38 | 37 | 81 | 44 |
| North | 160 | 37 | 37 | 80 | 43 |
| East | 200 | 46 | 46 | 81 | 35 |
| West | 200 | 36 | 36 | 77 | 41 |

Live, roundtrip and prepared paths have identical observed outlines in these
columns. No alignment, rescaling or recoloring is applied. The result supports
the center-cell-clipping diagnosis for the lectern body and rules out a native
live-palette or serialization truncation as the cause of this top-board loss.
The shader's center clip, runtime source hashes and the earlier resource-bound
overhang analysis are consistent with the observed loss.

There are measurement limits. Clouds and distant scenery changed, notably
in the east/west images, contaminating the whole-crop empty-frame difference
scores. Those IoUs and native-only pixel totals must not be used as shape
acceptance. Fixed-column brown predicates are also observations, not a semantic
wood mask. Cyan support is visible in every nonempty path, but the separate
cyan-block positive-control run has not been performed. This is one empty
lectern state, not a book-on, other-state or lifecycle qualification.

## Preserved Empty Actor And Cleanup

The engine supplies an empty actor container even for an empty lectern:
`{'minecraft:lectern': {1: {}}}`. The context Document retains this exact empty
payload through `make_cell`; the diagnostic asserts that its actor palette
equals the native actor palette before invoking the public builder. No actor
data is silently removed and no product module or qualification gate is patched.

Two preliminary attempts produced zero accepted images. The first deliberately
failed the initial no-actor guard and restored. The second verified exact empty
actor preservation, then rejected an incorrectly selected burst helper at the
single-frame interface and restored. Their reports and the failed helper
receipt are retained under `failed-preflight/`; neither is acceptance evidence.

Normal instance stop initially timed out. After inspecting the owned status and
startup log, identity-checked `stop --force` completed. `lifecycle.json` records
the stopped session and verifies that both owned game and MCDK processes are
absent. No window activation, desktop input or resize was used. The screenshot
queue was released immediately after the 24-image run completed.

## Offline Review

```powershell
python -X utf8 tools/analyze_lectern_body_context_r21.py `
  docs/evidence/lectern-context-r21-runtime-v3/report.json `
  --output .runtime/lectern-context-r21-runtime-replay
```

The output directory must be fresh. The analyzer checks all capture hashes,
camera equality and shared-fragment source binding before producing the
unscaled review. `review/analysis.json` retains all original diagnostic scores,
the column observations and their limitations. `manifest.json` hashes the
retained package files; it is a package inventory, not a qualification manifest.
