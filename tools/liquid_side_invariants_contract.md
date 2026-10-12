# Offline Liquid Side Invariants V1

`analyze_liquid_sides.py` is a host-only replay tool. It makes no SDK calls, starts
no native sessions, installs no assets and changes no worlds or configuration.
Its output never accepts native absolute RGB transfer, native UV/filter/sampler,
native animation or whole production. Missing physical controls or references
produce `NOT_TESTED` and `visible_side_correctness_observed: false`.

The frozen prospective design remains the separate note SHA256
`686fe72af4b88dac2488fdc62615be8d44f5eb7de852f67d8767ec17d8c6c42a`.
This tool implements the structural part and verifies a separately recorded
native original-art review. The old 81-combination absolute RGB failures, limits,
assets and reports are not edited or reinterpreted by this tool.

## Commands

```powershell
python tools/analyze_liquid_sides.py --geometry water_depth_0_foreground --output FRESH_GEOMETRY.json
python tools/analyze_liquid_sides.py --plan FROZEN_PLAN.json --output FRESH_OFFLINE_PREFLIGHT.json
python tools/analyze_liquid_sides.py --plan FROZEN_PLAN.json --input FROZEN_EVIDENCE.json --output FRESH_ANALYSIS.json
python -m unittest discover -s tests -p test_liquid_side_invariants.py -v
```

Outputs and their `.sources` archives must be fresh. Geometry and offline
preflight outputs cannot pass native acceptance. The native capture owner must
persist a separate receipt containing the returned `geometry`, the exact
`plan_sha256`, and positive `created_qpc_100ns` in the SAME clock domain as capture
`frame_qpc_100ns`, before its first PNG. CLI invocation timing is not a capture
timestamp. Do not add a receipt timestamp retrospectively.
Offline preflight exits1 with `preflight_geometry_ready:false` if a declared side
is off screen or L has less than24 projected pixels. That is a capture blocker,
not an invitation to change a camera after observing water images.

## Source Geometry

Only these existing built-in source IDs are accepted:

- H: `water_depth_0_foreground`.
- L: `water_depth_3_foreground`.
- C: `water_flow_corner_foreground`.
- F: `water_falling_column_foreground`.

The geometry export uses the existing exact source documents and registry state
resolution, but computes rational corners independently of runtime shape/vertex
helpers. It emits `source_cells`, expected quantized `surfaces`, and
`native_readback_cells`: the full one-cell neighborhood around nonempty source
cells, including explicit air. These cells are LOCAL document coordinates. The
capture runner must map world readbacks back into these coordinates without
normalizing semantic names, depths or layers.

H has corners `[178,178,178,178]`, faces31. L has `[35,35,35,35]`, faces31.
F lower/middle have `[255,255,255,255]`, faces30; its top has H's corners/faces.
C center `(3,3,3)` has `[222,92,43,188]`, faces5: its north and west faces are
hidden. Use C north `(3,3,2)` and west `(2,3,3)` for the initial sloped probes;
occupied controls may choose another remaining visible side in the preflight.
Side faces must exist and face the declared camera; source geometry cannot be
changed to expose a face that is hidden in the built-in source.

## Plan

Top-level fields:

```json
{
  "schema": 1,
  "kind": "liquid_side_visible_v1",
  "limits": {},
  "source_bindings": {},
  "marker": {"path": "ABSOLUTE_MARKER.png", "sha256": "64_lowercase_hex"},
  "original_artwork": {
    "still": {"path": "ABSOLUTE_NATIVE_STILL.png", "sha256": "..."},
    "flow": {"path": "ABSOLUTE_NATIVE_FLOW.png", "sha256": "..."}
  },
  "declarations": [],
  "crop_pairs": [],
  "missing_pairs": [],
  "original_pairs": []
}
```

`limits` must exactly equal the tool's `LIMITS`; obtain it through the imported
module. These are unchanged fixed checks: mask IoU .95, landmark/silhouette
boundary3 pixels, low side24 pixels, marker contrast12, marker samples80, absolute
RGB maximum3. The RGB field remains bound and false, not repurposed as a marker
colour-transfer fit. `source_bindings = source_bindings()` binds every listed
tool, source document, registry and cell/model implementation; referenced bytes
and local installed bytes are both rechecked.

Each declaration contains:

```json
{
  "id": "scene_marker_h_vnw",
  "source_id": "water_depth_0_foreground",
  "source_cells": [],
  "control": "supported_positive",
  "route": "scene",
  "role": "marker",
  "view": "vnw",
  "projection": {},
  "sides": [{"position": [3,3,3], "layer": 0, "face": "north"}],
  "background_id": "scene_marker_support_vnw",
  "excluded_rectangles": [],
  "occupied_positions": []
}
```

`source_cells` comes from `builtin_geometry(source_id,control)`. Routes are
`scene`, `full`, `missing`, `native`; roles are `marker`, `original`,
`native_original`. A support-only baseline uses `supported_negative`, no sides,
and the EXACT same projection, route and support cells. H/L may share that
baseline. Predeclared rectangle exclusions are complete native PNG coordinates
`[x0,y0,x1,y1]`; world crosshair may use the existing central40-pixel exclusion.
Never derive or revise exclusions from water pixels after capture. An occupied
stone hull is excluded geometrically with the same three-pixel inset budget.

Perspective projection:

```json
{
  "kind": "perspective",
  "origin": [0,0,0],
  "position": [-5,4,-7],
  "target": [3.5,3.5,3.5],
  "vertical_fov": 66.2,
  "roll": 0,
  "screen": [1920,1080],
  "native_image_screen": [1920,1080]
}
```

Origin translates LOCAL document points into the world's camera coordinates.
Use actual same-session stone calibration and actual camera readback, not this
illustrative numeric example. Bind that calibration in the runner's source and
session receipts. No FOV fitting from water pixels is available.

Scene affine projection:

```json
{
  "kind": "affine",
  "origin": [0,0,0],
  "affine": [[1,0,0,0],[0,-1,0,0]],
  "toward": [-1,1,-1],
  "screen": [1920,1080],
  "native_image_screen": [1920,1080]
}
```

Replace illustrative coefficients with geometry-derived logical XYZ-to-engine
XY rows from frozen native doll/layout/pose observations. Row0 is
`rx*x + ry*y + rz*z + tx`; row1 is `ux*x + uy*y + uz*z + ty`. `toward` is the
declared camera-to-visible-face vector. Full engine-to-native viewport scaling
is separate; cropped screenshots are not supported. Actual before/after
projection snapshots must equal the frozen declaration.

A crop pair names actual declared H/L marker sides at the same route/view:

```json
{
  "id": "scene_north_crop",
  "high": "scene_marker_h_vnw",
  "low": "scene_marker_l_vnw",
  "high_side": {"position":[3,3,3],"layer":0,"face":"north"},
  "low_side": {"position":[3,3,3],"layer":0,"face":"north"}
}
```

Canonical U is north x, south1-x, west1-z, east z. Crop registration rectifies
both images onto the SAME `(u,physical_height)` grid, which is driven by frozen
geometry at at-most-one-pixel spacing. Correct fixed-height landmark bands stay
registered when the waterline lowers. U flip, V reversal and stretched-fraction
wrong mappings must be discriminated by the marker; ambiguous/constant markers
are NOT_TESTED. Bitmap-edge samples are excluded before mask IoU and the separate
physical-pixel boundary budget is enforced.
The reported landmark Euclidean distance is capped at4 pixels;4 means it exceeds
the unchanged3-pixel budget, not a claim of an exactly measured4-pixel error.

The marker must be an opaque square or vertical square-frame strip with every
frame byte-identical. The checker reads its NW quarter by integer bitmap
coordinates `floor(u*width/2)`, `floor((1-height)*width/2)`. Use asymmetric unequal
column runs and irregular bands, including distinct patterns in the L-visible
lower rows. Bind matching diagnostic sampling in the separate resource plan;
this file generates no marker resources and never replaces original water art.

Missing pair:

```json
{
  "id": "corner_source_neighbor",
  "baseline": "missing_marker_c_vnw",
  "occupied": "missing_marker_c_occupied_vnw",
  "restored": "missing_marker_c_restored_vnw",
  "occupied_positions": [[2,3,3]]
}
```

All three use C and route missing. The occupied declaration also lists exactly
that position. Source cells remain identical in all states. Surface comparison
ignores model IDs/group order, but preserves exact heights, faces, layer, material
parts, template, rotation and tint. Occupancy must be settled and ordinary owners
ready. Original source neighbor remains in shape evaluation after its draw is
hidden; substituting air in the provider must fail.

## Evidence And Review

Evidence includes `schema:1`, `evidence_kind:"physical_native_capture"`, exact
hashed `plan` and `preflight` references, `session_binding`, existing reliable
full-native WGC `captures` keyed by every declared ID, `states`, and
`completed/restored:true` plus empty `cleanup_errors`. All captures must postdate
the actual preflight QPC and match declared dimensions. Synthetic tests never
qualify native behavior.

Each candidate state has exact `source_cells`, `ready:true`,
`projection_before/projection_after`, and captured applied owner `groups`:

```json
{
  "origin": [0,0,0],
  "uniforms": [[0,0,0,0],[0,0,0,0],[0,0,0,0],[39686,0.45,0,1]],
  "layer": 0,
  "texture": "flowing_water_grey",
  "template": "DECLARED_SIDE_TEMPLATE",
  "visible": true
}
```

These four vec4s are actual owner-applied payloads. The checker independently
decodes address6, face6, rotation8, paired8-bit corner heights and24-bit tint.
Resource texture/template come from the STRUCTURED group key's resource pair,
not a parsed repr string. These four pure built-ins have layer0; retain it
explicitly. Optional `quantized_surfaces` must match that decoded payload exactly.
Missing triplet states also set `occupancy_settled:true` only after no changed,
pending, building, staging/retired request or owner error remains.
Physical candidate evidence must supply a `groups` list, including an empty list
for an empty support-only state. Semantic `quantized_surfaces` alone are accepted
only for synthetic diagnostic fixtures.

Native original states supply actual `native_readbacks` as a hashed JSON
reference. That record has exact `session_binding`, `before` and `after` arrays
matching the emitted `native_readback_cells`, `flow_frozen:true`, and exact
`original_artwork` references from the plan. Boolean assertions alone cannot
replace native source readbacks. The runner must retain the raw server/client
snapshot records used to construct these arrays and verify both sides agree.

Original pair:

```json
{"id":"scene_h_vnw_art","candidate":"scene_original_h_vnw","native":"native_original_h_vnw"}
```

Both declarations have the same source and view. Candidate role is original;
reference role is native_original and route native. One native reference may
be reused for Scene/full/missing comparisons at the same physical view.
Both candidate and native before/after projections must exactly match their
frozen declarations. Native projection drift is a failure even when capture
hashes, exact source readbacks and a previously recorded direct review still match.
Every pair collection (`crop_pairs`, `missing_pairs`, `original_pairs`) requires
unique nonempty string IDs so results cannot overwrite earlier observations.

Evidence `original_review` references a separate immutable JSON record:

```json
{
  "plan_sha256": "...",
  "reviewer": "INDEPENDENT_REVIEWER",
  "pairs": {
    "scene_h_vnw_art": {
      "capture_sha256": {"candidate":"...","native":"..."},
      "four_face_direction": "NOT_TESTED",
      "physical_height_crop": "NOT_TESTED",
      "original_side_artwork": "NOT_TESTED",
      "original_top_artwork": "NOT_TESTED"
    }
  }
}
```

Properties may be OBSERVED, FAIL or NOT_TESTED. Use actual native original-art
pixels and the fixed 32-frame source reference when phase is ambiguous. A
marker result or owner metadata is not an original-art review. This separate
record accepts only practical visible ordering/crop/artwork; it cannot grant
native absolute RGB/filter/timing acceptance. Fixed original artwork SHA256s
are checked against both actual original files.

## Finite Coverage

Use H/L vnw (north+west) and vse (south+east) through all three candidate routes:
12 positive marker images and6 shared support baselines. C/F vnw across routes
adds12 (positive+support). Missing C occupied/restored adds2:32 marker PNGs.
Add18 original candidate holdouts and6 actual native original references:56
side/crop/art PNGs. Retain alpha12 separately. The original design's optional
timed animation/body extensions remain independent and are not accepted here.

`visible_side_correctness_observed` requires full four-face H/L coverage on all
routes, all12 crop pairs, C/F on all routes, a settled occupied-neighbor triplet,
all18 original-art review pairs, and physical capture provenance. A narrower
finite plan can be replayed diagnostically, but cannot claim full visible side
correctness. Production and every native absolute UV/filter/animation flag stay
false regardless of direct visual observation.
