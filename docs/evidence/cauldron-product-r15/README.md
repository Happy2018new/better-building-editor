# Cauldron Product Qualification, Round 15

Engine: NetEase `3.10.0.420447`, Bedrock `1.21.130.0`.

The qualified scope is the finite liquid surface inside the existing native
cauldron shell, using the ordinary editor and full/missing projection owners.
The product profile is selected only for this exact engine version. Future or
malformed appearances retain the native route instead of receiving a fabricated
liquid surface.

## Accepted Results

| Check | Actual Evidence | Result |
| --- | --- | --- |
| Six fill levels | Six lava levels, editor/full/missing, paired against empty shell | All six increase; contents remain inside the bowl |
| Four appearance families | Lava, RGB dye, potion, ordinary water, powder snow | Distinct contents in all three routes |
| Animation | Five representative appearances in all three routes | Animated families change 13-42% of stable local pixels; powder snow changes 0% |
| Real-world occupancy | Five appearances in missing projection | Companion hidden when foreground becomes occupied, restored after clearing |
| Editor visibility | Lava and ordinary water, section and hidden Y layer | Shell and liquid hide together; stone support stays visible; restoration passes |
| Public gallery | `test.entities.cauldrons`, 33 cases in one ordinary scene | 33 published groups, six native geometry parts, no publication errors |
| Lifecycle | All three final reports | Completed, restored, unchanged sources, no cleanup errors |
| Default Session and biome switch | Cold-started default profile, plains/swampland/plains in all three routes | Uniform RGB and actual liquid colors follow the requested biome |

The root and cauldron agent reviewed the 30 filled/empty content images in
`final-matrix-v1-analysis.png`. The cauldron agent additionally reviewed the full
occupancy, restoration, section and gallery images. Pixel metrics support this
review; publishing a model or passing a native call alone is not treated as
visual acceptance.

## Appearance Policy

Ordinary water deliberately uses the document biome water preset and installed
`water_still_grey` artwork. Changing the editor/projection biome changes that
preset through `biomes.water_appearance`; four biome choices are covered by the
profile tests. This is a product appearance, not an exact native-cauldron color
claim. `default-biome-smoke-v2.json` and `default-biome-analysis.png` additionally
verify the actual blue/green change in all three default production routes.
The original fill-level matrix uses the default document biome.

Dye and potion contents use the separate installed `cauldron_water` artwork.
`CustomColor` uses its low 24 RGB bits, including signed int values. Potion IDs
5-46 use measured native colors; forms 0/1/2 share that color table. Unknown tags
and source NBT are preserved. Lava uses the native 16-tick flipbook cadence;
ordinary and colored water use two ticks per frame. Powder snow uses a static
native texture. Every generated vertex/fragment shader declares high precision.

The native six-level geometry and powder-snow fits are recorded separately in
`../cauldron-surface-r15/`. The accepted snow6 fit is
`snow6-live-calibrated-v2`; the failed first calibrated attempt is not acceptance.

## Source And Evidence Binding

`qualification.json` binds the native measurement source, generated resource
contract, twelve owned/shared implementation files, four unchanged runtime
reports and all three analysis outputs. The runtime gate compares its generated
fingerprints and requires every declared acceptance gate. Bundle tests also
check the current source files, dedicated assets and registry subsets against
the files actually used in the runtime reports.

The retained reports preserve original capture paths and capture hashes. Only
representative full screenshots and the complete contact sheets are committed.
All 340 original files, including unsuccessful attempts, are preserved in the
ignored local archive `.runtime/cauldron-product-r15-raw/` and in the isolated
test project `D:/bbe-r15-cauldron-production/docs/evidence/cauldron-product-r15/`.
The qualification tool needs the full originals when revalidating all captures;
the checked-in bundle tests verify the compact retained evidence and source
contracts without relying on those external paths.

## Revalidation

1. Regenerate native data from hash-checked evidence with
   `tools/generate_cauldron_native_data.py`.
2. Regenerate all four resource families with
   `tools/generate_cauldron_resources.py`, using the installed vanilla pack and
   versioned measurement file. Changed dimensions, cadence, geometry or registry
   entries are rejected.
3. Cold-start an owner-bound instance and save its launch source map. Run
   `tools/probe_product_cauldron.py` for the matrix, `--extras` for animation and
   missing occupancy, and `--visibility --gallery` for editor visibility and the
   whole public blueprint. Camera parameters come from that public blueprint.
4. Run `tools/analyze_product_cauldron.py` and review the actual screenshots.
   Empty controls isolate the finite contents, and animation is measured only
   inside their stable local footprint.
5. Run `tools/qualify_cauldron_r15.py --accept-reviewed-product` only after that
   review. Without the explicit review flag the generated profile stays disabled.
6. Run `python -m unittest discover -s tests -p "test_cauldron*.py" -v`.

The final managed instances (`cauldron-product310-r15-final`, PID 41820, and
`cauldron-default310-r15`, PID 41848) were restored and stopped normally after
their tests. The first default-path attempt was rejected by its empty-region
preflight because of natural terrain; it did not write blocks and restored its
state. The successful retry used an empty area 16 blocks above the player's
initial position. No foreground activation or desktop input was used. The
additional public `test.dynamic.fire` screenshot is gallery load/visibility
evidence, not detailed qualification of the complete fire family.
