# Editor Liquid Bank Publication

## Reproduced Failure

The editor liquid owner prepares a masked PaperDoll bank while retaining its
published bank. Previously, `SkeletonLiquidRenderer._settle` changed `front`
and cleared `pending` before hiding the previous surface. A native hide that
mutated then raised left the new front committed while the previous surface
visibility cache remained true. An adapter returning explicit false was
discarded by `LiquidControls`, so the same partial switch claimed readiness.
An identical stationary request did not retry the previous-bank hide.

Focused host tests reproduced both results before the implementation change.
They also reproduced readiness being claimed by removed/offscreen branches
while publication recovery still failed, and new native layout being written
before failed recovery completed.

## Scoped Contract

The existing `SkeletonLiquidRenderer` journals the incoming slot-four unmask
and previous surface hide before each native call. It publishes uniform and
visibility caches, then changes `front`, only after both calls succeed.
Failure forces the previous values without consulting success caches; failed
recovery writes remain with this owner. Original exceptions and identities of
refused recovery writes remain available in diagnostics.

The existing `LiquidControls` callback forwards the native visibility result.
ModSDK UI `SetVisible` has no return value, so ordinary `None` is accepted as
success. Explicit false from an adapter is treated as refusal; it is not used
as a claim about the documented ModSDK UI return contract.

Each owned registry entry attempts recovery before removal, clipping,
validation latches, geometry writes, or a ready-request shortcut. Failed
recovery keeps the entry pending and reports the renderer error. Explicit
retry clears the request latch, but does not discard its journal. Stationary
updates can finish recovery; healthy entries continue their own preparation.

The containing Scene/LiquidTile components still own and unmount the same two
PaperDolls. Their IDs never enter `RemoveFreeModel`. `LiquidPreview` retains
its existing detached document plan and publication behavior. Preparation
frame counts and settle timing are unchanged.

## Host Validation

| Focused Suite | Passing Tests |
| --- | ---: |
| `test_liquid_viewport.py` | 25 |
| `test_liquid_render.py` | 35 |
| `test_liquid_preview.py` | 5 |
| `test_projection_pair.py` | 20 |

The six new viewport tests cover old-bank hide and incoming unmask failures
after native mutation, both explicit false and exceptions; retained failures
while restoring visibility or the masked payload; blocked layout/submission
during recovery; retry and stationary recovery; removed/offscreen readiness;
and continued preparation of a healthy owned sibling.

Independent source review found no remaining blocker in this bank publication
and stationary recovery scope. Scoped MOD review parsed three matching files;
its advisories were the existing `group_view` argument count and `update`
crossing the function-length threshold after adding the recovery guard.
`git diff --check` passed.

This change does not add a general transaction for ordinary UI geometry/pose
setters or `_show` calls outside bank promotion. It does not change the water
material, UV data, side-pixel diagnostics, shader assets, or profile gate.
The production liquid profile remains disabled. No game or native renderer
operation was invoked; host tests do not establish native visual acceptance.
