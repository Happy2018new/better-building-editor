# Shelf body and diagnostic shadow controls

Target engine: NEMC `3.10.0.420447`. Production qualification remains **false**.

The native observation read all 384 shelf states (12 woods x 32 states) and
captured 52 views. This package preserves 20 selected native originals, including
all twelve unpowered front views, the powered oak control, and the remaining
three cardinal orientations. `index.json` explicitly lists the omitted native
captures; the original complete run remains in `.runtime/shelf-native-shape-r18-v2`.
The package is not evidence that every shelf state or texel has been accepted.

The final body diagnostic preserves **all 32 original PNGs and receipts**:
native world, empty, live palette, serialized roundtrip, prepared palette,
candidate proxy in four views, followed by explicit entity-shadow on/off pairs.
The run completed, restored the world/camera/environment/workspace, retained
unchanged game sources, and recorded no cleanup errors. Native-size review crops
are unscaled. The root reviewed the complete body and shadow contact sheets.

## Shadow defect

The independent diagnostic created an anchor entity but omitted
`SetEntityShadowShow(False)`. Formal full and missing projection paths already
disable entity shadows. The on/off experiment reproduces and removes the dark
patches using the same entity, camera, and geometry. This was a diagnostic bug,
not an intended effect. The shared pose diagnostic and body diagnostic now both
disable shadows by default; the negative control enables them explicitly.

| View | Interior support pixels darkened by enabled shadow |
| --- | ---: |
| South | 1530 |
| East | 1512 |
| North | 18022 |
| West | 17677 |

These counts select the cyan support interior, excluding its silhouette. They
measure shadow contamination, not universal proof of rendering correctness.

## Body candidate

Live, roundtrip, and prepared native palettes omit the observed oak shelf body;
the cyan support remains visible. The isolated proxy restores a similar solid
shape. Its generator uses traced Java 1.21.9 resource geometry and unmodified
32x32 textures from the installed target engine. It emits 240 candidate models,
splitting the backing into three solid sections to avoid a zero-thickness front.
Only the tested oak model, artwork, and block registration are included here;
`candidate-contract.json` records the complete generated output hashes.

The proxy is **not installed in the root product**. Powered left/center/right
mapping, all direction/wood UVs, three content slots, connected groups, editor,
full/missing integration, lifecycle and native lighting parity remain pending.
Do not derive runtime direction mapping from aux arithmetic.

Recompute the portable body and shadow review:

```powershell
python tools/analyze_shelf_body_r18.py docs/evidence/shelf-body-r18-v1/body/report.json .runtime/shelf-review-fresh
```

`manifest.json` binds packaged bytes. Absolute original capture paths are
retained in reports; the analyzer falls back to the packaged sibling PNG when
the original path no longer exists. Reports are diagnostic observations and
never open a product gate.
