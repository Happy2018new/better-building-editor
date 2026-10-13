# R13 native water comparison in the visible near section V4b

The unchanged H/L stone/water sources are now visibly present through both
native setters and the full projection. This follows the V3 near/far control:
the new frozen plan explicitly reserves player foot +2 instead of the absent
+24 reference. Every original visibility/readback/source gate passes. Water
side UV, tint/alpha, animation and production rendering remain unaccepted.

| Source | Route | Source/readback gate | Stone envelope pixels | Water envelope pixels |
| --- | --- | --- | ---: | ---: |
| H, depth 0 | native palette | PASS | 215,249 | 206,833 |
| H, depth 0 | native direct | PASS | 215,249 | 206,833 |
| H, depth 0 | full projection | PASS | 215,249 | 206,404 |
| L, depth 3 | native palette | PASS | 215,249 | 31,168 |
| L, depth 3 | native direct | PASS | 215,249 | 31,168 |
| L, depth 3 | full projection | PASS | 215,249 | 31,302 |

Source commit `ab2bbc7`; plan SHA256
`5a79b5a4fb58221269e28b3d968816c7575adbfa86254e5173b45f503786ef1c`.
Geometry plan SHA256
`f910636c905388fabe93da3993259f3bbf915dfea6019308195bbf6664d79d5a`.
Owner `liquid-r13-native-write-v4b`, session
`211f3e3692fc4c0fae79d2a92974cfde`; game PID 56632 / creation
`134363488549295541`, MCDK PID 51980 / creation `134363488546967793`.

The same session performed fresh three-view stone calibration: vertical FOV
66.6, individual fits 66.3 / 66.3 / 66.6, all original gates passing. Fourteen
original PNGs comprise preflight, six stone calibration images, one empty
native baseline and six unchanged H/L palette/direct/full captures. All use
reliable 1994×1105 background WGC; foreground unchanged, no activation, real
input, resize or player-position write. The main source comparison preserves
all 216 initial/cleanup air cells, exact complete 36-cell source neighborhoods
on both sides before/after each frame, stable actual camera and minimum two
render events after each request. The original visibility scorer returns
`OBSERVED`, separately from every render qualification flag remaining false.

The original H native and full PNGs were opened. Both show the same supported
transparent water shape, with the stone and rear terrain visible. The full
projection is brighter and has a different side pattern. Different animated
capture times do not identify a UV or cadence cause; these originals are not
substitutes for independent structural-marker and animation controls.

A separately recorded **post-capture diagnostic** compares blue changed
pixels with the existing fixed source shape, without fitting images, height,
FOV, or thresholds. Its scope is explanatory and does not add a predeclared
acceptance to the original plan. The existing .95 IoU / 3-pixel boundary
conditions remain unchanged:

| Source | Comparison | Mask IoU | Every boundary within 3 pixels |
| --- | --- | ---: | --- |
| H | native direct / fixed 178-byte heights | .984622 | FAIL |
| H | full / fixed 178-byte heights | .986172 | FAIL |
| H | native direct / full | .997278 | FAIL |
| L | native direct / fixed 35-byte heights | .990348 | PASS |
| L | full / fixed 35-byte heights | .986133 | PASS |
| L | native direct / full | .995484 | PASS |

Palette/direct blue masks match at .999913 for H and .999935 for L, both with
the original boundary condition passing. H native has 1,202 offending boundary
pixels concentrated around the top y 328–380; full H has 554. These failures
are retained, together with six derived error overlays. The diagnostic does
not close even complete H/L geometry, much less UV, alpha, animation or the
editor/missing-projection holdouts. No production renderer was altered.

The fixture, source/profile, flow setting, camera, environment, visuals and
observer restored; runtime completed/restored, cleanup and persistence errors
empty. Ready to stopped took 113.538 seconds and creation to stopped 183.619.
Both exact process identities are absent, session stopped, temporary config
removed, frozen source/binary checks unchanged and outer deadline met.

[The immutable archive](evidence/liquid-native-write-r13-v4b/archive-index.json)
contains 193 indexed files / 16,771,108 bytes, including 117 exact-byte source
files, fourteen original PNGs and twelve explicitly derived diagnostic PNGs.
Manifest SHA256 is
`d43ed2405aa85ce8cc184e39134a41d89a914088672ca1144d9866ecf6cde342`.
The incomplete V1, absent far V2 and near/far V3 archives remain unchanged.

Next: keep this proven near position and fresh same-session calibration for
predeclared independent structural side-marker and alpha/background controls.
Investigate the fixed H boundary disagreement independently; preserve its
failure instead of compensating FOV or fitting height to water pixels. Then
accept editor, full/missing projection, wet bodies and animation separately.
