# Liquid Uniform Transport Round 9 Checkpoint

Date: 2026-10-12, 00:59 Shanghai. Owner: `p0-liquid-r9`.
Worktree: `.runtime/r9-liquid`, branch `codex/r9-liquid`, base `c249b23`.
Game: NEMC `3.9.0.401155`, runtime `1.21.120.0`.

This is a transport milestone, not a production liquid fix. Native geometry,
height accuracy, UV orientation, complete animated sampling, public editor/full/
missing controls and production allocation acceptance remain **false**. No
native height formula was inferred. Round-8 raw evidence was read only.

## Feasible Layout

The bounded candidate carries four liquid cells per actor. Static full-UV
proxies reference the four parsed native liquid tiles. Palette X is a slot
in `0..3`, palette Y is primitive kind in `0..6`, and palette Z is zero.
The maximum palette volume is `(1,4,7)`: 28 indices per actor, and at most
16 actors for 64 cells of a single texture family. This is a layout bound,
not a measured production memory or performance claim.

`EXTRA_ACTOR_UNIFORM1` carries four local indices in a four-cubed batch.
Groups 2/3 carry two packed integers per slot: `h00 + 256*h10` and
`h11 + 256*h01`. Each independently supplied height code is 8 bits.
Group 4 carries `(39686, opacity, packed RGB tint, diagnostic mode)`.
Diagnostic packed tint and opacity codes are observed below. Production
blended opacity and tint behavior have not been accepted.

Two top primitives preserve the source quad's `(00,10,11)` and `(00,11,01)`
triangles by collapsing the unused corner. Actual triangle topology and UV
agreement with native water controls still require independent pixels.
Sides currently retain direct native TEXCOORD_0 over the deformed quad;
correct clipped side UVs have not been established.

The earlier low-Y separated-height layout was tested only at code 1 and
X/Z addresses 255. It produced a visible diagnostic plane in live and
roundtrip paths. The ten-code and full endpoint matrix was not completed.
That layout was superseded by the smaller uniform carrier before any
production acceptance. The 448-attachment and large integer-address schemes
were not installed or accepted.

## Reviewed Native Observations

`liquid-uniform-native-r9-v2.json` completed and restored with no cleanup
errors. Live and roundtrip PNGs contain four separated diagnostic planes.
The explicit corner tuples are `(0,255,1,254)`, `(15,16,63,64)`,
`(127,128,254,255)`, `(1,254,16,15)`. They cover all ten supplied codes:
`0,1,15,16,63,64,127,128,254,255`.

The fixed replay ROI is `(500,350,1500,780)`, RGB tolerance is 1, and the
minimum is 100 pixels per declared color. Actual color counts in each live
and roundtrip plane are 1,682 to 1,880. The fourth-height frames separately
observe codes 254/64/255/15. The local-cell diagnostic observes indices
0/5/42/63. The later masked replay uses each path's independent `heights_012`
capture to constrain all three diagnostics to its own four planes. Counts
are 1,880/1,682/1,875/1,872 in every live and roundtrip diagnostic; unrelated
near-black pixels are excluded from the index-zero count.
These observations support only the supplied values in four uniform slots.
They do not identify the native vertex storage format or accept all 256 codes.

Original native-water surface PNGs were opened. Four nonplanar bodies are
visible through the 28-carrier geometry in live and roundtrip attachments.
No native world liquid shape control was compared. The same live attachment
was retained for its later frame. A fixed front-side interior polygon,
eroded by an 11-pixel MinFilter and excluding the crosshair, contains 11,735
pixels. Frames are separated by 2.2545089 seconds. Of those pixels, 9,328
change, 2,249 have maximum-channel delta greater than 12, mean delta is
7.757648, and maximum delta is 53. This supports only observed same-attachment
still-water texture change. No sampling negative control, flow/lava animation,
UV orientation, or complete animated sampling acceptance is claimed.
All captured frames are fresh, nonblank, owner-bound WGC PNGs with the owned
game remaining background. No activation or alternate capture backend ran.

## Preserved Failure And Verification

The first uniform shader used GLSL reserved identifier `packed`. Its native
PNG shows shader compiler errors and no candidate bodies. The replay against
installed headers independently reproduces `Illegal use of reserved word`
under GLES 2. GLES 3 accepted it, illustrating why both profiles are checked.
The failure does not establish that uniform payloads are unsupported.

After renaming that local variable, both GLES 2/3, BLEND and BLEND+FOG compile
and link; all **896** synthetic pixel checks pass. This host oracle cannot
replace the native PNG observations. Three fixture-restoration and nine
existing carrier/install host tests pass. New host tools compile, and manual
source review was performed. MCP host-tool review selected zero files, so no
nonzero structural-review result is claimed.

## Editor Transport Limit

`liquid-uniform-editor-r9-v1.json` completed and restored without cleanup
errors. All native PaperDoll render calls returned true. Reviewed captures
show four gray fallback planes for `RenderBlockGeometryModel`, including
after `SetEntityUIExtraUniforms`; entity-ID attachment paths are blank.
The documented block-geometry render parameters provide `molang_dict`,
but no per-geometry vec4 payload. No shader-uniform behavior is inferred
from the presence of that parameter.

The isolated direct Bedrock-entity diagnostic uses four thin up planes and
an `entity_static` descendant. Its first host GLES replay failed a duplicate
`uv` declaration from redundant includes; that original is preserved. The
corrected direct shader passes 16 synthetic checks under GLES 2/3 and
BLEND/BLEND+FOG. Native v2 used zero-thickness planes; native v3 used
8x1x8 planes. Both reports completed and restored without cleanup errors.
V3 world rendering displays the four diagnostic planes. Its entity-ID UI
paths remain blank. Identifier-based UI rendering displays colors from the
reversed identifier-wide UI payload, but planes are oversized and clipped;
this is not acceptance of four independently addressable editor planes.
The native cow positive control renders but emits a Molang
`query.property does not have an actor` banner; that failure is retained.

Identifier-wide payloads cannot independently feed many groups sharing the
same entity identifier. `GetModelId` and `SetExtraUniformValue` are documented
for skeleton models, with groups 1..4 mapped to `EXTRA_VECTOR1..4`. The isolated
skeleton diagnostic below does not constitute a production adapter.
No production liquid backend was implemented.

Parsed native flipbook entries remain: still water ticks/frame 2; flowing
water `quad:1`, `replicate:2`, no explicit ticks/frame; still lava ticks/frame
16; flowing lava `quad:1`, `replicate:2`, ticks/frame 10. The snapshot geometry
does not simulate fluid. Any later tint must use `Document.biome`; the parent
water provider's unspecified opacity (`None`) must not be replaced with 1.

## Independent Skeleton Payload Observation

The model fixture follows the dictionary-form mesh/skeleton examples parsed
from installed `for_developer/ceshi_rightlegdown` resources, with one static
root and 16 vertices/eight triangles. Its material inherits documented
`entity_for_skeleton`, includes the installed model/extra-vector headers,
and ignores bone animation for this static diagnostic. The host shader
passes 16 GLES 2/3 BLEND/BLEND+FOG synthetic checks. The first host invocation
could not find Playwright's default browser; it was rerun with installed Edge.

Native v1 completed and restored the page, but scale 0.6 clipped and overlapped
planes. That original remains a failed framing observation. V2 uses scale
0.15 and separately framed PaperDolls sharing the same model definition.
`RenderSkeletonModel` returns true, asynchronous `GetModelId` returns distinct
IDs 1/2, and those IDs remain stable during all updates. All
`SetExtraUniformValue` calls return true. Reviewed six native PNGs show:
default-zero on both models; original/reversed independent payloads; left-only
reversal; left-only zero; right-only original with left still zero; and the
original/reversed repeat. No actor, world block or environment was changed.

Fixed masks come from the independent frame's declared colors within each
native control ROI, eroded by a 3-pixel MinFilter. Every plane remains strictly
inside its own control. Left slot masks contain 8,736/8,652/8,652/8,652 pixels;
right masks contain 8,652/8,652/8,652/8,736. Every masked pixel matches the
separately declared expected color in all six frames, RGB tolerance 1 and
minimum 100. Owner/PID/creation identity, fresh WGC frame times and original
PNG hashes pass the replay. This observes only the supplied first three
height codes in each of four slots via `EXTRA_VECTOR2/3`, independently per
native model. Fourth-height decoding, `EXTRA_VECTOR1/4`, liquid deformation,
native sampling, tint/opacity, and editor integration remain unaccepted.

V3 extends the same two-model diagnostic with seven phases. Independent
fourth-height code/index observations use `(height3, slot*85, index*4)` RGB;
the invalid tag becomes magenta only on the selected model. Packed RGB
`0x123456` and `0xABCDEF` decode independently, followed by opacity codes
0.5 and 0.25 encoded into an opaque diagnostic blue channel. All thirteen
captures pass the same separately framed fixed masks, expected RGB tolerance
1 and minimum 100 pixels. Both IDs remain distinct and stable and all native
uniform calls return true. Host GLES 2/3 BLEND/BLEND+FOG also passes all 80
checks against the installed headers. This proves the supplied fourth-height,
local-index, tag, tint and opacity-code transport. It does not prove shader
deformation, native UVs/animation, production blended alpha, or a liquid backend.

V3 completes/restores the diagnostic page and seven-file fixture, then its
owned session is stopped. Game PID 49060 and MCDK PID 27288 are independently
absent. Session `fda5865d2e774c43874664e8a131a376` is stopped/ready=false.
The tested extended vertex/fragment hashes are
`3c22d3e567e93f8589e33251c9a1e11af56cb528fb4afbb676ae255e20378587`
and `e1020c1ef7c93b0362dea76951e6d0a111a856ee97487df4e92ea4dd8b5a9d02`.
The twelve payload/fixture-restoration tests pass after the run, all four
modified diagnostic scripts compile, and `git diff --check` passes.

Both games were recycled. V2 handles grow 61,263 to 63,517 over 12.05 seconds
and private commit grows 2,571,927,552 to 2,582,814,720 bytes. These include
background game/capture activity and have no isolated idle baseline; no
production memory or retention conclusion is made.

## Recovery And Resource Identity

All three owned games were stopped after bounded captures, with independently
queried game/MCDK PIDs absent. Sessions are stopped and ready=false:

| Session | Game PID / MCDK PID |
| --- | --- |
| `182f6acf37c94f4a9c164317ca60155a` | 37956 / 36568 |
| `fbcc4af18c374d77b8c62a6b29dc2a25` | 42060 / 15756 |
| `cb60c3b0fd7a485ca3c743264403ae39` | 29084 / 42688 |

For v2, handles increase from 64,713 before the fixture to 70,182 after
cleanup over 27.73 seconds. Private commit increases from 2,602,369,024 to
2,762,498,048 bytes. Working set decreases from 811,200,512 to 423,596,032.
V1 showed similar handle growth before any large carrier palette. These
samples include background game activity and captures; they are not isolated
Combine costs, evidence of bounded retention, or production scalability.
Games were recycled instead of permitting indefinite growth.

The separated overlay restored all 84 installed file hashes. Both uniform
versions restored their 12 hashes and original bytes, removing only generated
files. Git status shows no remaining BP/RP fixture changes.

The editor v1 12-file overlay and direct v2/v3 18-file overlays were restored.
The additional owned sessions are stopped with ready=false and their game /
MCDK PIDs independently absent:

| Session | Game PID / MCDK PID |
| --- | --- |
| `9bce224f778f416ea22befc0ac16bbd4` | 43408 / 47892 |
| `e305f44445524ba0a553a6c1f79b664e` | 43856 / 30540 |
| `9746a4f02fee43d4b9f0015fc056f4db` | 21080 / 11300 |
| `d4828ed7d84a4584b8a1504b64b285e1` | 32224 / 6936 |
| `cdd6d478042841a586ef9056a765c921` | 10904 / 46048 |

The skeleton diagnostic's seven-file overlay restored all original/absence
hashes after both games exited. Both loaded the independently verified final
focus guard DLL; all captures remained owner-bound background WGC frames.

Session `3992368c8bfc4109aaa5cdcb99366baa` failed before ready with
`Focus guard module snapshot failed`. Its MCDK PID 14508 exited, no matching
game remained, and its 18-file overlay was restored. This does not establish
a native shader failure.

WGC executable SHA-256 is
`cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8`.
Loaded focus guard is
`c22fa0cd0bdbfb7d9218d59573b61619111f9bd180562c9bd51c69276c11c178`.
The tested v2 vertex and fragment hashes are
`4895d33b947dfcc3ea7d40f949ac49b5f7df5265b64e39621060da28ce8ddabe`
and `312da16b13786dff91742380fe719b4a057c77b389fd94e00109787be59ee463`.

## Raw Artifacts

All originals remain under this worktree's ignored `.runtime` directory.
Reports contain original PNG paths/hashes and per-frame metadata.

| Raw File | SHA-256 |
| --- | --- |
| `liquid-separated-y001-xz255-r9-v1.json` | `a5268dec4029bf04aa620c4bebcac906eb33691fd75f9d0acd247a796028858f` |
| `liquid-uniform-native-r9-v1.json` | `befbfd6f63ee6e19bd85f4e3e85d74bd5aa7fc2b06d6eb305da4c6faf943fec4` |
| `liquid-uniform-native-r9-v2.json` | `920d9d7337a8dc22214b518dd6b0f07cc296de425a527ca471890af8087bc93e` |
| `liquid-uniform-pixels-r9-v2.json` | `a37d22d3df6fde5d85274611c6ab6003a48bde4bed01dc29c604ad737e744c6d` |
| `liquid-uniform-gles-r9-v1-replay.json` | `fe8ae1ee57587033611eb319dc7e886a13f94e70a8f8e619a1abffd65af9381f` |
| `liquid-uniform-gles-r9-v2.json` | `9b71dccdeaa782697843bc1f02f91163ff188f4758d23910513faa7cd8b5227d` |
| `liquid-uniform-r9-v2-install/contract.json` | `de819a9fd6db07d8469ef03aac01d6dac20abbc725532f1e72d70f75c48537c5` |
| `liquid-uniform-install-r9-v2/installation.json` | `37b224f3b925f26d7cd5102f21a13b8bf291822cb44ad693225b07ac1caac328` |
| `liquid-uniform-editor-r9-v1.json` | `541baaffa7aa9783255d0e54d4a9b0075f90ed08b834b6cec3ca596fc94c9378` |
| `liquid-uniform-direct-gles-r9-v1.json` | `f690019be11ce0cf75919f410276a6ff423c757dd7bb54a99257a9314421ce1b` |
| `liquid-uniform-direct-gles-r9-v2.json` | `fd9feb038b38dc13c7e9753098994d85f0051c1da744a57b6d3cf41e7462723f` |
| `liquid-uniform-direct-editor-r9-v2.json` | `626023eea437121389b07ea0e8346301ce8ffc0492c867d540b462385400028c` |
| `liquid-uniform-direct-editor-r9-v3.json` | `4c341b6212d515ee36ad8abbd7697875d39f687d285550e1d742ad6dcbb0e167` |
| `liquid-uniform-pixels-r9-v3-masked.json` | `854e598aefbd2bbfc36cba681c48dc0fafbe20164df9fd4f4c4d52f1edf10f5f` |
| `liquid-skeleton-gles-r9-v1.json` | `39a389613f618803191f0dfd411f73c543c66eddd1731b9d16975b1e9b13ed13` |
| `liquid-skeleton-editor-r9-v1.json` | `db62f60a8b65f49288c01284d2d97fe6ab2f9d847846ca3145c6681a6ad0818c` |
| `liquid-skeleton-editor-r9-v2.json` | `376c0e65b0a06f1dbfd6dce524d20652fc5e973d50615d93235abd46f2a28f30` |
| `liquid-skeleton-pixels-r9-v2.json` | `3edbf41a81dee9cd047eb4a750012d50f01a287af74e76982db605f89b77394c` |
| `liquid-skeleton-gles-r9-v3.json` | `21ff11105ac399e35650bb9461f012844d730c294fa0896e15d70b9dae3e9e47` |
| `liquid-skeleton-editor-r9-v3.json` | `84855b4ea4ea0b1fde73d77cd680dab12ce11de41bdcf4df26f953f0be5fd636` |
| `liquid-skeleton-pixels-r9-v3.json` | `ae2b104f689f4220d7d5ecd278790e9a46d38b03d35632c9472fa35564dca052` |

## Next Acceptance Gates

1. Independently review source corner phases, every primitive kind and native
   top/side UV orientation, including nonplanar shared edges and omitted faces.
2. Analyze same-attachment still/flow water/lava animation with fixed interior
   masks and a sampling negative control.
3. Measure cold/warm 1/8/64-cell batches, cached geometry names, actor creation,
   attachment removal, repeated edits, RSS, private commit and handles against
   an idle baseline. Stop or recycle on sustained unbounded growth.
4. Obtain versioned native heights/neighbor-face observations independently
   from the supplied-height decoder; never substitute a Java liquid formula.
5. Integrate a bounded lifecycle with independent editor/full/missing public
   controls and waterlogged foreground bodies before accepting production.
