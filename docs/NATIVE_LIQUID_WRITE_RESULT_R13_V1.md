# R13 native liquid write comparison V1

The single cold launch reached the real world entirely in the background, but
the palette/direct experiment remains **incomplete and NOT_TESTED**. One empty
native baseline PNG was taken. Palette H wrote stone and water and passed the
client/server exact readbacks and two actual render-event barrier, then the
fixed 120-second normal budget expired before its PNG. No palette, direct or
full-projection water image was obtained. The previous native visibility
hypothesis is still unproven; production `WorldAdapter` remains unchanged.

Plan SHA256 is
`c79a3bfaad583f038f71338ccf04726f6e48f92ae8bbb24ef5514f68ab56cefa`,
source commit `7754a7c`, owner `liquid-r13-native-write-v1`, session
`6c8ca4fa1c884ee3be2a4734cb21989e`. The new startup guard SHA256 is
`04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93`.
The actual world first PNG and six shown/hidden calibration PNGs are reliable
1994×1105 WGC frames. Startup and all captures report the foreground unchanged;
no activation, input or resize was sent. Root and water owners opened the real
preflight image. The cube calibration's FOV 66.6 and restoration passed. That
cube is client projection geometry, **not a native terrain write positive**.

Measured phase times in this run were startup 90.067 seconds, actual-world
readiness 12.952, initial WGC 1.464, physical read 1.078, runtime health 2.947,
calibration 89.700, and the incomplete side/write probe 35.999. Calibration
includes the unchanged ten-second weather wait, six captures, independent
stone signal extraction and strict three-view FOV fitting. This consumed most
of the original 120-second work reservation. No timeout or observation was
retrospectively converted into a pass.

Native handles grew from 592 to 66,956 during startup, 70,976 to 85,350 through
calibration, and reached 88,058 in the incomplete probe, below the unchanged
100,000 cutoff. This is substantially different from the previous run's
roughly 800 handles; the background owner is investigating the new hook's
resource behavior before another launch. The measured slowdown and growth
must be addressed in a separate frozen plan, not by replaying this one.

All cleanup gates passed: 216 reserved cells read as air; flow, camera,
visual state, source/profile, environment and the actual render observer were
restored. Exact game PID 10664 / creation `134363433535618248` and MCDK PID
48420 / creation `134363433532360946` are absent. The owned session is stopped,
temporary `.mcdev.json` removed, and all frozen pack/helper files unchanged.
Cleanup and persistence error lists are empty. Ready to stopped took 138.920
seconds and game creation to stopped 235.107, both inside the fixed outer
limits.

The new replay analyzer binds its source and immutable visibility limits
before the first comparison PNG. It uses the built-in source cells to declare
separate stone-support and water-unit envelopes, fixed HUD/crosshair exclusions,
RGB difference greater than 12 and at least 80 signal pixels. This is only a
publication diagnostic; geometry, color, UV, transparency, animation and
production acceptance stay false. Seven host tests cover actual evidence
shapes, missing native pixels, fixed threshold, HUD-only changes, support-only
changes, viewport mismatch, wrapped camera rotation and empty-frame ordering.
The three existing pending-publication/direct-write tests also pass.

Raw plans, receipts, stdout/stderr, eight native PNGs and calibration-derived
images are preserved byte for byte in
[the evidence archive](evidence/liquid-native-write-r13-v1/archive-index.json).
Absolute runtime source references are retained in the original receipts;
the archive index maps original paths to committed immutable copies.
