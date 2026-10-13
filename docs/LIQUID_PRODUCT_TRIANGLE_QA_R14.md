# Independent Product Water QA

The user accepts a declared Java-style or custom water renderer when it looks
reasonable. These checks validate the selected product contract without
promoting any previous native-parity failure to a pass. No game was opened.

## Actual Triangle Checks

The existing water shader verifier submits isolated GL points. A vertex shader
called at an arbitrary interior point evaluates its bilinear height formula;
the real model instead submits four vertices and rasterizes two triangles.
Those surfaces differ for nonplanar corner heights. The new
[`verify_liquid_product_triangles.py`](../tools/verify_liquid_product_triangles.py)
uses the real mesh vertex positions, indices and product vertex/fragment shaders
in GLES 2 and GLES 3, with back-face culling enabled.

The independent oracle defines physical cube corners, outward face directions
and barycentric triangle interpolation. It does not import the mesh generator
or derive expected geometry from the shader. An asymmetric, repeated-frame
coordinate texture removes water-artwork symmetry and animation as confounders.
The geometry probe independently checks interpolated UV and fragment depth;
the marker probe uses the unchanged production fragment shader and source-alpha
blend over a known colored background.

The final [host v4 receipt](evidence/liquid-product-triangles-r14/host-v4.json)
passes **46,848 pixel checks** across 12 animated/frozen UI/world model bindings:

- All six outward faces, four payload slots and independently offset cells.
- Full height, low height and unequal nonplanar quantized corner heights.
- Four flowing-top rotations, four side orientations and bottom-fixed crops.
- Visible and masked surfaces, triangle interiors and internal diagonals.
- Colored backgrounds through the declared translucent product material.

Three mutations are applied only in memory, leaving resources untouched. The
oracle must detect reversed triangle winding, stretching a low side to the full
texture height, and a horizontal side-UV flip. All three are detected. The report
records their expected negative observations separately from the normal checks.

Ten focused unit tests protect the independent oracle itself, including a
nonplanar triangle-versus-bilinear counterexample, all six outward normals,
UI/world camera inversion, malformed mesh roles and the mutation controls.

The receipt binds exact resource-contract, mesh, shader, verifier, expansion
helper and recursively included installed-header bytes. If those inputs change
during the host run, the result is refused. The checked resource contract is
`e5e8fd4a68f9af42feae7591bcd434d0c9edc99e8f256197e760b7f076e8fb53`.

Initial v1 and v2 reports are retained in
[`verifier-preliminary.zip`](evidence/liquid-product-triangles-r14/verifier-preliminary.zip).
They exposed two verifier mistakes: exclusion of the shared triangle diagonal,
and expecting unrotated UVs from the dedicated flowing-top shader. They were not
production-render failures. The final checks fix those expectations without
relaxing the pixel tolerance or changing the shaders.

## Actual Product Owners

[`test_liquid_product_owner_contracts.py`](../tests/test_liquid_product_owner_contracts.py)
uses the public built-in water blueprints and the real candidate profile,
`LiquidPreview` and `LiquidProjection`, with a controlled SDK model adapter.
Eight focused tests pass:

- All 14 public cases retain focus geometry and flow when neighboring draws are
  removed by missing-projection occupancy; complete source cells remain intact.
- The east-flow fixture independently predicts heights
  `(85/117, 1/6, 1/6, 85/117)` and top direction code 192, even with only the focus
  targeted. The lower-northern-neighbor fixture keeps four heights `20/27` and
  direction code 128 when that lower neighbor is omitted from draws.
- Editor cutaway and missing projection retain hidden water-above context.
- Coincident identical water in both logical layers renders once, including
  water/flowing-water aliases and foreground-only or background-only targets.
  Both saved layers and typed actor bytes, bools, integers and lists remain intact.
- Conflicting depths explicitly fail and preserve the published editor plan.
- Failed new payload upload preserves the visible world generation, latches
  without repeated uploads and permits a successful explicit retry.
- Failed native removal retains hidden ownership until a later successful retry.

The coincident-layer check found a real alpha-composition edge case: drawing
the same water twice changes alpha .45 to .6975. The product owner fixed it by
coalescing identical rendered parts while retaining the logical cells. The
independent tests verify that fix. Legacy providers retain their prior behavior.

## Reproduce And Boundaries

```powershell
python -X utf8 -m unittest tests.test_liquid_product_triangle_oracle tests.test_liquid_product_owner_contracts -q
python -X utf8 tools/verify_liquid_product_triangles.py --headers D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/data/shaders/glsl --browser "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --output .runtime/liquid-product-triangles-new.json
```

Choose a fresh report path; the verifier refuses to overwrite prior evidence.
Use `--root <checkout>` only to check that checkout's exact installed product
contract. Shader includes must come from its corresponding game installation.

These checks do **not** accept real-game screenshots, artwork quality,
animation cadence, skeletal bone/instance matrices, entity/camera ownership or
integration with scene bodies. World skinning is explicitly excluded from this
triangle run. The source model is checked with a non-skinned world shader and
an independently inverted UI transform. The separate native editor/full/missing
tests must still establish the final appearance and cleanup behavior. Existing
R11-R13 native side and boundary failures remain unchanged.

This is an evidence report, not a second TODO list. The active task list remains
[`IMPLEMENTATION_GAPS.md`](IMPLEMENTATION_GAPS.md).
