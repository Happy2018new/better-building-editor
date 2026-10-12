# R10 Occupied Chest Evidence

Recorded on 2026-10-12 in the protected background instance
`e42a61e7599446599e32d1cd0ab2503e`, owner `entities-r10-background`.
This checkpoint changes verification tools and evidence only.

The accepted scope is the fixed public ordinary and default copper double chest,
both north-facing, viewed from above in missing projection. A real native-world
stone occupies the sub/right target cell. The remaining main/left cell retains
its logical double-chest context. Dynamic occupancy, projection restart with the
stone already present, and clearing/recovery all passed. Main-half stone
occupancy, arbitrary real chest completion, other materials/directions and other
views are outside this acceptance.

An independent stone cube fixes the remaining-cell image bounds before any chest
capture. The native full double chest restricted to those bounds is the
logical-half reference. The predeclared quartz plane is four blocks below the
target, identical in shown/hidden controls. Public material, state, actor and
pairing data are preserved while translated to the isolated document.

Original gates remain: at least 1000 native pixels, shape IoU >= 0.82, texture
cosine >= 0.45, relative scale error <= 0.20, center distance <= 3 pixels and
boundary RMS <= 4 pixels. Each native full double contributes 29,758 pixels;
each logical-half reference contributes 14,948 pixels.

| Case | Full/recovered IoU | Full/recovered cosine | Dynamic/initial half IoU | Dynamic/initial half cosine |
| --- | ---: | ---: | ---: | ---: |
| Ordinary north double | 0.998978 | 0.986678 | 0.995097 | 0.976562 |
| Copper north double | 0.998978 | 0.975355 | 0.995097 | 0.954763 |

Scale, center distance and boundary RMS are zero for all accepted comparisons.
Document/history, hide/show state, camera, public source and frozen production
and tools remained unchanged during the run. All 30 full native PNGs and the
separate preflight PNG were opened with `view_image`. Each capture records a
fresh native-resolution Windows.Graphics.Capture frame and unchanged foreground.
The startup guard retained the foreground Edge window and NOACTIVATE game flag.

The native-single diagnostic fails for both cases: center distance is 3.5 pixels;
copper cosine is 0.151534. A real single plus the remaining ghost passes the
aggregate shape gates but visibly has a central gap, and the copper single has a
different texture. These controls are diagnostic only and do not establish
arbitrary real chest completion. R7/R8/R9 failures remain preserved, and rejected
chest candidate `008ca89` is not merged.

The independent read-only restoration audit and final cleanup audit passed:
foot `[0.5, 73.0, 0.5]`, flight capability true, flying false, rotation within
0.02 degrees of the recorded baseline, no temporary client/server flags, no
projection entities and closed workspace. No corrective audit teleport occurred.
The instance was stopped after quiet resource growth was observed. The final
one-second audit measured 286,345 handles before/after. This is a resource
observation with no attribution to production rendering or capture.

Raw evidence stays under the instance's `artifacts/chest-occupied-r10-public-v1`.
`tools/data/entities_visual_acceptance_r10.json` records hashes and replayed
metrics. Reproduce offline with a fresh output path:

```powershell
py -3 tools/pack_chest_occupied_evidence_r10.py C:/Users/Happy2018new/.pyreact-debug/instances/e42a61e7599446599e32d1cd0ab2503e/artifacts <fresh-manifest.json> --session C:/Users/Happy2018new/.pyreact-debug/instances/e42a61e7599446599e32d1cd0ab2503e/session.json
```

The packer verifies captured PNG hashes and standalone metadata, original gates,
frozen oracle/registry fingerprints, actual occupancy states, restoration and
stopped-session provenance, then recomputes the lifecycle and diagnostic metrics
from PNGs in a temporary directory. It never writes into the raw run.
