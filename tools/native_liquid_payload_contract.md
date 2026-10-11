# Isolated Liquid Payload Experiment

This is an unaccepted transport experiment, generated outside the production
packs. It consumes four explicit heights in `(00, 10, 11, 01)` X/Z order and an
explicit six-face mask. It does not infer native liquid heights, neighbor face
rules, world state, flow direction or any Java liquid algorithm.

`generate_liquid_payload_poc.py --native-data GAME/data --output FRESH_DIRECTORY`
generates a resource overlay and an independent custom-actor pose fixture.
The authorized experiment owner may merge this overlay into a cold-start test copy.
The generated `blocks.json`, `terrain_texture.json` and `terrain.material` are
partial dictionaries and must be merged by JSON key, never copied over their
production counterparts. No manifest, application startup or world operation
is performed by the generator.

## Carrier Layout

- Each four-cubed logical batch has at most 64 source cells and 448 carrier cells.
- A top uses two degenerate quads, each containing one real triangle. Three
  independently supplied heights survive each triangle; shared corners are
  quantized once with the same rounding rule.
- North/south/west/east sides use two supplied top edge heights and a zero bottom.
  The caller controls face presence. A bottom is a separate quad.
- Palette X/Z carry two integer height codes. Palette Y carries
  `logical_cell_index + 64 * primitive_kind`, in `[0,447]`.
- The static proxy's fixed UV point carries the third triangle height. At most
  256 static proxy IDs are required, independent of document size or height
  combinations. No per-liquid-cell client entity is created.
- The source plane has X/Z corners at `-0.25/+0.25` around its native cell centre.
  Its Y is an integer. Eight-bit X/Z codes reach 255; six-bit codes reach 63.
  Native packed-input preservation is unverified for both this exact geometry
  and the UV point. Shader `highp` cannot repair prior native quantization.
- The generated static cube is `[8,1,8]` with only its `up` face present. Its
  top remains at model Y=8; the nonzero body tests removal of zero-volume cubes
  without changing the decoder input. Its UV point still has size `[0,0]`.
  A separate static control has identical geometry and full-area UV. It is
  diagnostic and does not carry a third height.

Six-bit height quantization has maximum error `1/126` blocks; eight-bit has
maximum error `1/510` blocks. These are transport error bounds, not native height
accuracy claims. Missing or unobservable heights are rejected.

## Shader Binding

The isolated world actor uses these SDK extra uniforms:

| Uniform | Value |
| --- | --- |
| `EXTRA_ACTOR_UNIFORM1` | caller-owned RGB tint, unused W |
| `EXTRA_ACTOR_UNIFORM2` | native liquid atlas rectangle `(u0,v0,w,h)` |
| `EXTRA_ACTOR_UNIFORM3` | payload atlas rectangle `(u0,v0,w,h)` |
| `EXTRA_ACTOR_UNIFORM4` | `(39683, height_denominator, 0, opacity)` |

Both rectangles require a validated native source. The documentation exposes
`CreateBlockInfo(levelId).GetTextureAtlasUV(textureKey)`, but the installed
NEMC 3.9.0.401155 client has no such method. This was checked in a ready,
owner-bound cold-start session reporting runtime `1.21.120.0`. Therefore this
atlas-rectangle shader has no usable binding route on the tested client. Do not
guess bounds from terrain metadata or present the CPU/GLES oracle as a native
backend. `WorldToScreenPoint` and `GetViewMatrix` are absent as well.
The native keys are `still_water_grey`, `flowing_water_grey`, `still_lava` and
`flowing_lava`. The current installed `terrain_texture.json` and
`flipbook_textures.json` are captured and hashed by the generator. Native
flipbook entries animate these tiles in place, but sampling through the custom
mesh must still be demonstrated in native PNGs. The experiment does not add or
override their flipbook definitions.

Other actor draws retain the current production shader through a generated
fallback function. This does not establish material descendant inheritance
or native texture binding; both remain explicit test gates.

An alternative may bind a native liquid key directly in a custom model and
sample its actual `TEXCOORD_0`. That would leave UV available for native
flipbooks, but the third height would need a separate tested input. Neither a
fractional local model coordinate nor `WATER_TEXTURE_UV_RANGE` is accepted as
that input: native quantization and actor uniform availability are unmeasured.

## Native Fixture Prerequisites

Moving only the camera is insufficient to load a remote section. The pose
probe saves the player foot, reserves an air region in both layers, creates a
temporary stone platform, moves the player near the source, waits for client
foot and palette replication, and allows three seconds for section loading.
It then sets the validated camera rotation with `GetRotFromDir` and yaw+180,
waits two seconds, and captures through owner-bound WGC without desktop input.
It restores the player, camera, environment, world region and client actors.
Each capture preserves process identity and background-focus metadata.

The ordinary stone control v6 and custom shulker control v1 visibly render both
world source and live/roundtrip palette projections. Their difference counts
are diagnostics only; moving background objects cannot establish shape
agreement. The pose v10 and nonzero static point-UV carrier v2 completed and
restored successfully but have no visible source or projection. Pose setters
returned true while the actual serialized actor entry remained `{0:{}}`.
Those reports retain `native_pose_accepted=false`; neither method success nor
non-null Combine results establishes a usable mesh or pose transport.

The full-area UV static control v3 and pose v11 with an explicit local opaque
texture remain invisible after a fourth guarded cold startup. A standalone
full-volume client entity using the same fixture registration is also
invisible. This leaves the fixture rendering failure unresolved; it does not
prove that zero-size UV, flat model geometry, native pose baking or atlas
animation is unsupported. The probe's ordinary attachment uses actor tag
`19487`, so these are source/model visibility tests. The payload decoder tag
`39683` was never activated in native pixels. No native carrier-address or
liquid texture sampling claim follows from them.

Compact report identities, cleanup results and acceptance boundaries are
recorded in `data/liquid_payload_r7_checkpoint.md`. All original failed reports
and captures remain under the isolated worktree's ignored `.runtime` directory.

## Native Gates

1. With `liquid_payload_pose_poc`, capture a client palette before and after the
   documented `SetBlockEntityModelScale`, `SetBlockEntityModelRotation` and
   `SetBlockEntityModelPosOffset` calls. Preserve the exact actor schema and
   typed values. Compare untouched, client-roundtrip and explicit actor mutation
   geometries in native pixels. Successful setters or preserved dicts alone do
   not establish pose baking. Do not guess actor field names.
2. For one or two carrier cells, independently verify Y integer addresses at
   0/63/64/127/128/383/447, X/Z height endpoints and the source corner phases.
   Compare zero-size UV points at 0/63/64/127/128/255 with explicit source values.
3. Open the owner-bound native PNGs. Verify nonflat, nonplanar supplied heights,
   shared triangle edges, all side faces and omitted faces. This is transport
   evidence only; public native height acceptance is independent.
4. Verify liquid atlas sampling at two separated native flipbook times using a
   supported positive and a payload-only negative control. Preserve original
   PNGs and metadata; black/stale frames or failed capture invalidate the gate.
5. Measure native Combine time and native memory for a full batch before calling
   the transport scalable. Sparse serialized lists do not establish sparse
   native allocation. Maximum volume is 1,835,008 indices at six bits and
   29,360,128 at eight bits. If native storage is dense, the eight-bit layout is
   unsuitable without a different packing strategy.

Every report keeps `native_geometry_accepted`, `accuracy_accepted`,
`production_memory_accepted` and `animated_sampling_accepted` false until their
independent native evidence is explicitly reviewed. The host CPU/GLES oracle
does not satisfy these gates. World cleanup, process binding, quiet background
captures, strict layers and the public liquid controls remain owned by root.
