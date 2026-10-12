# Frame Editor Submission Diagnostic R10C

Production rendering acceptance remains false. This diagnostic changes only
ephemeral native editor palettes; it does not edit world blocks or shaders.

The synthetic public `frame_filled` case places a facing-2, rotation-0 sword
frame at `(3, 3, 3)` in an `8 x 8 x 8` document. Both combined controls submit
the native frame at sparse index `219` and
`modern_projection:preview_item_minecraft_diamond_sword_0_f2_r0` at `795`.
Native volume is `8 x 8 x 17`, with model layout retaining logical `8 x 8 x 8`.
Native Combine succeeds and editor readiness/cache signatures are current.

The body-only control contains no item proxy. Both combined-versus-body
comparisons contain zero changed pixels at the existing channel threshold 25.
Removing frame common/state/actor entries from the ephemeral palette, while
keeping the same item, native volume, render path and model layout, reveals
1,390 item pixels. A registered blue shulker proxy at the same sparse index
provides a positive control with 29,674 changed pixels.

The complete editor Scene viewport is `[470, 355, 1540, 846]`. Body-versus-blank
bounds are `[911, 583, 997, 700]`; item-only bounds are `[927, 602, 984, 680]`.
All item-only pixels lie inside the body bounds, so this control rules out total
item absence and displacement outside the frame. It demonstrates suppression
when the native frame body is present. A material or depth-transform mismatch
is a possible cause, but this run does not establish the specific mechanism.

The initial missing-capture-executable failure is preserved as v1. v2 and v3
are fresh background WGC captures with unchanged foreground ownership. Their
exact hashed source bytes were frozen before subsequent diagnostic edits.
The evidence index `tools/data/flat_frame_editor_submission_r10c.json` contains
report, receipt, PNG and frozen-source paths, hashes and archive locations.
Large PNGs are kept in the local archive, outside Git.

An independent restoration audit found the original document, closed workspace,
original factory class, zero diagnostic markers and zero accepted profiles.
Graceful shutdown timed out. Owner-bound forced shutdown then stopped both
recorded processes, and their identities were independently confirmed absent.

Validation: five focused diagnostic regressions and 17 blueprint tests passed;
Python compilation and `git diff --check` passed. Production shader candidates,
skinning/glint compatibility and additional facing/rotation cases remain open.
