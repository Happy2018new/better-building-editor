# Liquid Payload Round 8 Checkpoint

Date: 2026-10-11. Owner: `p0-liquid-r8`. Base: `dev` at `67dfc74`.
Game: NEMC `3.9.0.401155`; runtime `1.21.120.0`.

This is an isolated diagnostic checkpoint. Native geometry, native input
format, pose transport, height accuracy, complete animated sampling,
production memory and public controls acceptance remain **false**. There is
no production liquid backend change or inferred native height formula.

## Reviewed Results

| Discriminator | Actual reviewed native result |
| --- | --- |
| Existing white shulker geometry under the overridden blend descendants | World source, live Combine and deserialized Combine visibly render |
| Same registration and known shulker texture, changed only to an up-only `[8,1,8]` cube with `[16,16]` UV size | World, live and roundtrip visibly render |
| The same carrier under the wrapped shader's production fallback | World, live and roundtrip visibly render |
| The same carrier and shader, changed only to `[0,0]` UV size | World, live and roundtrip are invisible |
| Direct `minecraft:shulker` block `client_entity` registration | Invisible |
| Copied original shulker client entity | Invisible; standalone also reports original-only Molang variables absent |
| Copied shulker without animations/scripts, using a local opaque texture | Invisible |
| Up plane referencing native `still_water_grey` directly | Native gray water artwork visibly renders in world/live/roundtrip |
| Up plane referencing native `still_lava` directly | Native orange lava artwork visibly renders in world/live/roundtrip |

These native PNGs were opened. The point-UV failure applies to this tested
carrier and registration, not every possible geometry API. The static path
is the supported next diagnostic route; the client-entity pose path remains
unaccepted. API returns and palette roundtrip equality are recorded separately
from visual observations.

## Fractional Height Failure

The diagnostic top Y in model units is `code/16`; the intended block-coordinate
fraction is `code/256`. The tagged shader (`39684`) displays
`fract(POSITION.xyz + .5)` as RGB while retaining native `TEXCOORD_0`.

| Carrier Y address | Code | Reviewed green-channel observation |
| --- | --- | --- |
| 0 | 0 | Dominant 0 |
| 0 | 1 | Dominant 1 |
| 0 | 255 | Dominant 254 |
| 447 | 1 | Dominant 255, 1,916 diagnostic pixels |
| 447 | 255 | Patchy 0 (882 pixels) and 255 (852 pixels) |

At address 447 the palette is explicitly constructed from the live single
cell: volume `(1,1,448)`, common index `[447]`; it is not a captured native
447-cell world palette. Attachment offset Y=-447 recenters the diagnostic
for the same camera. Both high-address PNGs were opened. The green-channel
counts use the live-versus-empty difference inside `(920,450,1080,640)`, with
maximum RGB difference greater than 40. They are diagnostic counts, not an
exact reconstruction of the engine vertex format.

The endpoint discriminator fails. Eight-bit fractional POSITION.Y cannot be
accepted across the current 0..447 carrier address range. The native input
storage format and the source of the loss remain unidentified. Addresses
63/64, 127/128 and 383 were not run before shutdown. An attachment transform
or later shader arithmetic cannot establish that lost input bits survived.

## Same-Attachment Water Animation

`liquid-native-tile-water-animation-r8-v4` retains the same attached live
geometry for both `live` and `live_later`. The script waits 1.1 seconds after
the first completed WGC capture; actual fresh frame QPC separation is
**2.1878474 seconds**. Both captures are nonblank 1994x1105 frames from the
same owner, game identity and HWND. The requested-frame freshness checks pass.

Both original PNGs were opened and the water pattern changes inside the
stationary plane. An interior polygon `[(910,562),(980,516),(1082,544),
(1026,596)]`, eroded by an 11-pixel minimum filter and excluding crosshair
rectangle `(973,528,1014,568)`, contains 3,365 pixels. Of these, 2,626 change,
380 have maximum RGB channel delta greater than 12, mean maximum channel
delta is 5.4472511144 and maximum is 38. This excludes the crosshair, borders
and unrelated animated scenery; a whole-image difference is not the evidence.

This supports the narrow observation that the original still-water tile
animates through this static carrier and the production fallback shader.
It does not accept the payload decoder, lava/flowing-water animation, UV
orientation, tint, opacity, lighting or full liquid geometry. The report's
`animated_sampling_accepted` remains false. Still/flow tile names and flipbook
entries come from parsed installed resources; no atlas rectangles are guessed.

The live PNG SHA-256 is
`eb595fa89cd0df5af036ed616cdb1514ccdb02af6e983912de70335c9e92e678`;
the later PNG is
`60308278154e9e552728da9f71b5715604a92c503b48cabca5af584748bed36a`.
Capture helper SHA-256 is
`cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8`.
The initial preflight failed because the root `.runtime/native_wgc` helper
was absent. That original failure was retained as
`liquid-visibility-shulker-r8-preflight-v1.capture.json`, SHA-256
`8aefcbecdbf1a02ddbdc8210392b77d09820cc97b39850eff44a45d39bf5d58a`.
Subsequent captures used the already validated helper from the preserved
`p0-blueprint-qa-r3` runtime. No alternate capture backend was substituted.

## Recovery And Source Identity

The final session `fedc053e50664e109129e638272fa699` used MCP 58754, game PID
4444 / identity `134361982799881539`, and MCDK PID 49972 / identity
`134361982797819585`. Parent observations reported handles increasing from
about 196k to 474k and 613,846 at 22:05. Cause is unassigned; this is not a
measured native Combine allocation cost or evidence of production scalability.

The final probe reports `completed=true`, `restored=true`, environment cleanup
true and no cleanup errors. At 22:05 Shanghai, owner-bound `instances.py stop`
returned normally. The registry is `state=stopped`, `ready=false`; an independent
process query found neither recorded PID. No further native scenario started.
All 15 listed scenario reports are completed and restored with zero cleanup errors.

After process exit, the fixture restore verified all 28 installed hashes and
restored original bytes or removed only generated fixture files. Git status
then showed no BP/RP modifications. Earlier owned sessions
`ab4b7bb646224cc9923889dec0aca26e`, `9f46eb66e36745b29cff693161d474aa` and
`2742e09016d04ea3a451cd260d737e52` had already been stopped.

Frozen overlay: `.runtime/liquid-native-input-r8-v4`; original-byte backup:
`.runtime/liquid-native-input-install-r8-v4`. Contract SHA-256 is
`582eb13afb177ebf8a3cb0365f115b3699fc6547afad96fcfbff6e429f02cee2`;
installation report is
`b051a09cc8b472a32be6a6e218f4ed2c413175d7eeae759b8a377b5a32bdaadd`.
Native vertex shader is
`98b27283be20eb2cc59e6c1eb05dd65a880c1cbe3452ee6821dc044987010053`;
fragment is
`a137bf2e51bdfc40979db6eb451bf729cda81c980eeea9cdea5a01c7a9a7e163`.

A source-only recenter attempt was never installed. It has been removed from
the generator, so checked-in source reproduces the tested v4 shader. A fresh
offline generation reproduces all 28 resource hashes exactly. Temporary
resources remain outside Git. The checked-in host tools compile; 12 host tests
pass, including restoration rejection on a changed file or a different project.
No zero-file MCP review is claimed as a structural review.

## Next Layout Candidate

Separate face/cell addressing from the height channel. For the next bounded
diagnostic, a carrier is placed at palette `(left_code,0,right_code)`; its
static proxy still supplies top Y=`third_code/16` model units and full valid
native-tile UV. Decode the third code from the low Y fractional input. Pass
primitive kind in an explicit entity uniform group and logical cell position
in the geometry attachment offset. A four-cubed batch could use seven kind
groups with at most 448 attachments. Reuse geometry names for identical
height triples and texture family only after verifying those identities.

This keeps the fractional Y channel at carrier address 0. It is a candidate,
not a validated solution: X/Z endpoint and corner-phase retention also need
native coverage. Maximum per-mesh palette envelope is `(256,256,1)` or
65,536 indices instead of `(256,256,448)` or 29,360,128. Up to 448 separate
meshes may still have that same 29m aggregate envelope, additional draw/submit
overhead and cache lifetime costs. No speed or memory improvement follows from
the per-mesh number alone.

Required gates before integration:

1. Prove all ten supplied third-height codes at low Y with X/Z endpoints 0/255
   and actual source corner phases. Review live and roundtrip native pixels.
2. Prove attachment offsets and uniform kind groups place two cells and all
   primitive kinds correctly without reintroducing a high-Y input address.
3. Review a nonplanar four-corner top, shared triangle edges, each side and
   omitted faces. Direct `TEXCOORD_0` on a deformed quad does not automatically
   establish correct triangle UVs; compare orientation and artwork to controls.
4. Demonstrate same-attachment native tile animation through the actual decoder,
   including still/flow water and lava, with an appropriate sampling negative.
5. Measure cold/warm Combine and attach time, RSS, handles and removal for
   bounded 1/8/64-cell batches. Stop on unbounded growth and preserve recovery
   evidence. Establish cache limits and repeated-edit cleanup before scaling.
6. Keep native height/corner/face semantics and public controls as independent
   gates backed by reviewed native observations. No Java formula substitution.

No reliable basic-water or complete-liquid ETA can be committed from this
checkpoint. The earlier conditional 2-4h basic-water / 6-10h full-acceptance
estimates lost their transport premise when high-address preservation failed.

## Raw Evidence

Original reports, PNGs, capture metadata and frozen overlays remain in the
round-8 liquid worktree at repository-root `.runtime/r8-liquid/.runtime`.
The root owner will preserve this path as an evidence-only archive junction during
worktree archival. Do not launch or modify the archived worktree.

| Raw Report | SHA-256 |
| --- | --- |
| `liquid-visibility-blend-shulker-r8-v1.json` | `a56028ee587f5f5bcd5dba0da8ec3ba8c30a6ff45365da1ca2f48ae9c0db2597` |
| `liquid-visibility-carrier-r8-v2.json` | `a1ffdbb38ac10aa532eb7f3b0cbb4325a24d5f2cd7643d85ad8d70400433d46c` |
| `liquid-visibility-shader-carrier-r8-v3.json` | `d0613248771a4c009adb0ae7b266ca917ae63177cea19f2e979240d196f31e4a` |
| `liquid-visibility-shader-point-r8-v3.json` | `cd10b03e4f01e135d3641fad70ef5dae02e75cef54d92d040a65cb007342c023` |
| `liquid-visibility-direct-shulker-r8-v1.json` | `2f7b0e81420c2bbbee72dca5acedf401744a5044847b56c38c68313575486d36` |
| `liquid-visibility-copied-shulker-r8-v1.json` | `7ddd1fac1ac12d7e608ab8c27f36eacf80126e74826f9cc16c21d04d6d4f4bb9` |
| `liquid-visibility-plain-shulker-r8-v2.json` | `780b8542be9c3c24f7bf0039facbc84bb351ba53fcd666c9f9915b8d4b891009` |
| `liquid-native-input-y000-r8-v4.json` | `39455a1b12a15539250b72bba0cba6330bddf68d529be81055e58df98b660254` |
| `liquid-native-input-y001-r8-v4.json` | `d9eac0f0de0e674df9484a7804b2f3d2fe0c887611805a6216330b0e03a7080e` |
| `liquid-native-input-y255-r8-v4.json` | `fb67673627daa220dda563151ea70162a9b2442e2112f540024b5981e79b1463` |
| `liquid-native-input-y001-address447-r8-v4.json` | `d15224cbec9e5d46559dbf69540f0ca2422b2a382de425558c0621ad6622154e` |
| `liquid-native-input-y255-address447-r8-v4.json` | `d09ade35c9d069b68dfec7d293ebda506af256f71e4288d3b5896999f6fc8833` |
| `liquid-native-tile-water-r8-v4.json` | `ed0d64df60e32658b039aa82028b66c889aff65a5c2770052501317da7172d6d` |
| `liquid-native-tile-lava-r8-v4.json` | `c1103c76ab70886cf43d36e121151ed5751125fccc7f70eee1df9f3a0e0e4390` |
| `liquid-native-tile-water-animation-r8-v4.json` | `cbb74b24d0b0ff1bd72c5e255ddcb5adbd73006e06a6e2780ddb2270b82910d9` |
