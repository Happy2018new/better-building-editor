# Centered poppy native control result R13 V3

The isolated original-texture poppy is visible in full-world projection, but
the unchanged native fidelity test fails. Production remains disabled:
`POSITION_PLANT_PROXIES = {}`. The diagnostic identifier is
`modern_projection:diagnostic_centered_poppy`. This result grants neither
native mesh/offset authority nor editor, missing-mode, other-height or
other-coordinate acceptance.

The executed, independently reviewed plan is preserved as
`tools/data/snow-centered-r13-v3-result/plan.json`, SHA256
`2ab6f3788fc8bb207f1f40b45ca064c62ff577ea860781f914379e13cf4494fd`.
Its source baseline is `a7c0a8c`. All 95 indexed files retain their original
bytes and SHA256, totaling 12,719,617 bytes. The archive includes all 13
original PNGs, derived masks, exact input source, original/installed BP/RP
inventories, startup receipts, phase result and supervisor result. Failed
first captures remain in the evidence rather than being replaced.

## Scope and result

The native target was `(6, -48, 6)`, supported by dirt at `(6, -49, 6)`.
The projection origin was `(5, -49, 5)`. Camera offset was
`(-2, .15, -2.5)`, with FOV getter 60, screen 499 by 277, physical image
1994 by 1105 and fixed crop `(498, 276, 1495, 828)`. Same-session stone
qualification found a 113,706-pixel ROI, bounds `[306,115,683,455]`.
`WorldToScreenPoint` was absent. No analytical camera fit or screenshot
translation fit was used. Actual camera direction, render-event waits,
placement and offset acknowledgments passed.

| Difference against matched blank | Native pixels | Projection pixels |
| --- | ---: | ---: |
| Dry plant | 12,367 | 10,924 |
| Snow h0 | 25,956 | 25,846 |
| Covered h0 minus snow h0 | 10,341 | 9,088 |

Both dry-plant positive controls pass the unchanged minimum of 80 pixels.
The native/projection comparison uses the existing three-pixel tolerance
and minimum precision/recall of .75:

| Native/projection comparison | Recall | Precision | Result |
| --- | ---: | ---: | --- |
| Dry plant | .5981240397832942 | .6853716587330648 | Fail |
| Snow h0 | 1.0 | 1.0 | Pass |
| Combined covered h0 | .9088666376433029 | .938951739078108 | Pass |

The combined covered result cannot override the failed dry-plant comparison.
Native dry plant bounds were `[462,225,608,416]`; projected dry plant bounds
were `[443,225,573,414]`. These bounds describe the observed disagreement;
they are not used to recover a native random offset, mesh pivot or correction.
The phase completed without an error; `pixels.diagnostic_matches` and
`production_acceptance` are false.

The interleaved schedule captured native plant, native blank, projected
plant, projected blank, native snow, native covered, projected snow and
projected covered. Every projection frame verifies the actual world target
is blank before and after its capture. Every native phase stops the virtual
projection, so native covered snow does not contaminate projection frames.

## Original-image inspection receipt

All 13 original PNGs were opened directly during this execution, comprising
three startup images, stone/blank qualification and eight native/projection
states. The first scheduled image is black and rejected. The first SDK-ready
image is a loading screen; application readiness is accepted only by the
later real grass-world/HUD image. The two dry plant images both visibly
contain a poppy, with a horizontal/shape disagreement. The snow and covered
images were also inspected. QA independently recomputed all eight-state
mask pixel counts and native/projection comparisons, and inspected native
plant, projected plant and projected covered original images. No threshold
or crop changed after seeing these results.

## Ownership, cleanup and bounded cost

There was one cold launch and one matrix, taking 167.31750199996168 seconds
within the frozen 240-second total budget. Session
`c39ff8732a2946dc90250a51b007026c` belongs to owner
`snow-r13-centered-native`. Game PID 62504 had creation identity
`134363455933965559`; MCDK PID 52912 had identity
`134363455931257472`. WGC captures stayed background, with no activation,
desktop input or window resizing. Cleanup inspected those exact identities,
then terminated only the still-owned processes; final live/mismatch maps
are empty. Separate post-run passive host reads found both PIDs absent.

All four candidate resources, original resource absence, host adapters,
configuration, world fixture/environment, player and camera were restored.
Independent post-run SHA256 comparison matched the complete original BP/RP
inventory (1,436 files) and all three host-file backups. Native texture bytes
are unchanged. The profile journal is absent and its default is still empty.
Supervisor and phase cleanup error lists are empty.

## Next diagnostic boundary

The next native control must use a small frozen set of physical coordinates
and documented client/server `GetBlockClip`/`GetBlockCollision` observations,
with fixed placement and relative camera. Selection boxes must not be called
mesh pivots. A plan requires independent review before a bounded launch;
geometry or offsets must not be fitted to these PNGs. Production acceptance
still requires separate native holdouts, editor and missing-mode checks.
