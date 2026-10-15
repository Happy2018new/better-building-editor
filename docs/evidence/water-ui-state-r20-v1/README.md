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
This limited visual pass does not qualify the full public fixture matrix.

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

Run `python -X utf8 verify_package.py --pixels` to verify every packaged byte,
reconstruct the exact v6/v7 source closure from the existing r19 and r20
archives plus this resource delta, replay valid editor acceptance, preserve
both failed timing budgets, and recompute diagnostic ROI comparisons. The
script does not start Minecraft or perform desktop input. Raw session
credentials and raw launch responses are excluded. Session IDs, process
identities, original paths, and owner-bound capture receipts remain for
provenance. Some schema-3 receipts record user foreground changes while
explicitly forbidding agent activation and activation fallback. The six formal
editor controls use the earlier schema-2 background-only capture path and
record an unchanged foreground. The granular host archived here is the final v3 revision;
the v2 report retains its original host hash and is a timing observation,
not a claim that its host bytes equal that final revision.
