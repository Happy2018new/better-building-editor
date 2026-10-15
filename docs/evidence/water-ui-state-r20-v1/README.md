# Water UI State Diagnostics, Round 20

This package preserves valid editor-water pixels, instance-dependent native
UI behavior, invalid loading-screen captures, and unresolved timing failures.
Production water remains unqualified. No root product water code, shader,
model, texture, or admission flag was changed for these experiments.

The root reference instance shows ordinary public pool water. A separate v6
instance submits identical water control requests but shows only the stone
supports. Its 23-path resource delta adds exactly the reference portal
resources; shared model/material entries remain equal. A successful native
and candidate world portal draw does not make editor water visible. Thus
resource registration and one successful portal draw are not sufficient.

On the same v6 water dolls, RenderSkeletonModel with the original water pose
and a second pose remains invisible. A temporary RenderEntity call containing
the original pose and a cow identifier displays the original water geometry,
not a cow. Its fixed pool ROI equals the reference water ROI exactly. Restoring
RenderSkeletonModel makes that water absent again. This is an API/state
diagnostic, not a validated product workaround or an established root cause.

V7 uses the same 3,093-file source closure as v6 but the reference launch
configuration. Its first three captures are identical Minecraft loading
screens, despite stable SDK state and fresh WGC timestamps. These captures
are invalid for water acceptance and cannot establish a cold-start failure.
Later, before the parameter experiment changes any call, ordinary water is
visible. Every parameter phase shows the same water ROI. Neither the launch
configuration nor any one call parameter is established as the cause because
startup readiness and elapsed time changed as well.

The six formal v7 editor pool controls have 96,000 independently visible water
pixels, complete section removal/restoration, and restoration RMSE zero.
Opaque south/east side correlations are 0.963751/0.982906, with RGB RMSE
2.58685/1.81785. Mirrored, constant, and wrong-phase controls all reject.
The subsequent 19-case editor batch preserves 92 captures and 54 base control
rows. All 18 applicable section visibility controls and all 15 non-partial
geometry checks pass, including neighbor solids and transparent overlap.
The frozen fence body/rear controls contribute 560/440 eligible pixels.
The same pool side controls pass again. This covers the editor route only;
it does not qualify the full three-route public fixture matrix.

The next editor batch preserves 56 captures for fence, pane, slab, and stairs.
All four fixed-alpha controls pass with six phases each: zero, 0.25, 0.45,
0.75, one, and restored default. Body and rear regions contribute at every
intermediate phase, default restoration has RMSE zero, and geometry context
is unchanged. This report has no non-partial geometry cases, so its generic
geometry gate is false because it has no such observations. The separate
19-case report supplies those editor geometry observations. World alpha
controls and dense animated direction controls remain outstanding.

The same formal batch retains LiquidPreview.advance maximum 230.000019 ms,
above the existing 100 ms limit. The earlier 102-image core batch report and
analysis retain LiquidProjection.advance maximum 168.999910 ms, eight editor
visibility failures, and sixteen world visibility passes. Core report capture
hashes are retained; its 102 PNGs remain in the local runtime directory and
are not included or pixel-replayed by this package.

Two later short granular repeats did not reproduce the long call. Their
Windows CPython 2.7 time.clock values measure high-resolution elapsed wall
time, not CPU time. The GetThreadTimes attempt reports unsupported; its zero
CPU fields are not measured zero. These repeats do not replace either failed
maximum or establish a performance fix. The first incorrectly CPU-labelled
granular report is deliberately excluded.

The 19-case editor batch adds a 434.999943 ms LiquidControls.update failure
at water_style_flow_east_wet, starting 1792077074.389. Its nested RenderPose
and payload maxima are only 1 ms, which does not locate the long call's cause.
The batch's 8 ms preview maximum does not replace the earlier 230 ms failure.
The owner timers measure elapsed wall time and can include scheduling delays;
these samples do not establish exclusive CPU execution time.
The alpha batch adds a 370.000124 ms LiquidControls.update failure at
water_style_wet_oak_slab_wet, starting 1792077519.254. Both requested groups
and registry entries are zero for that call. All four long-call samples
(169, 230, 370, and 435 ms) remain preserved and fail their original limits.

A later world-only nested diagnostic performs 24 full/missing wet/dry
transitions and records a 32 ms LiquidProjection.advance call containing a
31 ms WorldLiquidRenderer.advance child. A second 24-transition repeat adds
native creation/publication/destruction timing and records maxima 7/6/6 ms
for projection/renderer/native creation. Both retained reports use no
screenshots, camera changes, player movement, or desktop input. They record
all calls above 5 ms and restore the owner and wrappers.
The embedded runtime cannot import ctypes, so thread CPU time is unavailable.
This short diagnostic is not a replacement budget run or visual acceptance.

Run `python -X utf8 verify_package.py --pixels` to verify every packaged byte,
reconstruct the exact v6/v7 source closure from the existing r19 and r20
archives plus this resource delta, replay valid editor acceptance, preserve
both failed timing budgets, and recompute diagnostic ROI comparisons. The
script does not start Minecraft or perform desktop input. Raw session
credentials and raw launch responses are excluded. Session IDs, process
identities, original paths, and owner-bound capture receipts remain for
provenance. Some schema-3 receipts record foreground changes while
explicitly forbidding agent activation and activation fallback. The six formal
editor controls use the earlier schema-2 background-only capture path and
record an unchanged foreground. Six receipts in the later 19-case batch
record foreground changes among other processes; the owned game is in the
background both before and after each capture. These original receipts are
retained, and the verifier checks their actual background status instead of
claiming every foreground remained unchanged. The granular host archived here is the final v3 revision;
the v2 report retains its original host hash and is a timing observation,
not a claim that its host bytes equal that final revision.
Likewise, world timing v1 retains its original host hash, while the packaged
world host is the extended v2 revision bound exactly to its own report.
