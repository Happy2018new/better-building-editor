# Shelf Skeleton Candidate R21

This is an isolated oak/unpowered shelf-body candidate for engine 3.10.0.420447.
Native shape, UV, lighting, depth, lifecycle and product qualification remain
false. Contents, enchanted items and product routing are separate work.

## Uniform Scale And V1 Amendment

The world shader transforms normals through the same Z reflection, bone,
instance and WORLD matrices as positions, using normal w=0 and normalization.
This candidate requires its caller to supply uniform scale. The shared
WorldLiquidRenderer validates positive axes but does not enforce equal axes.
The current probe explicitly supplies scale (16,16,16), so its call satisfies
the requirement. No shared owner change is needed for this fixed probe.

The frozen v1 contract incorrectly said existing owners enforce uniform scale.
This paragraph amends that statement. The v1 resources, contract, cold clone,
runner and host sources remain unchanged so the frozen v1 experiment can still
run. V2 corrects only the contract wording and generator provenance.

## Verification

- The 12 focused shelf skeleton tests pass.
- A fresh `.runtime/shelf-skeleton-r21-v2` has all eight resource files byte
  identical to `.runtime/shelf-skeleton-r21-v1`; `reference.json` is also exact.
- Only `limits` and `generator_sha256` differ between the two contracts.
- V1 and v2 each pass 18 target-header GLES compile/link checks, 192 actual
  shader-pair synthetic pixel checks and 144 axis-function pixel checks.
- The frozen v1 clone, resource contract and every frozen host hash still
  verify. No MC instance was launched for these offline checks.

These checks establish resource identity and offline behavior only. Native
material selection, geometry and lighting still require the scheduled captures.

## Reproduce

Choose fresh output and report paths. Generate with
`tools/generate_shelf_skeleton_resources_r21.py --native-data <engine-data>
--output <fresh-output>` and verify with
`tools/verify_shelf_skeleton_r21.py --project <output> --headers
<engine-data>/shaders/glsl --browser <edge-executable> --report <fresh-report>`.
Run the focused tests with
`python -B -X utf8 -m unittest tests.test_shelf_skeleton_r21 -v`.

The model has actual geometric normals and retains the existing shelf UVs and
four-slot address/rotation encoding. UI light uses document normals; world
light uses transformed normals. Its fancy axis formula is a named candidate,
with no claim that the native shelf selects that lighting branch. The probe
admits selector images before light readbacks, and requires reviewed raw native,
empty and selector images before expanding to additional diagnostic modes.
