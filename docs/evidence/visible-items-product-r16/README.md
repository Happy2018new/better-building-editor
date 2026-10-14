# Measured Item Contents, Round 16

Engine: NEMC `3.10.0.420447`, Bedrock `1.21.130`.

This evidence is separated from deployment qualification. The measured icon
profile remains disabled in production until its complete declared acceptance
matrix and a default-profile cold start pass. Shelf and campfire contents have
independent family gates; frame acceptance cannot enable either family.

## Measured Resource Contract

- 2,394 loaded item identifiers; 1,907 vanilla identifiers examined.
- 30,640 measured identifier/aux texture observations.
- 425 accepted flat item identifiers, 6,066 accepted identifier/aux pairs,
  deduplicated into 450 bitmap silhouettes.
- The exact installed atlas, source bitmap, target engine, geometry, shader,
  icon pose, enchantment policy and generated registrations are fingerprinted.
- Durable aux values reuse their measured silhouette while document NBT stays
  unchanged. Unknown visual userdata and special item classes are excluded.
- Exclusions include block geometry, potion/tint variants, maps, dynamic
  compasses/clocks, banners/shields, spawn eggs, dyed leather, tridents/spears
  and loaded crossbows. These require separate rendering families.

`tools/data/item_icon_catalog_nemc_3.10.0.420447.json` is the measured source.
`generate_item_icon_catalog.py --check --install <target install>` verifies
reproducibility and rejects stale engine, pose, bitmap or glint contracts.

## Actual Runtime Findings

The healthy v5 capture contains 12 representative item categories, editor,
full projection, missing projection and actual native frame references. It
also contains shelf/campfire slot cases and true-time enchantment sequences.
All native references restore player, inventory and world changes.

The six-face pilot found two genuine product defects: upward-facing content
had a 180-degree base error, and nonzero frame rotations ran in the opposite
direction from native `ItemRotation`. Both are corrected in the shared icon
vertex path and declared in the versioned pose contract. Campfire/shelf layouts
are excluded from frame-only corrections.

The native ceiling-facing frame reference accepted and returned the typed
item but did not display that item. Its native visual oracle remains
unavailable; this is not recorded as a successful pose comparison.

Regular/glow frames produce identical owned content plans for all 48 poses,
verified by an exhaustive static test. Their native support bodies remain a
separate engine rendering responsibility.

The distance-six representative capture matches native outlines for all 12
categories with recall and precision 1 at a two-pixel tolerance. Emerald is
still too small for the 48-pixel minimum. One bucket editor pair differed by
0.00015 UI units due to native float layout; a bounded 0.001-unit layout
tolerance (at most 0.004 physical pixels in this capture) now accepts this
rounding while actual one-pixel drift and changed model identities fail.

## Enchantment Visibility

The original sine-based effect visibly moved, but that was insufficient for
acceptance. A compact public-blueprint-derived scene enlarges proxy swords to
157 pixels and a real native enchanted diamond sword to 158 pixels. Ordinary
and empty frames are negative controls. No image enhancement is used.

The baseline effect had RGB temporal range p90 65 versus native 98 and median
highlight centroid speed 0.044 versus native 0.185 body widths per second.
The baseline is retained as a rejected visibility control.

The replacement samples the target engine's actual
`textures/misc/enchanted_item_glint.png`, uses two rotated scrolling layers,
and applies the native squared additive color formula. Its scroll phases are
continuous across the engine's 210-second clock wrap. Explicit `highp`
precision is declared in both vertex and fragment shaders.

Healthy recapture `.runtime/visible-items-r16-glint-zoom-v3` completed with no
cleanup errors. The replay reports valid evidence, all declared bodies pass,
and native-relative glint visibility passes in editor, full and missing
projection. Native-relative ratios are:

| Route | RGB Range | Luma Range | Visible Coverage | Centroid Speed |
| --- | ---: | ---: | ---: | ---: |
| Editor | 1.64 | 1.67 | 1.11 | 0.62 |
| Full projection | 1.60 | 1.67 | 1.13 | 0.80 |
| Missing projection | 1.51 | 1.55 | 1.11 | 0.54 |

The test requires 150-pixel bodies, real native reference validity, duration,
ordinary/empty controls and relative contrast/coverage/motion. It does not
claim exact native lighting or shader parity. Sparse centroid speed is a
visibility diagnostic, not a continuous animation velocity measurement.

The glint capture predates the side-wall generator correction below. Its
fingerprinted visibility result remains evidence for that captured resource
contract; it does not qualify the newly regenerated complete geometry bundle.

## Side-View Findings And Generator Correction

The generated items are extruded geometry, with two bitmap surfaces and
exposed alpha-silhouette edges, 0.5/16-block thickness and a versioned frame
plane at 15/16 blocks. Mesh faces carry normals, but the owned shaders do not
yet use these normals to distinguish side-face lighting. Thickness and plane
offset still require independent native side-view qualification.

The shared silhouette generator tested the west edge against its east
neighbor and the east edge against its west neighbor. This generated internal
walls and omitted exterior boundaries. The neighbor directions are corrected;
single-texel, adjoining horizontal/vertical two-texel and asymmetric separated
texel regressions verify all exterior edges and reject internal walls. All
dependent 3.9 block proxies, 3.9 skeleton sprites and 3.10 measured icon meshes
were regenerated, and all three generators' reproducibility checks pass.

The public north-facing frame fixture was captured at 70 degrees before and
after the correction, with native frame placement/readback, editor, full and
missing projection, paired hidden controls and stable camera/source checks.
Both batches completed and replayed with valid evidence and no cleanup errors.

The earlier cold start displayed no editor item pixels at this angle. The
corrected geometry's new cold start displayed 1,045 plain and 1,012 enchanted
item pixels. The editor's apparent disappearance is reproduced and later
visibility is observed, but these are separate cold starts. They do not prove
that geometry was the sole cause, nor exclude a shared-depth or cold-start
resource-state issue.

The side-view acceptance remains failed. The existing alpha-mask metric
models the front surface and does not cover the extruded side silhouette.
World/native comparison after the correction has recall 0.98646 and precision
0.98503, but the plain reference is only 21 pixels wide, below the 48-pixel
minimum. No threshold was relaxed. Future checks must enlarge the same actual
native item, measure plane separation/thickness and test controlled repeated
layouts within one instance before declaring 3-D parity.

`sides-review-v1/review.png` displays before/after crops without filtering or
color adjustment; full-resolution paired PNGs are adjacent. The archive
contains selected raw images, hashes and replay summaries rather than the full
local capture reports. It is not presented as a complete standalone replay.

## Bounded Pose Batches

The final eight-case batch has valid evidence and restoration but stops at
the owned process-handle budget. It covers upward rotations 0/1 and north
rotations 0 through 5. Actual native-outline comparison passes six cases;
north rotations 1/5 have recall 0.98413/0.98403, below the 0.985 threshold.
These failures remain open. Another twelve measured side-face pose cases
completed locally, but later world camera drift invalidated their overall
batch. It is retained as diagnostic evidence only. Neither batch completes
the declared regular/glow frame matrix or qualifies production deployment.

## Boundaries And Remaining Qualification

- Shelf native block bodies are absent in Combine and require an independent
  body implementation before shelf contents can be released.
- Campfire slot geometry exists but needs independent accepted slot poses.
- Lectern book NBT and public fixture exist; book geometry is not implemented.
- Complete item pose/depth/opacity acceptance and production cold start remain
  required before enabling the measured icon profile.
- Side-view plane separation, thickness, lighting and shared editor depth
  remain unqualified; repeated controlled layouts are the next investigation.
- Native process handles grow with elapsed runtime. Capture tools stop before
  their owned handle budget, record exact completed/remaining case identities,
  restore all changes and restart short batches. A clean partial batch is not
  presented as a complete matrix.

## Local Evidence Index

| Evidence | Path |
| --- | --- |
| Full representative and slot capture | `.runtime/visible-items-r16-product-v5/report.json` |
| Original native closeup comparison | `.runtime/visible-items-r16-product-v5-native-analysis/analysis.json` |
| Six-face discovery | `.runtime/visible-items-r16-orientations-pilot-v1-analysis-v2/analysis.json` |
| Upward correction/nonzero rotation discovery | `.runtime/visible-items-r16-orientations-pilot-v3-analysis/analysis.json` |
| Larger representative comparison | `.runtime/visible-items-r16-representatives-near-v1-analysis-v2/analysis.json` |
| Rejected weak glint baseline | `.runtime/visible-items-r16-glint-zoom-v1-analysis-v2/analysis.json` |
| Rejected camera drift capture | `.runtime/visible-items-r16-glint-zoom-v2/report.json` |
| Accepted larger glint comparison | `.runtime/visible-items-r16-glint-zoom-v3-analysis/analysis.json` |
| Bounded final eight-case pose comparison | `.runtime/visible-items-r16-final-poses-v2-analysis/analysis.json` |
| Invalid later side-face pose batch | `.runtime/visible-items-r16-side-poses-v1-analysis/analysis.json` |
| Valid 70-degree comparison before correction | `.runtime/visible-items-r16-oblique-before-v1-analysis/analysis.json` |
| Valid 70-degree comparison after correction | `.runtime/visible-items-r16-oblique-after-v1-analysis/analysis.json` |
| Archived selected native side-view comparisons | `sides-review-v1/summary.json` |
| Target-header shader compile/link | `.runtime/item-icons-r16-shader-compile-v6.json` |

Raw paired captures and Windows.Graphics.Capture receipts remain in each
local capture directory. Archived selected captures and replay results are
adjacent to this document. Production acceptance is deliberately separate.
