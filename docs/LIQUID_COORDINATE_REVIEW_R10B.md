# Liquid Coordinate Review R10B

This host-only follow-up closes two evidence-validation bugs. All original
plans, reports, PNGs, source archives and the verified ZIP remain unchanged.
The production liquid profile stays disabled, and every native UV and
production acceptance flag remains false. No game instance was launched.

## Validation Changes

Every score entrypoint now validates the whole sequence collection before
scoring: IDs must be unique nonempty strings, roles must be exactly `training`
or `holdout`, and both roles must occur. Preparation, extraction and rendering
entrypoints reuse the same validation. A deliberately wrong training sequence
with a colliding holdout ID is rejected before any scoring call. Previously,
the holdout result could overwrite the training result in the ID-keyed map.

The primary, background and absolute-center analyzers now require the outer
capture path to resolve to the inner WGC receipt path. Both SHA256 values and
byte counts must match the exact payload, and PNG encoding and wrapper,
receipt and frame dimensions must agree. Sampling decodes that verified
payload from memory. The primary analyzer validates every control wrapper.
A positive wrapper redirected to the negative PNG is rejected even when the
original inner receipt still passes its existing provenance checks.

Twenty focused tests pass, including these rejection regressions and strict
archive validation. All seven coordinate tools compile under host Python 3.
Independent read-only review found no remaining actionable issue in these
fixes. Every file in the original evidence directory was rehashed and matches
its pre-edit bytes, including the source archives and ZIP.

## Frozen Source Replay

Updated live tools correctly reject the original plan by default because the
plan records the old source hashes. The primary analyzer has an explicit
`--frozen-source-archive` option. It verifies every exact archive path and
SHA256 recorded in the original `frozen_sources` manifest, requires each
archive SHA to match its recorded live-source SHA, and permits changed or
absent live sources only after that verification. It does not execute the
archived analyzer; the fresh result records the current analyzer fingerprint
and every live-source difference separately. This mode rechecks preserved
evidence with the improved analyzer and must not be described as execution
of the original archived program.

Run from the liquid worktree with a fresh output path:

```powershell
python tools/analyze_liquid_coordinate_markers.py --input C:/Users/Happy2018new/.pyreact-debug/instances/356fe1cdf0f843bd804b22df63a0fd97/artifacts/native-coordinate-r10b-v2.json --output .runtime/coordinate-review-r10b/native-rank-replay-v2.json --frozen-source-archive
```

The verified fresh replay reproduces the original training rank RMSE
`0.20500418481930024`, selection `nw/bottom/identity/edges`, six distinct
sequence IDs, empty capture failures and rejection. Its exit status is 1
because the UV gate fails; the complete new report is still written.

Nearest, background and center diagnostic plans also record their diagnostic
tools as live-only fingerprints. Their updated CLIs retain those strict
checks and reject old plans. Exact execution of those archived diagnostics
requires a separate reviewed harness that verifies all archived dependencies,
including the `sources/tools/*-v1.py` snapshots and the
`sources/reviewed_frozen_harness.py` dependency. Do not rewrite original
paths/hashes, overwrite owned live tools or disable their source checks.
Earlier geometry and contrast evidence remain external frozen dependencies.

Fresh review artifacts are outside the immutable evidence directory:

| Artifact In `.runtime/coordinate-review-r10b/` | SHA256 |
| --- | --- |
| `native-rank-replay-v1.json` | `275ec3865211756e6062cf11d42bf3b41c322c2963bf063ffef086f066de5646` |
| `red-channel-statistics-v1.json` | `fdc0b3d7c86a5285176028d0879edebaf641b00ce6645cbf9db376c79a6f2c56` |

The statistics source is `.runtime/analyze_coordinate_red_r10b_review.py`,
SHA256 `3585c55f6b7cf25de5812c0e686f6c61373253e89e38a7b6bb76ad7e5b1f13c5`.

## Bounded Red Channel Analysis

The preserved absolute-center diagnostic selects bilinear sampling, which
equals the source texel at these fixed centers. Marker levels span 40 to 232;
sampled source standard deviations range from 51.51 to 60.04 across channels.
Recorded native observations have the following standard deviations and red
ranges. All numbers are RGB byte units except correlations.

| Sequence | Red Range | Red Std | Green Std | Blue Std | Red Correlation |
| --- | --- | ---: | ---: | ---: | ---: |
| `0/north` | 30.00 to 66.00 | 7.533 | 14.341 | 20.625 | .7610 |
| `0/west` | 31.00 to 66.00 | 7.378 | 14.508 | 21.101 | .6468 |
| `1/north` | 37.00 to 66.00 | 7.163 | 13.469 | 21.665 | .8765 |
| `1/west` | 37.48 to 64.00 | 6.483 | 13.147 | 22.265 | .8021 |
| `3/north` | 40.00 to 65.39 | 6.527 | 14.028 | 20.252 | .9093 |
| `3/west` | 37.48 to 64.00 | 6.675 | 13.631 | 20.914 | .8541 |

Green observations span 38.32 to 101.00, blue 43.79 to 132.08. Green and blue
rank correlations range from .9547 to .9828 and pass the .95 channel threshold.
Red has fewer distinguishable byte levels, so quantization can create more
ties and obscure closely spaced marker levels. It is not a sufficient
explanation for one global monotonic mapping: the same expected red level
has observed spreads up to 18.34 units in the training cases and 16.77 in the
holdouts. Rounding and bilinear sampling of rounded pixels contribute at
most a one-unit spread to a spatially uniform identical value. Different
filtering, shading, blending, backdrop contribution or a wrong UV prediction
must also contribute; these observations do not uniquely separate them.

The unchanged negative-control backdrop at identical sample coordinates has
red standard deviation 8.21 to 50.61 and range 97 to 225. Removing water can
change light transport, so this is evidence of backdrop variation rather than
a measured per-pixel blend coefficient. The prior transferred-transmission
subtraction diagnostic failed and does not validate that coefficient here.

Read-only installed GLSL and material declarations provide concrete reasons
why ranks across different world positions need not be preserved:

- `data/shaders/glsl/renderchunk.fragment` samples `uv0`, multiplies all channels
  by the light texture unless `ALWAYS_LIT`, multiplies RGB by vertex color,
  multiplies alpha by vertex alpha under `BLEND`, and optionally mixes fog.
- `data/shaders/glsl/renderchunk.vertex` supplies vertex color, light UV and
  position-dependent blend alpha fade. The tint and active uniforms were not
  captured, so their exact native values remain unknown.
- `vanilla/materials/terrain.material` declares sampler 0 as `TexelAA`,
  sampler 1 as bilinear and enables `Blending` for `terrain_blend`.
  `data/shaders/glsl/util.h` implements TexelAA with UV derivatives and a
  sampling mode based on LOD; it is not always raw bilinear or nearest.
- The optional `vanilla_netease` water fragment overwrites sampled RGB with a
  world-X/Z texture lookup, then applies the same tint, light, alpha and fog
  terms. Its presence does not prove that this material was active.

A positive spatially constant tint alone preserves ranks. Spatially varying
light/tint/alpha and an additive nonuniform backdrop can reverse ranks even
with correct UVs, especially for the attenuated red channel. The frozen raw
rank gate therefore tests a stronger, unverified global photometric condition
in addition to UV correctness. Its failure remains a valid rejection of this
experiment's acceptance contract, but it does not alone prove missing or
incorrect UVs. Conversely, passing green/blue and a preferred candidate do
not establish pixel mapping or native acceptance. Center/edge nearest
predictions still alias at these sample locations.

## One Next Experiment

Freeze one source-only grayscale coordinate-code experiment before another
cold capture: use complementary binary Gray-code bit planes of the full
32-by-32 texel X/Y address in the conventional flow strip, with high/low
levels shared by RGB and original dimensions/opaque alpha. Ten address bits
and their complements fit within the existing 32-frame strip, with remaining
frames reserved for independently readable phase/reference guards. Preserve
the original atlas, flipbook, shaders and materials. Record real native frame
phase from those guards; do not assume a cadence from the missing flow tick
declaration.

For each frozen geometry point, compare a bit plane and its complement at
the same native pixel. With stable light, alpha and background over the pair,
the signed difference cancels the fixed additive backdrop and retains the
coordinate bit under a positive channel tint. Use predeclared high-signal
green/blue signs and a fixed minimum difference, with neither gain fitting
nor background-transmission fitting. Guard failure or insufficient signal
rejects the pair rather than triggering exclusions or model changes.

The ten decoded bits distinguish quadrant, local U and local V. Freeze
training and changed-depth holdouts plus positions where center/edge source
predictions differ, including predeclared samples across code boundaries.
This can test source/quadrant, vertical basis, orientation and pixel mapping
in one experiment; center-only sampling cannot do the last. Retain the
independent camera/shape gates, all dry controls and restored state. Because
the active backend and its filtering remain unresolved, classify source
predictions before capture and reject ambiguous boundary mixtures rather
than fitting a UV shift or replacing the original gates. No part of this
future experiment has been executed in this follow-up.
