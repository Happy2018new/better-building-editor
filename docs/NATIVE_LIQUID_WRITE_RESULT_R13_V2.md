# R13 native liquid write comparison V2

The controlled experiment completed and restored, producing fourteen reliable
1994×1105 background WGC PNGs. **Both palette and direct SetBlockNew native
water references are visually absent**, for H and L. The corresponding full
projection is visible. The palette-only publication hypothesis is therefore
insufficient; the production writer has not been changed on that basis.

The exact source is `b018534`; plan SHA256 is
`82a14b8aa8b98dfd90f52e56d6e9b76041ac6e30c233fa8bbcdc6989bf4b936e`.
Owner `liquid-r13-native-write-v2`, session
`fe85154cdf3d47849b46ac7ddc3cb440`, game PID 59380 / creation
`134363452064026900`, MCDK PID 57676 / creation `134363452061580849`.
Startup uses the repaired guard `04b073e…` and existing MCDK `b8eb895…`.
Foreground remained unchanged throughout; no activation, input or resize was
sent. The actual world and three-view calibration passed with FOV 66.6;
calibration is projection stone geometry, not native terrain publication.

Every native write preserved the exact built-in source and passed before/after
client/server readback of its complete 36-cell one-block neighborhood. The
initial air and final cleanup regions remain the complete 216 cells. Camera
position, rotation, FOV, viewport and forward were stable, with at least two
actual GameRenderTickEvent advances after each request. Both H and L use the
same cells and NW camera. Native stone and water at y -37/-36 were missing
from the images even though all readbacks matched. Both original H native
PNGs and the corresponding full H PNG were opened for inspection.

The fixed source-derived water envelope has **zero changed pixels** for all
four native captures. Full H has 206,404 water-envelope pixels and full L
31,302; both have 215,249 support-envelope pixels. A moving chicken produced
481/527 changed pixels in the broad H support envelope, illustrating why this
diagnostic threshold alone must not accept a native stone body. L support
envelopes have zero signal. The complete replay returns FAIL, with native
visibility, geometry, UV, transparency, animation and production flags false.

The new plan reserved normal 240, fixture cleanup 270, outer 300 seconds after
actual-world readiness, bounded by exact game creation plus 480 seconds. This
changes only the measured execution reservation; it does not change source,
camera, expected image thresholds or the native 100,000-handle cutoff.
Calibration took 62.660 seconds; the complete write/projection matrix took
50.773. Ready to stopped took 133.100 seconds and creation to stopped 232.724.
The last passive native handle sample is 95,514, below the unchanged cutoff.

All restoration succeeded: both world layers in the 216 reserved cells are
air; flow, camera, source/profile, visual settings, environment and observer
were restored. Exact game and MCDK identities are absent, session stopped,
temporary configuration removed, frozen pack/helper sources unchanged, cleanup
and persistence errors empty, and the outer deadline met. Runtime success
describes completion and restoration, not native liquid rendering acceptance.

The next experiment must isolate native section/loading or camera publication
with a real near-player stone/water positive, rather than repeat the same
palette-versus-direct failure or fit water pixels. User-facing production
liquid support remains gated until trustworthy native references and the
separate editor/projection UV, transparency and animation controls pass.

[The immutable archive](evidence/liquid-native-write-r13-v2/archive-index.json)
maps original absolute runtime references to committed exact-byte copies;
the previous V1 timeout and every older failure remain unchanged.
