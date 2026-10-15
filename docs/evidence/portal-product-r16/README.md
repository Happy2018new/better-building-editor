# End Portal Surface Qualification

Updated 2026-10-15 after the independent book owner and water bounding-box
extension changed shared infrastructure. New ordinary default-path runs contain
31 editor and 28 world captures, completed with restoration and unchanged
sources. All 11 new review sheets were opened; animation, clipping, visibility,
occupancy restoration and opacity remain correct. The editor run also supplies
the default-editor evidence. Full raw captures remain in
`.runtime/portal-owner-r18-{editor,world}-v1`; reports and sheets below bind this
revision. The round-16 and round-17 source folders below are historical.

Engine: NEMC `3.10.0.420447`, MCBE `1.21.130`. Public gallery:
`test.dynamic.portals`. Accepted on 2026-10-14, round 16.

The product now enables finite End portal planes and End gateway cube surfaces
for this exact engine bundle. Nether portals retain the native renderer. The
custom shader uses the installed native `end_sky` and `end_portal_colors`
artwork in three moving layers. This is a declared project style; exact native
ray-plane appearance is not claimed. No source block state or NBT is replaced.

| Evidence | Captures | Checked Behavior |
| --- | ---: | --- |
| `editor` | 31 | Opposing cameras, top view, moving pixels, zoom 1/2/3, cutaway 9 to 0, layer hide/restore, rotation, mirror, public gallery |
| `world` | 28 | Full and missing projection for both families, moving pixels, one occupied cell and restoration, opacity 0/0.45/1 |
| `default_editor` | 31 | Same editor matrix after cold start, with no candidate profile injection |

All 17 contact sheets were opened and their actual pixels reviewed before
admission. Color and temporal-difference counts are additional diagnostics,
not a replacement for pixel review. World crop counts can include foliage.
The final starfield is visible on the dark surface, its pixels move, hidden
cells disappear, surviving source neighbors keep their original face context,
and opacity zero removes the entire companion. Source hashes stayed frozen
during each run; occupancy writes and camera/UI changes were restored.

`qualification.json` binds the captured renderer, resource contract, reports,
review sheets and raw screenshot fingerprints. The two qualification metadata
constants in `portal_profile.py` are normalized out of the implementation
fingerprint to avoid a circular digest. Their isolated admission value differs
from the final product value; all renderer bytes are identical.

The repository keeps reports, original capture receipts, hashed review sheets
and qualification metadata. The 90 full-resolution screenshots remain locally
in ignored `.runtime/archive/portal-product-r16`, alongside the retained original
probe folders. The committed evidence is about 12 MB. A fresh clone can inspect
the contact sheets and source provenance but cannot independently replay raw
pixel analysis without those local screenshots. Capture hashes and acceptance
results are unchanged by this archival step.

The shared four-cell transport, preview owner, world companion, cancellation,
occupancy and cleanup remain the existing liquid rendering infrastructure.
Portal-specific modules own only their supported shapes and appearance.
The source palette and block actors retain their complete logical data.

Offline GLSL 100/300 compilation recorded 18 stage/flag combinations. Four
GLSL 100 skinned vertex variants hit the inherited native `mat3x4` header
failure, which also occurs for the native baseline. They are explicitly
recorded as unsupported inherited variants, not successful compilation.
All remaining variants passed; shader float/varying precision is explicit.

The earlier local candidates `.runtime/portal-product-r16-editor-v1` and
`world-v1` were too dark; `editor-v2` was too bright. They are diagnostics and
are excluded from this qualification. Accepted sources are `editor-v3`,
`world-v2` and `default-editor-v1`.

End gateway cooldown and transient activation beam remain pending. This
qualification does not remove that work from scope. Teleportation and particles
are outside visual rendering adaptation. Future engine versions do not inherit
this qualification: regenerate the versioned resource contract and repeat the
public gallery editor/world matrix before admitting the new bundle.
