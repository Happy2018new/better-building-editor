# NEMC liquid reference study — 2026-10-13

The current liquid candidate preserves the installed artwork and has an
explicit side-height UV mapping, but its native atlas interpretation, default
opacity, flow direction and animation clock are not yet accepted. Static
inspection identifies an animation reset discontinuity and several specific
validation gaps. It does not identify a unique cause of the saved native-side
image differences, or qualify the candidate for production.

This is a read-only study of NEMC **3.9.0.401155**, with repository liquid
sources checked against root `dev` **`a280682`** on 2026-10-13. The inspected
worktree was `codex/r13-liquid` at `362a860`; the listed liquid production
sources are identical between these commits. No game was launched, historical
evidence was changed, or business code was changed for this study.

The complementary [Java reference study](LIQUID_JAVA_REFERENCE_STUDY_20261013.md)
documents downloaded official Java versions and their source mappings. Java
is a useful independent reference, not proof of the Bedrock native renderer.

## Findings and evidence limits

| Topic | Established by this study | Still requires independent evidence |
| --- | --- | --- |
| Source artwork | Generated PNGs are byte-identical to installed PNGs. Still alpha is 240, flow alpha is 255. | Native final opacity and lighting are not given by those alpha bytes. |
| Native metadata | Still has `ticks_per_frame: 2`; flow has `replicate: 2` and terrain `quad: 1`. | Exact quadrant selection, frame phase and flow cadence are not established by these fields alone. |
| Side UV | Current code maps `U=u/2`, `V=(1-height)/2`, anchored at bottom `V=1/2`. | This broad structure resembles the Java reference; exact Bedrock atlas/filter behavior remains unaccepted. |
| Sampler | Installed skeleton base specifies sampler 0 `textureFilter: Point`; current materials inherit it. | Runtime address/border behavior and any effective backend overrides are not established. Current bilinear frame bleeding must not be assumed. |
| Animation | `TIME` is documented to reset from 210 to 0. Current 32-frame periods do not divide 210 seconds. | The native atlas animation clock and phase are not established. |
| Flow top | Current flow direction is a gradient of four computed surface heights. | This is not an implementation of native fluid-state flow. Zero-gradient and falling flow are explicitly unknown. |
| Mesh interior | Four vertices and a fixed NW–SE diagonal produce two planar triangles. | A mathematical bilinear interior oracle can disagree with the actual mesh; native geometry must be compared against actual triangles. |
| Partial occlusion | Current classifier tests a versioned solid-name set, combines the two logical layers by Boolean OR, and ignores face direction. | Stairs, single slabs and panes require separate geometry/height/face evidence; the name set is not a directional shape contract. |
| Transparency | Candidate uses source-alpha blending, no depth writes, and double-sided faces. | Multiple overlapping groups, far faces and partial projection completion still need a declared draw-order/occlusion test. |

## Installed references and reproducibility

Installed source root used below:

`D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/data`

Paths and one-based lines below are relative to that installed root. Hashes
identify the exact files inspected; an engine update should create a new
versioned snapshot rather than silently reuse these line numbers or findings.

| File | SHA-256 |
| --- | --- |
| `resource_packs/vanilla/textures/flipbook_textures.json` | `54fef45e43eabb065a703f829d70320430c746744289775e57af582cb240fd7a` |
| `resource_packs/vanilla/textures/terrain_texture.json` | `9ce3e389999a7aff19968a60fd21dad1811cf63ec3edd6afac0af0df649e212c` |
| `resource_packs/vanilla_netease/materials/entity.material` | `b6079bb007bff8a307c65001bf1f3b3021b6d0492a90bb541db1bbf714e9716f` |
| `shaders/glsl/uniformPerFrameConstants.h` | `5a34477b34c0743fe066235e54129f4b0205d897bdb702cfbfdb49918bf1e196` |
| `shaders/glsl/renderchunk.vertex` | `174a82e624cf2c7c66e39ac6c4d19bc8bf37c91696bd7c59cafd842df7ce2f6d` |

The [Bedrock Wiki flipbook reference](https://wiki.bedrock.dev/blocks/flipbook-textures)
was retrieved through the project's knowledge library at
`BedrockWiki/blocks/flipbook-textures.md`. Its descriptions establish 20 game
ticks per second, `blend_frames` default true, and `replicate` controlling the
fraction of source pixels displayed (2 gives one quarter of a frame). They
do not establish which source quadrant is selected, native texel border
behavior, native atlas phase, or the omitted flow cadence in this installed
version. Installed metadata and measured native behavior take precedence over
extrapolating these descriptions.

## Artwork, alpha and material opacity

`flipbook_textures.json:309` names `water_still_grey`, with
`ticks_per_frame: 2` at line 311. Lines 314–316 name `water_flow_grey`, with
`replicate: 2` but no explicit `ticks_per_frame` or `blend_frames` entry.
`terrain_texture.json:1870` names `flowing_water_grey`, with `quad: 1` at
line 1871; the still entry starts at line 1931 without `quad`.

The following values were independently read with Pillow and SHA-256, then
compared byte-for-byte with generated repository PNGs:

| Native PNG | Size | Alpha range | SHA-256 |
| --- | --- | --- | --- |
| `resource_packs/vanilla/textures/blocks/water_still_grey.png` | 16 × 512; 32 square frames | **240–240** | `db3edc3132d88a595d466e90840a8e8839593776421435c23aa880fbd2a779c3` |
| `resource_packs/vanilla/textures/blocks/water_flow_grey.png` | 32 × 1024; 32 square frames | **255–255** | `f803fa03de42513b8e19db50e8c0743c5c82a06337afe0191efddd3e47684246` |

The copies under `resource_pack/textures/models/modern_projection/liquid/`
use names `still_water_grey.png` and `flowing_water_grey.png`. Both are
identical to their corresponding installed originals. Any claim that both
source images have alpha 255 is incorrect for this installed version.

This does not make still native opacity 240/255 or flow native opacity 1.
Installed `renderchunk.vertex:87` begins the blended-layer handling: vertex
color alpha below 0.95 participates in the `FANCY` branch at line 93, the
other branch constructs alpha 1 at line 98, and line 107 fades color alpha
toward 1 with distance. PNG alpha alone is insufficient to reproduce this
material contract. Presence of source code also does not prove which native
variant was active in a specific saved capture.

Current `modern_projection_liquid_still_water_grey.fragment:15` and
`modern_projection_liquid_flowing_water_grey.fragment:15` set
`DIAGNOSTIC_DEFAULT_OPACITY = 0.45`. Lines 27–30 select that fixed diagnostic
default when `EXTRA_VECTOR4.y < 0`, apply UI `CURRENT_COLOR.a` for the
orthographic case, and multiply the final projection opacity. With these
generated shaders, unspecified biome opacity does not sample PNG alpha.
`biomes.py:131` explicitly defines `None` as an unspecified engine default,
to be resolved by a verified render material contract. The diagnostic 0.45
has not closed that native default contract.

Relevant generator boundaries are
`tools/generate_liquid_skeleton_resources.py:339` (read size/alpha),
`:343` (copy original PNG), `:349` (separate animation metadata status),
`:350` (sampling acceptance false), `:432` (diagnostic opacity), and
`:443` (blend contract acceptance false). A later implementation should keep
artwork identity, biome tint, native opacity and user projection opacity as
separate responsibilities.

## Side UV and atlas interpretation

`resource_pack/shaders/glsl/modern_projection_liquid_world.vertex:35`
selects the side endpoint heights. At line 39 it computes
`height = v * mix(left, right, u)`; lines 40–43 place the four horizontal
faces; line 44 sets `liquidUv = (u, 1-height)`.

`modern_projection_liquid_flowing_water_grey.fragment:17` then multiplies
those coordinates by half of the 32-pixel frame size. Relative to one full
source frame, the resulting side coordinates are:

```text
U = u / 2
V = (1 - height) / 2
bottom: V = 1 / 2
top:    V = (1 - endpoint_height) / 2
```

The orientation is U increasing with +X on north, −X on south, −Z on west,
and +Z on east, from the actual face point construction. Reduced water height
changes the top V while retaining the bottom anchor. The Java study confirms
the broad half-frame/bottom-anchor structure as a reference. That resemblance
does not accept the current Bedrock native quadrant, texel mapping or flow
animation.

`generate_liquid_skeleton_resources.py:211` interprets `quad: 1` as a NW
half-by-half source region and edge mapping. The generator itself leaves
`native_sampling_accepted` false at line 217. Neither the installed JSON nor
the retrieved wiki proves every detail of that NW edge interpretation.
The flowing top deliberately uses a separate, full-frame center-window
hypothesis at lines 382–384. It must not be accepted merely because the side
uses a half-frame candidate.

Sampler state narrows the uncertainty. Installed
`vanilla_netease/materials/entity.material:806` defines
`entity_for_skeleton`; lines 812–816 add sampler 0 with
`textureFilter: Point`. At line 906, `entity_for_skeleton_alpha` inherits
that base. Repository liquid materials inherit the alpha base, for example
`resource_pack/materials/entity.material:75` and `:86`, without replacing
sampler 0. Thus bilinear mixing with a preceding frame is not established for
the current candidate and must not be reported as an observed defect.

There is still an explicit sampling difference to test. Flow samples texel
edges, reaching local pixel 0 and 16; still uses
`clamp(UV)*(FRAME_PIXELS-1)+0.5`, reaching texel centers. Point sampling removes
the assumed bilinear blend, but exact boundary ownership, source quadrant
selection and native atlas packing are separate questions. A future filter
change could introduce inter-frame filtering if the strip border is sampled
without a frame-local inset.

## Animation time and reset

Installed `uniformPerFrameConstants.h:12` states:

```glsl
// TIME will loop from [0, 210]
// make sure your shader handles the case when it transitions from 210 to 0
```

Current still and flow fragments at lines 22–24 use:

```glsl
float clock = TIME * 20.0 / TICKS_PER_FRAME;
float frame = mod(floor(clock), FRAME_COUNT);
vec4 texel = mix(sampleFrame(frame), sampleFrame(mod(frame+1.0,FRAME_COUNT)), fract(clock));
```

For 32 frames, the documented reset has the following arithmetic consequence:

| Candidate | Ticks/frame | Period | Nominal clock at TIME=210 | Frame modulo 32 before reset | Frame after reset |
| --- | --- | --- | --- | --- | --- |
| Flow | 1 | 1.6 s | 4200 | 8 | 0 |
| Still | 2 | 3.2 s | 2100 | 20 | 0 |

Immediately before the limit the blended image tends toward frame 8 or 20,
respectively; resetting `TIME` selects frame 0. The clock phase therefore
does not continue across the documented wrap. This is a deterministic
candidate discontinuity, not proof of the native atlas clock, native cadence,
or the cause of existing screenshot differences. A future fix should preserve
the accepted animation cadence rather than change it solely to divide 210.

## Flow direction and mesh interpolation

`behavior_pack/modern_projection/projection/liquid_flow_top.py:16` quantizes
`atan2(z,x)` to 256 turns. Lines 41–58 derive its input from four candidate
corner heights:

```text
dx = nw + sw - ne - se
dz = nw + ne - sw - se
```

This four-corner gradient is a declared hypothesis. The function explicitly
retains a still top when the gradient is zero, including falling states, and
states that native direction is unknown in that case. It is not equivalent
to the Java fluid-state flow algorithm documented in the complementary study.
The source texture's orientation and the angle convention must be checked
together; an angle offset must not be copied without that coordinate check.

`liquid_shape_data.py:9` supplies 16 depth heights, weight 11 for source and
falling-source states, and weight 1 for other contributions.
`liquid_shape.py:112` always samples all four corner cells. The Java study
distinguishes the historical weight-11/all-four implementation from later
weight-10 and conditional-diagonal implementations. Their differences are
concrete comparison cases, not authorization to replace the Bedrock candidate
with the newest Java algorithm.

The mesh interior is a separate issue from corner heights.
`generate_liquid_skeleton_resources.py:235` emits only four vertices per face
in `(NW, NE, SE, SW)` order; line 238 fixes triangles `(NW,SE,NE)` and
`(NW,SW,SE)`. The vertex shader's nested `mix` expression at line 27 is
evaluated only at those vertices. Rasterization interpolates two planar
triangles, not a continuous bilinear patch.

For an illustrative noncoplanar tuple `(0.8,0.2,0.8,0.2)`, a bilinear formula
at the center gives 0.5, whereas the fixed NW–SE diagonal gives 0.8. The 0.3
difference is mathematical, not a measured native error. Native rendering may
also use that diagonal; the mismatch only demonstrates why an oracle which
evaluates the bilinear interior cannot validate the actual mesh interior.
Do not replace the mesh or fit corner heights on the basis of this example.

## Partial blocks and two-layer occlusion

`behavior_pack/modern_projection/projection/liquid_native_shapes.py:17`
implements `blocks_liquid(cell)` as `is_solid(foreground(cell)) or
is_solid(background(cell))`. At line 21, `occludes_liquid(cell, unused_face)`
returns that same Boolean, explicitly ignoring the face argument.
`block_traits.py:15` tests only `value[0] in SOLID_BLOCKS`; the block's aux,
states, local shape, connecting neighbors and relevant liquid height do not
participate. `tools/generate_block_traits.py:131` generates that name set from
dump metadata rows where `solid` is exactly true. This is a versioned native
metadata classification, not a measured directional liquid-occlusion profile.

An independent AST read of the generated `SOLID_BLOCKS` found 599 names and
the following examples, without importing game-side modules:

| Block | Included in the current solid-name set |
| --- | --- |
| `minecraft:stone` | Yes |
| `minecraft:oak_double_slab` | Yes |
| `minecraft:oak_stairs`, `minecraft:stone_stairs` | No |
| `minecraft:oak_slab`, `minecraft:stone_block_slab` | No |
| `minecraft:glass_pane`, `minecraft:iron_bars` | No |
| `minecraft:oak_fence`, `minecraft:cobblestone_wall` | No |
| `minecraft:glass`, `minecraft:snow_layer` | No |
| `minecraft:water`, `minecraft:air` | No |

No name ending `_stairs`, no single name ending `_slab` without `double`, and
no name ending `_pane` appears in this particular set. This disproves a claim
that the current classifier necessarily culls stairs/slabs/panes as full
solid cells. Its actual risk is the opposite loss of geometry: these examples
are not blocked in any face direction. If they contain no same-family liquid,
the corner rule treats them as a nonblocked empty contribution at
`liquid_shape.py:53`, while the neighbor-face rule at line 134 cannot express
a partially covered face.

Consequently, the same result is used for upper and lower slabs, differently
oriented stairs, connected and isolated panes, and different liquid surface
heights. A single metadata Boolean cannot determine whether a specific top,
bottom or horizontal part of a fluid face is covered. Neither adding all of
these names to the solid set nor treating every non-solid as geometric air
would constitute native validation.

The two-layer OR is likewise a coarse classifier: it retains logical layers,
but does not compute their geometric union or the water-filled space around
a partial foreground object. `DocumentLiquidShapes._sample` at lines 101–106
separately detects liquid depth from both layers and rejects conflicting
depths. When a liquid depth is present, the corner calculation uses that depth
even if the solid Boolean is also true; a same-family neighboring liquid at
line 134 bypasses the solid face classifier. Thus waterlogged cells are not
simply treated as dry full-solid cells, but their partial shape contract has
still not been established by this code.

`tests/test_liquid_native_shapes.py:54` covers a whole stone neighbor and
`:66` covers layer/actor isolation for a waterlogged fence. Those are useful
source-preservation checks, not native tests for directional slab/stair/pane
occlusion. The Java study's directional shape comparisons supply reference
cases, but its `VoxelShape` APIs and height boxes cannot be copied into NEMC
as if they were installed SDK or resource capabilities.

Any next profile should keep corner-contribution classification, directional
face occlusion and native model resources as distinct contracts, backed by
versioned source evidence. The intended fluid behavior remains a **snapshot
without propagation**: this study does not introduce water simulation,
neighbor updates, fluid spreading or time-dependent world writes.

## Transparency and existing evidence

`generate_liquid_skeleton_resources.py:369` and `:393` generate side/top
materials with `Blending`, `DisableDepthWrite`, `DisableCulling`,
`SourceAlpha` and `OneMinusSrcAlpha`. The installed alpha skeleton base already
disables depth writes; the candidate also makes faces double-sided. This can
be appropriate for translucent water, but it does not independently establish
stable ordering for multiple overlapping water groups or determine which far
faces should contribute when a solid foreground object occupies the same cell.

Those are bounded test obligations, not a claim that the current engine always
draws them incorrectly. Editor and world projection need separate checks;
projection must retain complete source-neighbor information when a matching
real block removes only a virtual draw entry. A disappearing rendered entry
must not silently change a neighboring fluid's shape or flow input.

The [saved near-height audit](LIQUID_NEAR_HEIGHT_BASIS_R13.md) confirms the
actual V4b source neighborhoods and byte payloads, while leaving native height
and production acceptance false. It also records the installed near-water
shader's possible wave displacement. Installed
`vanilla_netease/materials/terrain.material:47` requires `MATERIAL_ENABLE`
to use/override the near-water entry, and its define is commented at line 49.
The existence of that shader is not proof it was active in the saved capture.

## Suggested next validation, before new game sessions

1. Exercise the declared TIME limit directly with immutable expected phase
   calculations at `210-epsilon`, `210`, `0`, and `epsilon`, separately for
   still and flow. Distinguish candidate continuity from native phase matching.
2. Enumerate the actual 32-pixel flow texel addresses for each face endpoint,
   frame and selected region, using the inherited Point sampler. Test edge
   ownership separately from a prospective linear-filter frame-inset test.
3. Compare mesh vertices, indices, height-byte rounding and interpolation with
   an independent piecewise-triangle oracle. Include a noncoplanar tuple and
   the opposite diagonal so a bilinear-only oracle cannot pass unnoticed.
4. Add distinct reference cases for historical/all-four versus
   conditional-diagonal corner rules, zero-gradient/falling flow, and cardinal
   texture rotation. Keep Java expected values labeled by version and separate
   from Bedrock native acceptance.
5. Preserve explicit/unspecified biome opacity and user projection opacity in
   independent expected-value checks. Raw PNG alpha, diagnostic 0.45 and native
   default opacity must not become interchangeable values.
6. Check the current classifier independently against versioned expectations
   for upper/lower single slabs, stairs facing each direction, connected/isolated
   panes, and a partial foreground object with background water. Separate dry
   corner contributions from partial face coverage and from two-layer fluid
   presence; do not promote a dry name-membership test to native geometry.
7. Declare one bounded background game capture set only after those checks:
   native versus candidate top and four sides, overlapping translucent groups,
   waterlogged solid with a visible object behind it, and a projection whose
   adjacent virtual entry is replaced by a real block. Reuse fixed camera and
   immutable source data. Compare structural coverage independently from
   brightness or animated-blue threshold contours.

These suggestions do not extend any acceptance flag. Current generated shape
and flow-top data still have `PRODUCTION_ACCEPTED = False`; the generator
separately records native shape, UV, alpha, animation, editor and memory
acceptance as false at lines 450–452. Version updates should diff the source
snapshots and regenerate only the affected profiles, with these contracts
remaining explicit.
