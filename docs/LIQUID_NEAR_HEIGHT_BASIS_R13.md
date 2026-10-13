# R13 V4b saved height inputs and boundary investigation

The complete saved native neighborhoods match the candidate's inputs. There
is no observed missing/extra liquid neighbor, blocked corner or above-water
cell that explains H's failed boundary. The rule and published payload agree;
this does not establish that the rule is the exact native mesh-height rule.

All eight H and eight L palette/direct × before/after × client/server
36-cell snapshots have only stone at `(6,-59,6)` and water at `(6,-58,6)`;
every other foreground cell and every background cell is air, with no actor.
For each top corner there is therefore one liquid sample and three empty
same-height samples, with no water above. The stone is below this sampling
plane and hides the bottom face; it does not remove one of the three empty
corner samples.

The existing versioned candidate gives source depth 0 height 8/9, weight 11,
and empty weight 1. A single source corner is consequently
`(8/9 × 11) / (11+3) = 44/63 = 0.6984126984`. Nearest eight-bit rounding gives
178/255. Low depth 3 is `(5/9 × 1) / (1+3) = 5/36`, rounded to 35/255. Both
production-provider inputs and the independent rational oracle follow this
declared rule. The saved full-projection top/side groups actually publish
height pairs 45,746 (=178×257) for H and 8,995 (=35×257) for L.

The candidate's original accepted scope consists of static uniform 2×2 pools
and eight declared neighbor contexts; its native geometry, general accuracy
and production flags are still false. Native `GetBlockNew` / palette state
reports `liquid_depth`, not mesh corner height. The complete source readback
therefore verifies the rule inputs, not the native height formula itself.

Three bounded explanations remain for investigation, with distinct evidence:

- Height quantization is measurable but small: projecting the exact rational
  height instead of its fixed byte changes the H top corners by at most
  **0.339 pixels** and L by 0.989. H's >3-pixel failure cannot be attributed to
  its eight-bit rounding alone. No height was refitted to water pixels.
- Same-session stone calibration's independent individual fits are 66.3,
  66.3 and 66.6; the accepted shared FOV is 66.6. Using those already measured
  endpoints solely for a numerical sensitivity calculation moves H corners
  by up to **2.283 pixels** and L by 2.011. This identifies a nonzero camera
  uncertainty contribution; it neither changes the fixed FOV nor supplies a
  complete explanation for the failed boundary.
- The post-capture diagnostic uses thresholded changed blue pixels, whose
  contour also depends on translucency, background, filtering and rasterized
  coverage. Its whole-envelope mask is not an independent geometric marker.
  The original H native/full images visibly differ in brightness and animated
  pattern, so the failed blue contour cannot by itself choose a new native
  height or UV rule. A predeclared structural-marker/dry-background control
  should distinguish geometric displacement from this appearance effect.

Installed `renderchunk_water_near.vertex` also contains explicit TIME/world
coordinate wave displacement. However, `vanilla_netease/materials/terrain.material`
states that using/overriding its `netease_water_near/far` entries requires
`MATERIAL_ENABLE`, and its define is commented in this source. V4b does not
prove that those entries were active. Wave displacement remains an unproven
candidate and is not a reason to copy that shader or modify production.

[The immutable supplemental audit](evidence/liquid-native-height-basis-r13-v4b/audit.json)
records the exact source/readback references, all 16 neighborhood checks,
rational heights, saved byte/uniform agreement and source-only numerical
sensitivity. It includes original installed shader/material bytes and the
rule/candidate sources. Original V4b plans, PNGs, failures and manifest remain
unchanged; no rendering threshold, production source or qualification changed.
