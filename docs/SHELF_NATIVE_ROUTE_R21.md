# Native Shelf Route V3 Evidence

The south-facing unpowered oak shelf body selects the native `terrain_base`
fragment in engine 3.10.0.420447. Both full raw images were opened by the shelf
worker. A strict top-body ROI at x=[912,1088), y=[440,455) excludes support and
background terrain: all 2640 corresponding empty-image pixels are sky,
1200 native marker-strip pixels are exact yellow, and 1440 alternate pixels
retain native wood artwork with 58 distinct RGB values. No cyan occurs there.

This conclusion applies only to that native world draw. It does not establish
other woods, states, editor/UI rendering, original light inputs or a production
appearance fix. The original unsegmented acquisition report keeps
`native_route_qualified=false`; the independent body review is a separate record.

Portable evidence is in `docs/evidence/shelf-native-route-r21-v3`. It includes
exact raw PNGs/report, four-resource before/after bytes and patches, native
shader/material sources with recursive shader headers, frozen host snapshots,
compiler receipt, freeze records, strict ROI replay, and lifecycle records.
It deliberately does not include a complete behavior/resource-pack clone.

The two-image capture completed, restored its fixture and environment, and
verified unchanged frozen source with no cleanup errors. Normal stop timed out;
the exact observer subsequently recorded MC exit 0xC0000409 and MCDK exit 0.
Finalization reported stopped with force=false. Stop/finalize original stdout
was not saved; these facts are explicitly root-attested, while exact-exit.json
and the token-redacted stopped-session snapshot preserve available raw records.

Five focused tests passed. The compiler record has 40 native/selector pairs,
80 programs and 608 pixel checks: 78 programs compile/link; both programs in
one GLES100 skinning pair have the same inherited native failure. All applicable
RGB, native-artwork, alpha, discard and BYPASS comparisons pass.

Replay only needs Python and Pillow, with no local game/project paths:

```powershell
python -B -X utf8 tools/pack_shelf_native_routes_r21.py verify --package docs/evidence/shelf-native-route-r21-v3
```

The package also includes the replay tool under `host/tools`, so it can be
copied independently and checked from its own directory. Frozen v3 tools,
runner, source clone and receipts remain unchanged. V4 terrain input readback
is a separate offline experiment and is not part of this archive commit.
