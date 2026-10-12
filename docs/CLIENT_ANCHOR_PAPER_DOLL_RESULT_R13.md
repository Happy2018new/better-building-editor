# Owned Client Anchor PaperDoll Result R13

## Result

The single R13 v2 attempt did not visibly include the plain diamond sword on
the owned `modern_projection:anchor` client actor. The native binding API
returned item model ID `0`, and offset, rotation and scale readbacks matched
the frozen values. Both empty frames and both plain frames showed no visible
item. The pre-body ordinary-item gate found **0 stable changed pixels**, below
the frozen 80-pixel minimum. All four marker gates passed.

The stone-body stage was gated off before palette creation, geometry combine
or body attachment. This result therefore supplies no body-depth or occlusion
observation. Production rendering, editor frame content and enchantment glint
acceptance remain **false**.

## Runtime And Cleanup

The owner retained background session `773c643b5cf344918e04d8b4eef2657a` and
physical window `29102794`, at `1994 x 1105`. The one attempt took
`17.825965799973346` seconds. The hard 150-second supervisor completed without
timeout or replay. Initialization and real HTTP requests counted against the
90-second normal budget, cleanup used the deadline at 120 seconds, and each
HTTP request had an absolute time limit.

The plain item used `isClientEntity=True`, root bone, zero offset and rotation,
and unit scale. The exact actor ID was passed to the entity PaperDoll, with
UI scale `0.35`, render depth `-50` and zero initial rotations. The owned actor
was positively identified as `modern_projection:anchor`, and its root bone
returned a four-row transform matrix. The initial player foot position
`[0.5, -60.0, 0.5]` was read only.

The exact item attachment was removed successfully. The actor had a positive
type before destruction and an independent `None` type after destruction.
The owned page was popped, and navigation, document, profile and camera
snapshots were restored. There were no cleanup errors. Source configuration,
pack lookups and all five loaded anchor resources were unchanged. No shader,
pack, world, inventory, player-position or desktop-input mutation occurred.

The immutable owner journal includes **46 raw RPC entries**, with zero
`isError` responses, and **47 HTTP entries** including connection DELETE.
Setter, create, bind, render and cleanup attempts were recorded before calls.

## Calibration And Limits

The fixed V4 marker calibration was reused: scale `3.9974978978239917`,
translation `[0.12427449291408266, -2.1534588486227904]`, top-left and
bottom-right training markers, and top-right and bottom-left holdout markers.
The original API-only uniform mapping still failed its separate one-pixel
check. Scoring used the predeclared full physical width below the top 10
percent; that region was independent of calibration.

Maximum marker edge or center residual was `0.18848827908690424` physical
pixels. Deferred PaperDoll `GetModelId` returned `-1` in every empty and plain
read, whereas the earlier player-ID V4 reported `0`. This is a diagnostic
readback difference; it does not identify the cause of the missing visual.

The negative observation applies to this one transparent anchor, root
attachment and fixed item/UI pose. It does not establish that every client
actor, entity UI or native attachment is ineligible. No world-rendered
attachment comparison was captured. Body geometry, shared depth, occlusion,
clipping, alpha and glint remain untested.

## Evidence

The self-contained archive at
`docs/evidence/client-anchor-paper-doll-r13-v2/full-evidence/` retains the
original runtime and supervisor reports, every raw RPC and HTTP response,
four original PNGs and capture receipts, post-cleanup health evidence, log,
offline score, visual review, supplements, and the full 123-file frozen source
inventory. `complete-archive-index.json` records every original byte count and
SHA-256. The local `.gitattributes` disables text conversion for immutable
archive files.

Reviewed source pins:

| Artifact | SHA-256 |
| --- | --- |
| R13 v2 probe | `2d93d4314e49dadc4bbe6e93b40c9b6c1e7e0ec5ab7b0c3304072f6ba8366a85` |
| R13 v2 plan | `5a7e328635d1f3f5c83f8f2ed08d2ed5ba56e3aed8526943d3b0f27845126b05` |
| Owner runner | `ff4218f7c9dd1a72436f1c4645ca1dbde4e100c111143d804cf3f6ef439e88de` |
| Owner source index | `173cd8f53df0c8397da3d7167bed66499d00427569d4f6e7b124e4afcffff968` |

The 26 probe tests and 10 owner deadline tests passed before dispatch. QA
independently verified the 31-file bundle, 18 generated snippets, 123-file
source inventory, 57 actual local imports and 15 source/world/appdata resource
copies. The separately bounded health helper also has focused offline cleanup
failure coverage.

Fresh health passed in `4.960054199967999` seconds under its independent
40-second outer supervisor. Client and server clocks advanced, two server
timer callbacks ran in order, and the nonce-owned temporary marker was
deleted. All four original PNGs were opened after health passed; entities
also independently verified their receipts, inspected the same PNGs and
reproduced the zero-pixel ordinary gate. The result archive contains
144 indexed original artifacts plus their original artifact index.

| Result Artifact | SHA-256 |
| --- | --- |
| Original artifact index | `40170a7aeaff14c5411730680e845d1d231edf24102aa35e902060bc5030832f` |
| Fresh health report | `27fc2f7b8b0f89b9004c2d237970bd1fa8800246101fa39e8da0bcfcfba458ff` |
| Health helper | `f07aa74756167559663fa2e3b0894e456b7272b1a22b9471779bff71b63f32e8` |
