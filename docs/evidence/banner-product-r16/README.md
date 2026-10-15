# Banner Product Acceptance, Round 16

Updated 2026-10-15 after the enchanting-table body adapter changed the shared
palette preparation source. The 26 editor, 16 world and 3 opacity captures were
rerun on the ordinary default profile and visually reviewed. The editor run
also supplies the default-path evidence; it does not inject a candidate.
Full-resolution captures for this revision remain in
`.runtime/banner-table-r18-{editor,world,opacity}-v1`. Reports and contact sheets
below now bind this revision. The earlier archive described below is historical.

The default editor admits standing and wall banners only on NEMC
`3.10.0.420447`. It uses the measured banner-only preview depth mapping
(`450.0` origin and `0.64` scale), authentic item-placed actor payloads, and
the original native pattern renderer. Generic block entities retain their
existing renderer.

The public `test.entities.banners` gallery contains three standing and three
wall banners with zero, three and six captured patterns. The saved cells and
typed NBT remain unchanged by preview preparation and rendering.

| Evidence | Captures | Observed Behavior |
| --- | ---: | --- |
| `editor/report.json` | 26 | Identity, Y rotations, X/Z mirrors, opposing cameras, three zoom levels, cutaway, layer visibility and all edit-layer modes |
| `world/report.json` | 16 | Full and missing projection, identity/rotation/mirrors, two occupied banner cells hidden and restored |
| `opacity/report.json` | 3 | Actual projection slider path: opaque at 1, translucent at 0.45, completely hidden at 0 |
| `default_editor/report.json` | 26 | Cold-start default Session route, without injecting a candidate native render profile |

All captures used the owned background instance, reliable WGC capture and
no agent window activation. Every review sheet was opened and examined.
The reports record completion, cleanup, unchanged implementation bytes and
the exact capture hashes. `qualification.json` binds these reports and the
versioned shader/resource contract.

The repository keeps the reports, original capture receipts, hashed contact
sheets and qualification manifest. The 71 full-resolution screenshots remain
locally in the ignored `.runtime/archive/banner-product-r16` folder, and their
original probe folders also remain local. This reduces committed evidence to
about 12 MB. A fresh clone can inspect the committed review sheets and source
provenance, but cannot independently replay the raw-pixel analysis without
the local screenshots. No screenshot fingerprint or acceptance result changed.

The zero-opacity check first used `Session.set`, which updates saved state
without the slider's shader publication. That discarded diagnostic lives in
the ignored `.runtime/banner-product-r16-opacity-v1` directory. Accepted
opacity evidence uses `Session.range_value`, the same path as the UI.

Gate metadata is excluded from the implementation digest because the gate
contains the qualification fingerprint. Candidate admission was enabled only
inside the disposable project before the default cold-start test. The final
repository gate refers to the reviewed product manifest. Renderer bytes were
identical between candidate and default acceptance.

GLSL 100/300 supported variants compiled offline. The GLSL 100 skinned variant
inherits the installed native banner header's unsupported `mat3x4` construct;
the native baseline fails the same way and is recorded separately in the local
compile receipt. Exact parity for every arbitrary pattern sequence or future
engine version is not inferred from these six samples.
