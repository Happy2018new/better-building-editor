# Native portal attribute readback, R20

This package records an actual native End gateway block at 2026-10-15 23:31
Asia/Shanghai. It does not qualify projection appearance or any product profile.

The clone-only `portal_base` override rendered vertical depth stripes on the
real native gateway. The observed native north face has 16 planes, with rounded
depths 0, 2, 4, ..., 30. Every present stripe has coverage 1.0 and RGB p99 spread
0; every intervening odd stripe is completely black. The color lookup traverses
the 4x4 texture in reverse: depth 0 reads (0.875,0.875), depth 30 reads
(0.125,0.125). Blue-channel values are consistent with truncating normalized
depth to an unsigned byte. Pixel readback does not establish normal encoding.

`observed/report.json` completed and restored all world blocks, player position,
temporary platforms, camera, editor document and profile. Its complete cloned
project SHA map remained unchanged. The ordinary starfield presence detector
rejects the native attribute stripes by design; that field is not an appearance
acceptance result. The attribute-specific decoder accepts the uniform stripes.

The earlier R20 v1 control was invalid because its fragment lacked an explicit
float precision. It is not used to infer native attributes. This corrected v3
control compiled and linked in GLES 2/3. Projection-adapter GLES 2 skinning uses
an engine header with an inherited mat3x4 limitation, recorded separately from
new errors; all supported compile/link cases pass. Compilation is not visual QA.

`actual-inputs` preserves the exact material, shader, model registry and config
used for the observation. `compiled` includes expanded shaders and their SHA,
compiler SHA and logs. `host-sources` includes the decoder and current generators;
the native-layout option was added after the readback and is not claimed to be
the source of the already acquired v3 image. The original clone-preparation
script is preserved under `launch`. The complete SHA map binds the original
clone; this bounded subset is not a full runnable game-project import closure.

No installed game file, production portal resource, profile or qualification
was overwritten. Particles and native gateway beams are outside the finite
portal-surface comparison and are visible only in the native fixture.

Replay decoding from the repository root:

```powershell
python -X utf8 tools/analyze_portal_attributes_r20.py --report docs/evidence/portal-native-attributes-r20-v1/observed/report.json --output .runtime/portal-attribute-replay-r20.json
```

Expected: `control_observed=true`, the sixteen even depths, and
`pixel_acceptance=false`. The manifest binds every package file except itself.
