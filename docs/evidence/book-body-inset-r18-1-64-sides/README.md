# Actual horizontal-neighbor occupancy control

This native diagnostic confirms that the body clipping defect affects the
four horizontal sides as well as the bottom. It does not qualify production.
The root book gate remains false and its body model remains unchanged.

The source has an enchanting table over a gray support and four same-height
`minecraft:smooth_stone_slab [0]` neighbors. Their half-height geometry leaves
the table's upper side walls visible. Only the real world cell at the table's
logical position is occupied; the four slab targets remain missing. The
support-only control removes only the logical table from the document.

All 12 captures completed and restored, installed sources were unchanged,
and cleanup errors are empty. Both exact-pixel contact sheets were actually
inspected. `review-00.png` lower-right clearly shows that the occupied table
loses its book and top but retains textured walls as an open box. The reverse
low view in `review-01.png` lower-left independently shows the opposite sides
surviving above the slabs. The control views have no textured table walls.

Thus all four horizontal faces are an observed defect, not an untested risk.
The clone's 1/64 model-pixel bottom inset cannot fix these original X/Z
boundaries, and its bottom also failed in the separate bottom-only test.
The native engine used is `3.10.0.420447`.

The first side attempt rejected the obsolete `minecraft:stone_slab` name
while encoding the source, before any game mutation. Its failed log remains
at `.runtime/book-inset-r18-1-64-sides-proof.log`. The successful attempt uses
the canonical name confirmed in the checked-in registry. Its full raw PNGs
and native capture receipts remain at SHA-bound paths in `report.json`.

Managed instance: `3ea9825b16d24869a34e776f61e4f31a`, owner `book-owner-r18`.
No geometry or shader repair is admitted by this result.
