# Water UI Submission Candidate

Offline only. No source/resource integration, launch, connection, capture,
index operation or production admission is performed by these files.
The existing distance-cache A/B runner and frozen project are unchanged.

## Specific Hypothesis

On affected native PaperDolls, assigning the skeleton selects the right model
but leaves the native UI draw path in an invisible state. A final RenderEntity
submission selects the working draw path while retaining that assigned water
model. This is a hypothesis about the API sequence, not a proven engine cause.

`entity_draw_pose` replaces only a water owner's `_render_pose`: first submit
the exact skeleton model, then submit RenderEntity with the same scale,
rotation and render_depth=-50. Its final API matches the existing v6 matched
pose control, whose entity phase shows the exact 96,436-pixel reference water
ROI while the preceding/following skeleton phases show no water. All eight
model IDs remain equal across those phases. A one-time entity prime followed
by ordinary skeleton submissions is contradicted by that reversible result.

## Construction And Ownership

LiquidTile mounts two managed Dolls with no automatic native submission;
widgets.PaperDollPrimitive returns immediately for managed=True. LiquidControls
then creates the renderer, applies geometry/clip offset, and calls update.
The renderer masks any old payload, shows its incoming bank, submits the
skeleton, waits for natural-frame model-ID readiness, stages uniforms and
publishes the bank. Pose changes resubmit through the same `_render_pose`.
The candidate changes that one submission operation. It does not add a second
owner, an entity_id, a CreateClientEntity call, a player/local actor reference,
or a shared world entity. The identifier minecraft:cow is the exact documented
UI source from the real v6 control. It is not a request to display cow pixels:
any cow pixels or replaced water geometry reject this candidate.

The real v6 control changed already-created dolls after asynchronous model-ID
readiness. It did not validate consecutive S-then-E calls on a brand-new bank.
An immediate entity submission could replace a skeleton that has not finished
allocating. The first falsification therefore uses the existing settled pool
banks. Even a passing result leaves initial construction unqualified; a later
product integration must confirm that ordering on the same pool's fresh bank
before enabling it. The current candidate deliberately makes this risk explicit
instead of inserting unmeasured delays or another owner lifecycle.

Identifier-based rendering is not documented to guarantee per-control native
ID independence. The existing renderer's duplicate-ID rejection remains
mandatory for both banks and all groups. Returning success from either API
is never pixel proof. No hidden automatic fallback or retry is introduced.

The PaperDoll layer 306, position, viewport size, scissor parent, -50 depth,
preview tag134 distance, uniforms, shader, model resources and publication
masking are unchanged. The candidate never reads a model ID synchronously.
Only the water controls may receive this override; shared Scene, cauldron,
portal, book, item and world renderers keep their current APIs.

## Single Pool Falsification

After separate root runtime/WGC scheduling, reuse one ordinary frozen pool
and its already-owned water dolls, with a stable captured application frame.
Freeze animation and camera as in the existing matched-pose control. Preserve
the original bound `_render_pose` methods and original water control state.
Run skeleton baseline, candidate S-then-E, skeleton restore, candidate repeat,
then final restore on the same owned dolls, with equal natural settle windows.
Reapply the same four uniform vectors to each actual asynchronously obtained
ID after each phase. Capture the unchanged native viewport and native state.

The candidate is rejected if either API fails; native IDs alias across owned
banks/groups; cow or other wrong geometry appears; model payload/tag134,
screen geometry or depth changes; water still has zero independent visibility;
or final restoration/cleanup fails. If the skeleton baseline is invisible,
candidate must recover the reference wet-minus-hidden water region on both
candidate phases and the intervening skeleton restore must reproduce absence.
If the baseline is already visible, the run is inconclusive for the invisible
state and must not claim a fix; correct-looking candidate pixels alone cannot
close it. One ordinary depth step and return on the same pool can falsify shared
depth preservation, without adding fixtures or a matrix. Restore all per-owner
overrides in finally. Do not enable the product path before native confirmation.

Run `python -B .runtime/water-ui-submit-r21-v1/check.py` for offline submission
and existing renderer-lifecycle regressions. Those tests establish Python
ownership and call ordering, not native visibility or shared-depth acceptance.
