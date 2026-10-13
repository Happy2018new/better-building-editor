# Native Snow H0 V1F: Complete Matrix, Projected Poppy Positive Control Failed

The one released original-texture V1F run completed all eight native and
projection state captures in 132.21816719998606 seconds. Native plant-only
and covered h0 show a red poppy. Projected plant-only shows no poppy and
projected covered h0 shows only snow. The native plant positive control
passed; the projected plant positive control failed. Covered-minus-snow
therefore cannot establish accepted projected plant contribution. The
runtime completed rc0 and all restoration checks passed, but plant pixels,
offsets and production are not accepted. Alpha was not run.

| Fixed ROI observation | Native | Projection |
| --- | ---: | ---: |
| Plant minus blank | 12370 px | 0 px |
| Snow minus blank | 25956 px | 25846 px |
| Covered minus snow | 10344 px | 0 px |
| Plant positive control, minimum 80 px | pass | fail |

The fixed crop `(498,276,1495,828)`, difference threshold 20 and qualified
stone-cell ROI were identical across this matrix. The visible stone/blank
qualification gave 113706 filled component pixels. Snow-only native versus
projection has precision and recall 1 within the frozen three-pixel
tolerance. The coarse covered-area comparison also returns a diagnostic
match because most area is snow; that flag does not override the absent
plant positive control. Global `positive_controls_passed` and
`diagnostic_matches` are false. No renderer cause is inferred.

Preparation `7a6a6b467beb889e888ad3d0ab6759f0ae1723c1` passed minimal independent
incremental QA and 28 focused tests in 33.900 seconds. The formal product
follow path stayed enabled. Before each nonblank projected first capture,
the probe observed actual actor GetPos settle at `(0.5,-59,0.5)`, at least
two actual render events, unit part scales and exact logical origin
`(5,-49,5)`. Actual native offset submissions transitioned from initial
`(1,-1.5,1)` to compensated `(-5,10,-5)` with boolean success for all parts.
Actor/model/source/parts/scales, settled physical anchor and compensated
world origin remained stable before and after each capture. Offset
arguments and native acknowledgments are submission evidence; no public
offset getter or GPU readback is claimed.

The first camera candidate yaw+180 qualified with actual GetForward cosine
`0.9999999999998105`; the second candidate was not requested. Camera pose,
FOV 60, SDK screen 499x277, PNG 1994x1105 and unchanged player foot
`(0.5,-60,0.5)` were retained. The first scheduled original is black and the
first SDK-ready original remains a loading overlay. Actual application
queries at T72.7866563/T75.1461128 changed from uninitialized to actual
owner/session/bridge/ready/HUD. Its separate first application original
shows grass world, hand and HUD. All 13 original PNGs were opened directly
after the completed runtime; none was replaced.

Session `fea09f3d993142c1b1f4aa4e2263516b` owned game PID 12648 creation
`134363320620951138` and MCDK PID 20832 creation `134363320618934992`.
The supervisor verified capacity and made one launch under unchanged
240/190/50/90 bounds, with no deadline overrun. Native layers/world state
and unchanged player were verified restored. Saved follow camera position,
equivalent rotation, locks and FOV matched actual readback across render
events before its journal was cleared. The transparent offset factory and
render observer were removed. Phase and supervisor cleanup errors are
empty. Exact owned handles were closed and independently verified absent.
Three host backups, own texture absence, native texture and all 1432
behavior/resource hashes were independently verified restored. WGC was
released immediately after closure.

Passive game handle samples were 669/672/695 before readiness, then fresh
864 baseline and 871/870/869. No rapid growth trigger fired; resource health
remains unaccepted. The existing 29 positive / 232 height / 8 negative
acceptance and empty position registry remain unchanged. V1D stayed unrun,
V1E failure stayed intact, and no further candidate or alpha launch followed.

The minimal result archive preserves 57 runtime/instance/executed-plan
files plus index and independent cleanup verification. Full source and plan
inputs remain in the exact V1F preparation freeze rather than duplicated.

| Pin | SHA-256 |
| --- | --- |
| Executed original plan | `902e584b934200a8047791692b349074d18d0f275d4ce524b149b22497e6cc48` |
| Frozen plan index | `686f7f71e1278bfbaaff4f45a444643d6180d92747e1851a6867151c267976ef` |
| Result index | `5f9234781b4e0fb28e6a90756524a4c7bd6427f3f32a4cb0a40443a833e179f3` |
| Cleanup verification | `ef6f12a966d2800b3764c9b27c7cd6f1c7df4db979e919e47ccfd0e65f0eb9a4` |
