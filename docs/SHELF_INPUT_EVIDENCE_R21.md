# Shelf Skeleton and native terrain inputs, R21

These packages preserve two completed diagnostic acquisitions. They do not
qualify the current shelf projection appearance, lighting, or editor rendering.
The original reports, frozen sources, and raw images are retained without
relabeling their failed or unqualified fields.

## Portable Replay

Requires Python 3 and Pillow. Run from the repository root:

```powershell
python -B -X utf8 tools/pack_shelf_input_evidence_r21.py verify --package docs/evidence/shelf-skeleton-r21-v1
python -B -X utf8 tools/pack_shelf_input_evidence_r21.py verify --package docs/evidence/shelf-terrain-inputs-r21-v4
```

Each package also contains the same verifier at
`host/tools/pack_shelf_input_evidence_r21.py`; run it with `--package .` from the
package directory. Replay needs neither a game installation nor a local clone.
It checks the exact payload set and hashes, frozen host and overlay bindings,
original acquisition completion/restoration, independent pixels, and the stopped
session against exact process exit observations. The source manifests contain
historical local paths as provenance; replay does not dereference those paths.
Shader compilation is recorded in the v4 receipt, not rerun by portable replay.

## Skeleton V1: 24 Raw Images

Two selection groups contain native/empty/selector, and two detail groups contain
native/empty/selector/document normal/world normal/intensity/TILE/unlit/candidate.
Every original raw image was opened by the shelf agent. Both actual selector
masks contain 38,800 pixels, bounds `[896,437,1099,636]`.

South front normals read `(127,127,255)` and west front normals `(0,127,127)`;
top normals remain `(127,255,127)`. Therefore normal delivery and the tested
90-degree world rotation work. Boundary pixels are postprocessing mixtures,
not proof of diagonal mesh normals. Actor TILE reads white, while the candidate
uses the entity fancy-axis formula. Candidate RGB means are about 22 percent
brighter than native in both directions. This is descriptive evidence of a
remaining mismatch, not an accepted correction coefficient.

The original v1 contract incorrectly claimed existing owners enforce uniform
scale. The world probe actually supplies `(16,16,16)` and therefore satisfies
uniform scale for this acquisition; see `SHELF_SKELETON_CANDIDATE_R21.md` for the
existing amendment. The frozen contract itself remains unchanged.

## Terrain V4: Two Raw Images

This frozen successor changes only the selected `terrain_base` fragment from v3.
Native vertex, alpha/discard/BYPASS behavior and material registry remain intact.
Eight screen stripes read actual COLOR, lightmap, flags, and native final RGB,
each adjacent to a distinct marker. Both original images were opened by the
shelf agent and root. The independent sky-only body ROI excludes the striped
terrain background; the original unsegmented report stays unqualified.

Actual flags are `(51,0,51)`: FANCY, FOG, TEXEL_AA, ATLAS_TEXTURE. No ALWAYS_LIT
is set. Sampled texture1 lightmap is neutral `(237,237,237)`. Actual interpolated
COLOR is white on upward faces and varies vertically across the front, from
approximately 203 near its top to 164 near its bottom in this fixture. This does
not establish a height formula, AO origin, or transferable per-face coefficient.
The native vertex shader simply forwards engine-provided COLOR and UV1; the
fragment multiplies texture0 by texture1 and COLOR before fog. The native
meshing/AO generation is not present in those shader files.

## Lifecycle And Limits

Both acquisitions completed, restored their state, and retained unchanged frozen
resources. One normal stop per session returned `Game has not closed`; exact
observers then recorded Minecraft exit `0xC0000409` and MCDK exit zero. Sessions
were subsequently finalized as stopped without force. These are not clean game
exit claims. Saved raw receipts are distinguished from transcript-attested CLI
outcomes in each `lifecycle/facts.json`.

The packages omit full clones and source tar archives. Local session tokens are
redacted, with the original session SHA256 and redaction provenance retained.
They contain 26 new raw diagnostic images plus the required small frozen
resource/host and native source closure. The v4 package also retains its two v3
route prerequisite images, separately labeled under `route-evidence`.

Remaining work is a native-input-grounded lighting candidate and fresh native
comparison. Existing data does not authorize fitting a scalar or a screen-height
curve, extending a south fixture to other states, or claiming product closure.
