# Native Dripstone AABB Holdout Plan

The holdout plan is fixed in `holdout_samples()` before collecting new native
observations. Run `tools/verify_dripstone_native_boxes.py --holdout` through
the same owned desktop runner used for the original box probe.

The matrix contains 46 X/Z positions and two root heights, `-47` and `-31`.
Each root has a standing/hanging merged-tip pair and two stone supports:
184 measured dripstone cells and 184 stone positive controls in total.
All coordinates remain inside a compact 67 by 20 by 67 selection, with
no measured/support overlap. Reserved cells and their immediate neighbors
must be air before placement. World and player restoration are mandatory.
The temporary player platform is near the selection's horizontal center,
so the opposite edge does not depend on loading from the minimum corner.

Both axis sweeps use coordinates `-33,-32,-31,-17,-16,-15,-1,0,1,15,16,17,31,32,33`,
holding the other horizontal axis at `6`. A diagonal sweep pairs that same
sequence with its reverse, and `(6,6)` repeats the original X/Z control at
both new heights. Thus signs, zero, nearby axis changes, multiple signed
chunk boundaries and Y independence are measured together.

The report retains every native client/server clip and collision box,
stored native states, world seed, runtime versions, the source tool hash
and the original AABB evidence fingerprint. It requires exact agreement
between all four box methods for every cell. This provides raw holdout
evidence; it does not fit a screen-space correction or implement a table
of native offsets.

The original four X/Z observations are compatible with 16 equally spaced
horizontal positions over `[-0.125,0.125]`. That quantization and Y
independence remain hypotheses until checked against this holdout.
The documentation for `minecraft:random_offset` says that world position
affects collision, selection and geometry, and exposes ranges and steps.
It does not expose the native coordinate hash or palette seed contract.

No production algorithm is established by this sampling plan. Any proposed
algorithm must have an independently identified source or derivation,
specified integer/overflow semantics, and agreement with native holdout
boxes. Native geometry and strict projection pixels still require their
separate tests even if a box algorithm is later verified.
