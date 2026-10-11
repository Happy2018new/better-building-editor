# Round Seven Entity Visual Evidence

The hanging-sign front and chest top candidates remain unaccepted. This
checkpoint adds only verification tools and evidence. It contains no production
resource change and does not authorize integrating chest candidate `008ca89`.
The original `.45` sign IoU threshold, color cutoffs and layout tolerances remain
unchanged. The hashed manifest is
`tools/data/entities_visual_unaccepted_evidence_r7.json`.

## Hanging-Sign Front

The original `absolute_delta` failure remains editor IoU `.349806` and projection
IoU `.353114`, with failed layout comparisons. Offline replay reproduced each
original mask exactly. The native mask selects 8,171 dark green outline pixels
at RGB `(0,64,0)` as well as 3,502 bright glyph pixels; the original editor and
projection masks select only the bright glyphs. The existing `wood_composite`
diagnostic recovers outline coverage. Its agreement is evidence about extraction,
not acceptance or permission to change the contract.

The final fresh holdout used frozen production revision `5234fee`, excluding
`008ca89`, and the existing unmodified `wood_composite` implementation. An
owner-bound WGC preflight passed at 16:58:31, then the front-only matrix began
before 17:00. All eight frames were reliable, background-only 1994x1105 PNGs.
Camera, document, renderer and native palette/style snapshots were recorded
before and after each frame and remained unchanged. Production and tool hashes
also remained unchanged. The complete matrix failed: editor IoU `.167580`,
projection IoU `.165383`, and both layout comparisons failed.

Offline inspection identifies a limitation in that control. The native mask
contains 109 pixels outside the actual board, at local bounds
`[465,360,491,379]`. All 109 are inside the automatically measured
`panel_bounds=[93,195,518,433]`. The visible board is only
`[93,195,426,433]` in that crop. The brown row-span detector merged terrain with
the board, so clipping to its reported panel would retain the pollution.
Manually restricting the diagnostic to the actual board yields native and
projection coverage of 11,915 pixels and IoU `1.0`, with editor IoU `.976094`.
Those post-hoc restrictions do not replace the failed holdout.

The native and editor shown/blank board pixels outside the text rectangle are
identical. The projection has 163 board pixels over the original 20-channel
delta cutoff, with maximum delta 37. Background leakage and projection baseline
stability must both be controlled in a separately frozen future holdout. No
oracle, ROI, threshold or original report was changed to obtain a pass.

Three preparatory failures are retained: raw palette tuple-key serialization,
Python 2 comprehension variable leakage, and a white legacy PrintWindow frame
caused by omitting `MCDEV_NATIVE_CAPTURE_HELPER`. The last was not a WGC failure.
The permanent wrapper now requires the WGC helper and executable before setup.

Actual PNGs inspected include the original native/editor/projection frames and
all three masks, the final WGC preflight, final native/editor/projection shown
frames, and the rejected white PrintWindow frame. The inspection does not expand
front-only evidence into a complete sign matrix.

## Chest Top

The `008ca89` UV candidate passed offline source and generator checks but has no
valid visual positive control. The first unchanged public single-chest fixture
used native target `[6,143,6]` and camera `[6.5,149.5,6.65]`. The native screenshot
has no visible chest; the proxy screenshot has a centered chest. The largest
native signal component was 69 pixels, below the unchanged 1,000-pixel minimum.
The native block and client actor state existed, but the disappearance cause is
not established. The public fixture, typed source and document were preserved.

The permanent harness records an explicit target height offset and retains the
three public fixture plans. A future offset `+8` is available but was never run.
All original chest shape, scale, texture and alignment gates remain unchanged.

## Restoration

All four owned entity sessions are stopped and their game/MCDK processes absent.
No force kill was used. The final independent audit passed: 28 client flags and
28 server flags clear, no projection, workspace, jobs or work in progress,
player restored to its recorded spawn `[1.5,71,-31.5]`, flying false, daylight
cycle restored, HUD restored and reserved native cells cleared. A normal stop
initially exceeded its poll interval; after processes exited normally, a second
stop finalized metadata and removed the owned junction.

The intermediate instance handle count grew from 61,226 to 159,596. The final
WGC instance had 837 handles at the last sample. The cause is unestablished.
No additional live experiments followed the final matrix.
