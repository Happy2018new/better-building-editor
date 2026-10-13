# Flowing-water top candidate R12

The diagnostic opt-in `candidate_profile(frozen=True, flowing_top=True)` adds
flowing-water top artwork, a distinct UV template and an eight-bit direction
decoder. `candidate_profile()` and `candidate_profile(frozen=True)` retain their
existing output. All native direction, top UV and production acceptance flags
remain false. This work performs no game runs and changes no liquid propagation.

The installed NEMC 3.9.0.401155 `blocks.json`, `terrain_texture.json` and
`flipbook_textures.json` are bound by SHA256 in
`tools/data/native_liquid_flow_top_candidate_nemc_3.9.0.401155.json`. They establish
the original material keys and atlas/flipbook metadata. They do not establish
the fluid renderer's direction algorithm or top UV mapping. MCP searches of
`assets flowing_water_grey`, `api GetLiquidFlow`, `api 流动`, and `all flow direction`
provided no authoritative native direction implementation. The candidate JSON
records this limit instead of inferring direction from `quad:1` or `replicate:2`.

Corner order is NW, NE, SE, SW in logical document x/z axes. The independent
candidate computes a downhill vector
`(NW+SW-NE-SE, NW+NE-SW-SE)`. It does not alter corner height, blocked/above,
occlusion, layer or alias rules. Direction code is nearest
`atan2(z,x)/(2*pi)*256`, modulo 256, so 0, 64, 128 and 192 identify +x, +z, -x and
-z. Angular quantization error is at most 0.703125 degrees. A zero vector
(including flat and saddle corners) is an unknown native direction. This
candidate keeps the still top in that case; equal heights, falling states,
same-fluid-above, waterlogging and native velocity can require a different rule.

The UV template `candidate_water_top_center_turn256_v1` is separate from
`native_water_side_nw_bottom_edges_v1`. For angle theta and centered logical
coordinate `(x,z)=(u-.5,v-.5)`, its full-frame source coordinate is
`(.5,.5)+.5*(cos(theta)*x+sin(theta)*z,-sin(theta)*x+cos(theta)*z)`.
This rotates a half-size square around the full frame center and remains inside
the frame for every angle. It is an explicit sampling hypothesis, including
pixel edges and filter behavior. The side NW quadrant and bottom-anchored crop
retain their existing implementation.

A dedicated mesh carries four top faces only (16 vertices, eight triangles).
Separate UI/world vertex shaders decode all 256 codes and reject non-top faces
and codes outside eight bits. Separate animated/frozen model names and fragment
shaders share the original native water strip. Existing opacity `.45`, explicit
flow cadence 1 tick with blending, material blend/culling states and native
coordinate paths are preserved. Original still/side independent asset bytes
are identical to the previous resource contract. The actor-material adaptation
fingerprint changes only because four top material entries were appended; it
does not add actor visual qualification.

The flow source binds the registry version/palette, existing height-candidate
fingerprint and three installed metadata sources. The resource contract binds
the flow source's exact bytes, canonical candidate hash, direction implementation
hash and generator hash.
`check_version_bundle.py` validates these plus the generated flow and deployment
tables, separate top capabilities and installed resource bindings. Any version,
metadata, rule, UV or generator change requires regeneration and native
qualification for the changed bundle. Qualification fingerprints remain empty.

Regeneration uses the selected installation, preserving the existing diagnostic
opacity and animation arguments:

```powershell
python -X utf8 tools/generate_liquid_flow_top.py --native-data <game-data>
python -X utf8 tools/generate_liquid_skeleton_resources.py --output <fresh-bundle> --native-data <game-data> --world-bone --preview-depth --diagnostic-water-opacity 0.45 --flow-ticks-per-frame 1 --flowing-top
```

Merge the generated model/material entries and copy independent outputs into
the project. Copy the bundle contract to `tools/data/liquid_deployment_r12_contract.json`,
refresh only the changed adaptation fingerprint in the native actor-material
snapshot, then emit the closed deployment table:

```powershell
python -X utf8 tools/generate_liquid_deployment.py --contract <fresh-bundle>/contract.json --native-data <game-data>
python -X utf8 tools/generate_liquid_flow_top.py --check --native-data <game-data>
python -X utf8 tools/check_version_bundle.py --provenance-only
```

Offline verification covers all 256 angle codes, four payload slots, axial and
diagonal directions, rotation/mirror equivalence, invalid data, independent top
and side grouping, unchanged complete documents/actors, selection with complete
neighbor context, generated version fingerprints and source drift rejection.
The host GLES replay uses the installed include files and original water strip
plus an asymmetric coordinate texture so native artwork symmetry cannot hide a
wrong decoder. Its report is
`tools/data/liquid_flow_top_host_gles_r12.json`. Host pixel checks validate this
candidate implementation; they cannot establish native flow direction,
filtering, device behavior or production appearance.

Native acceptance must freeze both water aliases, every saved depth state,
both logical layers and complete neighbor/above/below inputs. Capture native
top-only pixels with marked world axes for axial, diagonal and intermediate
slopes, flat/saddle/falling surfaces, blocked/air boundaries and waterlogged
cells. Independently compare top material choice, angle offset/handedness,
source extent, filtering and frame zero before animation/alpha controls.
Re-run separate UI/world views against the same source snapshot and retain
version, source, height and resource hashes. Only those observations can
replace this hypothesis with a qualified versioned native rule.
