# Native water side artwork and clock measurement

Run `python tools/measure_native_liquid_side_uv.py CONTRACT.json FRESH_REPORT.json`.
The output path must not exist. Exit zero means the declared spatial and clock
properties passed the fixed controls and holdouts. Synthetic success does not
establish native facts. Geometry, complete UV and production acceptance remain
false in every report.

## Frozen native input

The top-level contract requires `schema_version: 1`,
`native_name: "minecraft:water"`, `setter: "SetBlockNew"`, `completed: true`,
`restored: true`, empty `cleanup_errors`, `flow_freeze.forbidden: true`, and
`flow_restore.native_return_verified: true`. No flowing-name normalization,
layered block values, changed native neighbors, or collision inference is
permitted.

Each file reference contains its original absolute `path` and `sha256`.
`artwork` supplies `native_name`, `blocks`, `atlas`, `flipbook`, and `png`.
The loader resolves `water.textures.side` through the native terrain and
flipbook metadata. The bitmap must be that original resolved PNG, not a copy
or a generated crop. Explicit frame reordering is rejected; original alpha
range, replicate and optional clock metadata are preserved in the report.

`session_binding` records `id`, `owner`, `game_pid`, `game_identity`, and
`session_file`. `calibration` binds passed, completed, restored independent
stone calibration in that same session. `shape_analysis` binds a passed
`verify_liquid_surface_profile.py` report and its original source report,
profile, analyzer and fixture sources. All referenced hashes are rechecked.

`preflight` binds a JSON file created before every temporal frame. It contains
positive integer `created_qpc_100ns`, the exact `session_binding`,
`sample_grid`, `hypotheses`, and declared `sequences`. Its sequence declarations
contain the exact `id`, `case`, `geometry_role`, `source_plan`, `camera`,
`camera_pose`, `surfaces`, `temporal_control`, and `frame_roles`. Publish this hash before starting
the batch and preserve it. The final contract cannot change these declarations.
The native frame QPC timestamps must be later than the preflight timestamp.

`sample_grid` supplies arrays `u` and `vertical_fraction`, both within
`[0.1,0.9]`. Points are the Cartesian product on every declared side surface;
their world and projected pixel positions are computed from fixed geometry.
No pixel-driven grid, camera, corner-height, crop, or threshold adjustment is
available.

## Sequence structure

Each sequence includes:

- `id`, unique across the contract; `case`, matching the frozen shape row;
  `geometry_role`, either `training` or `holdout`.
- `source_plan`, identical to that case in the original frozen capture report.
  It contains `reserved`, `platform`, and exactly four `controls`:
  `supported_positive`, `supported_negative`, `liquid_only`, `empty`.
  Each control contains explicit `cells: [[position,[exact_name,aux]],...]`.
  The exact same water cells must be the sole difference in both control pairs.
- `camera`, identical to the frozen shape report, including calibrated
  `vertical_fov`, engine `screen`, and full PNG `native_image_screen`;
  `camera_pose`, with the unchanged actual SDK observations in `stable`.
- `surfaces: [{cell_origin:[x,y,z],corner_heights:[nw,ne,se,sw],side:"north"}]`.
  Other sides are `south`, `west`, `east`. Each surface must match a visible
  side and exact four heights in the frozen shape report, and face the camera.
- `static_controls`, the four complete capture records from the frozen shape
  evidence. Their PNG path/hash must be identical to its `raw_captures`.
- `temporal_control`, either `supported_positive` or `liquid_only`, fixed in
  the preflight; `frames`, temporally ordered complete capture records whose
  `control` always equals that declaration.
  Each has `role: "calibration"`, `"training"`, or `"holdout"`. Training
  geometry needs all three roles; held-out geometry needs calibration and
  holdout frames. Calibration frames fit only its constant photometric model.

Every static and temporal record includes complete
`native_before_capture`/`native_after_capture` snapshots for both server and
client. Every reserved foreground/background/actor cell must equal the exact
requested control plus the unchanged stone platform. Each `capture` contains
the existing reliable, fresh, background-safe Windows.Graphics.Capture record,
including owner/process/window identities, PNG hash/bytes/dimensions, unchanged
`camera_before`/`camera_after`, and native `capture.frame.frame_qpc_100ns`.
`clock_origin_qpc_100ns` supplies one common QPC origin. Cadence uses those
actual timestamps at 20 ticks per second; CLI call timing is not substituted.

At least one training and one independent geometry-holdout sequence are
required. Use the source-depth-zero pool for training and depths one and three
as geometry holdouts. Split each temporal sequence into predeclared initial
calibration frames, subsequent training frames, and later temporal holdouts.
Use irregular intervals spanning several source frames and more than one
animation cycle; static snapshots alone cannot establish cadence.

## Fixed search and gates

Example `hypotheses` plan:

```json
{
  "regions": ["full", "nw", "ne", "sw", "se"],
  "side_v": ["bottom", "top", "stretch"],
  "orientations": ["identity", "rot90", "rot180", "rot270", "flip_x", "flip_y", "transpose", "transverse"],
  "ticks_per_frame": [1, 2, 3, 4, 5, 10],
  "blend_frames": [false, true],
  "pixel_mapping": ["centers", "edges"],
  "phase_steps_per_frame": 16
}
```

Explicit `phases` may replace `phase_steps_per_frame` (integer one through
sixteen). Explicit positive fractional cadence candidates are also supported
for diagnostics; predeclare them and validate the integer candidate on the
independent holdouts before using an integer runtime setting.

`bottom` uses `v=1-height`, `top` uses `v=height`, and `stretch` uses
`v=1-height/top`. D4 orientation precedes full or quarter selection. `centers`
maps normalized UV to first/last pixel centers; `edges` maps to texture edges.
All quarter offsets are tested. Top/bottom mapping is mathematically equivalent
under a vertical UV flip, so the default property gate identifies height versus
stretched fraction (`v_basis`) and reports the selected compound mapping.
It does not claim those redundant labels were independently identified.

One constant model per sequence fits calibration frames only:
`positive = (1-opacity)*background + gain_rgb*texture + bias_rgb`.
Opacity is bounded zero through one; channel gains zero through two.
Hypotheses are ranked using training geometry and training frames only.
Geometry holdouts and later temporal holdouts never select or refit a
hypothesis. They use the same sequence photometric coefficients.

Defaults require RGB RMSE at most 3, explained variance over a background-only
null model at least 0.9, and fitted texture RMS at least 2 for every sequence.
Every required wrong-property control must lose by at least 0.5 training RMSE
and fail the held-out gates. The default required properties are `v_basis`,
`region_scale`, and `ticks_per_frame`; alternatives are searched across every
spatial and clock group. Missing controls, ambiguous alternatives or constant
visible colors fail. `limits` may tighten these values but cannot relax them.

The narrow `native_side_sampling_accepted` flag additionally requires both
height-basis and replication-scale identification. `native_cadence_accepted`
requires cadence identification. Neither implies full UV/orientation,
hidden-face, tint, collision, motion or production equivalence.

## Focused verification

Run `python -m unittest discover -s tests -p test_native_liquid_side_uv.py -v`.
Expected synthetic observations use direct integer bitmap accesses and an
independent temporal expression. Tests cover correct and wrong V/replication/
cadence, null/signal gates, holdout independence, cross-group clock alternatives,
threshold immutability, source metadata/path hashes, exact controls, process
identity, camera and state drift, preflight binding, and world-derived sides.
