# R13 native water near/far section diagnostic V3

Both native write routes visibly publish the unchanged stone/water source at
player foot +2. The same source at foot +24 remains visually absent. This is
a decisive native positive control, not liquid UV, transparency, animation or
production acceptance. It rules out a palette-only setter explanation for the
previous blank references. The experiment does not uniquely establish why the
high terrain section is absent.

| Height above foot | Setter | Neutral stone pixels | Stone envelope coverage | Wet blue pixels |
| --- | --- | ---: | ---: | ---: |
| +2 | direct SetBlockNew | 215,249 | 1.0 | 206,442 |
| +2 | WorldAdapter palette | 215,249 | 1.0 | 206,455 |
| +24 | direct SetBlockNew | 22 | 0.000102 | 0 |
| +24 | WorldAdapter palette | 0 | 0.0 | 0 |

Source commit `48555db`; frozen plan SHA256
`eeefd53faa05e0daf1dbc8410bdcc83ad0c7e32bd03a41f0e82c9817c9ab58db`.
Owner `liquid-r13-native-sections-v3`, session
`99ebd504de124b53ace65eecbb51e37f`, game PID 65480 / creation
`134363472616491558`, MCDK PID 60920 / creation `134363472613854527`.

The matrix produced twelve native controls and one preflight PNG using reliable
1994×1105 background WGC. Foreground stayed unchanged; no activation, desktop
input, resize or player-position write was sent. No editor or projection was
created. Each of the two heights has empty, direct dry/wet, palette dry/wet and
restored frames. The dry near control visibly shows the stone; the wet near
control visibly shows blue water with terrain behind it. The high dry image
shows grass, HUD and a chicken without the source stone.

The predeclared body gate requires at least 1,000 neutral changed pixels and
50% spatial coverage of the source-derived stone envelope. Wet-minus-dry must
have at least eighty blue changed pixels in the separate source-derived water
envelope. The new gate rejects sparse chicken pixels that confused a previous
broad visibility diagnostic. The prior FOV 66.6 is only a generous publication
envelope hypothesis; no geometry or UV is qualified from that prior.

Each frame checks the exact complete 36-cell one-block source neighborhood on
both client and server before and after capture, with a stable actual camera
and at least two render events after each write. Both 216-cell air reservations
were checked before writing, and all 432 cells were cleared and read back on
cleanup. Original source state, camera, visual settings, liquid-flow setting,
environment and render observer were restored. Runtime completed/restored and
all cleanup/persistence errors are empty. Ready to stopped took 88.980 seconds;
creation to stopped took 206.140 seconds. Both exact process identities are
absent, session stopped, temporary configuration removed and frozen sources
unchanged. Runtime completion is separate from the per-height visibility
results above.

The next side-rendering diagnostic explicitly reserves the proven near +2
position and performs fresh same-session stone/FOV calibration. It keeps the
failed high controls and every rendering threshold. Production water remains
disabled until separate editor/projection shape, UV, translucency and animation
acceptance passes.

[The immutable archive](evidence/liquid-native-sections-r13-v3/archive-index.json)
contains all original run receipts, plans, thirteen PNGs and 118 exact-byte
source dependencies (173 files, 19,611,997 bytes). Its manifest SHA256 is
`3858c3fbe7448853c6ddf4060bb3dd8f8f1360a1779341b0000ebc47e588efa1`.
