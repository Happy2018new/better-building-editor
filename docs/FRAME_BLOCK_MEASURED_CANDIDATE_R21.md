# Narrow Measured Cube Candidate

The historical full-catalog generator keeps its `.5` cube, Z `.1875`, resource
identities and disabled production profile. The diagnostic clones measured stone
aux 0, quartz block aux 0 and grass block aux 0 with a `.25` cube centered at
Z `.4375`. This pose is shared as `MEASURED_POSE`, with `accepted=False`; it does
not establish the pose of the other catalog entries.

Generate the three-item candidate into a new directory:

```powershell
python -B -X utf8 tools/prepare_frame_block_measured_r21.py --install D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447 --output .runtime/frame-block-measured-candidate
python -B -X utf8 tools/prepare_frame_block_measured_r21.py --install D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447 --output .runtime/frame-block-measured-candidate --check
```

The entry rebuilds six native carried faces for exactly those three item pairs,
uses the corrected alpha-controlled grass overlay, creates separate pose-bound
resource keys, and emits a three-item profile and opaque-only registrations.
It validates installed metadata and bitmap provenance, including historical
stone atlas sharing with `infested_stone`. It has no registration or production
write option. The output must be fresh; `--check` verifies every output byte and
rejects unexpected files.

The candidate does not import the diagnostic `.93` light factor. Native captures
of that factor remain evidence for their exact frozen clones. Direction, all
rotations, absolute thickness, frame and editor shared depth, broad lighting,
special geometry and material-specific gates remain open. Ordinary diamond
sword glint acceptance does not qualify quartz cube glint. Production, pose and
material qualification remain false, and no 854-pair resource regeneration is
performed.

Before and after the generator refactor, the historical default stone/quartz
subset produced identical SHA256 values for all 12 output paths. Existing keys
`0d8d479f3958fea7` and `1cc58135f7b22c54` remained unchanged. The primary catalog
still contains the old grass bitmap identity and needs an explicit future
regeneration; the narrow entry rebakes its own grass resource separately.

The compatibility receipt compared the committed historical generator directly
with the edited generator, without writing shared resources. SHA256 of the
sorted 12-path output hash mapping is
`3038f294bb1c4379819fe3dd791a479cbc56b3e68a7dbe7676086a089ac58554`.
The historical generator Git blob SHA256 was
`049d2af19eaa16a56b159bc8f2b700dcb68881c56674b767fcfab4e4faadc622`.
The three new resource keys are `088a7d10a45b8429`, `3694abb015dcb2e6` and
`4e210f8fbdabb72a`. The grass atlas SHA256 is
`ab130fe030a9686eb0f5817b37a652535747d6ed22abc07c6741ed48a504dd8b`,
identical to the corrected atlas used by the three fresh grass holdouts.

The newly generated resource identities and default shaders have not been
captured in game. Native pixel evidence refers to the original frozen
diagnostic clones, including their unchanged empirical light variant.
