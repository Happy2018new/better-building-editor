# Native Shelf Body Diagnostic, Round 16

The reviewed `v2` record covers one `minecraft:oak_shelf` state in NEMC
`3.10.0.420447`. Four views show the real-world body. The same client palette
passed directly to Combine, serialized/deserialized unchanged, and passed
through the product's palette preparation all omit the shelf body. Their cyan
support remains visible. The native actor payload is empty in all three paths;
the original typed server NBT still identifies `Shelf`.

`v2/review.png` was inspected directly. `v2/analysis.json` subtracts matched
empty captures before counting shelf wood and cyan support. The initial
analysis incorrectly counted brown terrain and cyan sky; it is retained in
this folder as a failed host analysis, not accepted evidence. The revised
metric preserves the original positive thresholds and has negative controls
for unchanged colored terrain, sky and small frame noise.

The source fixture completed and restored world, player, camera and environment
state. The original 20 PNGs and reliable background-capture receipts remain
locally in `.runtime/shelf-native-r16`; this compact record retains report,
source and image fingerprints and a review sheet, not an independent raw replay
bundle. Both probe and analyzer are in `tools`.

This identifies a native body gap for the measured state, not production
qualification for all 12 woods, connection roles, powered states or item slots.
Implement and qualify a shared static shelf body family before enabling full
shelf support. The public default and nonempty item-slot blueprints already
provide product test fixtures.
