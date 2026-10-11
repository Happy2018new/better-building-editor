# Built-In Plant Capability, Round 9

This extends the 2026-10-11 23:23 checkpoint in
`docs/NATIVE_PLANT_DIAGNOSTICS_R9.md`. No additional native plant rendering
candidate is accepted. These probes diagnose documented custom-block
capabilities; they do not establish a vanilla plant hash, mesh pivot or
snowlogged rendering contract.

## Built-In Geometry Probe

Owned session `544f997f43a64d29925c9002a3821fc5` ran NEMC 3.9.0.401155,
runtime 1.21.120.0, in `.runtime/r9-snow`, branch `codex/r9-snow`.
Game PID 32948 had identity `134362059796709401`; MCDK PID was 43112.
All evidence is retained under:

`C:/Users/Happy2018new/.pyreact-debug/instances/544f997f43a64d29925c9002a3821fc5/artifacts/`

Five isolated format-1.21.100 definitions tested
`minecraft:geometry.full_block`, `minecraft:geometry.cross`, and the exact
documented `minecraft:random_offset` example. The example uses X/Z ranges
`[-8,8]` with zero steps and Y `[-2,0]` with three steps. These are capability
parameters, not a fitted native offset range. Three definitions were placed
under `behavior_pack/blocks`, and full/cross copies under
`behavior_pack/netease_blocks`. Their IDs are diagnostic IDs only.

`builtin-block-basic-info-r9-v1.json` confirms all five names registered.
The custom cross render layer is 10; native crimson roots reports 13.
Registration does not prove mesh or native-plant equivalence.

The native world displays the built-in cross and the modern random-offset
example. Original native and mesh PNGs were opened. Both `direct_world` and
`roundtrip` mesh paths produce a complete dirt cube for custom cross blocks.
The full-block positive control preserves a cube shape but also has a dirt
texture fallback. Built-in world rendering therefore does not supply a
usable plant mesh through these paths.

The dry probe uses original cell `(-47,117,-70)` and original public/right
camera offsets. It never tests snow heights. Its whole-crop difference
comparison includes support/background differences; a passing
`native_roots_comparison` is not an independent exposed-plant verdict.
Editor, full and missing rendering acceptance remain separate and open.

The first attempt is incomplete and restored: it incorrectly asserted that
writing air to an already-air cell must report a change. The original report
and failing probe bytes are preserved. The corrected second attempt restored
all fixtures but stopped after four rows when the owned game became
foreground at 2026-10-11 23:33:33 Shanghai. The original rejected capture
report remains preserved; no capture fallback, input or focus restoration
was used. The third attempt completed all 14 rows and restored all fixtures,
camera and workspace; its overall verdict remains false.

`builtin-plant-capability-r9-v3.json`, SHA256:
`2d197b9388ee4dbef3478da1f7d1cd43cdccbc3006012c6bdfd709ecd7fc036d`

The capture-time audit passes integrity for 84 native PNGs and 86 hashed
artifacts. Two switches between other applications are retained as permitted
background-use observations. Source bytes matched at audit time. Later
experimental source changes and final restoration are intentional; the
original audit is immutable.

`builtin-plant-capability-r9-v3-audit.json`, SHA256:
`08eb2b19337e1d612145cc799482fa3f483dd6ca4b428cf09463fe2598776d64`

Exact rejected definition files, original RP `blocks.json`, and host probe
versions remain under `experimental_source/builtin-v1/`. This owned session
stopped normally after restoration.

## Documented Netease Offset Probe

The official Netease guide documents `netease:block_random_offset` as a
flower-like offset with X/Z scopes containing two floats in `[0,1]`.
Equal endpoints fix the point. The component sets a transparent material
and cannot be combined with an opaque `netease:render_layer`. The guide
recommends model blocks to avoid clipping against opaque neighbors. No
native hash or mesh-pivot formula is documented.

The model-binding guide requires `netease_model` to reference a real model
identifier defined under RP `models/netease_block`. The next experiment
therefore binds the existing, unmodified `modern_projection:preview_fern`
model. It does not bind the hardcoded `minecraft:geometry.cross` as if it
were a Netease model file.

Three isolated format-1.10.0 definitions compare no offset, fixed X/Z scopes
`[.5,.5]`, and random X/Z scopes `[0,1]`. Each uses alpha rendering,
`netease:no_crop_face_block`, and light absorption zero. These values are
documented capability probes, not proposed native geometry. The diagnostic
IDs are `modern_projection:r9_offset_center_ne`,
`modern_projection:r9_offset_fixed_ne`, and
`modern_projection:r9_offset_random_ne`.

Session `28978d1a387543aa8bc37951fd2ece18`, game PID 1896, identity
`134362085717306217`, MCDK PID 42852, passed the documented 180-second
startup bound. Five normally bound client/server and HUD-screen reads
completed over 128.9 seconds before fixture setup. No fixture marker was
present. Handles increased from 81,041 to 99,209 and private memory from
2.628 to 2.638 GB during these read-only samples. This measures growth;
it does not establish its cause or resource acceptance. Guarded background
WGC then passed; the original startup frame was opened.

`plant-startup-stability-r9-v1.json`, SHA256:
`ac5ec580d4b4a4ed9442f4d9931cc12a1434fa8b6e3460d096c79e7e82cfd653`

The fresh `netease-offset-capability-r9-v3.json` completed all ten dry rows
at the original cell/public/right views and restored all native cells,
player, biome, world time, daylight rule, camera, mesh actors and workspace.
Cleanup errors are empty. Overall verdict remains false. Exact source bytes
and configuration remain under `experimental_source/netease-offset-v3/`.

Original native fern and direct-world frames were opened: the native plant
is visible, and its mesh frame contains support with no fern. Original
random custom-model native and direct-world frames were also opened: the
unmodified preview model appears in both, but its placement differs.
No translation, pivot, rotation, scope or hash was fitted.

Both mesh paths produce identical per-view broad object metrics:

| Definition | Public Recall / Precision | Right Recall / Precision |
| --- | --- | --- |
| Stone | .965020 / 1.0 | .999828 / 1.0 |
| Native fern | .419316 / 1.0 | .312136 / 1.0 |
| No-offset custom model | .836971 / .947228 | .773089 / .948302 |
| Fixed `[.5,.5]` custom model | .836971 / .947228 | .773089 / .948302 |
| Random `[0,1]` custom model | .717403 / .730607 | .514647 / .597311 |

These broad masks include support/background changes and never supply
native exposed-plant acceptance. No-offset and fixed scope agree in this
probe. Random scope changes native custom-model placement but fails both
mesh paths in both views. All three custom definitions still report the
same unit-cube clip box, so this clip query is not an authority for this
custom model's visual offset. Native fern's raw clip differs and is retained
in the report without centroid/pivot inference.

`netease-offset-capability-r9-v3.json`, SHA256:
`35ff1a991bad3efa60ec53a96c3a29005990bf377f57f667921c6f8600018df5`

Its capture-time audit passes 60 native PNGs and 62 hashed artifacts, with
no foreground switches. Sources match at audit time. Subsequent restoration
is intentional; this audit remains immutable.

`netease-offset-capability-r9-v3-audit.json`, SHA256:
`8300050d2ea34b7ca04c0a7c025c18080ff2df99dec16f2efacf29dc2a3d95d6`

## Documented Query Boundary

The MCP ModAPI catalog was searched with `api GetBlock --top 100`,
`api Offset --top 100`, `api BlockGeometry --top 30`, and
`api CombineBlock --top 10`. These results document clip/collision queries,
block state/palette/texture queries, custom block-entity effect/model offset
setters, actor-geometry offset setters, and the existing Combine paths.
No result in those searches documents a getter for a vanilla block's
rendered random offset, mesh vertices or mesh pivot. This is a boundary of
the reviewed catalog, not a claim that no engine facility can exist.

Combine's documented unsupported mode 0 skips unsupported blocks; mode 1
stops generation. A returned geometry name therefore does not certify plant
presence. Client palette acquisition is recommended for custom block-entity
appearances. All four earlier native paths already use client-side sources;
no server-palette substitution is proposed here. The documented Netease
component configures custom blocks and supplies no offset readback contract.
Candidates must stay in a renderer adapter with independent source-shape and
exposed-plant evidence; Cell and Session acquire no rendering duties.
The concrete remaining blocker is missing or mismatched visible plant
geometry under the existing dry+h0 gates. No new universal jitter accuracy
requirement is introduced. The accepted biome preset approximation and
existing fungus positional acceptance remain unchanged.

## Preserved Startup Failures

Session `1fbf3f074dad47bf946a20cdedaef3cd`, game PID 45164, MCDK PID 51580,
failed in normal `Client.__enter__` session binding before fixture,
projection or camera setup. The SDK returned no explicit return value.
`netease-offset-capability-r9-v1.json` has zero rows. Its false completed and
restored flags describe preflight non-entry, not an unrestored mutation.

The user reported this native startup assertion, relayed by the parent:

> The disabled skin popup has been displayed but the level data has no
> disabled cosmetics

Condition: `false`. Function: `DisabledSkinScreenController::onEntered`.
Source: `DisabledSkinScreenController.cpp`, line 46.
The original MCDK log does not transcribe that native assertion; the note
labels it as a user report. It is classified as a startup skin/cosmetics UI
incident before the fixture. Rendering causality and the relationship to
handle growth remain unproven. No automatic replay, input, assertion
dismissal or guard bypass was used. Normal WM_CLOSE did not exit the game;
the documented owner-bound force-stop completed after identity/log checks.

Its artifacts directory preserves the exact three experimental blocks,
modified RP `blocks.json`, unmodified fern model and probe bytes under
`experimental_source/netease-offset-v1/`.

`netease-offset-capability-r9-v1.json`, SHA256:
`11f4d189806415bff4e468dc99a755feb6665bc25f0a6c92be17dea96e758719`

`startup-ui-assert-r9-v1.json`, SHA256:
`22547b7e0033b0e6241e5bc6299add195fbe8fa00b4003da8f5dd32828e4f75a`

Session `4ffc09524aa64c34b10ed7507372d003`, game PID 27856, MCDK PID 20956,
uses the documented MCDK `skin_info` field with the runtime's vanilla
`data/skin_packs/vanilla/steve.png`, `slim:false`. The previous configuration
had no explicit skin. This is a bounded startup diagnostic, not a causal fix
claim. The relevant MCDK v1.6.1 README and generated configuration are
recorded with the evidence.

Normal SDK client/server reads completed and found no fixture marker.
Native `/screens` reported only `hud.hud_screen`. Guarded background WGC
passed at 00:00:54-00:00:55 Shanghai; its original PNG was opened and shows
normal gameplay without a visible popup. Before the component probe,
MCDK and the game exited. The log records normal MCP shutdown at
00:01:35; the cause is unestablished. The stale-instance guard rejected the
probe before report creation or mutation. No stop was issued by this agent
before that rejection. The parent also reports no stop of this session.
The registry was subsequently marked stopped through the owned normal path.

`plant-readiness-r9-v1.json`, SHA256:
`6061843826b132e2d977c82643f6cf33720ffe96c5cd8463452d14ea7a340016`

`session-exit-preflight-r9-v1.json`, SHA256:
`fdc1b3a6571a6efb986d7ced698ae7f11f4d7828d6ddb5868372f083d0872483`

Session `6bc04d40357f44349cd633a236bc23d5`, game PID 3472, MCDK PID 46128,
exceeded its 90-second SDK readiness bound. The normal manifest remained
failed, so no client-binding bypass, manual manifest promotion or fixture
call was made. Its log records the world game screen completing late at
00:07:07 and repeated `WindowsError: [Error 32]` in
`logging.handlers.doRollover`, logged from `mcp_log.py`, line 8. These are
observed rollover failures; their relationship to readiness, memory,
rendering or prior exit remains unestablished. The owned session stopped
normally. Exact configuration, model, definitions and probe bytes remain
under `experimental_source/netease-offset-stability-v1/`.

`startup-readiness-failure-r9-v1.json`, SHA256:
`0da768e5396c1a1d05ddc71cb8722d5b6e01029ca7390d86b367cbcd7dcff2b4`

## Acceptance Boundary

No authoritative vanilla mesh or jitter contract is established. Fungi keep
their existing positional acceptance only. Roots/sprouts, flowers,
grass/fern, torchflower and high-coordinate acceptance remain open. The
independent exposed-plant masks, fixed calibrated ROI, recall/precision
`.75/.75`, 3px edge tolerance and separate editor/full/missing verdicts remain
required. No dry+h0 failure is extended into remaining snow heights.

## Final Restoration

The documented component experiment completed without new rendering
acceptance. All startup failures above occurred before fixture mutation.
Session `28978d1a387543aa8bc37951fd2ece18` stopped normally after restored
captures and the source audit. No owned R9 game or MCDK remains active.

All eight temporary BP definitions and the three diagnostic RP entries were
removed. BP/RP have no tracked differences and no untracked files.
RP `blocks.json` matches its original Git blob exactly:
`cdf71f1c6bc95d58ba2e5de30f58a08a2bed91ab`.
The ignored startup configuration's temporary `skin_info` was removed;
automatic hot reload remains disabled. Rejected bytes and startup configs
remain in the owned evidence directories, not production assets.

After frozen experiments and restoration, the parent strict-layer fix
`8dbf996` was adopted as local commit `f4e2fbb`. Explicit-layer edits preserve
the unselected snow state; native-layer derivation remains separate. All 16
`tests/test_cell_edit.py` tests and three native fixture safety tests pass.
The three committed diagnostic tools also pass host `py_compile`.
These checks do not claim new live rendering acceptance.

Restoration and evidence consolidation finished before the 06:30 Shanghai
deadline on 2026-10-12 for parent integration and 07:00 hibernation.
