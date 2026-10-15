# Item rendering candidate R20 restoration

This is a paused, unqualified candidate. `item_icon_data.PRODUCTION_QUALIFIED`
must remain `False`. Do not promote diagnostic measurements to native visual
acceptance or relax existing native body/local-edge thresholds.

## Committed references

- `9eae52b0`: measured item front plane changed from 15 to 14.75 pixels for
  450 icon meshes, with replayable plane evidence.
- `135b8193`: layout-0 downward frame baseline uses 180 degrees, with
  replayable orientation evidence.
- `655ff72e`: `docs/evidence/item-glint-direction-r20-baseline-v1/` retains
  850 manifest entries, lossless pixel crops, native timing, source assets,
  and an independent replay. Old glint direction/speed acceptance, dynamic
  brightness acceptance, and production qualification are all false.

Replay the immutable glint baseline with:

```powershell
python -B -X utf8 docs/evidence/item-glint-direction-r20-baseline-v1/verify_package.py --pixels
```

## Preserved candidate

Frame layout 0 uses the measured native fancy-ambient formula from
`shaders/glsl/entityVertexUtil.h` in NEMC 3.10.0.420447. Source SHA256:
`5618dc4f8f734c0e49ef44250c2d404bd1010bf761d9611335a6795c5aa964f6`.
Normals share item orientation and follow the world skinning/instance path.
The base is lit before tile-lit squared glint is added. Nonframe layouts
retain their previous rendering.

The frame-only glint candidate has wave angles 80/-20 degrees, rates
2/15 and -4/11 cycles per second, UV offsets 4/15 and -8/11 per second,
and an 82.5-second wrapped `TOTAL_REAL_WORLD_TIME` clock. Frame glint color
is (.285, .1425, .4575), a .75 amplitude correction inferred from the
previous squared-glint brightness diagnostic. That final color has no
completed native dense acceptance capture.

`tools/run_visible_items_r16.py --native-target plain|enchanted` selects
the actual native fixture for both camera positioning and comparison.
The thickness analyzer rasterizes source texel prisms, measures sides and
front source-color gain, and always reports
`thickness_appearance_accepted=False` until the open visual gaps are solved.

## Evidence boundaries

- `.runtime/item-r20-glint-direction-v1/report.json`: product routes are
  measurable and the editor item is visible, but native capture has a
  345.46 ms gap above the unchanged 250 ms limit. `completed=False`.
  Diagnostic product direction errors are below .3 degrees and speed
  ratios are about 1.00-1.014. Old-color temporal gains remain about
  1.77 times native. This is not complete acceptance evidence.
- `.runtime/item-r20-glint-direction-v1-diagnostic/` retains those
  diagnostic product samples. Its printed fits were not saved as an
  acceptance analysis JSON.
- `.runtime/item-r20-glint-direction-v2/report.json` and
  `.runtime/item-r20-glint-direction-v3/report.json` both failed before
  dense capture while awaiting coordination, after 45 and 180 seconds
  respectively. Cleanup error lists are empty. Neither proves final
  color, cold acceptance, direction, or brightness parity.
- `.runtime/projects/item-r20-glint-direction-v2/` is the cold frozen
  source with the .75 frame-glint amplitude and all four automatic hot
  reload settings disabled. Do not reuse a previously used gate directory.

## Remaining ordinary-item gaps

Latest actual-source front diagnostic:
`.runtime/item-r20-lighting-v2-minus75-source-light-v1/analysis.json`.
It uses the plain `orientation.frame_f2_r1` capture, 29 visible source
texels, and RGB sample counts 84/163/163. Product RGB/source median gains
are [0.8231707, 0.8255319, 0.825]; native gains are
[0.7682927, 0.7667984, 0.7666667]. Absolute front brightness is still about
1.0763 times native. Relative side/front shading is about 1.0. Do not add
an arbitrary base-light scalar without establishing the native cause.

Thickness appearance, extrusion/body occlusion, editor-side visibility,
and Shelf integration remain open. Some earlier side captures had
invisible editor items. A 75-degree standard front-plane IoU is unsuitable
for actual native extrusion; retain the stricter native thresholds rather
than treating that mismatch as an acceptance pass. The frame-body
brightness probe in `.runtime/item-r20-lighting-brightness-v1/` had only
10-15 pixels per patch, below its 16-pixel minimum, so it is inconclusive.

## Verification and shutdown

Before the final diagnostic helper addition, all 108 `test_item*.py`
tests, catalog generation `--check` (6066 pairs, 425 IDs, 450 bitmaps),
and 16 GLES 2/3 compile/link variants passed. After that helper addition,
all four `test_item_thickness_acceptance.py` tests passed, owned-path
`git diff --check` passed, and behavior-pack review of `item_icon_data`
parsed one file with no findings. These offline checks do not substitute
for the missing runtime acceptance.

The owned game received normal stop. Identity-bound status subsequently
confirmed game PID 52140 and MCDK PID 39320 were both gone. The session
registry may retain a stale `ready` state; process liveness was checked.
No owned game or capture remains active. No forced process stop was used.

Resume only after scope and capture scheduling are coordinated. Dynamic
clock/compass calibration and additional special-item expansion are paused.
The separate frame-block task starts with a read-only integration survey.
