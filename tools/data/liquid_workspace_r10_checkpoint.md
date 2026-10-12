# Liquid Workspace Round 10 Checkpoint

2026-10-12, Shanghai. Worktree `.runtime/r9-liquid`, branch
`codex/r9-liquid-integrated`. Native session `f0daab3c7e20422896deba7349b39f2b`,
owner `liquid-r10-background`, NEMC `3.9.0.401155`, runtime `1.21.120.0`.

## Behavioral Change

Commit `d6845cd` preserves copied explicit target palettes across biome updates
and updates active liquid opacity without replacing native IDs or preparing
shape geometry. An occupancy refresh deliberately reselects the complete
document so an initially omitted occupied cell can return. All 173 original
liquid tests passed, and the earlier scoped runtime structural review had no
findings. The current suite has 178 passing liquid tests, including five
capture-provenance and independent-mask regressions.

The candidate metadata was synchronized to parent commit `1682a54`; it is
not part of this behavioral/evidence commit. The candidate source and JSON
fingerprint agree on
`6fb3a0d4fa674a29af6409f2bb68548a8e0f523b6bf9bcaa725ba98c8c1966db`.
All 14 biome presets remain available. Final appearance is read from
`Document.biome`. No fluid simulation is added.

## Native Public Controls

`tools/probe_liquid_workspace.py` exercises the actual ordinary Workspace
Scene and public `b.project()` path through an explicit unaccepted native
resource profile. Frozen still-water artwork and a frozen, explicitly
unaccepted flow frame isolate candidate state changes. It does not enable
production liquids.

V1 completed 92 captures: source, source pool, contained fence and contained
slab; each had supported positive, supported negative, liquid-only and empty
controls. Both Scene and world controls change `Document.biome` through
swampland, mangrove swamp and plains. Swampland carries explicit opacity
0.65; unspecified native opacity remains -1 in the payload. Native references
freeze flow and have exact client/server before/after foreground/background
snapshots. All 16 reference controls remained stable and matched their
requested native representation.

Full/missing world controls track the public work owner, current source,
liquid owner, staging/retired IDs and occupancy publication. Occupying the
center removes both liquid groups for a one-cell source/fence/slab; removal
restores both. The source-pool count changes 8 -> 6 -> 8. Body geometry is
still visible in the occupied fence/slab native screenshots. Candidate
opacity .4/.8 updates liquid uniform 4 and retains the same model IDs. V1
body uniform 4 stays .8, preserving the evidence for the parent bridge fix.

V2 completed and restored 82 captures for source and fence, adding Scene
depth and viewport controls. It temporarily applied only exact
`ClientBridge.update_projection_opacity` and `Session.range_value` methods
extracted from parent commit `4ffc2d1`, then restored the original methods.
Both body and liquid uniform 4 change .4/.8. Liquid IDs remain 169/170 for
fence and 183/184 for source. Reviewed pixels show the body support plinth
fading together with water, and all 5,537 independent water-mask interior
pixels change above two RGB levels in each case.

## Evidence Limits And Preserved Failures

V1 flow restoration used a stale client `api` alias in the persistent debug
namespace. Its original `restored=false` report remains unchanged. An
explicit server API recovery separately restored flow successfully. World,
player, camera, editor, workspace and environment cleanup had succeeded.
The future probe explicitly imports the server API in both freeze/restore.

The initial broad world ROI included changing creatures outside the fixture.
Both initial analyses are retained. Refined fixed camera envelopes exclude
surrounding content, the separate player platform and crosshair. Independent
liquid-only masks give IoU .9986896 for source/fence/slab, and .9990492 for
the pool, with identical bounding edges. These are supplied source/pool
silhouette observations, not acceptance of native contained cavities or
transparent-face ordering. Native world tint differs from the candidate
Document biome, and original native water animation is not synchronized
with the frozen candidate texture frame.

The V2 `depth_hidden` label is a probe mistake: top-view plane Y=3.75 is
above the supplied top Y=3+178/255 (~3.698), so unchanged water visibility
is expected. The model is also partly outside the top viewport. No depth
defect or acceptance is inferred. Future probe code uses depth 5.0, plane
Y=3.5, and a centered top-view pan. Actual near-edge pans are adjusted to
-.25/.7; offscreen/restore observations remain separate from partial-edge
acceptance. No further native startup is authorized while parent investigates
its frozen scaffold startup failures.

## Background And Resource Recovery

The patched MCDK and final native guard enforce NOACTIVATE. Exact Edge
foreground HWND 12390418/PID 26876 remained unchanged at startup and through
all 174 WGC captures. Replays independently verify owner, game PID/creation
identity, fresh compositor frame timestamps, nonblank native PNGs and hashes.
The guard/MCDK hashes and all PNG/capture-report fingerprints are recorded
in `liquid_workspace_evidence_r10.json`.

Only one cold liquid session was used. V1 handles grew 67,949 -> 106,048;
V2 grew 188,653 -> 217,560 over 204.18 seconds. V2 private commit grew
2,986,844,160 -> 3,038,547,968 bytes. The final observed handle count was
221,461 before stopping, below the 300,000 session cutoff. There is no
isolated idle baseline, so production memory acceptance remains false.
Future probes check a 280,000 handle guard before each capture and restore
their state if that budget is reached.

Normal WM_CLOSE exceeded its ten-second wait. At the next independent check,
game PID 38364 and MCDK PID 13688 were absent. Force-finalize updated the
session record without killing a live process. Session is stopped/ready=false.
All 16 resource overlay paths restore their original byte hashes or absence.
No generated resource overlay is committed. The 1,344 host GLES checks passed;
they do not replace native shape, UV, alpha, depth or memory verification.

## Required Future Gates

1. Fully framed actual Scene depth clipping below the supplied top and shared
   body/liquid depth ordering, including partial viewport-edge culling.
2. Independent native fence/slab/pane cavity masks excluding supports, with
   visible above-water and submerged foreground bodies.
3. Native top/side UV orientation, clipped side UVs, required rotations and
   frozen-flow sampling rules.
4. Native alpha and transparent-layer sorting in the same biome and controlled
   reference texture frame.
5. Cold/warm repeated edits and 1/8/64-cell allocations against isolated idle
   baseline, with no sustained handle/private-commit retention.
6. Complete still/flow/lava animated resources and parser-derived cadence.

Native shape/UV/alpha, production editor/world and production memory acceptance
all remain false. The raw failure reports, successful rerun, recovery receipt,
stop/resource receipt and reviewed frame fingerprints are preserved under the
worktree `.runtime` directory and indexed in the committed evidence manifest.
