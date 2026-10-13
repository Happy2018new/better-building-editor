# Scaffold Runtime Collection Handoff

This worktree prepares real-state diagnostics and capability collection. It has
not expanded the production support table and has not passed editor, full
projection, or missing projection pixel acceptance.

## Current State

- Worktree: `D:/bbe-r13e-scaffold`; branch: `codex/r13e-scaffold`.
- Baseline: `52189693`.
- `07454a5f`: semantic state collector, lifecycle, two-layer cleanup, and tests.
- `335cbd3b`: retain exact source bytes and verify their archived fingerprints.
- `9933b4d0`: use the observed native palette state buckets; require isolated
  upper cells and unchanged typed support palettes across all three phases.
- The production generator still reports 14 observed and 15,844 unobserved
  states. Unknown states remain unknown, never inferred non-supporting.
- All 87 scaffold tests pass. Native Python 2 payload compile checks pass.
- No new game was launched for these changes. New launches remain paused until
  the root owner resolves the independent full-pack startup failure.

## Independent Native Air Encoding

The background owner `background-minimal-r14-preworld-v2` qualified a real
`1.21.120.0` world using `UiInit`, actual render ticks, loaded grass, stable feet,
and background WGC. Its frozen scaffold probe read the two cells without any
world, item, rule, inventory, UI, or window mutation. The instance was then
retired; it cannot be reused.

Original sanitized observation:

```text
D:/bbe-r13e-background/docs/evidence/background-startup-contrast-r14-v2/palette.json
SHA256 7d8c1e20bb11df8447a82c2d0a558718ddaef646b8520774f274a4b1559444dd
```

Original owner and source association:

```text
D:/bbe-r13e-background/docs/evidence/background-startup-contrast-r14-v2/palette-origin.json
SHA256 92bdeb718431b884ef6e43fd2f835c91effd3a497ab3058ee639771b5cf6e3a8
```

Natural air returned `GetBlockStates=None`; this remains `None`. The native
palette contained `common={('minecraft:air', 0): [0]}` and
`states={('minecraft:air', 0): {}}`, with empty `extra`, `extraStates`, and actor
buckets. The helper now retains typed material/state buckets instead of assuming
the native `states` dictionary is empty. Parsing archived Python repr uses
`ast.literal_eval`; it never evaluates arbitrary code. The support helper does
not use `GetBlockEntityData` or return actor payloads.

The earlier single-cell run remains a recorded failure. Its repeated air setter
returned `False`, and it did not have native palette evidence to prove both
layers were restored. Do not relabel it as a successful no-op. The new control
records the setter boolean and actual physical restoration separately.

## Next Runtime Step

After the root allocates one serial, guarded game slot, run a new output. The
prepared folder cannot be executed in place; the runner creates its output
exclusively and freezes the sources for that invocation.

```powershell
python -X utf8 tools/run_scaffold_runtime_lifecycle.py .runtime/scaffold-r14-runtime-v2-run --execute --air-observation D:/bbe-r13e-background/docs/evidence/background-startup-contrast-r14-v2/palette.json --catalogue-count 256
```

This permits exactly one cold start and preserves a 330-second outer budget with
70 seconds reserved for cleanup. It checks a single stone/air control, 17 real
legacy/semantic lifecycle cases, then the first 256 semantic support states.
Cleanup records the exact game and MCDK creation identities. Only the approved
noactivation guard and WGC may be used; no foreground, resizing, desktop input,
fallback screenshot, or unrelated process cleanup is permitted.

Existing prepared artifacts, with no launch or mutation:

```text
.runtime/scaffold-r14-runtime-v2-prepared/plan.json
.runtime/scaffold-r14-collection-v2-prepared/plan.json
```

If either source changed after these preparations, retain their original files
and make a new prepared folder. Preparation is not acceptance evidence.

## Same-Owner Collection

`tools/collect_scaffold_runtime_support.py` prepares or collects ranges in one
existing fresh managed diagnostic owner. It launches no game and leaves final
game retirement to that exact owner. Default collection is only 256 states and
240 seconds. Its execution must be dispatched through `instances.py exec` with
the assigned owner and session, and the owner must have been created with the
reviewed guard. The diagnostic `ScaffoldLifecycleDiagnostic.Client` system must
be present for `UiInit` and actual render-tick admission.

```powershell
python -X utf8 tools/collect_scaffold_runtime_support.py .runtime/scaffold-r14-collection-v1-next --air-observation D:/bbe-r13e-background/docs/evidence/background-startup-contrast-r14-v2/palette.json
```

Preparation emits only a plan. Add `--execute --fresh-owned-flow-allowed` inside
the existing owner's dispatch to run. Set `--start-index` and `--count` only
after the first segment provides measured timing. A full range currently has
15,858 states; the tool partitions it into at most 256 states per segment and
preserves each raw JSON receipt. Increase `--max-seconds` from its default only
when the measured segment time fits the root's remaining round deadline.
The final union revalidates receipt bytes and loads one segment at a time, so
full raw readbacks do not all remain resident in memory.

Every segment uses eight slots, a 136-cell reserve, original SDK conversions,
real `GetBlockStates`, delayed readback, and explicit two-layer clearing. A
changed support, occupied upper cell, missing states, failed conversion, or
palette/extra-state/liquid drift remains unknown. The upper cell's actual native
palette must be proven dry; a background stone cannot be hidden behind
`GetLiquidBlock=None`. Boolean aux/index values do not count as integer zero.

The controller retains source bytes for its host import closure, validates the
exact game and MCDK creation identities, requires physical world admission and
WGC, and checks archived/current fingerprints. A failed native segment is never
automatically replayed. It preserves the receipt, attempts restoration only
with the exact recorded segment identity, and reports any missing or failed
restoration so the owner can retire the world. It does not write production
capability flags.

## Remaining Work

1. Run the new single-cell and 17-case lifecycle diagnostics with native palette
   evidence. Preserve raw `None`, actual aux values, and failures.
2. Measure the first 256-state segment. Resolve true non-air state failures
   before dispatching more segments.
3. Collect the full dump in one healthy fresh owner and verify exact coverage,
   non-overlap, matching source closure, typed semantics, and full restoration.
4. Connect verified semantic collection to the production support generator.
   The old 14-sample generator is intentionally unchanged until real evidence is
   available. Mixed legacy and semantic collection methods must not be merged.
5. Complete scaffold edit behavior: supported distance, hanging propagation,
   stable unknown-state handling, and exact undo/redo.
6. Accept actual editor, full, and missing projection pixels for top/bottom,
   unsupported appearance, distant complete context, and occupied real neighbors.
   Data collection and offline tests cannot substitute for these three views.
7. Keep the shared backlog and main handoff under the root owner's control.

Focused offline verification:

```powershell
python -m unittest discover -s tests -p 'test_scaffold*.py'
python tools/generate_scaffold_support.py --check
git diff --check
```
