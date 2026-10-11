# Liquid Payload Round 7 Checkpoint

Date: 2026-10-11. Owner: `p0-liquid-backend-r7`. Game: NEMC
`3.9.0.401155`; runtime reported `1.21.120.0`.

This checkpoint is an unaccepted transport experiment. Native geometry,
native input format, pose transport, height accuracy, animated sampling,
production memory and public controls acceptance remain **false**. It supplies
four independent heights and explicit face masks; it derives no native height
formula, face rule or flow direction.

## Results

| Probe | Actual reviewed result | Cleanup |
| --- | --- | --- |
| `liquid-pose-stone-control-r7-v6` | World stone and live/roundtrip projection visibly centered; projection diagnostics 28,555 pixels each | restored |
| `liquid-custom-proxy-control-r7-v1` | Existing white shulker proxy visibly renders world and live/roundtrip projection in the third session | restored |
| `liquid-pose-channel-r7-v10` | Thin custom block and standalone client entity invisible; live/roundtrip invisible | restored |
| `liquid-static-carrier-native-r7-v2` | Nonzero `[8,1,8]` cube with only up face and zero-size UV invisible | restored |
| `liquid-static-uv-control-r7-v3` | Identical up-only geometry with full `[64,64]` UV still invisible | restored |
| `liquid-pose-channel-r7-v11` | Thin block, standalone thin entity and standalone full-volume entity with explicit local opaque texture invisible | restored |

The latest baselines, standalone/entity-control captures and both projection
PNGs were actually opened. Temporary stone platforms are visible. All capture
reports retain owner/process identity, fresh WGC frame time and background
focus metadata. Difference counts are diagnostics, not shape acceptance;
moving background objects can produce a signal. The original negatives are
preserved, including earlier zero-volume and fallback-icon cases.

Pose v10/v11 actual serialized actor schema is the byte-string identifier
`modern_projection:liquid_payload_pose_poc` mapping to integer key `0`, mapping
to `{}`. The schema is unchanged after scale `(1,4,.5)`, X rotation `30`, Y
rotation `20` and offset `(.25,.125,-.25)`. All four setters returned true. Both
live and deserialized palettes returned geometry names; byte-for-byte palette
roundtrip equality is true. No visible mesh or pose retention follows from
these returns. The probe attaches ordinary actor tag `19487`, not decoder tag
`39683`; native decoder execution was never accepted.

## Compatibility And Cost

- The ready second cold session has no `GetTextureAtlasUV` method. The current
  atlas-rectangle decoder therefore has no validated NEMC 3.9 binding route.
  `WorldToScreenPoint` and `GetViewMatrix` are absent too.
- Structured installed terrain/flipbook resources verify still/flow water and
  lava texture references. They provide no atlas rectangle and do not establish
  animated sampling through a custom actor. `WATER_TEXTURE_UV_RANGE` exists in
  native water shader headers, but actor availability was not tested.
- Direct native-key `TEXCOORD_0` sampling is only a future candidate; a different
  tested third-height channel would be needed. No guessed bounds are accepted.
- Carrier transport uses 64 logical cells and at most 448 carrier cells per
  four-cubed batch. Six/eight-bit error bounds are `1/126` and `1/510` blocks.
  Worst native serialized volumes are 1,835,008 and 29,360,128 indices. Native
  dense allocation and Combine cost remain unmeasured, so scalability is not
  accepted.
- The host CPU suite has 9 passing tests. The GLES 2/3 oracle passed 1,792
  synthetic float/half-float checks across BLEND and BLEND+FOG. Neither validates
  engine vertex packing, registration, texture binding or liquid height rules.
- MCP review returned `files=0` for host tools; this is not a passed structural
  review. Host source was manually checked and compiled.

## Runtime Identity And Shutdown

Third ready session: `95467a4930b04deb8270f336fb762d36`, MCP `63901`, game PID
`32556`, creation identity `134361763930908430`.

Fourth first attempt: `61e342748efc4f50b483dd9f4c24c767`, failed closed with
`Focus guard module snapshot failed`; no native acceptance or guard bypass.

Fourth retry: `d8da9c65ddae4e12b225a9db8ac97f4d`, MCP `56016`, game PID `18664`,
creation identity `134361788444530231`. It used the existing no-activate DLL
and guarded MCDK, with reliable preflight v4. Handle samples grew from 161,948
to 235,873 to 318,461 while RSS remained about 710-733 MB and threads 64-66.
The cause is unassigned; no full-batch carrier cost was measured. The owner
stopped new native experiments after v11 cleanup. Ordinary shutdown returned a
timeout, but subsequent owner-bound status confirmed MCDK and game both dead;
no forced shutdown was needed.
The final registry was subsequently updated to `state=stopped`, `ready=false`.

Experimental BP/RP changes remain uncommitted. Resource overlay v6 freezes the
latest fixtures. Original-byte installation backup v3 is retained; later
controlled resource changes have their own overlay contract identities.
Overlay v6 `contract.json` SHA-256 is
`0a82ac622f76c97174809a3f8a6347df60ad309611cabb8e41281f3e7257e421`.

The smallest next native discriminator is a known visibly rendered client
entity substituted into the same block `client_entity` registration, followed
by changing only its geometry to the thin prism. A separate known full custom
cube under the exact overridden blend descendants can isolate the material
path. BP registration, ModBlock NBT, replication and generic shulker palette
rendering are established. RP model/controller/material selection and mesh
emission for these fixture identifiers are not established; pose transport is
downstream of these gates. No additional native scenario was started after the
final negatives.

## Original Report Identities

Reports and their referenced PNGs remain in `.runtime` under the isolated
`p0-neighbors-r4` worktree. SHA-256 values below identify original raw reports:

| Report | SHA-256 |
| --- | --- |
| `liquid-pose-stone-control-r7-v6.json` | `f7b1d2fcf5389cd90d05209d56bae8eaf245f49b9ac7ee9f9d27eb5ece3341e8` |
| `liquid-custom-proxy-control-r7-v1.json` | `bd0704b6edc89399a0e650fc74e79b190cffe34000430b68ca91da4f3294c75a` |
| `liquid-pose-channel-r7-v10.json` | `d1e3d9546f9b0f782e0ac38538ec41b8d6088ca7a59b77fa6b29e87ef6c13e7e` |
| `liquid-static-carrier-native-r7-v2.json` | `ccf1e8c00f04e6b482b5bffdf60850ac6e09eaa919867dd0ce9a0645e50b9c3d` |
| `liquid-static-uv-control-r7-v3.json` | `ca70dd4c3ef52b6cca89d6c3d0e4e7c1d0e1508afa7fde29f2f74ffab0c91596` |
| `liquid-pose-channel-r7-v11.json` | `f6a1a37ec0357049a39eee6277efea47865bfa11a6f227814e84ec1d4cdbe2f9` |
| `liquid-payload-poc-gles-r7-v4.json` | `1f6988efdd86f1581be4907afdfb7c36fc3714d0027b952fa8b7d792aebbd78f` |
