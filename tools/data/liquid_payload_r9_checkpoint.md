# Liquid Uniform Transport Round 9 Checkpoint

Date: 2026-10-11, 23:29 Shanghai. Owner: `p0-liquid-r9`.
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
Tint/opacity and general 24-bit tint transport have not been accepted.

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
0/5/42/63. One or two unrelated near-black pixels are included in the
index-zero global ROI; its 1,880-pixel plane was independently reviewed.
These observations support only the supplied values in four uniform slots.
They do not identify the native vertex storage format or accept all 256 codes.

Original native-water surface PNGs were opened. Four nonplanar bodies are
visible through the 28-carrier geometry in live and roundtrip attachments.
No native world liquid shape control was compared. The same live attachment
was retained for its later frame; animation ROI analysis remains pending.
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
