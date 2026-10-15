# Table bottom inset diagnostic, 1/16 model pixel

This is an isolated diagnostic, not product qualification. The root book gate
remains closed. Only the disposable clone's table body geometry was changed.
The bottom plane moves inward by 0.0625 model pixels (1/256 block); the top
stays at Y=12, all six faces remain, and native UV artwork is unchanged.

The 12 native captures completed with restoration, unchanged installed source
hashes, and no cleanup errors. The report and exact crop hashes are retained.
`review-00.png` and `review-01.png` were actually inspected, together with the
raw high occupied/control and low shown captures.

The original obsidian-textured occupied residue is no longer visible. The low
occupied/control pair has 25,117 interior support pixels with zero channel
difference. The high pair has a flat top-face lighting change: its broader
interior mask has 18,344 pixels, maximum difference 26, and 5,878 pixels above
8. Thus this evidence does not claim identical shading over the whole support.
See `occupancy-analysis.json` for the same-camera comparison and source hashes.

The low shown view retains an approximately one-pixel pale line at the table
and support boundary. This blocks acceptance of this inset until comparison
with a smaller inset establishes that the diagnostic did not create a visible
gap. No production assets or admission were written from this result.

Full source images remain at the paths in `report.json`. The managed instance
was `ac95c695b5904685b090c5d83b6df42f`, owner `book-owner-r18`; the startup receipt
is `.runtime/book-inset-r18-1-16-start.json`.
