# Native liquid surface diagnostic input

`measure_native_liquid_surface.py INPUT.json OUTPUT.json` runs only on the
host. OUTPUT must be a fresh path. Exit zero means the diagnostic was written;
it never means native liquid geometry or height accuracy was accepted.

The tool does not load PNGs, collect captures, validate process bindings, inspect
control pixels or fit the camera. Use the existing capture/binding checks before
preparing observations. The output explicitly records these unverified limits.

## Minimal input

Required top-level fields:

- `camera`: fixed `position`, `target`, `screen` in engine-projector pixel units,
  `vertical_fov` from the frozen compatible calibration, and optional `roll`.
  Without `native_image_screen`, observations and their budget use that same
  viewport and output units are `engine_pixels`. An optional full PNG viewport
  `native_image_screen: [width,height]` maps projected endpoints by independent
  X/Y ratios; observations and their budget then use `native_png_pixels`.
  No scale is fitted, inferred from pixels or verified against capture metadata.
  Do not substitute a compact screenshot or raw engine FOV for the calibrated
  source. Only complete viewports are supported; cropped images need a separately
  established coordinate transform and cannot be described by these dimensions.
- `cell_origin`: known world X/Y/Z of the cell's minimum corner. For a public
  `pure_liquids` case, derive it from the selected exact cell in
  `source_document(case_id, isolated=...)` plus the recorded world document
  origin. Keep the public original position and any isolation translation in
  `source`; do not infer X/Z from liquid texture or silhouette fitting.
- `declared_pixel_budget`: nonnegative pixels, explicitly declared by the
  caller. The existing 3px boundary budget can be recorded as 3, but this does
  not establish measurement accuracy. Intervals account only for this pixel
  disk; camera uncertainty is not included and accuracy is always unaccepted.
- `observations`: zero to four unique corner observations. Corner identities
  are X/Z offsets `[0,0]`, `[1,0]`, `[1,1]`, `[0,1]` relative to `cell_origin`.
  Each observable corner requires `pixel: [u,v]`,
  `visibility: "visible_boundary"` and a nonempty explicit `source`.
  Missing pixels, occluded corners and missing sources are not filled.
- `source`: caller-owned provenance, copied to the diagnostic. Include the
  public fixture/case/layer, selected cell, registry version/fingerprint,
  world translation, session/owner/process identity and fixed calibration
  path/hash. The mathematical tool preserves, but does not verify, this data.

Recommended observation source fields are the actual native PNG path/hash,
view identifier, `control: "supported_positive"` or `"liquid_only"`, and
`method: "manual_visible_outer_boundary"`. Include the associated control
report path/hash. No automatic PNG corner assignment is supported.

For the existing `499x277` engine viewport and `1994x1105` complete native PNG,
keep `camera.screen=[499,277]`, set `camera.native_image_screen=[1994,1105]`,
and provide the native PNG pixel and declared 3px budget unchanged. Projected
X/Y use scales `1994/499` and `1105/277` independently. The budget disk remains
in PNG coordinates, including with unequal scales; it is not approximated by
a disk in engine coordinates. This is host coordinate mathematics, not proof
that a PNG uses the supplied viewport or that the calibration remains valid.

The height domain is `[0,1]` blocks above the known cell origin. `near` defaults
to 0.05 camera-depth units and can be supplied explicitly. The entire declared
height line must remain in front of this plane and inside the viewport. Partial
near-plane/viewport geometry is rejected rather than fitted.

## Required real controls outside this mathematical tool

Use the exact public `test.layers.liquids` case and preserve its foreground or
background identity. The four public controls are `supported_positive`,
`supported_negative`, `liquid_only` and `empty`.

Before treating an observation as a native candidate, existing checks must
establish a reliable owner-bound native PNG, frozen compatible calibration,
unchanged camera/viewport and actual native state/neighborhood snapshots before
and after each capture. Require independent liquid-only versus empty signal
and supported-positive versus support-only signal, excluding supports, HUD,
overlapping cells and the unchanged boundary budget. Empty/invalid positive
controls must not supply corner observations. Retain the established pixel
thresholds; this tool does not use or adjust them.

Removing supports can change liquid state or shape. The liquid-only control
is an independent positive signal, not proof of identical supported geometry.
Native state drift or uncertain PNG identity invalidates the observation at
the caller's control gate, regardless of a small mathematical residual.

## Scope and result

The height interval is obtained analytically from the fixed projector's line
endpoints and depths. It is conditional on the supplied X/Z, camera and pixel
budget. No state-depth formula, native-height quantization or planar surface
assumption is used. A wrong X/Z can sometimes lie on the same projected line;
small residual therefore does not verify coordinate identity.

Each corner reports `diagnostic` or an explicit `unobservable` reason.
`four_corners_observed` is coverage of the four supplied observations, not a
native four-corner acceptance flag. Top-level `native_geometry_accepted`,
`accuracy_accepted` and `public_controls_eligible` remain false regardless of
caller-supplied source flags. Declared source `context_changed` is preserved,
and source snapshot and viewport/capture bindings explicitly remain unverified.
The sealed-shell capture report cannot become public accuracy evidence through
this mathematical tool. No flatness, hidden corner, neighbor face,
UV rule, liquid proxy or production geometry is inferred or generated.

For an isolated source, report only its independently visible external
corners. Another predeclared view can provide another diagnostic; hidden
corners in `source_pool`, `flow_corner`, or behind a solid remain unobservable.
Combine views only after checking matching native source/state/camera
provenance outside this tool. Do not fill absent corners from a flat-looking
image or from another control's inferred shape.

## Restored Contained Source Observations

`record_contained_liquid_heights.py REPORT.json OBSERVATIONS.json SESSION.json
OUTPUT.json` binds explicitly inspected, original-PNG corner pixels to the
captured source controls. It rechecks all four controls' PNG fingerprints,
owner/session identity, camera stability, native before/after snapshots, exact
public source translation and calibration fingerprint. The original capture
report supplies the independent positive pixel gates. It neither detects
corners nor verifies a pixel budget as measurement accuracy.

Round seven observations are in
`tools/data/contained_liquid_corner_observations_r7.json`; the versioned compact
diagnostic is
`tools/data/native_liquid_surface_diagnostics_nemc_3.9.0.401155.json`.
Sixteen explicitly visible corners cover source water/lava and the supported
and liquid-only controls in a barrier shell. Height intervals account only for
the declared 3px budget, excluding camera uncertainty. All public/native
geometry acceptance flags remain false. These observations do not establish
an uncontained height, a depth-state formula, flowing-state geometry or other
neighbors' weights, and must not become a production lookup table.

## Frozen Public Source Observations

The same recorder also accepts the completed, restored no-shell reports from
`capture_frozen_liquid_controls.py`. Current reports use schema 2 and explicitly
retain both logical cells and temporary native reference cells. Original schema-1
reports remain read-only compatible. The binder reconstructs all public source
cases and the shared air reservation, verifies flow suppression and restoration,
and rechecks every original PNG, camera and native snapshot. Background-only
liquid promotion is checked only in its native reference, never written into the
logical blueprint. This supports supplied visible corners of flowing and
neighbor cases, without assigning hidden corners or inferring a depth rule.

Here `context_changed=false` means no shell or altered block neighborhood was
introduced. Native flow simulation was still disabled; its baseline is the
explicit fresh owned world, and no flow-state getter exists. These controls do
not establish native flow propagation, UV direction, animation or height
accuracy. All geometry/accuracy/public-eligibility acceptance flags stay false.
