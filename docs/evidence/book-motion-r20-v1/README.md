# Moving Cover White Fragments

Measured on 2026-10-15 with NEMC 3.10.0.420447. These are bounded native WGC
bursts from managed, identity-checked instances with no agent activation,
desktop input, or resize. All four reports completed and restored with empty
cleanup errors and unchanged installed sources. Diagnostic aliases also retain
their exact source fingerprints before and after capture.

The only production geometry change is the closed enchanting book page-block
clearance: 0.01 to 1/32 model pixels. Cover surfaces, spine, UVs, topology,
culling, depth transform, shaders, and lectern geometry are unchanged. A depth
factor control was rejected because it placed the book behind the table top.

| Run | Valid Frames | Actual Span | Maximum Gap | White Peak | Isolated Peak | Dense Gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `final` | 476 | 16.9815401 s | 72.7276 ms | 0 | 4 | Pass |
| `pitch75` | 349 | 16.9573219 s | 187.972 ms | 0 | 3 | Pass |
| `baseline-negative` | 317 | 16.9633573 s | 115.151 ms | 100 | 100 | Reject |
| `old-gap010` | 299 | 16.9512204 s | 151.5111 ms | 3 | 3 | Diagnostic Alias |

The original isolated-pixel threshold remains 8; the maximum permitted frame
gap remains 250 ms. The prior detector required a brown center, which excluded
white page fragments by construction. It now also accepts a bright neutral
center while preserving the existing uniform-brown neighbor and contrast
requirements. Real page silhouettes and long page edges remain excluded.

The final two runs use final model names and the 1/32 clearance. Camera and
book owner remain fixed, captured crops show sustained rotation, and each
planned burst is 17 seconds. The high-pitch check changes only the editor
pitch from 25 to 75 degrees. The old-gap alias mesh is structurally identical
to the pre-fix installed mesh. Its mild recurrence does not exceed threshold
and is not presented as a threshold-negative control. The complete old baseline
is the threshold-negative control; its worst original frame is preserved here.

The baseline, final and old-gap sheets, plus original final frame 240, were
actually inspected. They show the real book and table, and the marked baseline
fragments are inside cover artwork. These results do not establish full native
pose, brightness, page, table boundary, or default-path acceptance. Production
qualification remains false until those independently bound checks pass.

Each directory preserves the original report, full burst receipt, analysis,
exact unscaled contact sheet, and selected original full-resolution PNGs. The
complete raw frames, per-frame receipts, and native manifests remain under:

- `.runtime/book-r20-final-dense-v1`
- `.runtime/book-r20-final-pitch75-v1`
- `.runtime/book-r20-baseline-v1`
- `.runtime/book-r20-old-gap010-v1`

The original reports and analyses retain their absolute source paths and
SHA256 bindings. Replay the complete raw report with
`tools/analyze_book_motion_r20.py`; these selected copies are for review and
are not a replacement input containing every burst frame.
