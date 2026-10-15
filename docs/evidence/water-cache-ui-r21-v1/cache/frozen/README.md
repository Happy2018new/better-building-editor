# Default depth adapter cache candidate

Status: offline candidate only. No MC/WGC launch or shared index ownership.

## Confirmed Boundary

Only `LiquidControls`' default `with_preview_distance` is cached. Each entry
retains at most one request, containing the source group, typed distance and
adapted group. `RenderGroup` is a namedtuple, but arbitrary callers may supply
mutable fields. Cache eligibility therefore requires the exact RenderGroup
type and recursively exact builtin immutable field types. Tuple and numeric
subclasses, lists and custom objects remain on the original adapter path.

Both source identity and the distance's exact type/value must match. A bool
cannot reuse a numeric zero request. The adapter first validates the original
payload; failed view/pose validation removes the cache. Custom adapters are
never cached. Renderer validation, view/pose callbacks, publication recovery
and layout updates still run as before. Clip/missing view, removal, missing
mounts, retry, invalidate, close and publication-restore failure clear the cache.

## Existing Evidence

`docs/evidence/water-timing-r21-v1/liquid-query.json` has SHA-256
`da1f1af60e63b884b4ff2243840a60831b70a7dff780501b7e1ec4a8cf1bdbb7`.
Its wall window contains 1170 Controls-to-adapter calls, 1170
Controls-to-renderer-validate calls, but only 412 Controls-to-renderer-update
calls. Adapter-to-payload-validation time is 0.0964673 seconds in aggregate.
These observations motivate removing repeated work, not a speedup percentage.

The old owner elapsed failures remain open: projection 168.999910 ms, preview
230.000019 ms and Controls 434.999943/370.000124 ms. In particular, the last
Controls outlier has zero requested groups and zero registry entries. No
algorithmic explanation or fix for those long samples has been established.

## Offline Replay

From the repository root:

```powershell
python -B .runtime/water-r21-depth-cache-v1/offline_compare.py
$env:PYTHONPATH = Join-Path (Get-Location) 'tests'
python -B -m unittest tests.test_liquid_viewport tests.test_liquid_transport tests.test_liquid_render tests.test_liquid_preview tests.test_liquid_projection tests.test_liquid_render_ownership tests.test_liquid_product_owner_contracts
```

The comparison loads the exact original viewport module from commit
`0898a8f6`, checks source SHA-256
`d07472df91d4c4cd93c2d7d84cd37c34c00cdac72ade470d290a6e125b0531cf`,
and uses the existing fake native controls. Sixty stable frames must have
60 baseline source-payload validations versus zero candidate validations;
both retain 60 renderer validations, view callbacks, pose callbacks and
publication restores, with identical final native payloads, submissions,
visibility and geometry. This is not in-game timing evidence.

## Shortest Scheduled Runtime Check

Do not run this plan until root grants the MC/WGC slot. Use one frozen
candidate project, one editor fixture `water_style_flow_east_wet`, fixed
camera and no matrix expansion. Preserve the existing input/window rules,
canonical resource preflights, session binding, source closure and normal
stop/exit-observer flow. This file launches nothing.

1. After the fixture naturally settles, save the original candidate method
   objects. Load the exact hash-checked baseline viewport module under its
   proper package and temporarily bind its unmodified `update` method to
   `LiquidControls`. Keep the live controls and owner registry. Never invoke
   updates in a synthetic loop: sample natural scene frames only.
2. Baseline: exclude five warmup frames, then count 60 owner update calls.
   Record active entries and default adapter source validations, renderer
   validations, view/pose callbacks, publication restores, actual native
   writes/submissions and both wall clocks. Preserve complete samples and
   outliers. Record a canonical stable scene/native-state snapshot.
3. Candidate: restore candidate `update`, remove old distance-request entries,
   exclude five warmup frames and collect the same 60 natural owner calls.
   Source validations in the stable window must be zero for unchanged
   eligible entries. The other validation/callback/recovery counts must
   remain present, and the native snapshot must match the baseline.
4. With the candidate, change depth once, clip/unclip once and exercise one
   invalid-distance rejection followed by explicit retry. Require a new
   adapter call for each invalidation/recovery and preserve the previous
   published payload/layout on rejection. This is a single-fixture lifecycle
   check; use the existing same-fixture UI controls rather than adding cases.
5. Restore all class/function wrappers in `finally`, close/restore the editor
   and profile, verify source closure and empty cleanup errors, then perform
   the established normal stop and exact process exit observation. No force.

Require positive baseline adapter calls before claiming a reduction. If the
single fixture has no eligible visible entries or the owner does not settle,
report the check as inconclusive and restore; do not add fixtures. Per-call
elapsed maxima remain observations, and the old 169/230/435/370 ms failures,
all native appearance gates and production admission stay open.

## Prepared Owner-Bound Runner

The two product/test files are committed as `a09aa9b9` on local `dev`.
Offline preparation has created `.runtime/projects/water-depth-cache-r21`
from the original 3093-file water clone. Exactly one source file differs:
`behavior_pack/modern_projection/projection/liquid_viewport.py`, copied from
that immutable commit. All resources, tools, skills and launch configuration
remain byte-identical to the old clone. The candidate closure digest is
`dfe714e3b5b0807aed1b906f53095f7b26dd2f733d19552c7181457ce5b7c642`.
All four automatic reload settings are false. No game has been started.

The original plan/receipt and launch inputs live in
`.runtime/water-r21-depth-cache-ab-v1/`. The receipt binds the complete source
map, configuration, exact original baseline source, host and embedded
instrumentation. The final instrumentation corrects Python 2 unbound-method
handling and retains raw class descriptors for exact restoration.

The separate `operational-amendment-v1.json` explicitly changes the operational
owner from `water-r21-depth-cache-ab-v1` to `water-r20-depth-cache-ab-v1`, matching
the running main DisabledSkin watcher's `water-r20-*` coverage. The original
plan, receipt, launch inputs, configuration and baseline bytes are preserved;
the original plan SHA-256 remains
`d841ba845a2e98ec070a34a9e4d2a26a09fb9e9bb74c1256da551957fcb16b6c`.
The frozen BP/RP and all 3093 project source files are unchanged. The amendment
bound the first revised host/README, external launcher and observer dependency files,
and the already-approved MCDK and noactivation DLL. It records the superseded
host hash without rewriting the original plan. The original v1 receipt remains
byte-identical with SHA-256
`c681a3331a3faf9f4d49f02614f4b87dae6ea0cf37047204ddef1b29ae1f7c59`.

The active `operational-amendment-v2.json` additionally binds the process-local
`OPENBLAS_NUM_THREADS=1` environment, effective-live process gate, latest host
and README, and both possible local import locations in the external dependency
closure. The dedicated host sets the environment before loading probes/census;
launcher and observer children inherit an explicit value of one. No global
environment, dependency file or frozen project is modified. The v2 receipt
hash-binds v1 and retains its superseded operational file hashes. Amendment
creation is offline:

```powershell
python -B .runtime/water-r21-depth-cache-v1/host.py amend
```

That one-use amendment already exists after preparation; do not recreate it.

```powershell
python -B .runtime/water-r21-depth-cache-v1/check_embedded.py
python -B .runtime/water-r21-depth-cache-v1/host.py preflight
```

Both commands leave the game unstarted. The preflight checks the actual
external `tools/watch_intrinsic_glint_exit_r21.py` and its dependency closure;
it does not assume that the older frozen project contains the observer. Its
approved SHA-256 is
`aa436ee9a0f496554c69330d8456fa21b6bb551b63032f0b5a453ad9748646aa`.
It also requires matching main watcher owner coverage, a status heartbeat
at most 60 seconds old, and an unexpired watcher deadline. It uses the canonical
commit-capacity helper, counts all Minecraft processes and rejects an existing
live owner for the candidate project. It requires at least 9 GiB commit before
root launch; the bound runner checks at least 6 GiB, fewer than 210000 owned
handles and no more than two game processes at each phase boundary.
The raw CIM rows retain both handle and thread counts. Only a row with zero
handles, zero threads and no live creation identity is excluded as an exited
shell; any unresolved row with other counts is conservatively included in the
effective-live game count. Managed sessions require a nonempty recorded
identity equal to the current identity, preventing two absent identities from
being treated as a live match. These changes are host-only resource accounting.

After root explicitly grants the runtime slot, the unified launch entry uses
the established noactivation launcher for the frozen project and amended owner.
It then starts the external exact exit observer and waits until both owned
game/MCDK handles are retained. The host validates observer process creation
identity, both retained target identities and both exact executable paths
before publishing `launch-ready.json`. It never starts the A/B runner itself:

```powershell
python -B .runtime/water-r21-depth-cache-v1/host.py launch --scheduled-by-root
```

The launch is one-use: `launch-attempt.json`, startup stdout/stderr and observer
evidence remain available on failure, with no automatic restart or stop. A
failure requires root inspection of the owner and receipts. Once the unified
launch succeeds, its exact session may be attached explicitly:

```powershell
python -B .runtime/water-r21-depth-cache-v1/host.py run --scheduled-by-root --session <NEW_SESSION_FILE>
```

The host has no stop action. The A/B runner refuses an existing `ab-report.json`,
requires the unified launch receipt and live retained exit observer,
checks the live session identity/project/noactivation state and rejects a
pre-opened editor. It measures natural owner frames with five warmup frames
and sixty measured frames on each A/B side. Both Windows clocks are wall
clocks; no thread-CPU measurement or per-call speedup is inferred.

Depth uses the real `session.move_depth(1)` path, then restores its original
target. Clip and invalid distance are explicitly labelled diagnostic callback
input injections on natural owner updates, followed by ordinary unclip/retry.
They do not assert native mouse/keyboard hit testing. The host records actual
native uniform writes, skeleton submissions and visibility calls, retains
complete timing rows, restores all wrappers/proxies in `finally`, closes and
restores the workspace/profile, and verifies the source closure. It takes no
screenshots or window actions. Root retains responsibility for normal stop,
reviewing the retained observer's final `process-exits.json` and releasing the
MC slot after both exact owned processes exit. No force, activation, input,
window repositioning or screenshots are added by the operational amendment.

`check_embedded.py` has replayed all seven phases with fake native controls,
plus injected host-abort cleanup, the Python 2 unbound-method branch and the
exact hash-checking installation snippet. These remain offline harness
checks. The one-use real owner run is still pending and cannot close any
original owner elapsed failure or appearance/admission gate.
