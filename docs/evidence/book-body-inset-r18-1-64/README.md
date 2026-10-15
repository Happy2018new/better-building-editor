# Table bottom inset diagnostic, 1/64 model pixel

This isolated candidate failed visual admission. No root production asset or
book gate was enabled. A cold-started disposable clone used a 0.015625 model
pixel (1/1024 block) bottom inset, preserving the original top and all six
native-textured faces.

The 12 native captures completed and restored with unchanged source hashes
and no cleanup errors. Both `review-00.png` and `review-01.png` were actually
inspected. The high occupied view in the lower-right of `review-00.png` still
shows the complete obsidian-textured bottom plane over the support. This is a
real failure; the smaller inset does not survive the actual mesh/shader
precision and clipping tolerance sufficiently to remove it.

`occupancy-analysis.json` binds the same-camera occupied/control comparison:
18,344 high-view support-interior pixels, maximum channel difference 126,
and 5,878 pixels above 8. Low-view support interiors are identical, but this
does not establish absence of a horizontal bottom plane hidden at that angle.
The shown low-view seam is less apparent than in the 1/16 test; that cannot
override the clearly visible occupied residue.

The root production model remains at its original zero inset. The 1/16 test
removed the texture residue but left a pale low-view line, and this smaller
test retained the residue. Neither candidate qualifies for production.

Managed instance: `3ea9825b16d24869a34e776f61e4f31a`, owner `book-owner-r18`.
Startup receipt: `.runtime/book-inset-r18-1-64-start.json`. Full source PNGs
remain at the SHA-bound paths in `report.json`; these crops are unscaled.
