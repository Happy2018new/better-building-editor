# Native Plant Mesh and Offset Sources, R10B

This is a source investigation for F01-S03 / M08, not new native rendering
acceptance. On NEMC 3.9.0.401155 / Minecraft 1.21.120.0, no authoritative
native plant mesh, mesh pivot or position-dependent random-offset contract
has been recovered from the reviewed API catalog and installed resources.
No new native instance was started for this follow-up.

The machine-readable record is
[plant-native-source-investigation-r10b.json](../tools/data/plant-native-source-investigation-r10b.json).
It fingerprints nine complete MCP documents, the exact block-basic-info
dictionary excerpt, installed native mappings, eleven additional installed
world-generation definitions and four immutable R9 diagnostic reports.
MCP hashes identify the exact returned UTF-8 text without newline conversion;
they are document fingerprints, not hashes of installed engine code.

## Documented API Boundary

| Reviewed Source | What It Establishes | What Remains Unestablished |
| --- | --- | --- |
| World block management | `GetBlockClip` and `GetBlockCollision` return the current AABB; neighbors can affect the result | Rendered vertices, mesh pivot and random-offset formula |
| World block combinations and palettes | Block identities and positions relative to the palette origin; client acquisition requires loaded terrain | World-position preservation as a rendered-jitter contract |
| Block geometry | Three Combine routes and actor transform setters; unsupported mode 0 skips and mode 1 stops | Returned geometry name as proof that a native plant is visibly present |
| Block rendering | Texture/atlas queries, block-entity offsets and render-distance queries | A vanilla block mesh or visual-offset getter |
| Block properties and basic-info dictionary | Name-based metadata including render layer, solidity and gameplay properties | Position-dependent offset, mesh vertices or pivot fields |
| Virtual-world models | Model creation, transforms, animation and box-collider setters | Native block mesh readback |
| Netease custom block JSON/model guides | Custom X/Z offset scopes and binding a real resource-pack model | Vanilla offset hash or native hardcoded cross export |

The additional focused queries `GetBlockMesh`, `GetBlockGeometry`,
`GetVertices`, `GetBlockRandom`, `GetBlockOffset`, `GetBlockModel` and
`GetMesh` return no API entries in the reviewed MCP catalog. The basic-info
getter accepts a block name, with no position argument; its dictionary
documents fourteen fields and no mesh, pivot or random-offset field.
Exact queries and returned-document hashes are retained in the manifest.

These are limits of this inspection. They do not prove that an engine
facility cannot exist. The knowledge catalog is newer than this installed
runtime; catalog availability alone cannot establish NEMC 3.9 support.

The Combine guide recommends client palette serialization for custom
block-entity appearances. The four existing R9 native paths already use
client sources, so changing to a server palette does not add a supported
source hypothesis. Successful Combine submission is not visible-plant proof.

`netease:block_random_offset` sets custom-block X/Z scopes with two floats
in `[0,1]`; equal endpoints fix a point. Its material and model-binding
requirements do not document native flower coordinates or expose an offset
getter. R9 already measured its custom-model capability separately.

## Installed Source Boundary

Installed vanilla resource-pack `blocks.json` SHA256:
`cb3aad2d0d012bfb63a462ec9a5d8af54128c8afc26d74ac6f4ae074c9d50faa`.

Installed vanilla `textures/terrain_texture.json` SHA256:
`9ce3e389999a7aff19968a60fd21dad1811cf63ec3edd6afac0af0df649e212c`.

The six candidate entries supply texture/sound mappings, with separate
carried-texture mappings for short grass and fern. Crimson/warped roots map
the south face to the pot texture and the other named faces to the main
texture. These are actual source identities; a cube-face mapping does not
establish texture assignment to native crossed planes.

The installed vanilla behavior pack has no `blocks/` directory, and the
vanilla resource-pack `models/` directory contains only `entity/`.
No native cross mesh or offset declaration for these six plants was
recovered from those inspected paths.

This follow-up additionally searched installed `data/definitions` and
`data/renderer` JSON/material/shader-source files. The precise regex and
file globs are in the manifest. Eleven matches are world-generation
single-block features, scatter features or feature rules; renderer matches
are zero. Their coordinate distributions place blocks in the world and
do not specify the plant's per-cell visual jitter. The legacy fern feature
names `minecraft:tallgrass` with `tall_grass_type=fern`; that world-generation
identity is not substituted for the measured runtime name or aux value.
The eleven matching files are individually hash-bound.

## Existing Native Evidence

The checked R9 box report has 72 rows over nine plants and eight declared
positions, including adjacent X/Z cells, equal X/Z at three Y values and a
negative-coordinate cell. Its original SHA256 remains
`8ac66f6f562c90bfaaf16bb4517ec81e8327be98e0727f447e991a4545515a89`.
Server/client boxes match; grass/fern vary on X/Z/Y, poppy/torchflower/
roots/sprouts vary on X/Z, and fungi remain centered in those samples.
Equal X/Z at different Y yields equal relative boxes only in the measured
samples. An AABB centroid is not established as a native mesh pivot.

The four unmodified R9 mesh paths omitted visible native crimson roots.
R9 built-in cross experiments produced a dirt-cube mesh fallback, while
the custom Netease model's random scopes changed visual placement without
changing its unit-cube clip box. Those preserved failures and the custom
box/visual disagreement make a box-only rendering replacement unsupported.
The full diagnostic records remain in
[NATIVE_PLANT_DIAGNOSTICS_R9.md](NATIVE_PLANT_DIAGNOSTICS_R9.md) and
[BUILTIN_PLANT_CAPABILITY_R9.md](BUILTIN_PLANT_CAPABILITY_R9.md).
No existing box or four-path experiment was repeated.

Poppy's independently audited dry/h0..h7 public/right success remains
finite evidence at `(-47,117,-70)`, with isolated candidate resources.
[PLANT_CROSS_CANDIDATE_R10B.md](PLANT_CROSS_CANDIDATE_R10B.md) retains the
mixed-family failures, restoration and unchanged pixel/ROI gates.
The production `(name, aux)` registration table cannot enforce that measured
position scope, so this result does not authorize poppy default registration.

## Scope and Further Work

Production static defaults remain brown/red mushrooms and crimson/warped
fungi. Mushroom shape acceptance stays public only; fungi stay public/right.
The original independent exposed-plant masks, separate editor/full/missing
controls, fixed calibrated unit-cell ROI, recall/precision `.75/.75` and
3-pixel edge tolerance remain unchanged.

The native snow inventory contains 148 seed-name eligibility entries
selected by the render-layer-13 predicate, with 29 true and 119 false.
It tests each selected name's default aux value. It is neither 148 accepted
plants nor complete state/layer coverage, and supplies no geometry authority.

A new native probe needs a distinct documented source/API hypothesis and
a bounded, independently declared coordinate/source plan. No inspected
source currently supplies such a native mesh/offset getter or formula.
Repeating the existing boxes or unchanged four paths would not resolve the
missing visual-geometry contract. Source-based texture work and finite
candidate diagnostics may continue without promoting their result to a
position-independent production mapping.
